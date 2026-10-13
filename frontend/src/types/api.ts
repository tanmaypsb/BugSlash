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

export interface FixFindingResponse {
  code: string | null;
  message: string;
  filename: string;
  location: {
    row: number;
    column: number;
  };
}

export type FixStatus =
  | 'FIX_VERIFIED'
  | 'PARTIALLY_FIXED'
  | 'NO_CHANGES'
  | 'VERIFICATION_INCOMPLETE'
  | 'FIX_FAILED'
  | 'REVIEW_REQUIRED';

export interface FixResponse {
  success: boolean;
  status: FixStatus;
  verification_status: 'VERIFIED' | 'PARTIAL' | 'INCOMPLETE' | 'FAILED' | 'NOT_NEEDED';
  message: string;
  fixed: boolean;
  original_count: number;
  resolved_count: number;
  remaining_count: number;
  introduced_count: number;
  resolved_codes: string[];
  original_findings: FixFindingResponse[];
  resolved_findings: FixFindingResponse[];
  remaining_findings: FixFindingResponse[];
  introduced_findings: FixFindingResponse[];
  filename: string;
  fixed_code: string | null;
  selected_finding?: FixFindingResponse | null;
  selected_resolved?: boolean | null;
  scope_note?: string | null;
  proposal_accepted?: boolean;
}

export interface FindingExplanationResponse {
  provider: string;
  model: string;
  finding: FindingResponse;
  source_context: string;
  meaning: string;
  why_reported: string;
  impact: string;
  suggested_correction: string;
  correction_kind: 'deterministic' | 'uncertain' | 'review_required';
}

export interface FixProposalResponse {
  provider: string;
  model: string;
  finding: FindingResponse;
  summary: string;
  risks: string[];
  diff: string;
  proposed_code: string;
  source_sha256: string;
  review_required: true;
  status: 'PROPOSAL_READY';
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
