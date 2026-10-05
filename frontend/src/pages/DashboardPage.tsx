import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileUpload } from '../components/FileUpload';
import { FindingsList } from '../components/FindingsList';
import { ScansTable } from '../components/ScansTable';
import { getScans, getUserFriendlyError } from '../services/api';
import type {
  ScanSummaryResponse,
  FileAnalysisResponse,
  ProjectAnalysisResponse,
  FindingResponse,
} from '../types/api';

export function DashboardPage() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<ScanSummaryResponse[]>([]);
  const [scansLoading, setScansLoading] = useState(true);
  const [scansError, setScansError] = useState('');

  // Analysis results (shown inline after upload)
  const [analysisFindings, setAnalysisFindings] = useState<FindingResponse[]>(
    []
  );
  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysisScanId, setAnalysisScanId] = useState<number | null>(null);
  const [scansRefreshKey, setScansRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void getScans(controller.signal)
      .then((data) => {
        setScansError('');
        setScans(data.scans);
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setScansError(getUserFriendlyError(err));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setScansLoading(false);
      });

    return () => controller.abort();
  }, [scansRefreshKey]);

  const handleAnalysisComplete = (result: {
    type: 'file' | 'project';
    fileResponse?: FileAnalysisResponse;
    projectResponse?: ProjectAnalysisResponse;
  }) => {
    if (result.type === 'project' && result.projectResponse) {
      const allFindings = result.projectResponse.results.flatMap(
        (r) => r.findings
      );
      setAnalysisFindings(allFindings);
      setAnalysisScanId(result.projectResponse.scan_id);
      setAnalysisVisible(true);
    } else if (result.type === 'file' && result.fileResponse) {
      setAnalysisFindings(result.fileResponse.findings);
      setAnalysisScanId(null);
      setAnalysisVisible(true);
    }

    // Refresh scan list after analysis
    setScansRefreshKey((value) => value + 1);
  };

  // Dashboard stats from actual data
  const totalScans = scans.length;
  const totalFilesAnalyzed = scans.reduce(
    (acc, s) => acc + s.files_analyzed,
    0
  );

  return (
    <>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Upload code and inspect analysis results</p>
      </div>

      <div className="stats-row">
        <div className="stat-item">
          <div className="stat-item__value">{totalScans}</div>
          <div className="stat-item__label">Total scans</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__value">{totalFilesAnalyzed}</div>
          <div className="stat-item__label">Files analyzed</div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div>
          <FileUpload onAnalysisComplete={handleAnalysisComplete} />
        </div>

        <div>
          <div className="section">
            <div className="section-header">
              <h2>Recent Scans</h2>
              {scans.length > 0 && (
                <button
                  className="btn btn--secondary btn--small"
                  onClick={() => navigate('/scans')}
                  type="button"
                >
                  View all
                </button>
              )}
            </div>

            {scansLoading ? (
              <div className="loading-state">
                <span className="loading-spinner" />
                Loading scans...
              </div>
            ) : scansError ? (
              <div className="error-banner" role="alert">
                {scansError}
              </div>
            ) : (
              <ScansTable scans={scans.slice(0, 5)} />
            )}
          </div>
        </div>
      </div>

      {analysisVisible && (
        <div className="section" style={{ marginTop: 4 }}>
          <div className="section-header">
            <h2>
              Analysis Results
              {analysisFindings.length > 0 && (
                <span
                  className="badge"
                  style={{ marginLeft: 8, verticalAlign: 'middle' }}
                >
                  {analysisFindings.length} finding
                  {analysisFindings.length !== 1 ? 's' : ''}
                </span>
              )}
            </h2>
            <div style={{ display: 'flex', gap: 8 }}>
              {analysisScanId !== null && (
                <button
                  className="btn btn--secondary btn--small"
                  onClick={() => navigate(`/scans/${analysisScanId}`)}
                  type="button"
                >
                  Open scan #{analysisScanId}
                </button>
              )}
              <button
                className="btn btn--secondary btn--small"
                onClick={() => setAnalysisVisible(false)}
                type="button"
              >
                Dismiss
              </button>
            </div>
          </div>
          <FindingsList findings={analysisFindings} />
        </div>
      )}
    </>
  );
}
