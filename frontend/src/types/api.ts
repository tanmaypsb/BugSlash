// Types matching the FastAPI/Pydantic response schemas from /openapi.json

// --- Health ---
export interface HealthResponse {
  status: string;
}

// --- Findings ---
export interface FindingResponse {
  language: string;
  file: string;
  line: number;
  column: number;
  category: string;
  severity: string;
  message: string;
  analyzer: string;
  confidence: number;
}

export interface ScanDetailFindingResponse {
  id: number;
  language: string;
  file: string;
  line: number;
  column: number;
  category: string;
  severity: string;
  message: string;
  analyzer: string;
  confidence: number;
  verification_status: string | null;
}

// --- Verification ---
export interface VerificationResponse {
  verified: boolean;
  status: string;
  message: string;
}

export interface VerificationResultResponse {
  finding: FindingResponse;
  status: string;
  confidence: number;
  evidence: VerificationResponse;
}

// --- File Analysis (POST /analyze) ---
export interface FileAnalysisResponse {
  file: string;
  language: string;
  findings: FindingResponse[];
  verification: VerificationResponse | null;
  verification_results: VerificationResultResponse[];
}

// --- Project Analysis (POST /analyze-project) ---
export interface ProjectFileResultResponse {
  file: string;
  language: string;
  findings: FindingResponse[];
  verification: VerificationResponse | null;
  verification_results: VerificationResultResponse[];
}

export interface ProjectAnalysisResponse {
  filename: string;
  scan_id: number;
  files_analyzed: number;
  results: ProjectFileResultResponse[];
}

// --- Scan History (GET /scans) ---
export interface ScanSummaryResponse {
  id: number;
  project_id: number;
  status: string;
  files_analyzed: number;
  created_at: string;
}

export interface ScanHistoryResponse {
  scans: ScanSummaryResponse[];
}

// --- Scan Detail (GET /scans/{scan_id}) ---
export interface ScanDetailResponse {
  id: number;
  project_id: number;
  status: string;
  files_analyzed: number;
  created_at: string;
  findings: ScanDetailFindingResponse[];
}

// --- Validation Error ---
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

export interface HTTPValidationError {
  detail: ValidationError[];
}
