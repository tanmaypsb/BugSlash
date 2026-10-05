import { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { FindingsList } from '../components/FindingsList';
import { getScan, getUserFriendlyError } from '../services/api';
import type { ScanDetailResponse } from '../types/api';
import { formatDate } from '../utils/format';

export function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const [scan, setScan] = useState<ScanDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const scanIdNumber = Number(scanId);
  const hasValidScanId = Boolean(
    scanId && Number.isInteger(scanIdNumber) && scanIdNumber > 0
  );

  useEffect(() => {
    if (!hasValidScanId) return;

    const controller = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setError('');
        const data = await getScan(scanIdNumber, controller.signal);
        setScan(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(getUserFriendlyError(err));
      } finally {
        setLoading(false);
      }
    }

    load();

    return () => controller.abort();
  }, [hasValidScanId, scanIdNumber]);

  // Summary stats
  const severityCounts = useMemo(() => {
    if (!scan) return { high: 0, medium: 0, low: 0 };
    const counts = { high: 0, medium: 0, low: 0 };
    for (const f of scan.findings) {
      const sev = f.severity.toLowerCase() as keyof typeof counts;
      if (sev in counts) counts[sev]++;
    }
    return counts;
  }, [scan]);

  if (!hasValidScanId) {
    return (
      <>
        <Link to="/scans" className="back-link">
          &#8592; Back to scans
        </Link>
        <div className="error-banner" role="alert">
          Scan ID must be a positive integer.
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <div className="loading-state">
        <span className="loading-spinner" />
        Loading scan details...
      </div>
    );
  }

  if (error) {
    return (
      <>
        <Link to="/scans" className="back-link">
          &#8592; Back to scans
        </Link>
        <div className="error-banner" role="alert">
          {error}
        </div>
      </>
    );
  }

  if (!scan) {
    return (
      <>
        <Link to="/scans" className="back-link">
          &#8592; Back to scans
        </Link>
        <div className="error-banner" role="alert">
          Scan not found.
        </div>
      </>
    );
  }

  return (
    <>
      <Link to="/scans" className="back-link">
        &#8592; Back to scans
      </Link>

      <div className="page-header">
        <div className="scan-detail-header">
          <div>
            <h1>Scan #{scan.id}</h1>
            <div className="scan-detail-meta">
              <span className="scan-detail-meta__item">
                Status:{' '}
                <strong>
                  <span className={`scan-status scan-status--${scan.status}`}>
                    <span className="scan-status__dot" />
                    {scan.status}
                  </span>
                </strong>
              </span>
              <span className="scan-detail-meta__item">
                Files: <strong>{scan.files_analyzed}</strong>
              </span>
              <span className="scan-detail-meta__item">
                Findings: <strong>{scan.findings.length}</strong>
              </span>
              <span className="scan-detail-meta__item">
                Created: <strong>{formatDate(scan.created_at)}</strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {scan.findings.length > 0 && (
        <div className="stats-row">
          <div className="stat-item">
            <div className="stat-item__value" style={{ color: 'var(--severity-high)' }}>
              {severityCounts.high}
            </div>
            <div className="stat-item__label">High severity</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__value" style={{ color: 'var(--severity-medium)' }}>
              {severityCounts.medium}
            </div>
            <div className="stat-item__label">Medium severity</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__value" style={{ color: 'var(--severity-low)' }}>
              {severityCounts.low}
            </div>
            <div className="stat-item__label">Low severity</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__value">{scan.findings.length}</div>
            <div className="stat-item__label">Total findings</div>
          </div>
        </div>
      )}

      <div className="section">
        <div className="section-header">
          <h2>Findings</h2>
        </div>
        <FindingsList findings={scan.findings} />
      </div>
    </>
  );
}
