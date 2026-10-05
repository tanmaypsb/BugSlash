from pydantic import BaseModel
from datetime import datetime


class FindingResponse(BaseModel):
    language: str
    file: str
    line: int
    column: int
    category: str
    severity: str
    message: str
    analyzer: str
    confidence: float


class VerificationResponse(BaseModel):
    verified: bool
    status: str
    message: str


class VerificationResultResponse(BaseModel):
    finding: FindingResponse
    status: str
    confidence: float
    evidence: VerificationResponse


class FileAnalysisResponse(BaseModel):
    file: str
    language: str
    findings: list[FindingResponse]
    verification: VerificationResponse | None
    verification_results: list[VerificationResultResponse]

class ProjectFileResultResponse(BaseModel):
    file: str
    language: str
    findings: list[FindingResponse]
    verification: VerificationResponse | None
    verification_results: list[VerificationResultResponse]

class ProjectAnalysisResponse(BaseModel):
    filename: str
    scan_id: int
    files_analyzed: int
    results: list[ProjectFileResultResponse]


class ScanSummaryResponse(BaseModel):
          
    id: int
    project_id: int
    status: str
    files_analyzed: int
    created_at: datetime


class ScanHistoryResponse(BaseModel):
    scans: list[ScanSummaryResponse]    

class ScanDetailFindingResponse(BaseModel):
    id: int
    language: str
    file: str
    line: int
    column: int
    category: str
    severity: str
    message: str
    analyzer: str
    confidence: float
    verification_status: str | None


class ScanDetailResponse(BaseModel):
    id: int
    project_id: int
    status: str
    files_analyzed: int
    created_at: datetime
    findings: list[ScanDetailFindingResponse]    