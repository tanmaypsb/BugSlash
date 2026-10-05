import { useNavigate } from 'react-router-dom';
import type { ScanSummaryResponse } from '../types/api';
import { formatRelativeTime, formatDate } from '../utils/format';

interface ScansTableProps {
  scans: ScanSummaryResponse[];
}

export function ScansTable({ scans }: ScansTableProps) {
  const navigate = useNavigate();

  if (scans.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__title">No scans yet</div>
        <div className="empty-state__description">
          Upload a file or project to start your first analysis.
        </div>
      </div>
    );
  }

  return (
    <div className="scans-table-wrap">
      <table className="scans-table" role="table">
        <thead>
          <tr>
            <th scope="col">Scan</th>
            <th scope="col">Status</th>
            <th scope="col">Files</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {scans.map((scan) => (
            <tr
              key={scan.id}
              onClick={() => navigate(`/scans/${scan.id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') navigate(`/scans/${scan.id}`);
              }}
              tabIndex={0}
              role="link"
              aria-label={`Scan #${scan.id}, ${scan.status}, ${scan.files_analyzed} files`}
            >
              <td>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                  #{scan.id}
                </span>
              </td>
              <td>
                <span className={`scan-status scan-status--${scan.status}`}>
                  <span className="scan-status__dot" />
                  {scan.status}
                </span>
              </td>
              <td>{scan.files_analyzed}</td>
              <td title={formatDate(scan.created_at)}>
                {formatRelativeTime(scan.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
