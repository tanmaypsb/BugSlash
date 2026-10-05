import type {
  HealthResponse,
  ScanHistoryResponse,
  ScanDetailResponse,
  FileAnalysisResponse,
  ProjectAnalysisResponse,
} from '../types/api';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isFinding(value: unknown): boolean {
  return (
    isRecord(value) &&
    isString(value.language) &&
    isString(value.file) &&
    isNumber(value.line) &&
    isNumber(value.column) &&
    isString(value.category) &&
    isString(value.severity) &&
    isString(value.message) &&
    isString(value.analyzer) &&
    isNumber(value.confidence)
  );
}

function isScanSummary(value: unknown): boolean {
  return (
    isRecord(value) &&
    isNumber(value.id) &&
    isNumber(value.project_id) &&
    isString(value.status) &&
    isNumber(value.files_analyzed) &&
    isString(value.created_at)
  );
}

const isHealthResponse = (value: unknown): value is HealthResponse =>
  isRecord(value) && isString(value.status);
const isScanHistoryResponse = (value: unknown): value is ScanHistoryResponse =>
  isRecord(value) &&
  Array.isArray(value.scans) &&
  value.scans.every(isScanSummary);
const isScanDetailResponse = (value: unknown): value is ScanDetailResponse =>
  isRecord(value) &&
  isNumber(value.id) &&
  isNumber(value.project_id) &&
  isString(value.status) &&
  isNumber(value.files_analyzed) &&
  isString(value.created_at) &&
  Array.isArray(value.findings) &&
  value.findings.every(
    (finding) =>
      isFinding(finding) &&
      isRecord(finding) &&
      isNumber(finding.id) &&
      (finding.verification_status === null ||
        isString(finding.verification_status))
  );
const isFileAnalysisResponse = (value: unknown): value is FileAnalysisResponse =>
  isRecord(value) &&
  isString(value.file) &&
  isString(value.language) &&
  Array.isArray(value.findings) &&
  value.findings.every(isFinding) &&
  (value.verification === null || isRecord(value.verification)) &&
  Array.isArray(value.verification_results);
const isProjectAnalysisResponse = (
  value: unknown
): value is ProjectAnalysisResponse =>
  isRecord(value) &&
  isString(value.filename) &&
  isNumber(value.scan_id) &&
  isNumber(value.files_analyzed) &&
  Array.isArray(value.results) &&
  value.results.every(
    (result) =>
      isRecord(result) &&
      isString(result.file) &&
      isString(result.language) &&
      Array.isArray(result.findings) &&
      result.findings.every(isFinding) &&
      (result.verification === null || isRecord(result.verification)) &&
      Array.isArray(result.verification_results)
  );

class ApiError extends Error {
  status: number;
  statusText: string;

  constructor(status: number, statusText: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
  }
}

/**
 * Centralized fetch wrapper with error handling, timeout, and abort support.
 */
async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 30000,
  signal?: AbortSignal,
  isExpectedResponse?: (value: unknown) => value is T
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Combine user signal with timeout signal
  const combinedSignal = signal
    ? composeAbortSignals(signal, controller.signal)
    : controller.signal;

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: combinedSignal,
    });

    if (!response.ok) {
      let errorMessage = `Request failed: ${response.status} ${response.statusText}`;

      try {
        const errorBody: unknown = await response.json();
        if (isRecord(errorBody) && typeof errorBody.detail === 'string') {
          errorMessage = errorBody.detail;
        } else if (isRecord(errorBody) && Array.isArray(errorBody.detail)) {
          const messages = errorBody.detail
            .filter(isRecord)
            .map((item) => item.msg)
            .filter((message): message is string => typeof message === 'string');
          if (messages.length) errorMessage = messages.join('; ');
        }
      } catch {
        // Response body wasn't JSON, use the default message
      }

      throw new ApiError(response.status, response.statusText, errorMessage);
    }

    let data: unknown;
    try {
      data = await response.json();
    } catch {
      throw new Error('BUGSLASH API returned an empty or invalid JSON response.');
    }
    if (isExpectedResponse && !isExpectedResponse(data)) {
      throw new Error('BUGSLASH API returned data in an unexpected format.');
    }
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      if (signal?.aborted) {
        throw new Error('Request was cancelled.');
      }
      throw new Error(
        'Request timed out. The server may be busy or unavailable.'
      );
    }

    if (error instanceof TypeError) {
      throw new Error(
        'Unable to reach BUGSLASH API. Make sure FastAPI is running at ' +
          API_BASE_URL
      );
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Compose two AbortSignals. When either fires, the returned signal fires.
 */
function composeAbortSignals(
  a: AbortSignal,
  b: AbortSignal
): AbortSignal {
  // If AbortSignal.any is available (modern browsers), use it
  if ('any' in AbortSignal) {
    return AbortSignal.any([a, b]);
  }
  // Fallback: create a new controller and listen to both
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  a.addEventListener('abort', onAbort, { once: true });
  b.addEventListener('abort', onAbort, { once: true });
  return controller.signal;
}

// --- Public API functions ---

export async function getHealth(
  signal?: AbortSignal
): Promise<HealthResponse> {
  return request<HealthResponse>(
    '/health', {}, 5000, signal, isHealthResponse
  );
}

export async function getScans(
  signal?: AbortSignal
): Promise<ScanHistoryResponse> {
  return request<ScanHistoryResponse>(
    '/scans', {}, 15000, signal, isScanHistoryResponse
  );
}

export async function getScan(
  scanId: number,
  signal?: AbortSignal
): Promise<ScanDetailResponse> {
  return request<ScanDetailResponse>(
    `/scans/${scanId}`, {}, 15000, signal, isScanDetailResponse
  );
}

export async function analyzeFile(
  file: File,
  signal?: AbortSignal
): Promise<FileAnalysisResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return request<FileAnalysisResponse>(
    '/analyze',
    {
      method: 'POST',
      body: formData,
    },
    60000,
    signal,
    isFileAnalysisResponse
  );
}

export async function analyzeProject(
  file: File,
  signal?: AbortSignal
): Promise<ProjectAnalysisResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return request<ProjectAnalysisResponse>(
    '/analyze-project',
    {
      method: 'POST',
      body: formData,
    },
    120000,
    signal,
    isProjectAnalysisResponse
  );
}

export function getUserFriendlyError(
  error: unknown,
  context: 'analysis' | 'request' = 'request'
): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 400:
        return context === 'analysis'
          ? 'Invalid file or analysis request. Check the file type and try again.'
          : 'The request was invalid. Please check the selected item and try again.';
      case 404:
        return 'The requested resource was not found.';
      case 422:
        return context === 'analysis'
          ? 'The API could not accept this file. Check the file type and try again.'
          : 'The API could not validate this request.';
      case 500:
        return context === 'analysis'
          ? 'Analysis failed. The BUGSLASH API responded but could not complete the analysis.'
          : 'Unexpected server error. Please try again later.';
      default:
        return `BUGSLASH API returned HTTP ${error.status}. Please try again.`;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
}
