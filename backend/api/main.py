import os
import shutil
import tempfile
from pathlib import Path
import zipfile
from database.connection import SessionLocal
from database.repository import save_scan, get_scans, get_scan_details
from api.schemas import FileAnalysisResponse, ProjectAnalysisResponse, ScanHistoryResponse, ScanDetailResponse
from fastapi import FastAPI, UploadFile, File, HTTPException  # fastapi - package ,, FastAPI - class ,, app - our application instanc
from engine import BugslashEngine 
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
    allow_origins=["http://localhost:5173"],
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

    suffix = Path(file.filename).suffix # provides the .py/.cpp/.go extension to the language detector

    # doing with temporary file cause we are giving the api the uploaded file 
    # not a path like /user/tanmay/libary/file.py  so we need to to temporary upload a file  
    with tempfile.NamedTemporaryFile(
        delete = False,
        suffix = suffix,
        dir = Path(__file__).resolve().parent.parent,
    ) as temporary_file:

        shutil.copyfileobj(
            file.file,
            temporary_file
        )

        temporary_path = temporary_file.name

    try:
        result = engine.analyze_file(temporary_path)

        result ["filename"] = file.filename
        result ["file"] = file.filename

        for finding in result["findings"]:
            finding.file = file.filename

        for verification_result in result["verification_results"]:
            verification_result["finding"].file = file.filename

        return result

    finally:
        os.remove(temporary_path)    
    
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
