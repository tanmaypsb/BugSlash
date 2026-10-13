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


class FixLocationResponse(BaseModel):
    row: int
    column: int


class FixFindingResponse(BaseModel):
    code: str | None
    message: str
    filename: str
    location: FixLocationResponse


class FindingContextRequest(BaseModel):
    language: str
    file: str
    line: int
    column: int
    category: str
    severity: str
    message: str
    analyzer: str
    confidence: float = 0.0


class FixResponse(BaseModel):
    success: bool
    status: str
    verification_status: str
    message: str
    fixed: bool
    original_count: int
    resolved_count: int
    remaining_count: int
    introduced_count: int = 0
    resolved_codes: list[str]
    original_findings: list[FixFindingResponse]
    resolved_findings: list[FixFindingResponse] = []
    remaining_findings: list[FixFindingResponse]
    introduced_findings: list[FixFindingResponse] = []
    filename: str
    fixed_code: str | None
    selected_finding: FixFindingResponse | None = None
    selected_resolved: bool | None = None
    scope_note: str | None = None


class ExplanationResponse(BaseModel):
    provider: str
    model: str
    finding: FindingContextRequest
    source_context: str
    meaning: str
    why_reported: str
    impact: str
    suggested_correction: str
    correction_kind: str


class FixProposalResponse(BaseModel):
    provider: str
    model: str
    finding: FindingContextRequest
    summary: str
    risks: list[str]
    diff: str
    proposed_code: str
    source_sha256: str
    review_required: bool
    status: str


class AppliedProposalResponse(FixResponse):
    proposal_accepted: bool


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
