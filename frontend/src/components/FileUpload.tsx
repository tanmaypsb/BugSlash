import { useState, useRef, useCallback } from 'react';
import { formatFileSize, isSupportedSourceFile, isZipFile } from '../utils/format';
import {
  analyzeFile,
  analyzeProject,
  getUserFriendlyError,
} from '../services/api';
import type {
  FileAnalysisResponse,
  ProjectAnalysisResponse,
} from '../types/api';

type UploadState =
  | 'idle'
  | 'selected'
  | 'uploading'
  | 'analyzing'
  | 'success'
  | 'error';

interface AnalysisResult {
  type: 'file' | 'project';
  fileResponse?: FileAnalysisResponse;
  projectResponse?: ProjectAnalysisResponse;
}

interface FileUploadProps {
  onAnalysisComplete?: (result: AnalysisResult) => void;
}

export function FileUpload({ onAnalysisComplete }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const resetState = useCallback(() => {
    setFile(null);
    setState('idle');
    setStatusMessage('');
    setErrorMessage('');
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const validateFile = (f: File): string | null => {
    const name = f.name.toLowerCase();

    if (f.size === 0) {
      return 'This file is empty. Choose a file with source code or project files.';
    }

    if (isZipFile(name)) {
      return null;
    }

    if (isSupportedSourceFile(name)) {
      return null;
    }

    return `Unsupported file type. Upload a source file (.py, .js, .c, .cpp, .java, .go, .rs) or a .zip project archive.`;
  };

  const handleFileSelect = (f: File) => {
    const validationError = validateFile(f);
    if (validationError) {
      setErrorMessage(validationError);
      setState('error');
      setFile(null);
      return;
    }
    setFile(f);
    setState('selected');
    setErrorMessage('');
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFileSelect(f);
    // Reset input so the same file can be re-selected
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFileSelect(f);
  };

  const handleAnalyze = async () => {
    if (!file) return;

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setState('uploading');
      setStatusMessage('Uploading...');
      setErrorMessage('');

      const isProject = isZipFile(file.name);
      await new Promise<void>((resolve) => {
        window.requestAnimationFrame(() => resolve());
      });

      setState('analyzing');
      setStatusMessage(
        isProject ? 'Analyzing project...' : 'Analyzing file...'
      );

      if (isProject) {
        const response = await analyzeProject(file, controller.signal);
        setState('success');
        setStatusMessage(
          `Analysis complete. ${response.files_analyzed} file${response.files_analyzed !== 1 ? 's' : ''} analyzed.`
        );
        onAnalysisComplete?.({ type: 'project', projectResponse: response });
      } else {
        const response = await analyzeFile(file, controller.signal);
        setState('success');
        const count = response.findings.length;
        setStatusMessage(
          `Analysis complete. ${count} finding${count !== 1 ? 's' : ''} detected.`
        );
        onAnalysisComplete?.({ type: 'file', fileResponse: response });
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      setState('error');
      setErrorMessage(getUserFriendlyError(err, 'analysis'));
      setStatusMessage('');
    } finally {
      abortRef.current = null;
    }
  };

  const handleCancel = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setState('selected');
    setStatusMessage('');
  };

  const isUploading = state === 'uploading' || state === 'analyzing';

  return (
    <div className="section">
      <div className="section-header">
        <h2>Analyze Code</h2>
        {file && state !== 'idle' && (
          <button
            className="btn btn--secondary btn--small"
            onClick={resetState}
            type="button"
          >
            Clear
          </button>
        )}
      </div>

      <div
        className={`upload-area${dragOver ? ' upload-area--dragover' : ''}${isUploading ? ' upload-area--disabled' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Drop a file here or click to select"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
      >
        <div className="upload-area__label">
          Drop a file here or click to select
        </div>
        <div className="upload-area__hint">
          Source file (.py, .js, .c, .java, .go, .rs) or ZIP project archive
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".py,.js,.jsx,.ts,.tsx,.c,.cpp,.cc,.cxx,.h,.hpp,.java,.go,.rs,.zip"
          onChange={handleInputChange}
          tabIndex={-1}
          aria-hidden="true"
        />
      </div>

      {file && (
        <div className="selected-file">
          <div className="selected-file__info">
            <span className="selected-file__name">{file.name}</span>
            <span className="selected-file__size">
              {formatFileSize(file.size)}
              {isZipFile(file.name) ? ' (project archive)' : ''}
            </span>
          </div>
          {!isUploading && (
            <button
              className="selected-file__remove"
              onClick={(e) => {
                e.stopPropagation();
                resetState();
              }}
              type="button"
              aria-label="Remove selected file"
            >
              Remove
            </button>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="analysis-status analysis-status--error" role="alert">
          {errorMessage}
        </div>
      )}

      {statusMessage && (
        <div
          className={`analysis-status${state === 'success' ? ' analysis-status--success' : ''}`}
          role="status"
        >
          {isUploading && <span className="loading-spinner" />}
          {statusMessage}
        </div>
      )}

      {isUploading && (
        <div className="loading-bar">
          <div className="loading-bar__fill" />
        </div>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button
          className="btn btn--primary"
          onClick={handleAnalyze}
          disabled={!file || isUploading}
          type="button"
        >
          {isUploading ? 'Analyzing...' : 'Analyze'}
        </button>
        {isUploading && (
          <button
            className="btn btn--secondary"
            onClick={handleCancel}
            type="button"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
