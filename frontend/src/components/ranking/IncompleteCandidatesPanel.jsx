import React, { useState } from 'react';
import { useApp } from '../../context/AppContext.jsx';
import { rankResume } from '../../api/rankingApi.js';

export default function IncompleteCandidatesPanel() {
  const { rankingResult, setRankingResult, activeJd } = useApp();
  const [retryingFile, setRetryingFile] = useState(null);
  const [retryMessage, setRetryMessage] = useState(null);

  const unrankedCandidates = rankingResult?.unranked_candidates ?? [];

  const handleRetry = async (candidate) => {
    setRetryingFile(candidate.filename);
    setRetryMessage(null);

    try {
      const updatedCandidate = await rankResume(
        candidate.upload_id,
        candidate.filename,
        activeJd?.jd_id || candidate.jd_id
      );

      // If retry succeeded and candidate is now complete
      if (updatedCandidate.status === 'complete' && updatedCandidate.final_score != null) {
        setRetryMessage({
          type: 'success',
          text: `Candidate "${candidate.filename}" successfully scored: ${updatedCandidate.final_score.toFixed(2)}`,
        });

        // Update local rankingResult in context
        if (rankingResult) {
          const newUnranked = rankingResult.unranked_candidates.filter(
            (c) => c.filename !== candidate.filename
          );
          const newRanked = [...rankingResult.ranked_candidates, updatedCandidate].sort(
            (a, b) => (b.final_score ?? 0) - (a.final_score ?? 0)
          );
          // Re-rank 1-indexed
          newRanked.forEach((c, idx) => {
            c.rank = idx + 1;
          });

          setRankingResult({
            ...rankingResult,
            ranked_candidates: newRanked,
            unranked_candidates: newUnranked,
            ranked_count: newRanked.length,
            unranked_count: newUnranked.length,
          });
        }
      } else {
        setRetryMessage({
          type: 'warning',
          text: `Evaluation retry ran, but candidate still has status: ${updatedCandidate.status}`,
        });
      }
    } catch (err) {
      setRetryMessage({
        type: 'error',
        text: `Retry failed: ${err.message || 'Server error'}`,
      });
    } finally {
      setRetryingFile(null);
    }
  };

  return (
    <div className="page-body">
      <div className="page-header">
        <div>
          <h1 className="page-title">Incomplete Candidate Evaluations</h1>
          <p className="page-description">
            Candidates who could not be fully scored due to technical extraction or service interruption.
          </p>
        </div>
      </div>

      <div className="alert alert-info">
        <svg style={{ width: '20px', height: '20px', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <strong>Ethical AI Guardrail:</strong> Incomplete candidates are never assigned an artificial 0 score or ranked among low-scoring candidates. Their score is withheld to prevent misleading disqualification.
        </div>
      </div>

      {retryMessage && (
        <div
          className={`alert ${
            retryMessage.type === 'success'
              ? 'alert-info'
              : retryMessage.type === 'warning'
              ? 'alert-warning'
              : 'alert-danger'
          }`}
          role="alert"
        >
          {retryMessage.text}
        </div>
      )}

      {unrankedCandidates.length > 0 ? (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Candidate Filename</th>
                <th>Evaluation Score</th>
                <th>Evaluation Status</th>
                <th>Safe Diagnostic Explanation</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {unrankedCandidates.map((c) => (
                <tr key={c.filename}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.filename}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      ID: {c.upload_id ? c.upload_id.substring(0, 14) + '...' : ''}
                    </div>
                  </td>
                  <td>
                    <span className="badge badge-warning">Score Withheld</span>
                  </td>
                  <td>
                    <span className="badge badge-danger">{c.status || 'Incomplete'}</span>
                  </td>
                  <td style={{ maxWidth: '400px' }}>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      {c.errors && c.errors.length > 0
                        ? c.errors[0]
                        : 'Evaluation could not complete all required scoring categories. Please retry.'}
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleRetry(c)}
                      disabled={retryingFile === c.filename}
                    >
                      {retryingFile === c.filename ? 'Retrying...' : 'Retry Evaluation'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card">
          <div className="card-body" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
            <svg style={{ width: '48px', height: '48px', color: 'var(--success-text)', margin: '0 auto 1rem' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              No Incomplete Candidates
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '440px', margin: '0 auto' }}>
              All evaluated resumes in the current recruitment batch completed successfully with valid scores and qualification evidence.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
