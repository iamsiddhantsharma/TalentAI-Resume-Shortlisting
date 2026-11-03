import React from 'react';
import { useApp } from '../../context/AppContext.jsx';

export default function Header() {
  const {
    activeJd,
    activeBatch,
    isRankingActive,
    rankingSubmitting,
    triggerRanking,
    refreshSystemState,
    currentUser,
    logout,
  } = useApp();

  const isReadyToRank = Boolean(activeJd && activeBatch && activeBatch.status !== 'discarded');

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-status-group">
          {/* Active Job Description Pill */}
          <div className="status-chip" title={activeJd ? `Active JD: ${activeJd.jd_id}` : 'No active Job Description'}>
            <span className={`status-dot ${activeJd ? 'active' : 'inactive'}`} />
            <span className="status-chip-label">Job Description:</span>
            <span className="status-chip-value">
              {activeJd ? activeJd.filename || activeJd.jd_id.substring(0, 12) + '...' : 'None Loaded'}
            </span>
          </div>

          {/* Active Candidate Batch Pill */}
          <div className="status-chip" title={activeBatch ? `Active Batch: ${activeBatch.batch_id || activeBatch._id}` : 'No active recruitment batch'}>
            <span className={`status-dot ${activeBatch ? 'active' : 'inactive'}`} />
            <span className="status-chip-label">Candidate Batch:</span>
            <span className="status-chip-value">
              {activeBatch ? activeBatch.batch_name || (activeBatch.batch_id || activeBatch._id).substring(0, 12) + '...' : 'None Active'}
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
        {currentUser && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.25rem 0.6rem',
              borderRadius: 'var(--radius-md, 6px)',
              backgroundColor: 'rgba(99, 102, 241, 0.1)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              fontSize: '0.78rem',
              color: 'var(--text-primary)',
            }}
            title={`Signed in as ${currentUser.username} (${currentUser.email || 'HR'})`}
            data-testid="current-user-chip"
          >
            <span>👤</span>
            <span style={{ fontWeight: 600 }}>{currentUser.full_name || currentUser.username}</span>
          </div>
        )}

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={refreshSystemState}
          title="Synchronize system status with backend"
        >
          <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Sync
        </button>

        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={triggerRanking}
          disabled={!isReadyToRank || isRankingActive || rankingSubmitting}
        >
          {isRankingActive || rankingSubmitting ? (
            <>
              <svg className="spinner" style={{ width: '14px', height: '14px' }} fill="none" viewBox="0 0 24 24">
                <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Ranking in Progress...
            </>
          ) : (
            <>
              <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Rank Active Batch
            </>
          )}
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={logout}
          title="Sign out of HR Suite"
          data-testid="logout-button"
          style={{ fontSize: '0.78rem' }}
        >
          Sign Out
        </button>
      </div>
    </header>
  );
}
