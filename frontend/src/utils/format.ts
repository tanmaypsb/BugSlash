/**
 * Format a byte count into a human-readable string.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/**
 * Format an ISO date string into a readable local format.
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format a relative time string (e.g., "2 hours ago").
 */
export function formatRelativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffMs = now - then;

  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return 'just now';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;

  return formatDate(iso);
}

/**
 * Confidence as a percentage string.
 */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/**
 * Supported single-file extensions for direct analysis.
 */
const SINGLE_FILE_EXTENSIONS = new Set([
  '.py',
  '.js',
  '.jsx',
  '.ts',
  '.tsx',
  '.c',
  '.cpp',
  '.cc',
  '.cxx',
  '.h',
  '.hpp',
  '.java',
  '.go',
  '.rs',
]);

/**
 * Check if a file is a supported single source file.
 */
export function isSupportedSourceFile(filename: string): boolean {
  const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();
  return SINGLE_FILE_EXTENSIONS.has(ext);
}

/**
 * Check if a file is a ZIP archive.
 */
export function isZipFile(filename: string): boolean {
  return filename.toLowerCase().endsWith('.zip');
}

/**
 * Get a language label from a language code.
 */
export function getLanguageLabel(lang: string): string {
  const map: Record<string, string> = {
    python: 'Python',
    javascript: 'JavaScript',
    c: 'C',
    cpp: 'C++',
    'c++': 'C/C++',
    c_cpp: 'C/C++',
    java: 'Java',
    go: 'Go',
    rust: 'Rust',
  };
  return map[lang.toLowerCase()] || lang;
}

/**
 * Get a short filename from a full path.
 */
export function getShortFilename(filepath: string): string {
  const parts = filepath.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1];
}
