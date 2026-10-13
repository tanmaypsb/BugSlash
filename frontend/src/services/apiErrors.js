export function getUserFriendlyError(error, context = 'request') {
  if (error && typeof error === 'object' && error.name === 'ApiError' && Number.isInteger(error.status)) {
    switch (error.status) {
      case 400:
        if (context === 'fix') return 'This file type has no available automatic fixer. Check the selected source and try again.';
        return context === 'analysis'
          ? 'Invalid file or analysis request. Check the file type and try again.'
          : 'The request was invalid. Please check the selected item and try again.';
      case 404:
        return 'The requested resource was not found.';
      case 409:
        return context === 'fix'
          ? 'The source or finding changed. Re-analyze the selected file and try again.'
          : 'The selected finding no longer matches this source. Re-analyze and try again.';
      case 413:
        return context === 'fix' ? 'This source file is too large for the requested fix operation.' : 'This request is too large.';
      case 503:
        return 'Local Ollama is unavailable or the configured model is missing. Analysis and deterministic fixes remain available.';
      case 502:
        return 'The local LLM returned an invalid response. No source was changed.';
      case 422:
        if (context === 'fix') return error.message || 'The API could not accept this source file for autofix.';
        if (context === 'analysis') return error.message ? `Analysis could not complete: ${error.message}` : 'Analysis could not complete. The API rejected the source.';
        return error.message || 'The API could not validate this request.';
      case 500:
        if (context === 'fix') return 'Autofix failed while applying or verifying safe fixes. You can retry.';
        return context === 'analysis'
          ? 'Analysis failed. The BUGSLASH API responded but could not complete the analysis.'
          : 'Unexpected server error. Please try again later.';
      default:
        return `BUGSLASH API returned HTTP ${error.status}. Please try again.`;
    }
  }
  return error instanceof Error ? error.message : 'An unexpected error occurred.';
}
