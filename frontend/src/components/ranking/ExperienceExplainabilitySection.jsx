import React from 'react';

/**
 * Safely format numeric values distinguishing genuine zero from unavailable/missing.
 * - 0.0 -> "0.000"
 * - null / undefined / NaN / "" -> "Unavailable"
 */
export function formatNumeric(val, decimals = 3) {
  if (val === null || val === undefined || isNaN(val) || val === '') {
    return 'Unavailable';
  }
  return Number(val).toFixed(decimals);
}

/**
 * Safely format duration years distinguishing genuine 0.0 from unavailable.
 * - 0.0 -> "0.0 yrs"
 * - null / undefined / NaN / "" -> "Unavailable"
 */
export function formatDurationYears(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val) || val === '') {
    return 'Unavailable';
  }
  return `${Number(val).toFixed(decimals)} yrs`;
}

/**
 * Safely format duration saturation target years distinguishing genuine target from unavailable.
 * - 5.0 -> "5.0 yrs" (or "5 yrs")
 * - null / undefined / NaN / "" -> "Unavailable" (Never "Unbounded")
 */
export function formatTargetYears(val) {
  if (val === null || val === undefined || isNaN(val) || val === '') {
    return 'Unavailable';
  }
  return `${val} yrs`;
}

/**
 * Safely format category weight percentage.
 * - 0.35 -> "35%"
 * - 0.3889 -> "38.89%"
 * - null / undefined / NaN / "" -> "Unavailable"
 */
export function formatWeight(val) {
  if (val === null || val === undefined || isNaN(val) || val === '') {
    return 'Unavailable';
  }
  const pct = Number(val) * 100;
  const rounded = Math.round(pct * 100) / 100;
  return Number.isInteger(rounded) ? `${rounded}%` : `${rounded.toFixed(2)}%`;
}

/**
 * Recruiter-facing explainability component for Experience Scoring.
 * Strictly adheres to Stage 5D and Stage 5D.1 hardening requirements:
 * 1. Exact provenance marker detection (never inferred from raw scores).
 * 2. Visual hierarchy: Summary -> Dual Metrics -> Domain Breakdown -> Supporting Evidence -> Diagnostics.
 * 3. Strict distinction between genuine 0.0 / 0.000 and "Unavailable".
 * 4. Saturation target null/missing displays "Unavailable", never converted to "Unbounded".
 * 5. Range status null/missing displays "Unavailable", never defaulted to "unspecified".
 * 6. Gate 1 (G1-C) alert displayed only when backend explicitly provides range_status = "unspecified".
 * 7. Original configured weight (35%) clearly distinguished from dynamically applied normalized weight.
 * 8. Weighted contribution displays the actual backend value without re-synthesizing via original weight.
 * 9. Exact global duration disclosure wording.
 * 10. Full backward compatibility with legacy categorical scoring.
 */
export default function ExperienceExplainabilitySection({
  expBreakdown,
  experienceDiagnostic,
  candidateWarnings = [],
  candidateErrors = [],
}) {
  const notes = expBreakdown?.notes || '';
  // Correction 1: Exact provenance marker match. Never infer from scores.
  const isEvidenceBased = notes.includes('Scoring method: evidence_based');

  // If breakdown is missing or unavailable/not_applicable, handle diagnostics
  if (!expBreakdown) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No experience evidence recorded.
      </div>
    );
  }

  // ===========================================================================
  // LEGACY PRESENTATION (Backward Compatibility)
  // ===========================================================================
  if (!isEvidenceBased) {
    return (
      <div className="legacy-experience-container">
        {/* Scoring Method Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <span className="badge badge-neutral" style={{ fontWeight: 600 }}>
            Legacy Categorical Scoring
          </span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Categorical relevance scoring without calibrated semantic similarity.
          </span>
        </div>

        <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          Evaluated candidate professional experience entries aligned with JD domain criteria:
        </div>

        {expBreakdown.evidence && expBreakdown.evidence.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {expBreakdown.evidence.map((item, idx) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-surface-subtle)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.85rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.35rem' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{item.criterion}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {item.supporting_role || 'Professional Role'} • {item.supporting_company || 'Employer'}
                    </div>
                  </div>
                  <span className={`badge ${item.supporting_decision === 'RELEVANT' ? 'badge-success' : 'badge-neutral'}`}>
                    {item.supporting_decision || 'Evaluated'}
                  </span>
                </div>
                {item.reason && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    {item.reason}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No individual role evidence recorded.
          </div>
        )}
      </div>
    );
  }

  // ===========================================================================
  // EVIDENCE-BASED PRESENTATION (Stage 5D & 5D.1)
  // ===========================================================================

  // 1. Parse or compute S_agg
  let sAgg = null;
  const matchSAgg = notes.match(/S_agg\s*\(([\d.]+)\)/i);
  if (matchSAgg && matchSAgg[1]) {
    sAgg = parseFloat(matchSAgg[1]);
  } else if (expBreakdown.evidence && expBreakdown.evidence.length > 0) {
    const validSims = expBreakdown.evidence
      .map((e) => (e.calibrated_similarity !== undefined && e.calibrated_similarity !== null ? e.calibrated_similarity : e.best_relevance_score))
      .filter((v) => v !== null && v !== undefined && !isNaN(v));
    if (validSims.length === expBreakdown.evidence.length) {
      sAgg = validSims.reduce((a, b) => a + b, 0) / validSims.length;
    }
  }

  // 2. Global duration factor D_global
  let durationFactor = null;
  if (experienceDiagnostic?.duration_factor !== null && experienceDiagnostic?.duration_factor !== undefined && !isNaN(experienceDiagnostic.duration_factor)) {
    durationFactor = Number(experienceDiagnostic.duration_factor);
  } else {
    const matchD = notes.match(/D_global\s*\(([\d.]+)\)/i);
    if (matchD && matchD[1]) {
      durationFactor = parseFloat(matchD[1]);
    }
  }

  // 3. Weights and contributions (Stage 5D.1 Fix B)
  const originalWeight = expBreakdown.original_weight;
  const normalizedWeight = expBreakdown.normalized_weight;
  const weightsDiffer =
    originalWeight !== null &&
    originalWeight !== undefined &&
    normalizedWeight !== null &&
    normalizedWeight !== undefined &&
    Math.abs(Number(originalWeight) - Number(normalizedWeight)) > 1e-4;

  const formattedOriginalWeight = formatWeight(originalWeight);
  const formattedAppliedWeight = formatWeight(normalizedWeight);

  // Component score E
  const scoreE = expBreakdown.score;

  // Weighted contribution: use actual backend value ONLY. Never calculate using original weight.
  const rawWeightedContrib = expBreakdown.weighted_contribution;
  const formattedWeightedContrib =
    rawWeightedContrib !== null && rawWeightedContrib !== undefined && !isNaN(rawWeightedContrib)
      ? Number(rawWeightedContrib).toFixed(2)
      : 'Unavailable';

  const evidenceList = expBreakdown.evidence || [];
  const saturationTarget = experienceDiagnostic?.saturation_target_years;
  const rangeStatus = experienceDiagnostic?.range_status;
  const relevantDuration = experienceDiagnostic?.relevant_duration_years;
  const diagStatus = experienceDiagnostic?.diagnostic_status;

  return (
    <div className="evidence-based-experience-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* ------------------------------------------------------------------ */}
      {/* HEADER & SCORING METHOD BADGE                                      */}
      {/* ------------------------------------------------------------------ */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          paddingBottom: '0.5rem',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            className="badge"
            style={{
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid var(--primary-500)',
              color: '#a5b4fc',
              fontWeight: 700,
              fontSize: '0.75rem',
              letterSpacing: '0.025em',
            }}
          >
            Evidence-Based Scoring
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Calibrated Semantic Similarity × Global Career Duration Factor
          </span>
        </div>
        <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
          Formula: E = 100 × S_agg × D_global
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* HIERARCHY 1: EXPERIENCE SCORE SUMMARY CARDS                        */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="experience-score-summary-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '0.75rem',
        }}
      >
        {/* Component Score E */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
          }}
        >
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Raw Component Score (E)
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
            {scoreE != null ? Number(scoreE).toFixed(1) : 'Unavailable'}
            {scoreE != null && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 400 }}> / 100</span>
            )}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            Unweighted experience score
          </div>
        </div>

        {/* Ranking Weight (Stage 5D.1 Fix B) */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
          }}
        >
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Applied Weight
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: '0.2rem' }}>
            {formattedAppliedWeight}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            {weightsDiffer ? (
              <span>
                Original: <strong>{formattedOriginalWeight}</strong> • Renormalized based on JD applicability
              </span>
            ) : (
              <span>Original configured weight: {formattedOriginalWeight}</span>
            )}
          </div>
        </div>

        {/* Weighted Contribution (Stage 5D.1 Fix B) */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
          }}
        >
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            Weighted Contribution
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--success-text)', marginTop: '0.2rem' }}>
            {formattedWeightedContrib}
            {formattedAppliedWeight !== 'Unavailable' && formattedWeightedContrib !== 'Unavailable' && (
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                {' '}/ {formattedAppliedWeight}
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
            Actual backend contribution to candidate rank
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* HIERARCHY 2: AGGREGATE SIMILARITY & GLOBAL DURATION DUAL METRICS   */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="dual-metrics-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1rem',
        }}
      >
        {/* Metric A: Aggregate Semantic Similarity */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.025em' }}>
              Semantic Similarity (S_agg)
            </span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#93c5fd' }}>
              {formatNumeric(sAgg, 3)}
            </span>
          </div>

          {/* Simple visual progress indicator */}
          <div style={{ background: 'var(--bg-app)', height: '6px', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.75rem' }}>
            <div
              style={{
                width: sAgg != null && !isNaN(sAgg) ? `${Math.min(Math.max(sAgg * 100, 0), 100)}%` : '0%',
                height: '100%',
                background: 'linear-gradient(90deg, #4f46e5, #60a5fa)',
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Measures semantic alignment between candidate verified work summaries and JD domain expectations using calibrated embeddings (threshold τ = 0.65).
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
            Averaged across {expBreakdown.total_criteria_count || evidenceList.length || 0} unique JD domain(s). Unsupported domains contribute 0.000.
          </div>
        </div>

        {/* Metric B: Global Duration Factor */}
        <div
          style={{
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.025em' }}>
              Duration Factor (D_global)
            </span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#a7f3d0' }}>
              {formatNumeric(durationFactor, 3)}
            </span>
          </div>

          {/* Simple visual progress indicator */}
          <div style={{ background: 'var(--bg-app)', height: '6px', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.75rem' }}>
            <div
              style={{
                width: durationFactor != null && !isNaN(durationFactor) ? `${Math.min(Math.max(durationFactor * 100, 0), 100)}%` : '0%',
                height: '100%',
                background: 'linear-gradient(90deg, #059669, #34d399)',
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Calculated against the JD saturation target (capped at 1.000).
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <div>
              Relevant Duration:{' '}
              <strong style={{ color: 'var(--text-primary)' }}>
                {formatDurationYears(relevantDuration, 1)}
              </strong>
            </div>
            <div>
              Target:{' '}
              <strong style={{ color: 'var(--text-primary)' }}>
                {formatTargetYears(saturationTarget)}
              </strong>
            </div>
            <div>
              Range:{' '}
              <span className="badge badge-neutral" style={{ fontSize: '0.7rem', padding: '0.1rem 0.35rem' }}>
                {rangeStatus !== null && rangeStatus !== undefined && rangeStatus !== '' ? rangeStatus : 'Unavailable'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* MANDATORY GLOBAL DURATION DISCLOSURE (Correction 3)                 */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="duration-disclosure-banner"
        style={{
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: 'var(--radius-md)',
          padding: '0.75rem 1rem',
          fontSize: '0.8rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.45,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
          <svg style={{ width: '18px', height: '18px', color: '#60a5fa', flexShrink: 0, marginTop: '2px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <strong>Duration Allocation Rule: </strong>
            Duration is pooled across relevant experience roles under the approved global duration formula. It is not independently calculated for each JD domain. Strong tenure in one domain can influence the global duration factor applied to aggregate domain similarity.
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* HIERARCHY 3: DOMAIN-LEVEL MATCHING BREAKDOWN                       */}
      {/* ------------------------------------------------------------------ */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.025em', margin: 0 }}>
            Domain-Level Semantic Matching
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {expBreakdown.qualifying_criteria_count || 0} of {expBreakdown.total_criteria_count || evidenceList.length || 0} domains satisfied
          </span>
        </div>

        {evidenceList.length > 0 ? (
          <div className="domain-breakdown-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {evidenceList.map((item, idx) => {
              const simVal = item.calibrated_similarity !== undefined && item.calibrated_similarity !== null
                ? item.calibrated_similarity
                : (item.best_relevance_score !== undefined && item.best_relevance_score !== null ? item.best_relevance_score : null);

              const isZero = simVal === 0.0;
              const isUnavailable = simVal === null || simVal === undefined;
              const hasSupport = !isZero && !isUnavailable && item.qualifies;

              return (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-surface-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.85rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.4rem' }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                        {item.criterion}
                      </span>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                        {item.supporting_role
                          ? `${item.supporting_role} • ${item.supporting_company || 'Employer'}`
                          : 'No supporting relevant role in resume'}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {/* Calibrated Similarity Badge */}
                      <span
                        className="badge"
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.75rem',
                          background: hasSupport ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          border: `1px solid ${hasSupport ? 'var(--success-border)' : 'var(--danger-border, rgba(239, 68, 68, 0.3))'}`,
                          color: hasSupport ? 'var(--success-text)' : 'var(--danger-text, #f87171)',
                        }}
                      >
                        S_m = {formatNumeric(simVal, 3)}
                      </span>

                      {/* Decision Badge */}
                      <span className={`badge ${item.supporting_decision === 'RELEVANT' ? 'badge-success' : 'badge-neutral'}`} style={{ fontSize: '0.7rem' }}>
                        {item.supporting_decision || (isZero ? 'UNSUPPORTED' : (isUnavailable ? 'Unavailable' : 'Evaluated'))}
                      </span>
                    </div>
                  </div>

                  {/* Supporting reason / Zero-credit diagnostic */}
                  {item.reason && (
                    <div style={{ fontSize: '0.78rem', color: isZero ? 'var(--warning-text)' : 'var(--text-secondary)', marginTop: '0.35rem', lineHeight: 1.35 }}>
                      {item.reason}
                    </div>
                  )}

                  {/* Additional supporting metrics if available */}
                  {(item.relevance_ratio != null || item.relevant_duration_years != null) && hasSupport && (
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '0.4rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {item.relevance_ratio != null && (
                        <span>Relevance Ratio: {formatNumeric(item.relevance_ratio, 2)}</span>
                      )}
                      {item.relevant_duration_years != null && (
                        <span>Role Duration: {formatDurationYears(item.relevant_duration_years, 1)}</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No preferred experience domains defined in the Job Description.
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* HIERARCHY 4: SUPPORTING EXPERIENCE EVIDENCE CARDS                  */}
      {/* ------------------------------------------------------------------ */}
      {evidenceList.some((e) => e.relevant_work_summary) && (
        <div>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.025em', marginBottom: '0.6rem' }}>
            Verified Work Summaries & Supporting Evidence
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {evidenceList
              .filter((e) => e.relevant_work_summary)
              .map((e, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'var(--bg-surface-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.85rem',
                  }}
                >
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#93c5fd', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                    Supporting Domain: {e.criterion}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontStyle: 'italic', marginBottom: '0.4rem', lineHeight: 1.4 }}>
                    "{e.relevant_work_summary}"
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Attributed Role: {e.supporting_role || 'Candidate Experience'} ({e.supporting_company || 'Employer'})
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* HIERARCHY 5: DIAGNOSTICS & SAFEGUARDS (Stage 5D.1 Fix A)          */}
      {/* ------------------------------------------------------------------ */}
      {(diagStatus === 'missing_dates' ||
        diagStatus === 'dates_missing_or_unparseable' ||
        diagStatus === 'ambiguous_dates' ||
        diagStatus === 'invalid_date_range' ||
        rangeStatus === 'unspecified' ||
        candidateWarnings.length > 0) && (
        <div
          className="experience-diagnostics-container"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.6rem',
            marginTop: '0.5rem',
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--warning-text)', textTransform: 'uppercase' }}>
            Evaluation Safeguards & Diagnostics
          </div>

          {/* Missing / Unparseable Dates Alert */}
          {(diagStatus === 'missing_dates' || diagStatus === 'dates_missing_or_unparseable') && (
            <div
              style={{
                background: 'var(--warning-bg)',
                border: '1px solid var(--warning-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem 1rem',
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
              }}
              role="alert"
            >
              <strong>Missing Dates Safeguard: </strong>
              Candidate demonstrated qualitative relevance, but start or end dates are missing or unparseable. Under TalentAI audit rules, duration credit is withheld (D_global = 0.000, E = 0.0) to prevent unverified tenure fabrication.
            </div>
          )}

          {/* Ambiguous Dates Alert */}
          {diagStatus === 'ambiguous_dates' && (
            <div
              style={{
                background: 'var(--warning-bg)',
                border: '1px solid var(--warning-border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem 1rem',
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
              }}
              role="alert"
            >
              <strong>Ambiguous Date Format: </strong>
              Candidate work dates are ambiguous (e.g. numeric day/month order) and could not be resolved without explicit locale rules. Duration factor is 0.000.
            </div>
          )}

          {/* Gate 1 (G1-C) Unspecified Range Alert — EXPLICIT backend marker only */}
          {rangeStatus === 'unspecified' && (
            <div
              style={{
                background: 'rgba(59, 130, 246, 0.1)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem 1rem',
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
              }}
              role="alert"
            >
              <strong>Gate 1 (G1-C) Unspecified Target: </strong>
              The active Job Description specifies neither minimum nor maximum experience duration. Under G1-C safeguards, no artificial target is invented; D_global is 0.000 until recruiter provides a duration target.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
