import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import zipfile
from database.connection import SessionLocal
from database.repository import save_scan, get_scans, get_scan_details
from api.schemas import (AppliedProposalResponse, ExplanationResponse, FileAnalysisResponse, FindingContextRequest, FixProposalResponse, ProjectAnalysisResponse, ScanHistoryResponse, ScanDetailResponse, FixResponse)
from fastapi import FastAPI, UploadFile, File, Form, HTTPException  # fastapi - package ,, FastAPI - class ,, app - our application instanc
from engine import BugslashEngine
from models.analyzer_error import AnalyzerExecutionError
from fixing.fix_engine import FindingNotFoundError, FixEngine
from fixing.llm_assistance import ProposalValidationError, explain_finding, propose_finding_fix, verify_proposal_source
from llm.ollama_client import LLMProviderError, OllamaClient
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError

from fastapi.middleware.cors import CORSMiddleware

# creates our fast api application
app = FastAPI(
    title = "BUGSLASH API",
    description = "Multi-language intelligent bug detection system",
    version = "1.0.0"
)


# CORS is added to connect between two different paths like my backend will be on localhost:abcd and my frontend will be on localhost:aaja so it will help both communicate
# CORS is not authentication / security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://bug-slash.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = BugslashEngine()


# known as route decorator that tells the FastAPI that when someone sends a GET request to / use the fucntion below
@app.get("/")
# function that runs when he request arrives
def home():
    return {
        "message": "BUGSLASH API is running"
    }

@app.get("/health")
def health_check():
    return{
        "status": "healthy"
        }

@app.get("/scans", response_model=ScanHistoryResponse)
def scan_history():
    db = SessionLocal()

    try:
        scans = get_scans(db)

        return{
            "scans": scans
        }
    finally:
        db.close()

@app.get("/scans/{scan_id}", response_model=ScanDetailResponse)
def scan_details(scan_id: int):
    db = SessionLocal()

    try:
        scan = get_scan_details(db, scan_id)

        if scan is None:
            raise HTTPException(
                status_code=404,
                detail=f"Scan {scan_id} not found."
            )

        return scan

    finally:
        db.close()

@app.post("/analyze", response_model = FileAnalysisResponse) # post because we are sending file to server


def analyze_file(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
        status_code=400,
        detail="No filename provided"
    )

    language = engine.language_detector.detect(file.filename)

    if language is None:
        raise HTTPException(
            status_code = 400,
            detail = f"Unsupported File type: {file.filename}"
        )

    upload_name = Path(file.filename.replace(chr(92), "/")).name
    temporary_directory = tempfile.TemporaryDirectory(
        prefix="bugslash-analysis-",
        dir=Path(__file__).resolve().parent.parent,
    )
    temporary_path = Path(temporary_directory.name) / upload_name
    with temporary_path.open("wb") as temporary_file:
        shutil.copyfileobj(file.file, temporary_file)

    try:
        result = engine.analyze_file(str(temporary_path))

        result ["filename"] = file.filename
        result ["file"] = file.filename

        for finding in result["findings"]:
            finding.file = file.filename

        for verification_result in result["verification_results"]:
            verification_result["finding"].file = file.filename

        return result
    except AnalyzerExecutionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        temporary_directory.cleanup()



fix_engine = FixEngine()


MAX_FIX_FILE_SIZE = 5 * 1024 * 1024


@app.post("/fix", response_model=FixResponse)
async def fix_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    language = engine.language_detector.detect(file.filename)

    if not fix_engine._language(Path(file.filename)):
        raise HTTPException(status_code=400, detail="Unsupported source type for automatic fixing.")

    contents = await file.read(MAX_FIX_FILE_SIZE + 1)
    if len(contents) > MAX_FIX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Source files must be 5 MB or smaller.",
        )
    try:
        contents.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Source must be UTF-8 encoded text.",
        ) from exc

    with tempfile.TemporaryDirectory(
        dir=Path(__file__).resolve().parent.parent
    ) as temporary_dir:
        temporary_path = Path(temporary_dir) / _safe_upload_name(file.filename)
        temporary_path.write_bytes(contents)

        try:
            result = await run_in_threadpool(fix_engine.fix_file, str(temporary_path))
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="A configured language tool timed out.") from exc
        except (RuntimeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=500, detail="Fixing or re-analysis failed. Check backend logs for details.") from exc

        upload_name = Path(file.filename).name
        result["filename"] = upload_name
        for finding_group in ("original_findings", "remaining_findings"):
            result[finding_group] = [
                {
                    "code": finding.get("code"),
                    "message": finding.get("message", ""),
                    "filename": upload_name,
                    "location": finding.get("location") or {"row": 1, "column": 1},
                }
                for finding in result[finding_group]
            ]
        result["fixed_code"] = result.get("fixed_code") if result.get("success") else None

        return result



MAX_LLM_CONTEXT_SIZE = 1024 * 1024
MAX_FINDING_PAYLOAD_SIZE = 8192


def _safe_upload_name(filename: str) -> str:
    return Path(filename.replace("\\", "/")).name


async def _read_source_upload(file: UploadFile, limit: int = MAX_FIX_FILE_SIZE) -> tuple[bytes, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    contents = await file.read(limit + 1)
    if len(contents) > limit:
        raise HTTPException(status_code=413, detail=f"Source file must be {limit // (1024 * 1024)} MB or smaller.")
    try:
        contents.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Source must be UTF-8 encoded text.") from exc
    return contents, _safe_upload_name(file.filename)


def _parse_finding_context(raw: str) -> FindingContextRequest:
    if len(raw.encode("utf-8")) > MAX_FINDING_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Finding context is too large.")
    try:
        return FindingContextRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Finding context is invalid.") from exc


def _validate_finding_file(finding: FindingContextRequest, filename: str) -> None:
    if _safe_upload_name(finding.file) != filename:
        raise HTTPException(status_code=400, detail="Finding context does not belong to the uploaded source file.")
    detected = engine.language_detector.detect(filename)
    if detected is None or detected != finding.language.lower():
        raise HTTPException(status_code=400, detail="Finding language does not match the uploaded source file.")
    if finding.line < 1 or finding.column < 0:
        raise HTTPException(status_code=400, detail="Finding location is invalid.")


def _rename_fix_findings(result: dict, filename: str) -> dict:
    result["filename"] = filename
    for group in ("original_findings", "resolved_findings", "remaining_findings", "introduced_findings"):
        for finding in result.get(group, []):
            finding["filename"] = filename
    if result.get("selected_finding"):
        result["selected_finding"]["filename"] = filename
    return result


@app.post("/fix/finding", response_model=FixResponse)
async def fix_one_finding(
    file: UploadFile = File(...),
    finding: str = Form(...),
):
    contents, filename = await _read_source_upload(file)
    context = _parse_finding_context(finding)
    _validate_finding_file(context, filename)
    if not fix_engine._language(Path(filename)):
        raise HTTPException(status_code=400, detail="Unsupported source type for deterministic finding-level fixes.")
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as directory:
        temporary_path = Path(directory) / filename
        temporary_path.write_bytes(contents)
        try:
            result = await run_in_threadpool(fix_engine.fix_finding, str(temporary_path), context.model_dump())
        except FindingNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="A configured language tool timed out while fixing this finding.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail="Finding fix or verification failed.") from exc
        result["fixed_code"] = result.get("fixed_code") if result.get("success") else None
        return _rename_fix_findings(result, filename)


@app.post("/llm/explain", response_model=ExplanationResponse)
async def explain_one_finding(file: UploadFile = File(...), finding: str = Form(...)):
    contents, filename = await _read_source_upload(file, MAX_LLM_CONTEXT_SIZE)
    context = _parse_finding_context(finding)
    _validate_finding_file(context, filename)
    try:
        explanation = await run_in_threadpool(explain_finding, context.model_dump(), contents.decode("utf-8"))
    except (ProposalValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Local LLM explanation failed. Static analysis remains available.") from exc
    client = OllamaClient()
    return {"provider": client.provider_name, "model": client.model, "finding": context, **explanation}


@app.post("/fix/propose", response_model=FixProposalResponse)
async def propose_finding_fix_route(file: UploadFile = File(...), finding: str = Form(...)):
    contents, filename = await _read_source_upload(file, MAX_LLM_CONTEXT_SIZE)
    context = _parse_finding_context(finding)
    _validate_finding_file(context, filename)
    source = contents.decode("utf-8")
    try:
        proposal = await run_in_threadpool(propose_finding_fix, context.model_dump(), source)
    except (ProposalValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Local LLM proposal failed. No source was changed.") from exc
    client = OllamaClient()
    return {"provider": client.provider_name, "model": client.model, "finding": context, **proposal}


@app.post("/fix/proposal/apply", response_model=AppliedProposalResponse)
async def apply_reviewed_proposal(
    file: UploadFile = File(...),
    finding: str = Form(...),
    proposed_code: str = Form(...),
    source_sha256: str = Form(...),
):
    contents, filename = await _read_source_upload(file, MAX_LLM_CONTEXT_SIZE)
    context = _parse_finding_context(finding)
    _validate_finding_file(context, filename)
    if context.language.lower() != "python":
        raise HTTPException(status_code=400, detail="Verified proposal application currently supports Python only.")
    original = contents.decode("utf-8")
    try:
        verify_proposal_source(original, proposed_code, source_sha256, context.model_dump())
    except ProposalValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as directory:
        temporary_path = Path(directory) / "accepted_proposal.py"
        temporary_path.write_text(proposed_code, encoding="utf-8")
        before_path = Path(directory) / "original.py"
        before_path.write_text(original, encoding="utf-8")
        try:
            before = await run_in_threadpool(fix_engine._analyze, before_path)
            if FixEngine._match_selected(before, context.model_dump()) is None:
                raise HTTPException(status_code=409, detail="The selected finding no longer matches the original source.")
            compile(proposed_code, filename, "exec")
        except SyntaxError:
            safe_before = [fix_engine._public_finding(item) | {"filename": filename} for item in before]
            return {
                "success": True, "status": "FIX_FAILED", "verification_status": "FAILED",
                "message": "The accepted proposal did not pass Python syntax verification.",
                "fixed": False, "original_count": len(before), "resolved_count": 0, "remaining_count": len(before),
                "introduced_count": 0, "resolved_codes": [],
                "original_findings": safe_before, "resolved_findings": [], "remaining_findings": safe_before, "introduced_findings": [],
                "filename": filename, "fixed_code": None,
                "selected_finding": {"code": context.category, "message": context.message, "filename": filename, "location": {"row": context.line, "column": context.column}},
                "selected_resolved": False,
                "scope_note": "The proposal was not returned as corrected source because verification failed.",
                "proposal_accepted": True,
            }
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="Static verification timed out.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail="Static verification failed.") from exc
        try:
            after = await run_in_threadpool(fix_engine._analyze, temporary_path)
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="Static verification timed out.") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail="Static verification failed.") from exc

        resolved, codes = FixEngine._resolved_findings(before, after, original.splitlines(), proposed_code.splitlines(), 'python')
        selected_resolved = not FixEngine._selected_finding_remains(
            after, context.model_dump(), original.splitlines(), proposed_code.splitlines(), "python"
        )
        if not after and selected_resolved:
            status, verification_status = "FIX_VERIFIED", "VERIFIED"
            message = "The selected proposal passed Ruff re-analysis and Python syntax verification."
        elif selected_resolved:
            status, verification_status = "PARTIALLY_FIXED", "PARTIAL"
            message = "The selected finding resolved, but other Ruff findings remain."
        else:
            status, verification_status = "VERIFICATION_INCOMPLETE", "INCOMPLETE"
            message = "The proposal was accepted, but the selected finding remains after verification."
        return {
            "success": True, "status": status, "verification_status": verification_status,
            "message": message, "fixed": original != proposed_code, "original_count": len(before),
            "resolved_count": resolved, "remaining_count": len(after),
            "introduced_count": max(0, len(after) - len(before) + resolved), "resolved_codes": codes,
            "original_findings": [fix_engine._public_finding(item) | {"filename": filename} for item in before],
            "resolved_findings": [fix_engine._public_finding(item) | {"filename": filename} for item in FixEngine._finding_differences(before, after, original.splitlines(), proposed_code.splitlines(), 'python')[0]],
            "remaining_findings": [fix_engine._public_finding(item) | {"filename": filename} for item in after],
            "introduced_findings": [fix_engine._public_finding(item) | {"filename": filename} for item in FixEngine._finding_differences(before, after, original.splitlines(), proposed_code.splitlines(), 'python')[1]],
            "filename": filename, "fixed_code": proposed_code, "selected_finding": {"code": context.category, "message": context.message, "filename": filename, "location": {"row": context.line, "column": context.column}},
            "selected_resolved": selected_resolved,
            "scope_note": "The proposal was explicitly accepted and verified with Ruff and Python syntax compilation; tests were not run.",
            "proposal_accepted": True,
        }


# this part for posting the zip file on to the api

@app.post("/analyze-project", response_model = ProjectAnalysisResponse)

def analyze_project(file:UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
        status_code=400,
        detail="No filename provided."
    )

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
        status_code=400,
        detail="Project upload must be a .zip file."
    )

    # creating temporary directory ... as soon as the work is finished, its deleted
    with tempfile.TemporaryDirectory() as temp_dir:

        zip_path = Path(temp_dir) / file.filename

        with open(zip_path, "wb") as buffer:
            # shutil is used here to copy the uploaded ZIP file onto the disk
            shutil.copyfileobj(
                file.file,
                buffer
            )

        # for extracting the zip file
        project_dir = Path(temp_dir) / "project"
        project_dir.mkdir()


        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(project_dir)

        except zipfile.BadZipFile:
            raise HTTPException(
                status_code = 400,
                detail="Uploaded file is not a valid ZIP archive"
            )

        try:
            result = engine.analyze_project(
                str(project_dir)
        )

        except AnalyzerExecutionError as error:
            raise HTTPException(status_code=422, detail=f"Project analysis incomplete: {error}") from error
        except Exception as error:
            raise HTTPException(
                status_code = 500,
                detail = f"Project Analysis failed: {error}"
            )

        for item in result:

            source_path = Path(item["file"])

            try:
                relative_path = source_path.relative_to(project_dir)
            except ValueError:
                relative_path = source_path.name

            item["file"] = str(relative_path)

            for finding in item["findings"]:
                finding.file = str(relative_path)

            for verification_result in item ["verification_results"]:
                verification_result["finding"].file = str(relative_path)

        db = SessionLocal()

        try:
            scan_id = save_scan(
                db,
                file.filename,
                result
                )
        finally:
            db.close()

        return {
            "filename": file.filename,
            "scan_id": scan_id,
            "files_analyzed": len(result),
            "results": result
        }
