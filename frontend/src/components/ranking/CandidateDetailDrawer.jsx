import React, { useState } from 'react';
import { useApp } from '../../context/AppContext.jsx';
import ExperienceExplainabilitySection from './ExperienceExplainabilitySection.jsx';

/**
 * Renders structured diagnostic notices when a category has no evidence items.
 * Clearly distinguishes between not-applicable categories, technical service failures,
 * and valid zero-score outcomes, without claiming a candidate lacks a skill during service failures.
 */
function CategoryDiagnosticState({ breakdown, defaultMessage }) {
  if (!breakdown) {
    return <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{defaultMessage}</div>;
  }

  const { status, score, notes } = breakdown;
  const isNotApplicable = status === 'not_applicable';
  const isUnavailable = status === 'unavailable';
  const isValidZero = score === 0 && !isUnavailable && !isNotApplicable;

  if (isNotApplicable) {
    return (
      <div
        className="category-diagnostic-notice"
        style={{
          background: 'var(--bg-surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '0.85rem',
          fontSize: '0.85rem',
        }}
        role="region"
        aria-label="Category not applicable notice"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <span className="badge badge-neutral">Not Applicable</span>
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Excluded from Evaluation</span>
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          {notes || 'This category is not defined in the active Job Description and has been excluded from scoring.'}
        </div>
      </div>
    );
  }

  if (isUnavailable) {
    return (
      <div
        className="category-diagnostic-notice"
        style={{
          background: 'var(--bg-surface-subtle)',
          border: '1px solid var(--danger-border, rgba(239, 68, 68, 0.3))',
          borderRadius: 'var(--radius-md)',
          padding: '0.85rem',
          fontSize: '0.85rem',
        }}
        role="region"
        aria-label="Evaluation unavailable notice"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <span className="badge badge-danger">Evaluation Unavailable</span>
          <span style={{ fontWeight: 600, color: 'var(--danger-text)' }}>Technical Service Failure</span>
        </div>
        <div style={{ color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
          {notes || 'Evaluation could not complete for this category due to an upstream service failure.'}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Note: This score is withheld due to a technical evaluation failure; it does not indicate that the candidate lacks this qualification.
        </div>
      </div>
    );
  }

  if (isValidZero && notes) {
    return (
      <div
        className="category-diagnostic-notice"
        style={{
          background: 'var(--bg-surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '0.85rem',
          fontSize: '0.85rem',
        }}
        role="region"
        aria-label="Zero score qualification notice"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
          <span className="badge badge-warning">Zero Alignment</span>
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>No Qualifying Evidence</span>
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>{notes}</div>
      </div>
    );
  }

  return (
    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
      {notes || defaultMessage}
    </div>
  );
}

export default function CandidateDetailDrawer() {
  const { selectedCandidate, setSelectedCandidate } = useApp();
  const [activeCategoryTab, setActiveCategoryTab] = useState('skills');

  // Keyboard navigation: Escape key closes the drawer
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSelectedCandidate(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setSelectedCandidate]);

  if (!selectedCandidate) return null;

  const {
    filename,
    name,
    archetype,
    edge_markers = [],
    is_synthetic_demo = false,
    legacy_score,
    evidence_score,
    score_delta,
    legacy_experience_score,
    evidence_experience_score,
    rank,
    final_score,
    component_scores = {},
    breakdown = {},
    experience_diagnostic,
    warnings = [],
    errors = [],
  } = selectedCandidate;

  const skillsBreakdown = breakdown.required_skills;
  const respBreakdown = breakdown.responsibilities;
  const toolsBreakdown = breakdown.tools_and_technologies;
  const expBreakdown = breakdown.experience_relevance;

  // Section-routing explainability: Tools mentioned in employment history but absent from project portfolio
  // Grounded strictly in supported backend notes and score values (legacy synthetic properties removed)
  const hasToolsInExpOnly =
    toolsBreakdown?.notes === 'Tools mentioned in employment history but not in project portfolio.' ||
    (toolsBreakdown?.score === 0 &&
      toolsBreakdown?.notes?.toLowerCase().includes('employment history'));

  return (
    <div className="drawer-backdrop" onClick={() => setSelectedCandidate(null)} role="presentation">
      <div
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="candidate-drawer-title"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
              <span className={`rank-badge ${rank === 1 ? 'rank-1' : rank === 2 ? 'rank-2' : rank === 3 ? 'rank-3' : 'rank-default'}`}>
                {rank ? `#${rank}` : '-'}
              </span>
              <h2 id="candidate-drawer-title" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {name || filename}
              </h2>
              {is_synthetic_demo && (
                <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                  🧪 Synthetic Profile
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span>{is_synthetic_demo ? `File: ${filename}` : 'Candidate Score Breakdown & Qualification Evidence'}</span>
              {archetype && (
                <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                  {archetype}
                </span>
              )}
              {edge_markers.map((marker) => (
                <span key={marker} className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                  Edge: {marker}
                </span>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                JD Alignment Score
              </div>
              <div
                style={{
                  fontSize: '1.4rem',
                  fontWeight: 700,
                  color: final_score != null ? 'var(--success-text)' : 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {final_score != null ? final_score.toFixed(2) : 'Unavailable'}
              </div>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedCandidate(null)}
              aria-label="Close Candidate Details Dialog"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="drawer-body">
          {/* Ethical AI Disclaimer */}
          <div className="disclaimer-banner">
            <svg style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <strong>Objective Alignment Measurement:</strong> This score represents deterministic qualification alignment against the active Job Description criteria. It does not represent a statistical probability of hiring success.
            </div>
          </div>

          {/* Milestone 3: Dual-Engine Score Comparison Card */}
          {is_synthetic_demo && (
            <div
              style={{
                marginBottom: '1.5rem',
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                borderRadius: 'var(--radius-lg)',
                padding: '1rem 1.25rem',
              }}
              data-testid="synthetic-dual-scoring-card"
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary-200)', textTransform: 'uppercase' }}>
                  Milestone 3 • Dual Engine Score Comparison
                </span>
                <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                  100% In-Memory Synthetic
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', textAlign: 'center' }}>
                <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Legacy Categorical</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }} data-testid="drawer-legacy-score">
                    {legacy_score != null ? legacy_score.toFixed(2) : '-'}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    Exp: {legacy_experience_score != null ? legacy_experience_score.toFixed(1) : '-'}
                  </div>
                </div>

                <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Evidence-Based (Phase 5)</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary-200)', fontFamily: 'var(--font-mono)' }} data-testid="drawer-evidence-score">
                    {evidence_score != null ? evidence_score.toFixed(2) : '-'}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    Exp: {evidence_experience_score != null ? evidence_experience_score.toFixed(1) : '-'}
                  </div>
                </div>

                <div style={{ background: 'var(--bg-surface)', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Score Delta (Δ)</div>
                  <div
                    style={{
                      fontSize: '1.2rem',
                      fontWeight: 700,
                      fontFamily: 'var(--font-mono)',
                      color: score_delta > 0 ? 'var(--success-text)' : score_delta < 0 ? 'var(--danger-text)' : 'var(--text-muted)',
                    }}
                    data-testid="drawer-score-delta"
                  >
                    {score_delta != null ? (score_delta > 0 ? `+${score_delta.toFixed(2)}` : score_delta.toFixed(2)) : '-'}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    {score_delta > 0 ? 'Evidence higher' : score_delta < 0 ? 'Legacy higher' : 'Equal scores'}
                  </div>
                </div>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.75rem', lineHeight: '1.4' }}>
                {score_delta !== 0 ? (
                  <>
                    <strong>Why did the score change?</strong>{' '}
                    The legacy engine maps duration to four discrete buckets (0.25, 0.5, 0.75, 1.0), whereas
                    the Phase 5 engine computes continuous saturation against the specific JD experience paradigm (Bounded, Min-Only, Max-Only, or G1-C).
                  </>
                ) : (
                  <>Both engines produced identical alignment for this candidate’s qualifications.</>
                )}
              </div>
            </div>
          )}

          {/* Component Score Summary Grid */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
              Component Score Breakdown
            </h3>
            <div className="grid-4" style={{ gap: '0.75rem' }}>
              <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Skills (25%)</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  {component_scores.required_skills != null ? component_scores.required_skills.toFixed(1) : '-'}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                  Weight: {skillsBreakdown?.normalized_weight ? `${(skillsBreakdown.normalized_weight * 100).toFixed(0)}%` : '25%'}
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Responsibilities (30%)</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  {component_scores.responsibilities != null ? component_scores.responsibilities.toFixed(1) : '-'}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                  Weight: {respBreakdown?.normalized_weight ? `${(respBreakdown.normalized_weight * 100).toFixed(0)}%` : '30%'}
                </div>
              </div>

              <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Tools & Tech (10%)</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  {component_scores.tools_and_technologies != null ? component_scores.tools_and_technologies.toFixed(1) : '-'}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                  Weight: {toolsBreakdown?.normalized_weight ? `${(toolsBreakdown.normalized_weight * 100).toFixed(0)}%` : '10%'}
                </div>
                {hasToolsInExpOnly && (
                  <div
                    style={{
                      fontSize: '0.68rem',
                      color: 'var(--primary-300, #93c5fd)',
                      marginTop: '0.25rem',
                      fontWeight: 500,
                    }}
                    title="Tools mentioned in employment history but not in project portfolio."
                  >
                    Found in employment history
                  </div>
                )}
              </div>

              <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Experience (35%)</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                  {component_scores.experience_relevance != null ? component_scores.experience_relevance.toFixed(1) : '-'}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                  Weight: {expBreakdown?.normalized_weight ? `${(expBreakdown.normalized_weight * 100).toFixed(0)}%` : '35%'}
                </div>
              </div>
            </div>
          </div>

          {/* Experience Duration Diagnostic */}
          {experience_diagnostic && (
            <div style={{ background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1rem', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Professional Duration Check
                </span>
                <span className={`badge ${experience_diagnostic.minimum_duration_satisfied ? 'badge-success' : 'badge-warning'}`}>
                  {experience_diagnostic.minimum_duration_satisfied ? 'Duration Satisfied' : 'Duration Insufficient'}
                </span>
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                Candidate has{' '}
                <strong>
                  {experience_diagnostic.relevant_duration_years != null && !isNaN(Number(experience_diagnostic.relevant_duration_years))
                    ? `${Number(experience_diagnostic.relevant_duration_years).toFixed(1)} years`
                    : 'Unavailable'}
                </strong>{' '}
                of relevant domain experience
                {experience_diagnostic.minimum_years != null && !isNaN(Number(experience_diagnostic.minimum_years))
                  ? ` (Requirement: ${Number(experience_diagnostic.minimum_years)} yrs minimum)`
                  : ''}.
              </div>
              {experience_diagnostic.diagnostic_message && (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  {experience_diagnostic.diagnostic_message}
                </div>
              )}
            </div>
          )}

          {/* Evidence Category Tabs */}
          <div className="tab-list">
            <button
              type="button"
              className={`tab-btn ${activeCategoryTab === 'skills' ? 'active' : ''}`}
              onClick={() => setActiveCategoryTab('skills')}
            >
              Required Skills
            </button>
            <button
              type="button"
              className={`tab-btn ${activeCategoryTab === 'responsibilities' ? 'active' : ''}`}
              onClick={() => setActiveCategoryTab('responsibilities')}
            >
              Responsibilities
            </button>
            <button
              type="button"
              className={`tab-btn ${activeCategoryTab === 'tools' ? 'active' : ''}`}
              onClick={() => setActiveCategoryTab('tools')}
            >
              Tools & Technologies
            </button>
            <button
              type="button"
              className={`tab-btn ${activeCategoryTab === 'experience' ? 'active' : ''}`}
              onClick={() => setActiveCategoryTab('experience')}
            >
              Experience Evidence
            </button>
          </div>

          {/* TAB 1: Skills Evidence */}
          {activeCategoryTab === 'skills' && (
            <div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                Extracted candidate skills matched against required role proficiencies:
              </div>
              {skillsBreakdown?.evidence?.length ? (
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Required Skill</th>
                        <th>Status</th>
                        <th>Matched Resume Skill</th>
                      </tr>
                    </thead>
                    <tbody>
                      {skillsBreakdown.evidence.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{item.required_skill}</td>
                          <td>
                            <span className={`badge ${item.matched ? 'badge-success' : 'badge-danger'}`}>
                              {item.matched ? 'Matched' : 'Missing'}
                            </span>
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                            {item.matched_resume_skill || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <CategoryDiagnosticState
                  breakdown={skillsBreakdown}
                  defaultMessage="No individual skill evidence recorded."
                />
              )}
            </div>
          )}

          {/* TAB 2: Responsibilities Evidence */}
          {activeCategoryTab === 'responsibilities' && (
            <div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                Semantic similarity against Job Description responsibilities (BGE-large 0.65 threshold):
              </div>
              {respBreakdown?.evidence?.length ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {respBreakdown.evidence.map((item, idx) => (
                    <div key={idx} style={{ background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.4rem' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{item.requirement_text}</span>
                        <span className={`badge ${item.qualifies ? 'badge-success' : 'badge-warning'}`}>
                          {item.qualifies ? 'Qualifies' : 'Below Threshold'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: '0.4rem' }}>
                        "{item.best_matching_passage || 'No matching passage found'}"
                      </div>
                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>Raw Cosine: {item.raw_similarity ? item.raw_similarity.toFixed(3) : '0.000'}</span>
                        <span>Normalized Relevance: {item.normalized_relevance ? item.normalized_relevance.toFixed(3) : '0.000'}</span>
                        <span>Section: {item.best_matching_section || 'general'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <CategoryDiagnosticState
                  breakdown={respBreakdown}
                  defaultMessage="No responsibilities evidence recorded."
                />
              )}
            </div>
          )}

          {/* TAB 3: Tools & Technologies Evidence */}
          {activeCategoryTab === 'tools' && (
            <div>
              {/* Section-Routing Contextual Callout */}
              {hasToolsInExpOnly && (
                <div
                  className="section-routing-callout"
                  role="region"
                  aria-label="Section routing explainability callout"
                >
                  <svg
                    className="section-routing-callout-icon"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div>
                    <div className="section-routing-callout-title">
                      Tools mentioned in employment history but not in project portfolio.
                    </div>
                    <div className="section-routing-callout-text">
                      TalentAI evaluates tools and technologies specifically against project portfolio evidence to verify standalone applied project work. Although relevant tool proficiencies are documented in this candidate's employment history, section routing excludes non-project sections from this component score. This indicates missing project documentation rather than an absence of technical proficiency, and does not by itself indicate the candidate is unqualified.
                    </div>
                  </div>
                </div>
              )}

              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                Extracted project evidence supporting required frameworks and tools:
              </div>
              {toolsBreakdown?.evidence?.length ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {toolsBreakdown.evidence.map((item, idx) => (
                    <div key={idx} style={{ background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.4rem' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{item.requirement_text}</span>
                        <span className={`badge ${item.qualifies ? 'badge-success' : 'badge-warning'}`}>
                          {item.qualifies ? 'Qualifies' : 'Below Threshold'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: '0.4rem' }}>
                        "{item.best_matching_passage || 'No project passage found'}"
                      </div>
                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span>Raw Similarity: {item.raw_similarity ? item.raw_similarity.toFixed(3) : '0.000'}</span>
                        <span>Normalized Score: {item.normalized_relevance ? item.normalized_relevance.toFixed(3) : '0.000'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : hasToolsInExpOnly ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  No qualifying project evidence found for defined tools and technologies.
                </div>
              ) : (
                <CategoryDiagnosticState
                  breakdown={toolsBreakdown}
                  defaultMessage="No tool evidence recorded."
                />
              )}
            </div>
          )}

          {/* TAB 4: Experience Evidence */}
          {activeCategoryTab === 'experience' && (
            expBreakdown?.status === 'not_applicable' || expBreakdown?.status === 'unavailable' ? (
              <CategoryDiagnosticState
                breakdown={expBreakdown}
                defaultMessage="No experience evidence recorded."
              />
            ) : (
              <ExperienceExplainabilitySection
                expBreakdown={expBreakdown}
                experienceDiagnostic={experience_diagnostic}
                candidateWarnings={warnings}
                candidateErrors={errors}
              />
            )
          )}

          {/* Technical Errors & Evaluation Diagnostics */}
          {(errors.length > 0 || warnings.length > 0) && (
            <div style={{ marginTop: '1.5rem' }}>
              {errors.length > 0 && (
                <div
                  style={{
                    marginBottom: warnings.length > 0 ? '1rem' : '0',
                    background: 'var(--danger-bg, rgba(239, 68, 68, 0.12))',
                    border: '1px solid var(--danger-border, rgba(239, 68, 68, 0.3))',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.75rem 1rem',
                  }}
                  role="alert"
                >
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: 'var(--danger-text, #f87171)',
                      textTransform: 'uppercase',
                      marginBottom: '0.35rem',
                    }}
                  >
                    Technical Evaluation Errors
                  </div>
                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-primary)', margin: 0 }}>
                    {errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {warnings.length > 0 && (
                <div>
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: 'var(--warning-text)',
                      textTransform: 'uppercase',
                      marginBottom: '0.4rem',
                    }}
                  >
                    Evaluation Diagnostics
                  </div>
                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
