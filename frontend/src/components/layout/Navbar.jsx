import React from 'react';
import { useApp } from '../../context/AppContext.jsx';

export default function Navbar() {
  const {
    activeTab,
    setActiveTab,
    rankingResult,
    isDemoMode,
    demoPresetId,
    exitDemoMode,
  } = useApp();

  const rankedCount = rankingResult?.ranked_count ?? 0;
  const unrankedCount = rankingResult?.unranked_count ?? 0;

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-icon">T</div>
        <div>
          <div className="brand-title">
            TalentAI
            <span className="brand-badge">HR Suite</span>
          </div>
        </div>
      </div>

      {isDemoMode && (
        <div
          className="demo-sidebar-badge"
          style={{
            margin: '0.5rem 1rem 0.75rem',
            padding: '0.75rem',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fbbf24', fontWeight: 600, fontSize: '0.8rem' }}>
            <span>🧪</span> Demo Sandbox Active
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Active: <strong>{demoPresetId}</strong>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ marginTop: '0.5rem', width: '100%', fontSize: '0.72rem', padding: '0.25rem 0.5rem' }}
            onClick={exitDemoMode}
          >
            Exit Demo Mode
          </button>
        </div>
      )}

      <nav className="sidebar-nav" aria-label="Main Navigation">
        <button
          type="button"
          className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span>Overview</span>
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === 'demo' ? 'active' : ''}`}
          onClick={() => setActiveTab('demo')}
        >
          <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          <span>Synthetic Demo</span>
          <span className="badge badge-warning" style={{ fontSize: '0.65rem', padding: '0.1rem 0.35rem', marginLeft: 'auto' }}>12 JDs</span>
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          <span>Upload & Ingestion</span>
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === 'ranking' ? 'active' : ''}`}
          onClick={() => setActiveTab('ranking')}
        >
          <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span>Ranked Shortlist</span>
          {rankedCount > 0 && <span className="nav-counter">{rankedCount}</span>}
        </button>

        <button
          type="button"
          className={`nav-item ${activeTab === 'incomplete' ? 'active' : ''}`}
          onClick={() => setActiveTab('incomplete')}
        >
          <svg className="nav-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>Incomplete Candidates</span>
          {unrankedCount > 0 && <span className="nav-counter alert">{unrankedCount}</span>}
        </button>
      </nav>

      <div className="sidebar-footer">
        <div>TalentAI v2.0 • Phase 8</div>
        <div style={{ marginTop: '4px', fontSize: '0.7rem' }}>Deterministic Ranking Engine</div>
      </div>
    </aside>
  );
}
