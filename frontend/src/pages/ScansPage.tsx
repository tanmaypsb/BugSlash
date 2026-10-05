import { useState, useEffect } from 'react';
import { ScansTable } from '../components/ScansTable';
import { getScans, getUserFriendlyError } from '../services/api';
import type { ScanSummaryResponse } from '../types/api';

export function ScansPage() {
  const [scans, setScans] = useState<ScanSummaryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        setLoading(true);
        setError('');
        const data = await getScans(controller.signal);
        setScans(data.scans);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(getUserFriendlyError(err));
      } finally {
        setLoading(false);
      }
    }

    load();

    return () => controller.abort();
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Scan History</h1>
        <p>All analysis scans stored in the database</p>
      </div>

      <div className="section">
        {loading ? (
          <div className="loading-state">
            <span className="loading-spinner" />
            Loading scans...
          </div>
        ) : error ? (
          <div className="error-banner" role="alert">
            {error}
          </div>
        ) : (
          <ScansTable scans={scans} />
        )}
      </div>
    </>
  );
}
