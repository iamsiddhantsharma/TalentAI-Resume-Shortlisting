import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AppProvider, useApp } from '../context/AppContext.jsx';
import * as rankingApi from '../api/rankingApi.js';
import * as batchApi from '../api/batchApi.js';
import * as jdApi from '../api/jdApi.js';

function TestConsumer() {
  const {
    activeJd,
    setActiveJd,
    activeBatch,
    setActiveBatch,
    rankingJob,
    rankingResult,
    isRankingActive,
    triggerRanking,
    selectedCandidate,
    setSelectedCandidate,
    refreshSystemState,
  } = useApp();

  return (
    <div>
      <div data-testid="jd-status">{activeJd ? activeJd.jd_id : 'no-jd'}</div>
      <div data-testid="batch-status">{activeBatch ? (activeBatch.batch_id || activeBatch._id) : 'no-batch'}</div>
      <div data-testid="ranking-active">{isRankingActive ? 'yes' : 'no'}</div>
      <div data-testid="job-id">{rankingJob ? rankingJob.job_id : 'none'}</div>
      <div data-testid="ranked-count">{rankingResult ? rankingResult.ranked_count : 0}</div>
      <div data-testid="selected-candidate">{selectedCandidate ? selectedCandidate.candidate_id : 'none'}</div>
      <button onClick={triggerRanking}>Start Ranking</button>
      <button onClick={() => setSelectedCandidate({ candidate_id: 'cand_123', name: 'Alice' })}>Select Candidate</button>
      <button onClick={() => setActiveJd({ jd_id: 'jd_updated_456' })}>Change JD</button>
      <button onClick={() => setActiveBatch({ batch_id: 'batch_updated_789' })}>Change Batch</button>
      <button onClick={refreshSystemState}>Refresh State</button>
    </div>
  );
}

describe('AppContext & Polling Lifecycle', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('restores in-flight job ID from localStorage and polls for status on mount', async () => {
    const savedJobId = 'job_stored_12345';
    localStorage.setItem('talentai_active_ranking_job_id', savedJobId);

    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_123' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_123' });

    const mockJobStatus = {
      job_id: savedJobId,
      status: 'processing',
      progress_percentage: 40.0,
      completed_count: 4,
      total_eligible: 10,
      result: null,
    };
    const pollSpy = vi.spyOn(rankingApi, 'getRankingJobStatus').mockResolvedValue(mockJobStatus);

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    expect(pollSpy).toHaveBeenCalledWith(savedJobId);
    expect(screen.getByTestId('job-id').textContent).toBe(savedJobId);
    expect(screen.getByTestId('ranking-active').textContent).toBe('yes');
  });

  it('stops polling and clears localStorage upon receiving terminal "completed" status', async () => {
    const savedJobId = 'job_completed_999';
    localStorage.setItem('talentai_active_ranking_job_id', savedJobId);

    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_123' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_123' });

    const completedResult = {
      jd_id: 'jd_123',
      active_batch_id: 'batch_123',
      total_eligible: 5,
      ranked_count: 5,
      unranked_count: 0,
      ranked_candidates: [],
      unranked_candidates: [],
    };

    const mockTerminalJob = {
      job_id: savedJobId,
      status: 'completed',
      progress_percentage: 100.0,
      completed_count: 5,
      total_eligible: 5,
      result: completedResult,
    };

    vi.spyOn(rankingApi, 'getRankingJobStatus').mockResolvedValue(mockTerminalJob);

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    // Should have populated rankingResult and cleared storage
    expect(screen.getByTestId('ranked-count').textContent).toBe('5');
    expect(localStorage.getItem('talentai_active_ranking_job_id')).toBeNull();
  });

  it('handles stale or unknown 404 job ID by terminating polling, clearing localStorage, and presenting recoverable message', async () => {
    const unknownJobId = 'job_stale_404';
    localStorage.setItem('talentai_active_ranking_job_id', unknownJobId);

    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_123' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_123' });

    // Mock 404 ApiError
    const notFoundError = new Error('Job not found');
    notFoundError.status = 404;
    vi.spyOn(rankingApi, 'getRankingJobStatus').mockRejectedValue(notFoundError);

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    // Polling must stop and localStorage must be cleared
    expect(screen.getByTestId('ranking-active').textContent).toBe('no');
    expect(localStorage.getItem('talentai_active_ranking_job_id')).toBeNull();
    expect(screen.getByTestId('job-id').textContent).toBe('none');
  });

  it('stops polling when job terminates with failed or interrupted status', async () => {
    const failedJobId = 'job_failed_error';
    localStorage.setItem('talentai_active_ranking_job_id', failedJobId);

    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_123' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_123' });

    const mockFailedJob = {
      job_id: failedJobId,
      status: 'failed',
      progress_percentage: 20.0,
      completed_count: 1,
      total_eligible: 5,
      error: 'Inference slot timeout occurred.',
      result: null,
    };

    vi.spyOn(rankingApi, 'getRankingJobStatus').mockResolvedValue(mockFailedJob);

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    expect(screen.getByTestId('ranking-active').textContent).toBe('no');
    expect(localStorage.getItem('talentai_active_ranking_job_id')).toBeNull();
  });

  it('clears selectedCandidate drawer state when active JD changes', async () => {
    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_initial' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_initial' });

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    // Select a candidate
    await act(async () => {
      screen.getByText('Select Candidate').click();
    });
    expect(screen.getByTestId('selected-candidate').textContent).toBe('cand_123');

    // Change the active JD
    await act(async () => {
      screen.getByText('Change JD').click();
    });

    // Stale candidate drawer must be cleared
    expect(screen.getByTestId('selected-candidate').textContent).toBe('none');
  });

  it('clears selectedCandidate drawer state when active batch changes', async () => {
    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_initial' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_initial' });

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    // Select a candidate
    await act(async () => {
      screen.getByText('Select Candidate').click();
    });
    expect(screen.getByTestId('selected-candidate').textContent).toBe('cand_123');

    // Change the active Batch
    await act(async () => {
      screen.getByText('Change Batch').click();
    });

    // Stale candidate drawer must be cleared
    expect(screen.getByTestId('selected-candidate').textContent).toBe('none');
  });

  it('clears selectedCandidate drawer state when a new ranking job starts', async () => {
    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_initial' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_initial' });
    vi.spyOn(rankingApi, 'startAsyncRanking').mockResolvedValue({
      job_id: 'job_new_ranking',
      status: 'queued',
      progress_percentage: 0.0,
      completed_count: 0,
      total_eligible: 10,
    });
    vi.spyOn(rankingApi, 'getRankingJobStatus').mockResolvedValue({
      job_id: 'job_new_ranking',
      status: 'processing',
      progress_percentage: 10.0,
      completed_count: 1,
      total_eligible: 10,
    });

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    // Select a candidate
    await act(async () => {
      screen.getByText('Select Candidate').click();
    });
    expect(screen.getByTestId('selected-candidate').textContent).toBe('cand_123');

    // Initiate new ranking job
    await act(async () => {
      screen.getByText('Start Ranking').click();
    });

    // Stale candidate drawer must be cleared immediately
    expect(screen.getByTestId('selected-candidate').textContent).toBe('none');
    expect(screen.getByTestId('job-id').textContent).toBe('job_new_ranking');
  });

  it('preserves selectedCandidate drawer state when refreshSystemState runs with identical JD and batch', async () => {
    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue({ jd_id: 'jd_same' });
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue({ batch_id: 'batch_same' });

    await act(async () => {
      render(
        <AppProvider>
          <TestConsumer />
        </AppProvider>
      );
    });

    // Select a candidate
    await act(async () => {
      screen.getByText('Select Candidate').click();
    });
    expect(screen.getByTestId('selected-candidate').textContent).toBe('cand_123');

    // Refresh system state without context change
    await act(async () => {
      screen.getByText('Refresh State').click();
    });

    // Drawer selection must be preserved
    expect(screen.getByTestId('selected-candidate').textContent).toBe('cand_123');
  });
});
