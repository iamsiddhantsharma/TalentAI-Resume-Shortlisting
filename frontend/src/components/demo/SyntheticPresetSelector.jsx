import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext.jsx';

const STRATA_CATEGORIES = [
  'All',
  'Backend & Distributed Systems',
  'Frontend, Mobile & Full-Stack',
  'AI, Machine Learning & Data',
  'DevOps, SRE & Cloud Infrastructure',
  'Security & Systems Engineering',
  'Quality & Engineering Leadership',
];

export default function SyntheticPresetSelector({ onPresetSelected }) {
  const {
    demoPresets,
    loadDemoPresets,
    enterDemoMode,
    isDemoLoading,
    systemError,
  } = useApp();

  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedJdId, setSelectedJdId] = useState('JD-BROAD-01');
  const [initialScoringMode, setInitialScoringMode] = useState('legacy');
  const [localError, setLocalError] = useState(null);

  useEffect(() => {
    if (demoPresets.length === 0) {
      loadDemoPresets().catch((err) => {
        setLocalError(err.message || 'Failed to load synthetic presets.');
      });
    }
  }, [demoPresets.length, loadDemoPresets]);

  const filteredPresets = demoPresets.filter((p) => {
    if (selectedCategory === 'All') return true;
    return p.family === selectedCategory;
  });

  const activePreset = demoPresets.find((p) => p.jd_id === selectedJdId) || demoPresets[0];

  const handleLaunchCohort = async (presetIdToLaunch = selectedJdId) => {
    setLocalError(null);
    try {
      await enterDemoMode(presetIdToLaunch, initialScoringMode);
      if (onPresetSelected) {
        onPresetSelected(presetIdToLaunch);
      }
    } catch (err) {
      setLocalError(err.message || 'Unable to load synthetic cohort.');
    }
  };

  const getParadigmBadge = (paradigm) => {
    switch (paradigm) {
      case 'Bounded':
        return <span className="badge badge-info">Bounded (Min + Max)</span>;
      case 'Min-Only':
        return <span className="badge badge-success">Min-Only (Floored)</span>;
      case 'Max-Only':
        return <span className="badge badge-warning">Max-Only (Capped)</span>;
      case 'Unbounded / G1-C':
        return <span className="badge badge-neutral">Unbounded / G1-C</span>;
      default:
        return <span className="badge">{paradigm}</span>;
    }
  };

  return (
    <div className="synthetic-demo-container" data-testid="synthetic-demo-container">
      {/* DEMO HEADER BANNER */}
      <div className="demo-header-card">
        <div className="demo-header-title-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="badge badge-warning" style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }}>
              🧪 SYNTHETIC DEMO SANDBOX
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              12 Broad JDs • 240 Synthetic Candidates • 100% In-Memory
            </span>
          </div>
          <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
            ZERO DATABASE ACCESS
          </span>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', margin: '0.75rem 0 1rem' }}>
          Explore TalentAI’s multi-category ranking engine using certified synthetic fixtures.
          Compare the legacy categorical scoring against Phase 5 evidence-based experience ranking across
          all 6 technical strata without touching real resumes or production collections.
        </p>

        {/* INITIAL SCORING MODE SEGMENTED SELECTOR */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', background: 'var(--bg-surface)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Initial Evaluation Engine:
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              You can toggle engines dynamically anytime in the ranking dashboard
            </div>
          </div>

          <div className="segmented-control" role="group" aria-label="Scoring mode selector">
            <button
              type="button"
              className={`segmented-button ${initialScoringMode === 'legacy' ? 'active' : ''}`}
              onClick={() => setInitialScoringMode('legacy')}
            >
              🏛️ Legacy Categorical
            </button>
            <button
              type="button"
              className={`segmented-button ${initialScoringMode === 'evidence' ? 'active' : ''}`}
              onClick={() => setInitialScoringMode('evidence')}
            >
              🔬 Evidence-Based Experience
            </button>
          </div>
        </div>
      </div>

      {(localError || systemError) && (
        <div className="alert alert-danger" style={{ marginTop: '1rem' }} role="alert">
          {localError || systemError}
        </div>
      )}

      {/* STRATA FILTER TABS */}
      <div className="demo-category-tabs" style={{ marginTop: '1.25rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {STRATA_CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            className={`btn btn-sm ${selectedCategory === cat ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedCategory(cat)}
            style={{ fontSize: '0.8rem' }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* PRESETS GRID */}
      <div className="demo-presets-grid" style={{ marginTop: '1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1rem' }}>
        {filteredPresets.map((preset) => {
          const isSelected = preset.jd_id === selectedJdId;
          return (
            <div
              key={preset.jd_id}
              className={`demo-preset-card ${isSelected ? 'selected' : ''}`}
              onClick={() => setSelectedJdId(preset.jd_id)}
              style={{
                background: isSelected ? 'var(--bg-surface-elevated)' : 'var(--bg-surface)',
                border: isSelected ? '2px solid var(--primary-500)' : '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                padding: '1.25rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--primary-200)', fontWeight: 600 }}>
                  {preset.jd_id}
                </span>
                {getParadigmBadge(preset.paradigm)}
              </div>

              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                {preset.title}
              </h4>

              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                {preset.family} {preset.target_years != null ? `• Target: ${preset.target_years} yrs` : '• Unbounded'}
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '1rem' }}>
                {preset.required_skills.slice(0, 4).map((skill) => (
                  <span
                    key={skill}
                    style={{
                      background: 'rgba(99, 102, 241, 0.12)',
                      color: 'var(--primary-200)',
                      fontSize: '0.72rem',
                      padding: '0.15rem 0.45rem',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    {skill}
                  </span>
                ))}
                {preset.required_skills.length > 4 && (
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', alignSelf: 'center' }}>
                    +{preset.required_skills.length - 4} more
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '0.75rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Cohort: <strong>20 candidates</strong>
                </span>

                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleLaunchCohort(preset.jd_id);
                  }}
                  disabled={isDemoLoading}
                >
                  {isDemoLoading && isSelected ? 'Loading...' : 'Launch Cohort →'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredPresets.length === 0 && !isDemoLoading && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          No synthetic presets found for category "{selectedCategory}".
        </div>
      )}
    </div>
  );
}
