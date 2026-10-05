import { useMemo, useState } from 'react';
import type { FindingResponse, ScanDetailFindingResponse } from '../types/api';
import { formatConfidence, getLanguageLabel } from '../utils/format';

type Finding = FindingResponse | ScanDetailFindingResponse;

function hasFindingId(f: Finding): f is ScanDetailFindingResponse {
  return 'id' in f;
}

interface FindingsListProps {
  findings: Finding[];
}

export function FindingsList({ findings }: FindingsListProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [languageFilter, setLanguageFilter] = useState('all');
  const [analyzerFilter, setAnalyzerFilter] = useState('all');

  const languages = useMemo(
    () => [...new Set(findings.map((finding) => finding.language.toLowerCase()))].sort(),
    [findings]
  );
  const analyzers = useMemo(
    () => [...new Set(findings.map((finding) => finding.analyzer))].sort(),
    [findings]
  );
  const severities = useMemo(() => {
    const standard = ['high', 'medium', 'low'];
    const additional = findings
      .map((finding) => finding.severity.toLowerCase())
      .filter((severity) => !standard.includes(severity));
    return [...standard, ...new Set(additional)];
  }, [findings]);
  const visibleFindings = useMemo(
    () =>
      findings.filter(
        (finding) =>
          (severityFilter === 'all' ||
            finding.severity.toLowerCase() === severityFilter) &&
          (languageFilter === 'all' ||
            finding.language.toLowerCase() === languageFilter) &&
          (analyzerFilter === 'all' || finding.analyzer === analyzerFilter)
      ),
    [findings, severityFilter, languageFilter, analyzerFilter]
  );

  if (findings.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state__title">No findings</div>
        <div className="empty-state__description">
          No issues were detected in this analysis.
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="findings-toolbar">
        <div className="filter-bar" role="group" aria-label="Filter findings">
          <label>
            <span className="visually-hidden">Filter by severity</span>
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value)}
              aria-label="Filter by severity"
            >
              <option value="all">All severities</option>
              {severities.map((severity) => (
                <option key={severity} value={severity}>
                  {severity.charAt(0).toUpperCase() + severity.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="visually-hidden">Filter by language</span>
            <select
              value={languageFilter}
              onChange={(event) => setLanguageFilter(event.target.value)}
              aria-label="Filter by language"
            >
              <option value="all">All languages</option>
              {languages.map((language) => (
                <option key={language} value={language}>
                  {getLanguageLabel(language)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="visually-hidden">Filter by analyzer</span>
            <select
              value={analyzerFilter}
              onChange={(event) => setAnalyzerFilter(event.target.value)}
              aria-label="Filter by analyzer"
            >
              <option value="all">All analyzers</option>
              {analyzers.map((analyzer) => (
                <option key={analyzer} value={analyzer}>
                  {getAnalyzerLabel(analyzer)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <span className="findings-toolbar__count" aria-live="polite">
          Showing {visibleFindings.length} of {findings.length}
        </span>
      </div>

      {visibleFindings.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state__title">No matching findings</div>
          <div className="empty-state__description">
            Try changing the filters.
          </div>
        </div>
      ) : (
        <div className="findings-list" role="list">
      {visibleFindings.map((finding, index) => {
        const isExpanded = expandedIndex === index;
        const key = hasFindingId(finding)
          ? `finding-${finding.id}`
          : `finding-${index}`;

        return (
          <div key={key} role="listitem">
            <div
              className={`finding-row${isExpanded ? ' finding-row--expanded' : ''}`}
              onClick={() => setExpandedIndex(isExpanded ? null : index)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setExpandedIndex(isExpanded ? null : index);
                }
              }}
              tabIndex={0}
              role="button"
              aria-expanded={isExpanded}
              aria-label={`${finding.severity} severity: ${finding.message}`}
            >
              <span
                className={`finding-severity finding-severity--${finding.severity.toLowerCase()}`}
              >
                {finding.severity}
              </span>
              <div className="finding-summary">
                <div className="finding-summary__message">{finding.message}</div>
                <div className="finding-summary__meta">
                  {finding.file}:{finding.line}:{finding.column}
                </div>
              </div>
              <div className="finding-meta-end">
                {finding.analyzer}
              </div>
            </div>

            {isExpanded && (
              <div className="finding-detail">
                <div className="finding-detail__grid">
                  <div className="finding-detail__field">
                    <span className="finding-detail__label">File</span>
                    <span className="finding-detail__value finding-detail__value--mono">
                      {finding.file}
                    </span>
                  </div>
                  <div className="finding-detail__field">
                    <span className="finding-detail__label">Location</span>
                    <span className="finding-detail__value finding-detail__value--mono">
                      Line {finding.line}, Col {finding.column}
                    </span>
                  </div>
                  <div className="finding-detail__field">
                    <span className="finding-detail__label">Category</span>
                    <span className="finding-detail__value finding-detail__value--mono">
                      {finding.category}
                    </span>
                  </div>
                  <div className="finding-detail__field">
                    <span className="finding-detail__label">Analyzer</span>
                    <span className="finding-detail__value">
                      {finding.analyzer}
                    </span>
                  </div>
                  <div className="finding-detail__field">
                    <span className="finding-detail__label">Language</span>
                    <span className="finding-detail__value">
                      {getLanguageLabel(finding.language)}
                    </span>
                  </div>
                  <div className="finding-detail__field">
                    <span className="finding-detail__label">Confidence</span>
                    <span className="finding-detail__value">
                      {formatConfidence(finding.confidence)}
                    </span>
                  </div>
                  {hasFindingId(finding) && finding.verification_status && (
                    <div className="finding-detail__field">
                      <span className="finding-detail__label">Verification</span>
                      <span className="finding-detail__value">
                        {finding.verification_status}
                      </span>
                    </div>
                  )}
                </div>
                <div className="finding-detail__message">{finding.message}</div>
              </div>
            )}
          </div>
        );
      })}
        </div>
      )}
    </>
  );
}

function getAnalyzerLabel(analyzer: string): string {
  const labels: Record<string, string> = {
    ruff: 'Ruff',
    eslint: 'ESLint',
    'clang-tidy': 'Clang-Tidy',
    spotbugs: 'SpotBugs',
    staticcheck: 'Staticcheck',
    clippy: 'Clippy',
  };
  return labels[analyzer.toLowerCase()] ?? analyzer;
}
