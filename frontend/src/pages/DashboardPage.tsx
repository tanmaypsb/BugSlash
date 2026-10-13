import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileUpload } from '../components/FileUpload';
import { FindingsList } from '../components/FindingsList';
import { ScansTable } from '../components/ScansTable';
import { fixFile, getScans, getUserFriendlyError } from '../services/api';
import { supportsAutofixSource } from '../utils/fixCapabilities.js';
import type {
  FixResponse,
  ScanSummaryResponse,
  FileAnalysisResponse,
  ProjectAnalysisResponse,
  FindingResponse,
} from '../types/api';

interface AnalysisResult {
  type: 'file' | 'project';
  sourceFile: File;
  fileResponse?: FileAnalysisResponse;
  projectResponse?: ProjectAnalysisResponse;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<ScanSummaryResponse[]>([]);
  const [scansLoading, setScansLoading] = useState(true);
  const [scansError, setScansError] = useState('');
  const [analysisFindings, setAnalysisFindings] = useState<FindingResponse[]>([]);
  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysisSourceFile, setAnalysisSourceFile] = useState<File | null>(null);
  const [analysisLanguage, setAnalysisLanguage] = useState('');
  const [analysisIsProject, setAnalysisIsProject] = useState(false);
  const [analysisScanId, setAnalysisScanId] = useState<number | null>(null);
  const [scansRefreshKey, setScansRefreshKey] = useState(0);
  const [fixResult, setFixResult] = useState<FixResponse | null>(null);
  const [fixLoading, setFixLoading] = useState(false);
  const [fixError, setFixError] = useState('');
  const fixAbortRef = useRef<AbortController | null>(null);

  useEffect(() => () => fixAbortRef.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    void getScans(controller.signal)
      .then((data) => {
        setScansError('');
        setScans(data.scans);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setScansError(getUserFriendlyError(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setScansLoading(false);
      });
    return () => controller.abort();
  }, [scansRefreshKey]);

  const clearFixState = () => {
    fixAbortRef.current?.abort();
    fixAbortRef.current = null;
    setFixLoading(false);
    setFixResult(null);
    setFixError('');
  };

  const handleFileSelected = () => {
    clearFixState();
    setAnalysisSourceFile(null);
    setAnalysisLanguage('');
    setAnalysisIsProject(false);
    setAnalysisFindings([]);
    setAnalysisScanId(null);
    setAnalysisVisible(false);
  };

  const handleAnalysisComplete = (result: AnalysisResult) => {
    clearFixState();
    setAnalysisIsProject(result.type === 'project');
    setAnalysisSourceFile(result.type === 'file' ? result.sourceFile : null);

    if (result.type === 'project' && result.projectResponse) {
      setAnalysisLanguage('');
      setAnalysisFindings(result.projectResponse.results.flatMap((item) => item.findings));
      setAnalysisScanId(result.projectResponse.scan_id);
      setAnalysisVisible(true);
    } else if (result.type === 'file' && result.fileResponse) {
      setAnalysisLanguage(result.fileResponse.language.toLowerCase());
      setAnalysisFindings(result.fileResponse.findings);
      setAnalysisScanId(null);
      setAnalysisVisible(true);
    }
    setScansRefreshKey((value) => value + 1);
  };

  const canFix = Boolean(
    analysisVisible &&
      !analysisIsProject &&
      analysisSourceFile &&
      supportsAutofixSource(analysisSourceFile.name, analysisLanguage)
  );

  const handleFixAll = async () => {
    if (!canFix || !analysisSourceFile || fixLoading) return;
    const controller = new AbortController();
    fixAbortRef.current = controller;
    setFixLoading(true);
    setFixError('');
    setFixResult(null);
    try {
      const result = await fixFile(analysisSourceFile, controller.signal);
      if (!controller.signal.aborted && fixAbortRef.current === controller) {
        setFixResult(result);
      }
    } catch (error) {
      if (!controller.signal.aborted && fixAbortRef.current === controller) {
        setFixError(getUserFriendlyError(error, 'fix'));
      }
    } finally {
      if (fixAbortRef.current === controller) {
        fixAbortRef.current = null;
        setFixLoading(false);
      }
    }
  };

  const downloadFixedFile = () => {
    if (!fixResult?.success || typeof fixResult.fixed_code !== 'string') return;
    const sourceName = (analysisSourceFile?.name || fixResult.filename).split(/[\\/]/).pop() || 'source';
    const extension = sourceName.match(/\.[^.]+$/)?.[0] || '';
    const baseName = extension ? sourceName.slice(0, -extension.length) : sourceName;
    const blob = new Blob([fixResult.fixed_code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const downloadSuffix =
      fixResult.status === 'FIX_VERIFIED' ? '_fixed' :
      fixResult.status === 'PARTIALLY_FIXED' ? '_partially_fixed' :
      fixResult.status === 'VERIFICATION_INCOMPLETE' ? '_unverified' :
      fixResult.status === 'NO_CHANGES' ? '_unchanged' : '_review';
    link.download = `${baseName}${downloadSuffix}${extension}`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const totalScans = scans.length;
  const totalFilesAnalyzed = scans.reduce((acc, scan) => acc + scan.files_analyzed, 0);

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Upload code and inspect analysis results</p>
      </div>

      <div className="stats-row">
        <div className="stat-item"><div className="stat-item__value">{totalScans}</div><div className="stat-item__label">Total scans</div></div>
        <div className="stat-item"><div className="stat-item__value">{totalFilesAnalyzed}</div><div className="stat-item__label">Files analyzed</div></div>
      </div>

      <div className="dashboard-grid">
        <div><FileUpload onFileSelected={handleFileSelected} onAnalysisComplete={handleAnalysisComplete} /></div>
        <div>
          <div className="section">
            <div className="section-header">
              <h2>Recent Scans</h2>
              {scans.length > 0 && <button className="btn btn--secondary btn--small" onClick={() => navigate('/scans')} type="button">View all</button>}
            </div>
            {scansLoading ? <div className="loading-state"><span className="loading-spinner" />Loading scans...</div> : scansError ? <div className="error-banner" role="alert">{scansError}</div> : <ScansTable scans={scans.slice(0, 5)} />}
          </div>
        </div>
      </div>

      {analysisVisible && (
        <div className="section" style={{ marginTop: 4 }}>
          <div className="section-header">
            <h2>Analysis Results{analysisFindings.length > 0 && <span className="badge" style={{ marginLeft: 8, verticalAlign: 'middle' }}>{analysisFindings.length} finding{analysisFindings.length !== 1 ? 's' : ''}</span>}</h2>
            <div style={{ display: 'flex', gap: 8 }}>
              {canFix && <button className="btn btn--primary btn--small" type="button" onClick={handleFixAll} disabled={fixLoading}>{fixLoading ? 'Fixing and re-analyzing...' : 'Fix All Safe Issues'}</button>}
              {analysisScanId !== null && <button className="btn btn--secondary btn--small" onClick={() => navigate(`/scans/${analysisScanId}`)} type="button">Open scan #{analysisScanId}</button>}
              <button className="btn btn--secondary btn--small" onClick={() => setAnalysisVisible(false)} type="button">Dismiss</button>
            </div>
          </div>

          {fixLoading && <div className="analysis-status" role="status"><span className="loading-spinner" />Applying safe fixes and verifying the updated file...</div>}
          {fixError && <div className="error-banner" role="alert">{fixError}</div>}

          {fixResult && (
            <div className="section" aria-live="polite">
              <h3>{fixResult.status === 'FIX_VERIFIED' ? 'Autofix verification complete' : fixResult.status === 'PARTIALLY_FIXED' ? 'Autofix partially completed' : fixResult.status === 'FIX_FAILED' ? 'Autofix failed verification' : fixResult.status === 'VERIFICATION_INCOMPLETE' ? 'Autofix needs review' : fixResult.status === 'REVIEW_REQUIRED' ? 'Manual review required' : 'No changes necessary'}</h3>
              <p>{fixResult.message}</p>
              <p>Verification: {fixResult.verification_status.replaceAll('_', ' ')}</p>
              <div className="stats-row">
                <div className="stat-item"><div className="stat-item__value">{fixResult.original_count}</div><div className="stat-item__label">Original findings</div></div>
                <div className="stat-item"><div className="stat-item__value">{fixResult.resolved_count}</div><div className="stat-item__label">Resolved findings</div></div>
                <div className="stat-item"><div className="stat-item__value">{fixResult.remaining_count}</div><div className="stat-item__label">Remaining findings</div></div>
                {fixResult.introduced_count > 0 && <div className="stat-item"><div className="stat-item__value">{fixResult.introduced_count}</div><div className="stat-item__label">New findings after fixing</div></div>}
              </div>
              {fixResult.resolved_findings.length > 0 && <div><h4>Findings resolved</h4><ul>{fixResult.resolved_findings.map((finding, index) => <li key={`resolved-${finding.code ?? 'finding'}-${finding.location.row}-${index}`}><strong>{finding.code ?? 'Finding'}</strong>   -  {finding.message}</li>)}</ul></div>}
              {fixResult.introduced_findings.length > 0 && <div role="alert"><h4>New findings after fixing</h4><ul>{fixResult.introduced_findings.map((finding, index) => <li key={`introduced-${finding.code ?? 'finding'}-${finding.location.row}-${index}`}><strong>{finding.code ?? 'Finding'}</strong>   -  {finding.message} (line {finding.location.row})</li>)}</ul></div>}
              {fixResult.remaining_findings.length > 0 && <div><h4>Findings remaining after re-analysis</h4><ul>{fixResult.remaining_findings.map((finding, index) => <li key={`${finding.code ?? 'finding'}-${finding.location.row}-${finding.location.column}-${index}`}><strong>{finding.code ?? 'Finding'}</strong> — {finding.message} (line {finding.location.row}, column {finding.location.column})</li>)}</ul></div>}
              {fixResult.success && typeof fixResult.fixed_code === 'string' && <button className="btn btn--secondary" onClick={downloadFixedFile} type="button">{fixResult.status === 'FIX_VERIFIED' ? 'Download Fixed File' : fixResult.status === 'PARTIALLY_FIXED' ? 'Download Partially Fixed File' : fixResult.status === 'VERIFICATION_INCOMPLETE' ? 'Download Unverified Output' : fixResult.status === 'NO_CHANGES' ? 'Download Unchanged Source' : 'Download Source for Review'}</button>}
            </div>
          )}

          {!analysisIsProject && analysisLanguage && analysisFindings.length === 0 && <p>No findings were detected. There is nothing to fix.</p>}
          {analysisIsProject && <p>Global autofix is available only for an individual source file while its original source is available.</p>}
          {!analysisIsProject && analysisLanguage && analysisSourceFile && !supportsAutofixSource(analysisSourceFile.name, analysisLanguage) && <p>No tested automatic fixer is configured for this source language.</p>}
          {analysisIsProject && analysisScanId !== null && <p>Saved project scans do not retain the original uploaded source file for autofix.</p>}
          {analysisFindings.length > 0 && <><h3>Original analysis findings</h3><FindingsList findings={analysisFindings} sourceFile={analysisSourceFile} /></>}
        </div>
      )}
    </>
  );
}
