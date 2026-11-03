import React, { useState, useMemo, useEffect } from 'react';
import { useApp } from '../../context/AppContext.jsx';
import CandidateDetailDrawer from './CandidateDetailDrawer.jsx';

export default function RankingDashboardView() {
  const {
    rankingJob,
    rankingResult,
    isRankingActive,
    rankingSubmitting,
    triggerRanking,
    setSelectedCandidate,
    setActiveTab,
    systemError,
    topN,
    setTopN,
    // Synthetic Demo sandbox
    isDemoMode,
    demoPresetId,
    demoScoringMode,
    demoPresets,
    isDemoLoading,
    loadDemoPresets,
    switchDemoScoringMode,
    switchDemoPreset,
    exitDemoMode,
  } = useApp();

  const [searchQuery, setSearchQuery] = useState('');
  const [minScoreFilter, setMinScoreFilter] = useState(0);
  const [sortField, setSortField] = useState('rank'); // 'rank' | 'final_score' | 'filename'
  const [sortAsc, setSortAsc] = useState(true);

  // Top-N state with string input allowing uninterrupted typing
  const [topNInput, setTopNInput] = useState(() => String(topN ?? 20));

  useEffect(() => {
    if (topN !== undefined && topN !== null) {
      setTopNInput(String(topN));
    }
  }, [topN]);

  const presetsList = demoPresets || [];

  useEffect(() => {
    if (isDemoMode && presetsList.length === 0 && loadDemoPresets) {
      loadDemoPresets();
    }
  }, [isDemoMode, presetsList.length, loadDemoPresets]);

  const rankedCandidates = rankingResult?.ranked_candidates ?? [];
  const unrankedCandidates = rankingResult?.unranked_candidates ?? [];

  // Filter and sort candidates
  const filteredCandidates = useMemo(() => {
    return rankedCandidates
      .filter((c) => {
        if (minScoreFilter > 0 && (c.final_score ?? 0) < minScoreFilter) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          return c.filename.toLowerCase().includes(q);
        }
        return true;
      })
      .sort((a, b) => {
        if (sortField === 'rank') {
          return sortAsc ? (a.rank ?? 999) - (b.rank ?? 999) : (b.rank ?? 999) - (a.rank ?? 999);
        }
        if (sortField === 'final_score') {
          return sortAsc ? (a.final_score ?? 0) - (b.final_score ?? 0) : (b.final_score ?? 0) - (a.final_score ?? 0);
        }
        if (sortField === 'filename') {
          return sortAsc ? a.filename.localeCompare(b.filename) : b.filename.localeCompare(a.filename);
        }
        return 0;
      });
  }, [rankedCandidates, searchQuery, minScoreFilter, sortField, sortAsc]);

  // Validation: N must be a positive integer
  const parsedN = parseInt(topNInput, 10);
  const isValidN = !isNaN(parsedN) && parsedN > 0 && String(parsedN) === topNInput.trim();

  // Effective N: clamped to available filtered count
  const effectiveN = useMemo(() => {
    if (!isValidN) {
      return filteredCandidates.length; // safe fallback when input is invalid
    }
    return Math.min(parsedN, filteredCandidates.length);
  }, [isValidN, parsedN, filteredCandidates.length]);

  // Displayed candidates: top N candidates in existing rank order
  const displayedCandidates = useMemo(() => {
    if (!isValidN) {
      return filteredCandidates;
    }
    return filteredCandidates.slice(0, effectiveN);
  }, [filteredCandidates, isValidN, effectiveN]);

  const handleTopNInputChange = (e) => {
    const val = e.target.value;
    setTopNInput(val);
    const num = parseInt(val, 10);
    if (!isNaN(num) && num > 0 && String(num) === val.trim()) {
      if (setTopN) setTopN(num);
    }
  };

  const handlePresetNClick = (presetVal) => {
    const safeVal = Math.max(1, presetVal);
    setTopNInput(String(safeVal));
    if (setTopN) setTopN(safeVal);
  };

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(field === 'rank');
    }
  };

  const getScoreClass = (score) => {
    if (score == null) return 'score-unavailable';
    if (score >= 75) return 'score-high';
    if (score >= 50) return 'score-mid';
    return 'score-low';
  };

  return (
    <div className="page-body">
      {/* SYNTHETIC DEMO TOP BANNER & COMPARISON CONTROLS */}
      {isDemoMode && (
        <div
          className="demo-dashboard-banner"
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: 'var(--radius-lg)',
            padding: '1.25rem',
            marginBottom: '1.5rem',
          }}
          data-testid="demo-ranking-banner"
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <span className="badge badge-warning" style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}>
                🧪 SYNTHETIC DEMO SANDBOX
              </span>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {rankingResult?.preset_title || demoPresetId}
              </span>
              <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                {rankingResult?.paradigm || 'Bounded'}
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {rankingResult?.family} • <strong>20 Synthetic Profiles</strong>
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <span>Preset:</span>
                <select
                  className="form-control"
                  style={{ padding: '0.35rem 0.65rem', fontSize: '0.82rem', width: 'auto', minWidth: '200px' }}
                  value={demoPresetId || ''}
                  onChange={(e) => switchDemoPreset(e.target.value)}
                  disabled={isDemoLoading}
                  data-testid="demo-preset-dropdown"
                >
                  {presetsList.map((p) => (
                    <option key={p.jd_id} value={p.jd_id}>
                      {p.jd_id}: {p.title}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={exitDemoMode}
              >
                Exit Demo Mode
              </button>
            </div>
          </div>

          {/* Milestone 3: Legacy Categorical vs. Evidence-Based Experience Segmented Toggle */}
          <div
            style={{
              marginTop: '1rem',
              paddingTop: '0.85rem',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Scoring Engine Evaluation:
              </span>
              <div className="segmented-control" role="group" aria-label="Scoring Mode Toggle">
                <button
                  type="button"
                  className={`segmented-button ${demoScoringMode === 'legacy' ? 'active' : ''}`}
                  onClick={() => switchDemoScoringMode('legacy')}
                  disabled={isDemoLoading}
                  data-testid="toggle-mode-legacy"
                >
                  🏛️ Legacy Categorical
                </button>
                <button
                  type="button"
                  className={`segmented-button ${demoScoringMode === 'evidence' ? 'active' : ''}`}
                  onClick={() => switchDemoScoringMode('evidence')}
                  disabled={isDemoLoading}
                  data-testid="toggle-mode-evidence"
                >
                  🔬 Evidence-Based Experience
                </button>
              </div>

              {isDemoLoading && (
                <span style={{ fontSize: '0.78rem', color: 'var(--primary-200)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <svg className="spinner" style={{ width: '13px', height: '13px' }} fill="none" viewBox="0 0 24 24">
                    <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Re-evaluating cohort in memory...
                </span>
              )}
            </div>

            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Formula: 0.25(Skills) + 0.30(Resp) + 0.10(Tools) + 0.35(Exp). Δ = Evidence - Legacy.
            </div>
          </div>
        </div>
      )}

      <div className="page-header">
        <div>
          <h1 className="page-title">
            {isDemoMode ? 'Synthetic Candidate Shortlist' : 'Candidate Shortlist & Ranking'}
          </h1>
          <p className="page-description">
            {isDemoMode
              ? `Evaluating 20 synthetic candidate profiles against ${demoPresetId}. 100% in-memory.`
              : 'Objective candidate alignment evaluated against the active Job Description.'}
          </p>
        </div>

        <div>
          {isDemoMode ? (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={triggerRanking}
              disabled={isDemoLoading}
            >
              {isDemoLoading ? 'Reloading...' : 'Reload Synthetic Cohort'}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              onClick={triggerRanking}
              disabled={isRankingActive || rankingSubmitting}
            >
              {isRankingActive ? (
                <>
                  <svg className="spinner" style={{ width: '14px', height: '14px' }} fill="none" viewBox="0 0 24 24">
                    <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Evaluating Resumes...
                </>
              ) : (
                'Re-Rank Active Batch'
              )}
            </button>
          )}
        </div>
      </div>

      {systemError && (
        <div className="alert alert-danger" role="alert">
          {systemError}
        </div>
      )}

      {/* IN-FLIGHT RANKING PROGRESS TRACKER */}
      {isRankingActive && rankingJob && (
        <div className="progress-card">
          <div className="progress-header">
            <div>
              <span style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary)' }}>
                Background Ranking Job in Progress
              </span>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Job ID: {rankingJob.job_id} • Status: {rankingJob.status}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span className="badge badge-info">
                {rankingJob.completed_count} / {rankingJob.total_eligible} Candidates Evaluated
              </span>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary-200)', fontFamily: 'var(--font-mono)' }}>
                {rankingJob.progress_percentage.toFixed(0)}%
              </div>
            </div>
          </div>

          <div className="progress-track">
            <div
              className="progress-fill"
              style={{ width: `${rankingJob.progress_percentage}%` }}
            />
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Running local LLM skill extraction, BGE semantic retrieval, and experience domain alignment. Page can be refreshed safely; progress will resume automatically.
          </div>
        </div>
      )}

      {/* INCOMPLETE CANDIDATES ALERT BANNER */}
      {unrankedCandidates.length > 0 && (
        <div className="alert alert-warning" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong>Notice: {unrankedCandidates.length} candidate(s) could not be completely scored.</strong>
            <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
              To ensure ethical fairness, they are segregated from the shortlist and have not been assigned an artificial 0 score.
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setActiveTab('incomplete')}
          >
            View Incomplete Candidates &rarr;
          </button>
        </div>
      )}

      {/* FILTER & CONTROLS TOOLBAR */}
      {rankedCandidates.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              type="text"
              className="form-control"
              style={{ width: '220px' }}
              placeholder="Search candidate filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <span>Min Score:</span>
              <input
                type="range"
                min="0"
                max="90"
                step="5"
                value={minScoreFilter}
                onChange={(e) => setMinScoreFilter(Number(e.target.value))}
              />
              <span style={{ fontFamily: 'var(--font-mono)', minWidth: '30px' }}>{minScoreFilter}</span>
            </div>

            {/* Top-N Candidate Display Control */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <label htmlFor="top-n-input" style={{ fontWeight: 600 }}>
                  Show Top:
                </label>
                <input
                  id="top-n-input"
                  type="number"
                  min="1"
                  step="1"
                  className="form-control"
                  style={{
                    width: '75px',
                    padding: '0.28rem 0.5rem',
                    fontSize: '0.85rem',
                    borderColor: !isValidN ? 'var(--danger-500, #ef4444)' : undefined,
                  }}
                  value={topNInput}
                  onChange={handleTopNInputChange}
                  aria-label="Number of top candidates to display"
                  data-testid="top-n-input"
                />
              </div>

              <div className="btn-group" role="group" aria-label="Quick Top-N presets" style={{ display: 'flex', gap: '0.2rem' }}>
                {[10, 20, 50, 100].map((presetN) => (
                  <button
                    key={presetN}
                    type="button"
                    className={`btn btn-sm ${isValidN && parsedN === presetN ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '0.2rem 0.45rem', fontSize: '0.75rem' }}
                    onClick={() => handlePresetNClick(presetN)}
                    data-testid={`quick-top-${presetN}`}
                  >
                    {presetN}
                  </button>
                ))}
                <button
                  type="button"
                  className={`btn btn-sm ${isValidN && parsedN >= rankedCandidates.length && rankedCandidates.length > 0 ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '0.2rem 0.45rem', fontSize: '0.75rem' }}
                  onClick={() => handlePresetNClick(rankedCandidates.length || 50)}
                  data-testid="quick-top-all"
                >
                  All ({rankedCandidates.length})
                </button>
              </div>

              {!isValidN && (
                <span
                  className="text-danger"
                  style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 500 }}
                  role="alert"
                  data-testid="top-n-validation-error"
                >
                  Please enter a positive whole number (min 1).
                </span>
              )}
            </div>
          </div>

          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }} data-testid="ranked-candidates-count">
            Showing {displayedCandidates.length} of {rankedCandidates.length} ranked candidates
          </div>
        </div>
      )}

      {/* CANDIDATE RANKING TABLE */}
      {displayedCandidates.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('rank')}>
                  Rank {sortField === 'rank' ? (sortAsc ? '▲' : '▼') : ''}
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('filename')}>
                  {isDemoMode ? 'Synthetic Candidate Profile' : 'Candidate Filename'} {sortField === 'filename' ? (sortAsc ? '▲' : '▼') : ''}
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => toggleSort('final_score')}>
                  {isDemoMode
                    ? `Score (${demoScoringMode === 'evidence' ? 'Evidence-Based' : 'Legacy'})`
                    : 'JD Alignment Score'}{' '}
                  {sortField === 'final_score' ? (sortAsc ? '▲' : '▼') : ''}
                </th>
                {isDemoMode && (
                  <th title="Difference between Evidence-Based and Legacy score (Δ = Evidence - Legacy)">
                    Score Delta (Δ)
                  </th>
                )}
                <th>Skills (25%)</th>
                <th>Responsibilities (30%)</th>
                <th>Tools (10%)</th>
                <th>Experience (35%)</th>
                <th>Experience Duration</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {displayedCandidates.map((candidate) => {
                const comp = candidate.component_scores || {};
                const diag = candidate.experience_diagnostic;
                const score = candidate.final_score;
                const delta = candidate.score_delta;

                return (
                  <tr key={candidate.filename || candidate.candidate_id}>
                    <td>
                      <span className={`rank-badge ${candidate.rank === 1 ? 'rank-1' : candidate.rank === 2 ? 'rank-2' : candidate.rank === 3 ? 'rank-3' : 'rank-default'}`}>
                        {candidate.rank ?? '-'}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {candidate.name || candidate.filename}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', gap: '0.4rem', alignItems: 'center', marginTop: '0.15rem' }}>
                        <span>ID: {candidate.candidate_id || (candidate.upload_id ? candidate.upload_id.substring(0, 14) + '...' : '')}</span>
                        {candidate.archetype && (
                          <span className="badge badge-neutral" style={{ fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}>
                            {candidate.archetype}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`score-pill ${getScoreClass(score)}`} data-testid={`score-${candidate.candidate_id || candidate.filename}`}>
                        {score != null ? score.toFixed(2) : 'N/A'}
                      </span>
                    </td>
                    {isDemoMode && (
                      <td>
                        {delta != null ? (
                          <span
                            className={`delta-badge ${delta > 0 ? 'delta-pos' : delta < 0 ? 'delta-neg' : 'delta-zero'}`}
                            data-testid={`delta-${candidate.candidate_id || candidate.filename}`}
                          >
                            {delta > 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2)}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>-</span>
                        )}
                      </td>
                    )}
                    <td>
                      <div className="mini-progress-container">
                        <div className="mini-progress-track">
                          <div
                            className="mini-progress-bar"
                            style={{
                              width: `${comp.required_skills ?? 0}%`,
                              backgroundColor: 'var(--primary-500)',
                            }}
                          />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                          {comp.required_skills != null ? comp.required_skills.toFixed(0) : '-'}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="mini-progress-container">
                        <div className="mini-progress-track">
                          <div
                            className="mini-progress-bar"
                            style={{
                              width: `${comp.responsibilities ?? 0}%`,
                              backgroundColor: 'var(--info-text)',
                            }}
                          />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                          {comp.responsibilities != null ? comp.responsibilities.toFixed(0) : '-'}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="mini-progress-container">
                        <div className="mini-progress-track">
                          <div
                            className="mini-progress-bar"
                            style={{
                              width: `${comp.tools_and_technologies ?? 0}%`,
                              backgroundColor: '#818cf8',
                            }}
                          />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                          {comp.tools_and_technologies != null ? comp.tools_and_technologies.toFixed(0) : '-'}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="mini-progress-container">
                        <div className="mini-progress-track">
                          <div
                            className="mini-progress-bar"
                            style={{
                              width: `${comp.experience_relevance ?? 0}%`,
                              backgroundColor: 'var(--success-text)',
                            }}
                          />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                          {comp.experience_relevance != null ? comp.experience_relevance.toFixed(0) : '-'}
                        </span>
                      </div>
                    </td>
                    <td>
                      {diag ? (
                        <span className={`badge ${diag.minimum_duration_satisfied ? 'badge-success' : 'badge-warning'}`}>
                          {diag.relevant_duration_years.toFixed(1)} yrs {diag.minimum_duration_satisfied ? '✓' : '⚠️'}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>-</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => setSelectedCandidate(candidate)}
                      >
                        Explain
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        !isRankingActive && (
          <div className="card">
            <div className="card-body" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
              <svg style={{ width: '48px', height: '48px', color: 'var(--text-muted)', margin: '0 auto 1rem' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                No Ranking Results Available
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '440px', margin: '0 auto 1.5rem' }}>
                Run an explainable ranking job across the active candidate batch to generate transparent scores and qualification evidence.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={triggerRanking}
                disabled={isRankingActive || rankingSubmitting}
              >
                Start Ranking Job
              </button>
            </div>
          </div>
        )
      )}

      {/* Candidate Score Explainability Drawer */}
      <CandidateDetailDrawer />
    </div>
  );
}
