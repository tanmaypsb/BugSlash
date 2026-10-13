import { useEffect, useMemo, useRef, useState } from 'react';
import type { FindingResponse, ScanDetailFindingResponse } from '../types/api';
import { formatConfidence, getLanguageLabel } from '../utils/format';
import { supportsFindingAutofix } from '../utils/fixCapabilities.js';
import { applyFindingProposal, explainFinding, fixFinding, getUserFriendlyError, proposeFindingFix } from '../services/api';
import type { FindingExplanationResponse, FixProposalResponse, FixResponse } from '../types/api';

type Finding = FindingResponse | ScanDetailFindingResponse;

function hasFindingId(f: Finding): f is ScanDetailFindingResponse {
  return 'id' in f;
}

interface FindingsListProps {
  findings: Finding[];
  sourceFile?: File | null;
}

export function FindingsList({ findings, sourceFile = null }: FindingsListProps) {
  const [pendingActions, setPendingActions] = useState<Record<string, string>>({});
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});
  const [fixResults, setFixResults] = useState<Record<string, FixResponse>>({});
  const [explanations, setExplanations] = useState<Record<string, FindingExplanationResponse>>({});
  const [proposals, setProposals] = useState<Record<string, FixProposalResponse>>({});
  const controllers = useRef(new Map<string, AbortController>());

  useEffect(() => () => {
    controllers.current.forEach((controller) => controller.abort());
    controllers.current.clear();
  }, []);

  const runAction = async <T,>(
    key: string,
    label: string,
    operation: (signal: AbortSignal) => Promise<T>,
    onSuccess: (result: T) => void
  ) => {
    if (!sourceFile || pendingActions[key] || controllers.current.has(key)) return;
    const controller = new AbortController();
    controllers.current.set(key, controller);
    setPendingActions((current) => ({ ...current, [key]: label }));
    setActionErrors((current) => ({ ...current, [key]: '' }));
    try {
      const result = await operation(controller.signal);
      if (!controller.signal.aborted && controllers.current.get(key) === controller) onSuccess(result);
    } catch (error) {
      if (!controller.signal.aborted && controllers.current.get(key) === controller) {
        setActionErrors((current) => ({ ...current, [key]: getUserFriendlyError(error, 'fix') }));
      }
    } finally {
      if (controllers.current.get(key) === controller) {
        controllers.current.delete(key);
        setPendingActions((current) => {
          const next = { ...current };
          delete next[key];
          return next;
        });
      }
    }
  };

  const downloadCorrectedSource = (result: FixResponse) => {
    if (!result.success || typeof result.fixed_code !== 'string' || !sourceFile) return;
    const baseName = sourceFile.name.replace(/\.[^.]+$/, '');
    const suffix = sourceFile.name.toLowerCase().endsWith('.py') ? '.py' : sourceFile.name.match(/\.[^.]+$/)?.[0] ?? '.txt';
    const mimeType = sourceFile.name.toLowerCase().endsWith('.py') ? 'text/x-python;charset=utf-8' : 'text/plain;charset=utf-8';
    const url = URL.createObjectURL(new Blob([result.fixed_code], { type: mimeType }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${baseName}_fixed${suffix}`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
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
          : `finding-${finding.file}:${finding.line}:${finding.category}:${index}`;
        const isFixSupported = Boolean(sourceFile && supportsFindingAutofix(sourceFile.name, finding.language, finding.analyzer, finding.category));
        const actionBusy = Boolean(pendingActions[key]);

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

                {sourceFile && (
                  <div className="finding-actions" aria-label="Finding actions">
                    {isFixSupported && (
                      <button className="btn btn--secondary btn--small" type="button" disabled={actionBusy}
                        onClick={() => void runAction(key, 'fix', (signal) => fixFinding(sourceFile, finding, signal), (result) => setFixResults((current) => ({ ...current, [key]: result })))}>
                        {pendingActions[key] === 'fix' ? 'Fixing finding...' : 'Fix This Bug'}
                      </button>
                    )}
                    <button className="btn btn--secondary btn--small" type="button" disabled={actionBusy}
                      onClick={() => void runAction(key, 'explain', (signal) => explainFinding(sourceFile, finding, signal), (result) => setExplanations((current) => ({ ...current, [key]: result })))}>
                      {pendingActions[key] === 'explain' ? 'Explaining...' : 'Explain with Ollama'}
                    </button>
                    <button className="btn btn--secondary btn--small" type="button" disabled={actionBusy}
                      onClick={() => void runAction(key, 'propose', (signal) => proposeFindingFix(sourceFile, finding, signal), (result) => setProposals((current) => ({ ...current, [key]: result })))}>
                      {pendingActions[key] === 'propose' ? 'Preparing proposal...' : 'Suggest Complex Fix'}
                    </button>
                    {actionErrors[key] && <div className="error-banner" role="alert">{actionErrors[key]}</div>}

                    {fixResults[key] && (
                      <div className="finding-detail__message" aria-live="polite">
                        <strong>{fixResults[key].status.replaceAll('_', ' ')}</strong>
                        <p>{fixResults[key].message}</p>
                        {fixResults[key].selected_resolved !== null && fixResults[key].selected_resolved !== undefined && <p>Selected finding: {fixResults[key].selected_resolved ? 'resolved' : 'still present'}</p>}
                        <p>Original: {fixResults[key].original_count} · Resolved: {fixResults[key].resolved_count} · Remaining: {fixResults[key].remaining_count}</p>
                        {fixResults[key].scope_note && <p>{fixResults[key].scope_note}</p>}
                        {fixResults[key].remaining_findings.length > 0 && <ul>{fixResults[key].remaining_findings.map((item, resultIndex) => <li key={`${item.code}-${item.location.row}-${resultIndex}`}>{item.code ?? 'Finding'}: {item.message} (line {item.location.row})</li>)}</ul>}
                        {fixResults[key].success && typeof fixResults[key].fixed_code === 'string' && <button className="btn btn--secondary btn--small" type="button" onClick={() => downloadCorrectedSource(fixResults[key])}>Download Fixed File</button>}
                      </div>
                    )}

                    {explanations[key] && (
                      <div className="finding-detail__message" aria-live="polite">
                        <strong>Ollama explanation · generated interpretation</strong>
                        <p><strong>What it means:</strong> {explanations[key].meaning}</p>
                        <p><strong>Why reported:</strong> {explanations[key].why_reported}</p>
                        <p><strong>Potential impact:</strong> {explanations[key].impact}</p>
                        <p><strong>Suggested correction:</strong> {explanations[key].suggested_correction}</p>
                        <p><strong>Correction type:</strong> {explanations[key].correction_kind.replaceAll('_', ' ')}</p>
                        <pre>{explanations[key].source_context}</pre>
                      </div>
                    )}

                    {proposals[key] && (
                      <div className="finding-detail__message" aria-live="polite">
                        <strong>{fixResults[key]?.proposal_accepted ? 'Proposal accepted' : 'Review required · proposal only · not applied'}</strong>
                        <p>{proposals[key].summary}</p>
                        {proposals[key].risks.length > 0 && <ul>{proposals[key].risks.map((risk, riskIndex) => <li key={riskIndex}>{risk}</li>)}</ul>}
                        <pre>{proposals[key].diff}</pre>
                        {finding.language.toLowerCase() === 'python' && finding.analyzer.toLowerCase() === 'ruff' ? (
                          <button className="btn btn--secondary btn--small" type="button" disabled={actionBusy || Boolean(pendingActions[`${key}-apply`])}
                            onClick={() => void runAction(`${key}-apply`, 'apply', (signal) => applyFindingProposal(sourceFile, finding, proposals[key], signal), (result) => setFixResults((current) => ({ ...current, [key]: result })))}>
                            Accept and Verify Proposal
                          </button>
                        ) : <p>Proposal application is currently limited to Python, where BUGSLASH can verify the result locally.</p>}
                      </div>
                    )}
                  </div>
                )}

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
