import React from 'react';
import { useApp } from '../../context/AppContext.jsx';

export default function OverviewView() {
  const {
    activeJd,
    activeBatch,
    rankingResult,
    setActiveTab,
    triggerRanking,
    isRankingActive,
    rankingSubmitting,
  } = useApp();

  const isReadyToRank = Boolean(activeJd && activeBatch && activeBatch.status !== 'discarded');

  const structuredJd = activeJd?.structured_data;
  const experienceReq = structuredJd?.experience_requirements?.[0];

  const totalFiles = activeBatch?.total_files ?? 0;
  const completedFiles = activeBatch?.completed_count ?? 0;
  const rankedCandidatesCount = rankingResult?.ranked_count ?? 0;
  const unrankedCandidatesCount = rankingResult?.unranked_count ?? 0;

  return (
    <div className="page-body">
      <div className="page-header">
        <div>
          <h1 className="page-title">Executive Recruitment Overview</h1>
          <p className="page-description">
            Monitor active role criteria, candidate pool ingestion, and explainable AI ranking status.
          </p>
        </div>

        <div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={triggerRanking}
            disabled={!isReadyToRank || isRankingActive || rankingSubmitting}
          >
            {isRankingActive ? 'Ranking in Progress...' : 'Start Batch Ranking'}
          </button>
        </div>
      </div>

      {/* System Readiness Alert */}
      {!isReadyToRank ? (
        <div className="alert alert-warning">
          <svg style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <strong>Setup Required: </strong>
            {!activeJd && !activeBatch && 'Please upload a Job Description and a candidate resume batch to enable ranking.'}
            {!activeJd && activeBatch && 'An active candidate batch is loaded, but no active Job Description was found. Please upload a JD.'}
            {activeJd && !activeBatch && 'Active Job Description is loaded, but no active candidate batch was found. Please upload candidate resumes.'}
            <div style={{ marginTop: '0.4rem' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setActiveTab('upload')}
              >
                Go to Upload Workflow &rarr;
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="alert alert-info">
          <svg style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <strong>Ready for Ranking: </strong>
            Active role criteria and candidate pool are synchronized. You can run explainable multi-category ranking at any time.
          </div>
        </div>
      )}

      {/* Synthetic Demo Sandbox Quick Access */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          marginBottom: '1.5rem',
        }}
      >
        <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', padding: '1.25rem 1.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <span className="badge badge-warning" style={{ fontSize: '0.75rem' }}>🧪 ISOLATED SANDBOX</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Try the Synthetic Demo Experience</span>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Test the ranking engine and compare Legacy vs Evidence-based experience scoring on 12 certified synthetic roles and 240 synthetic candidates. Zero real data or database access.
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setActiveTab('demo')}
          >
            Launch Synthetic Demo &rarr;
          </button>
        </div>
      </div>

      {/* Top Stat Tiles */}
      <div className="grid-4" style={{ marginBottom: '1.75rem' }}>
        <div className="stat-tile">
          <span className="stat-label">Batch Candidates</span>
          <span className="stat-value">{totalFiles}</span>
          <span className="stat-meta">{completedFiles} parsed & ready</span>
        </div>

        <div className="stat-tile">
          <span className="stat-label">Ranked Shortlist</span>
          <span className="stat-value" style={{ color: 'var(--success-text)' }}>
            {rankedCandidatesCount}
          </span>
          <span className="stat-meta">Completed evaluations</span>
        </div>

        <div className="stat-tile">
          <span className="stat-label">Incomplete Resumes</span>
          <span className="stat-value" style={{ color: unrankedCandidatesCount > 0 ? 'var(--warning-text)' : 'var(--text-muted)' }}>
            {unrankedCandidatesCount}
          </span>
          <span className="stat-meta">Isolated (no misleading score)</span>
        </div>

        <div className="stat-tile">
          <span className="stat-label">JD Required Skills</span>
          <span className="stat-value" style={{ color: 'var(--primary-200)' }}>
            {structuredJd?.required_skills?.length ?? 0}
          </span>
          <span className="stat-meta">Token-matched criteria</span>
        </div>
      </div>

      {/* Two Column Section: Active JD & Active Batch Cards */}
      <div className="grid-2">
        {/* Active Job Description Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Active Job Description</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setActiveTab('upload')}
            >
              Replace JD
            </button>
          </div>
          <div className="card-body">
            {activeJd ? (
              <div>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Source Filename</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {activeJd.filename || 'Direct Text Input'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    ID: {activeJd.jd_id}
                  </div>
                </div>

                {experienceReq && (
                  <div style={{ marginBottom: '1rem', background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Experience Criteria
                    </div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                      <strong>{experienceReq.minimum_years ?? 'Any'}</strong> years minimum
                      {experienceReq.maximum_years ? ` (up to ${experienceReq.maximum_years} yrs)` : ''}
                    </div>
                    {experienceReq.preferred_domains?.length > 0 && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                        Preferred Domains: {experienceReq.preferred_domains.join(', ')}
                      </div>
                    )}
                  </div>
                )}

                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                    Required Skills ({structuredJd?.required_skills?.length ?? 0})
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {structuredJd?.required_skills?.length ? (
                      structuredJd.required_skills.map((skill, idx) => (
                        <span key={idx} className="badge badge-neutral">
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>None extracted</span>
                    )}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                    Tools & Technologies ({structuredJd?.tools_and_technologies?.length ?? 0})
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {structuredJd?.tools_and_technologies?.length ? (
                      structuredJd.tools_and_technologies.map((tool, idx) => (
                        <span key={idx} className="badge badge-info">
                          {tool}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>None extracted</span>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
                No active Job Description is loaded. Upload one to establish role requirements.
              </div>
            )}
          </div>
        </div>

        {/* Active Candidate Batch Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Active Candidate Batch</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setActiveTab('upload')}
            >
              Upload Batch
            </button>
          </div>
          <div className="card-body">
            {activeBatch ? (
              <div>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Batch Name</div>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {activeBatch.batch_name || 'Untitled Recruitment Batch'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    Batch ID: {activeBatch.batch_id || activeBatch._id}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', marginBottom: '1.25rem' }}>
                  <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Batch Status</div>
                    <div style={{ marginTop: '0.25rem' }}>
                      <span className="badge badge-success">{activeBatch.status}</span>
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-surface-subtle)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Uploaded Files</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                      {activeBatch.total_files}
                    </div>
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                    {activeBatch.completed_count} out of {activeBatch.total_files} candidate resumes have been successfully parsed and embedded with normalized 1024-dimensional vectors.
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setActiveTab('ranking')}
                  >
                    View Ranking Dashboard &rarr;
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
                No active candidate batch found. Upload resumes or a ZIP archive to begin.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
