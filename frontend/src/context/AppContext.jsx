import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getActiveBatch } from '../api/batchApi.js';
import { getActiveJd } from '../api/jdApi.js';
import { startAsyncRanking, getRankingJobStatus } from '../api/rankingApi.js';
import { fetchDemoPresets, fetchDemoCohort } from '../api/demoApi.js';
import { authApi } from '../api/authApi.js';
import { setUnauthorizedHandler } from '../api/client.js';

const AppContext = createContext(null);

const STORAGE_KEY_JOB_ID = 'talentai_active_ranking_job_id';
const STORAGE_KEY_ACTIVE_VIEW = 'talentai_active_view';
const STORAGE_KEY_TOP_N = 'talentai_top_n';
const DEFAULT_TOP_N = 20;
const POLLING_INTERVAL_MS = 2500;

export function AppProvider({ children }) {
  // Navigation View: 'overview' | 'upload' | 'ranking' | 'incomplete'
  const [activeTab, setActiveTabState] = useState(() => {
    return localStorage.getItem(STORAGE_KEY_ACTIVE_VIEW) || 'overview';
  });

  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    localStorage.setItem(STORAGE_KEY_ACTIVE_VIEW, tab);
  };

  // HR Top-N Candidate Display Preference (persisted across page reload)
  const [topN, setTopNState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY_TOP_N);
    if (saved) {
      const parsed = parseInt(saved, 10);
      if (!isNaN(parsed) && parsed > 0) return parsed;
    }
    return DEFAULT_TOP_N;
  });

  const setTopN = useCallback((newN) => {
    const parsed = parseInt(newN, 10);
    if (!isNaN(parsed) && parsed > 0) {
      setTopNState(parsed);
      localStorage.setItem(STORAGE_KEY_TOP_N, String(parsed));
    } else {
      setTopNState(newN);
    }
  }, []);

  // HR User Authentication State
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authNotice, setAuthNotice] = useState(null);

  // Authoritative Backend State
  const [activeJd, setActiveJd] = useState(null);
  const [activeBatch, setActiveBatch] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  // Synthetic Demo Sandbox State
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoPresetId, setDemoPresetId] = useState(null);
  const [demoScoringMode, setDemoScoringMode] = useState('legacy'); // 'legacy' | 'evidence'
  const [demoPresets, setDemoPresets] = useState([]);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  // Background Ranking Job & Polling State
  const [rankingJob, setRankingJob] = useState(null);
  const [rankingResult, setRankingResult] = useState(null);
  const [rankingSubmitting, setRankingSubmitting] = useState(false);
  const [systemError, setSystemError] = useState(null);

  // Selected Candidate for Explainability Drawer
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  // Track active JD and Batch IDs to clear stale drawer selection on context change
  const lastJdIdRef = useRef(null);
  const lastBatchIdRef = useRef(null);
  const isDemoModeRef = useRef(false);
  isDemoModeRef.current = isDemoMode;

  useEffect(() => {
    if (isDemoMode) return;
    const currentJdId = activeJd ? (activeJd.jd_id || activeJd._id) : null;
    if (lastJdIdRef.current !== null && lastJdIdRef.current !== currentJdId) {
      setSelectedCandidate(null);
      setRankingResult(null);
    }
    lastJdIdRef.current = currentJdId;
  }, [activeJd, isDemoMode]);

  useEffect(() => {
    if (isDemoMode) return;
    const currentBatchId = activeBatch ? (activeBatch.batch_id || activeBatch._id) : null;
    if (lastBatchIdRef.current !== null && lastBatchIdRef.current !== currentBatchId) {
      setSelectedCandidate(null);
      setRankingResult(null);
    }
    lastBatchIdRef.current = currentBatchId;
  }, [activeBatch, isDemoMode]);

  // Polling ref to prevent concurrent timers
  const pollTimerRef = useRef(null);
  const isPollingRef = useRef(false);

  /**
   * Fetch active JD and active batch from authoritative backend endpoints.
   */
  const refreshSystemState = useCallback(async () => {
    if (isDemoModeRef.current) return;
    try {
      setSystemError(null);
      const [jd, batch] = await Promise.all([
        getActiveJd().catch((err) => {
          console.warn('Error fetching active JD:', err);
          return null;
        }),
        getActiveBatch().catch((err) => {
          console.warn('Error fetching active batch:', err);
          return null;
        }),
      ]);

      if (isDemoModeRef.current) return;

      setActiveJd((prevJd) => {
        const prevId = prevJd ? (prevJd.jd_id || prevJd._id) : null;
        const newId = jd ? (jd.jd_id || jd._id) : null;
        // Invalidate stale ranking results and candidate drawer if JD changed
        if (prevId && newId && prevId !== newId) {
          setRankingResult(null);
          setSelectedCandidate(null);
        } else if (prevId && !newId) {
          setRankingResult(null);
          setSelectedCandidate(null);
        }
        return jd;
      });

      setActiveBatch((prevBatch) => {
        const prevId = prevBatch ? (prevBatch.batch_id || prevBatch._id) : null;
        const newId = batch ? (batch.batch_id || batch._id) : null;
        // Invalidate stale ranking results and candidate drawer if active batch changed
        if (prevId && newId && prevId !== newId) {
          setRankingResult(null);
          setSelectedCandidate(null);
        } else if (prevId && !newId) {
          setRankingResult(null);
          setSelectedCandidate(null);
        }
        return batch;
      });
    } catch (err) {
      setSystemError(err.message || 'Failed to synchronize system status.');
    } finally {
      setIsInitializing(false);
    }
  }, []);

  /**
   * Stop any active background polling.
   */
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    isPollingRef.current = false;
  }, []);

  /**
   * Poll ranking job by ID until reaching a terminal state.
   */
  const pollJobStatus = useCallback(async (jobId) => {
    if (!jobId) return;

    try {
      const jobStatus = await getRankingJobStatus(jobId);
      setRankingJob(jobStatus);

      // Terminal status check
      if (jobStatus.status === 'completed') {
        stopPolling();
        localStorage.removeItem(STORAGE_KEY_JOB_ID);
        if (jobStatus.result) {
          setRankingResult(jobStatus.result);
        }
      } else if (jobStatus.status === 'failed' || jobStatus.status === 'interrupted') {
        stopPolling();
        localStorage.removeItem(STORAGE_KEY_JOB_ID);
        setSystemError(jobStatus.error || `Ranking job terminated with status: ${jobStatus.status}`);
      } else {
        // Queued or processing — continue polling
        if (isPollingRef.current) {
          pollTimerRef.current = setTimeout(() => pollJobStatus(jobId), POLLING_INTERVAL_MS);
        }
      }
    } catch (err) {
      // Stale or unknown job ID recovery
      if (err.status === 404) {
        stopPolling();
        localStorage.removeItem(STORAGE_KEY_JOB_ID);
        setRankingJob(null);
        setSystemError('The previously tracked ranking job was not found on the server. Please initiate a new ranking job.');
        return;
      }

      console.warn('Polling error (will retry next interval):', err);
      // Non-destructive retry on network glitch
      if (isPollingRef.current) {
        pollTimerRef.current = setTimeout(() => pollJobStatus(jobId), POLLING_INTERVAL_MS);
      }
    }
  }, [stopPolling]);

  /**
   * Start polling for a given job ID.
   */
  const startPolling = useCallback((jobId) => {
    stopPolling();
    isPollingRef.current = true;
    localStorage.setItem(STORAGE_KEY_JOB_ID, jobId);
    pollJobStatus(jobId);
  }, [stopPolling, pollJobStatus]);

  /**
   * Start an asynchronous ranking workflow.
   */
  const triggerRanking = useCallback(async () => {
    if (rankingSubmitting || isPollingRef.current) return;

    if (isDemoMode) {
      if (demoPresetId) {
        setIsDemoLoading(true);
        try {
          const cohortData = await fetchDemoCohort(demoPresetId, demoScoringMode);
          setRankingResult(cohortData);
        } catch (err) {
          setSystemError(err.message || 'Failed to re-evaluate synthetic demo cohort.');
        } finally {
          setIsDemoLoading(false);
        }
      }
      return;
    }

    setRankingSubmitting(true);
    setSystemError(null);
    setSelectedCandidate(null); // Clear stale drawer candidate when a new ranking job starts

    try {
      const jobResponse = await startAsyncRanking();
      setRankingJob(jobResponse);
      setRankingResult(null); // Clear previous results
      setSelectedCandidate(null);
      setActiveTab('ranking'); // Switch to ranking view
      startPolling(jobResponse.job_id);
    } catch (err) {
      setSystemError(err.message || 'Failed to schedule ranking job.');
    } finally {
      setRankingSubmitting(false);
    }
  }, [rankingSubmitting, isDemoMode, demoPresetId, demoScoringMode, startPolling]);

  /**
   * Load available synthetic presets from /demo/presets
   */
  const loadDemoPresets = useCallback(async () => {
    try {
      const data = await fetchDemoPresets();
      if (data && data.presets) {
        setDemoPresets(data.presets);
      }
      return data;
    } catch (err) {
      console.warn('Failed to load demo presets:', err);
    }
  }, []);

  /**
   * Enter synthetic demo mode with a selected preset ID and initial scoring mode
   */
  const enterDemoMode = useCallback(async (presetId, scoringMode = 'legacy') => {
    isDemoModeRef.current = true;
    setIsDemoMode(true);
    setIsDemoLoading(true);
    setSystemError(null);
    try {
      const cohortData = await fetchDemoCohort(presetId, scoringMode);
      setDemoPresetId(presetId);
      setDemoScoringMode(scoringMode);
      setRankingResult(cohortData);
      setActiveJd(cohortData.structured_jd);
      setSelectedCandidate(null);
      setActiveTab('ranking');
      return cohortData;
    } catch (err) {
      isDemoModeRef.current = false;
      setIsDemoMode(false);
      setSystemError(err.message || 'Failed to load synthetic preset cohort.');
      throw err;
    } finally {
      setIsDemoLoading(false);
    }
  }, []);

  /**
   * Switch scoring engine mode within synthetic demo (Legacy vs. Evidence-Based)
   */
  const switchDemoScoringMode = useCallback(async (newMode) => {
    if (!demoPresetId) return;
    setIsDemoLoading(true);
    setSystemError(null);
    try {
      const cohortData = await fetchDemoCohort(demoPresetId, newMode);
      setDemoScoringMode(newMode);
      setRankingResult(cohortData);
      setSelectedCandidate((prev) => {
        if (!prev) return null;
        const updated = cohortData.ranked_candidates?.find(
          (c) => c.upload_id === prev.upload_id || c.candidate_id === prev.candidate_id
        );
        return updated || null;
      });
      return cohortData;
    } catch (err) {
      setSystemError(err.message || 'Failed to switch synthetic scoring mode.');
    } finally {
      setIsDemoLoading(false);
    }
  }, [demoPresetId]);

  /**
   * Switch synthetic preset directly from the ranking view
   */
  const switchDemoPreset = useCallback(async (newPresetId) => {
    if (!newPresetId || newPresetId === demoPresetId) return;
    return await enterDemoMode(newPresetId, demoScoringMode);
  }, [demoPresetId, demoScoringMode, enterDemoMode]);

  /**
   * Safely exit demo mode and restore live system state
   */
  const exitDemoMode = useCallback(async () => {
    isDemoModeRef.current = false;
    setIsDemoMode(false);
    setDemoPresetId(null);
    setDemoScoringMode('legacy');
    setRankingResult(null);
    setSelectedCandidate(null);
    setActiveTab('overview');
    try {
      const [jd, batch] = await Promise.all([
        getActiveJd().catch(() => null),
        getActiveBatch().catch(() => null),
      ]);
      setActiveJd(jd);
      setActiveBatch(batch);
    } catch (err) {
      console.warn('Failed to restore live state on demo exit:', err);
    }
  }, []);

  /**
   * Check whether the browser carries an active HR session cookie.
   */
  const checkAuth = useCallback(async () => {
    setIsCheckingAuth(true);
    try {
      const user = await authApi.getCurrentUser();
      if (user && user.user_id) {
        setCurrentUser(user);
        setIsAuthenticated(true);
        setAuthNotice(null);
      } else {
        setCurrentUser(null);
        setIsAuthenticated(false);
      }
    } catch {
      setCurrentUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsCheckingAuth(false);
      setIsInitializing(false);
    }
  }, []);

  /**
   * Log in with HR team credentials.
   */
  const login = useCallback(async (username, password) => {
    const res = await authApi.login({ username, password });
    if (res && res.user) {
      setCurrentUser(res.user);
      setIsAuthenticated(true);
      setAuthNotice(null);
      await refreshSystemState();
      return res.user;
    }
    throw new Error('Authentication response did not contain user profile.');
  }, [refreshSystemState]);

  /**
   * Log out of HR suite and clear session.
   */
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.warn('Logout error:', err);
    } finally {
      setCurrentUser(null);
      setIsAuthenticated(false);
      setRankingJob(null);
      setRankingResult(null);
      setActiveJd(null);
      setActiveBatch(null);
      localStorage.removeItem(STORAGE_KEY_JOB_ID);
    }
  }, []);

  /**
   * Register global unauthorized (401) listener.
   */
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setIsAuthenticated((prevAuth) => {
        if (prevAuth) {
          setCurrentUser(null);
          setAuthNotice('Your session has expired. Please sign in again.');
          return false;
        }
        return false;
      });
    });
  }, []);

  /**
   * Initialize state and verify HR session on boot.
   */
  useEffect(() => {
    checkAuth();
    refreshSystemState();

    // Check for persisted in-flight job in localStorage
    const savedJobId = localStorage.getItem(STORAGE_KEY_JOB_ID);
    if (savedJobId) {
      startPolling(savedJobId);
    }

    return () => {
      stopPolling();
    };
  }, [checkAuth, refreshSystemState, startPolling, stopPolling]);

  const value = {
    activeTab,
    setActiveTab,
    activeJd,
    setActiveJd,
    activeBatch,
    setActiveBatch,
    isInitializing,
    rankingJob,
    rankingResult,
    setRankingResult,
    rankingSubmitting,
    isRankingActive: isPollingRef.current || (rankingJob && (rankingJob.status === 'queued' || rankingJob.status === 'processing')),
    systemError,
    setSystemError,
    selectedCandidate,
    setSelectedCandidate,
    refreshSystemState,
    triggerRanking,
    stopPolling,
    // HR Authentication State & Actions
    currentUser,
    isAuthenticated,
    isCheckingAuth,
    authNotice,
    login,
    logout,
    checkAuth,
    // HR Top-N Display Preferences
    topN,
    setTopN,
    // Synthetic Demo Sandbox Exports
    isDemoMode,
    demoPresetId,
    demoScoringMode,
    demoPresets,
    isDemoLoading,
    loadDemoPresets,
    enterDemoMode,
    switchDemoScoringMode,
    switchDemoPreset,
    exitDemoMode,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
