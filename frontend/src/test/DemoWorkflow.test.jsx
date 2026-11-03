import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider, useApp } from '../context/AppContext.jsx';
import * as demoApi from '../api/demoApi.js';
import * as batchApi from '../api/batchApi.js';
import * as jdApi from '../api/jdApi.js';
import * as rankingApi from '../api/rankingApi.js';
import SyntheticPresetSelector from '../components/demo/SyntheticPresetSelector.jsx';
import RankingDashboardView from '../components/ranking/RankingDashboardView.jsx';

// Mock Synthetic Presets fixture
const MOCK_PRESETS = [
  {
    jd_id: 'JD-BROAD-01',
    title: 'Principal Distributed Storage Engineer',
    family: 'Backend & Distributed Systems',
    paradigm: 'Bounded',
    target_years: 8.0,
    required_skills: ['Go', 'Raft', 'gRPC', 'RocksDB', 'PostgreSQL'],
    candidate_count: 20,
    is_synthetic_demo: true,
  },
  {
    jd_id: 'JD-BROAD-02',
    title: 'Senior Event-Driven Python Architect',
    family: 'Backend & Distributed Systems',
    paradigm: 'Max-Only',
    target_years: 4.0,
    required_skills: ['Python', 'FastAPI', 'Kafka'],
    candidate_count: 20,
    is_synthetic_demo: true,
  },
];

// Mock Synthetic Cohort Ranking response
const MOCK_COHORT_LEGACY = {
  jd_id: 'JD-BROAD-01',
  preset_title: 'Principal Distributed Storage Engineer',
  family: 'Backend & Distributed Systems',
  paradigm: 'Bounded',
  target_years: 8.0,
  scoring_mode: 'legacy',
  is_synthetic_demo: true,
  total_eligible: 20,
  ranked_count: 2,
  unranked_count: 0,
  structured_jd: {
    jd_id: 'JD-BROAD-01',
    title: 'Principal Distributed Storage Engineer',
    required_skills: ['Go', 'Raft'],
  },
  ranked_candidates: [
    {
      upload_id: 'upload_broad_cand_01',
      candidate_id: 'CAND-01',
      filename: 'cand_01_synthetic.pdf',
      name: 'Aiden Vance',
      archetype: 'Senior Over-Saturated',
      edge_markers: [],
      rank: 1,
      final_score: 82.50,
      legacy_score: 82.50,
      evidence_score: 91.25,
      score_delta: 8.75,
      component_scores: {
        required_skills: 100.0,
        responsibilities: 85.0,
        tools_and_technologies: 90.0,
        experience_relevance: 70.0,
      },
      breakdown: {
        required_skills: { score: 100.0, normalized_weight: 0.25 },
        responsibilities: { score: 85.0, normalized_weight: 0.30 },
        tools_and_technologies: { score: 90.0, normalized_weight: 0.10 },
        experience_relevance: { score: 70.0, normalized_weight: 0.35, notes: 'Evaluated under legacy categorical buckets.' },
      },
      experience_diagnostic: {
        minimum_duration_satisfied: true,
        relevant_duration_years: 12.0,
      },
      is_synthetic_demo: true,
    },
    {
      upload_id: 'upload_broad_cand_16',
      candidate_id: 'CAND-16',
      filename: 'cand_16_synthetic.pdf',
      name: 'Rory Campbell',
      archetype: 'Missing Dates Edge Case',
      edge_markers: ['missing_dates'],
      rank: 2,
      final_score: 45.00,
      legacy_score: 45.00,
      evidence_score: 45.00,
      score_delta: 0.00,
      component_scores: {
        required_skills: 60.0,
        responsibilities: 70.0,
        tools_and_technologies: 50.0,
        experience_relevance: 0.0,
      },
      breakdown: {
        required_skills: { score: 60.0, normalized_weight: 0.25 },
        responsibilities: { score: 70.0, normalized_weight: 0.30 },
        tools_and_technologies: { score: 50.0, normalized_weight: 0.10 },
        experience_relevance: { score: 0.0, normalized_weight: 0.35, notes: 'Zero duration credit due to missing dates.' },
      },
      experience_diagnostic: {
        minimum_duration_satisfied: false,
        diagnostic_status: 'missing_dates',
        relevant_duration_years: 0.0,
      },
      is_synthetic_demo: true,
    },
  ],
  unranked_candidates: [],
};

const MOCK_COHORT_EVIDENCE = {
  ...MOCK_COHORT_LEGACY,
  scoring_mode: 'evidence',
  ranked_candidates: [
    {
      ...MOCK_COHORT_LEGACY.ranked_candidates[0],
      final_score: 91.25,
      component_scores: {
        ...MOCK_COHORT_LEGACY.ranked_candidates[0].component_scores,
        experience_relevance: 95.0,
      },
      breakdown: {
        ...MOCK_COHORT_LEGACY.ranked_candidates[0].breakdown,
        experience_relevance: {
          score: 95.0,
          normalized_weight: 0.35,
          notes: 'Evaluated under evidence_based continuous saturation.',
        },
      },
    },
    {
      ...MOCK_COHORT_LEGACY.ranked_candidates[1],
      final_score: 45.00,
    },
  ],
};

function DemoIntegrationHarness() {
  const { isDemoMode, activeTab, rankingResult } = useApp();
  return (
    <div>
      <div data-testid="is-demo-mode">{isDemoMode ? 'yes' : 'no'}</div>
      <div data-testid="active-tab">{activeTab}</div>
      <div data-testid="candidate-count">{rankingResult?.ranked_candidates?.length ?? 0}</div>
      {activeTab === 'demo' && <SyntheticPresetSelector />}
      {activeTab === 'ranking' && <RankingDashboardView />}
    </div>
  );
}

describe('Synthetic Demo & Comparison Workflows (Milestones 2 & 3)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    // Default mock responses
    vi.spyOn(demoApi, 'fetchDemoPresets').mockResolvedValue({
      total_presets: MOCK_PRESETS.length,
      presets: MOCK_PRESETS,
      is_synthetic_demo: true,
    });

    vi.spyOn(demoApi, 'fetchDemoCohort').mockImplementation((jdId, mode) => {
      if (mode === 'evidence') {
        return Promise.resolve(MOCK_COHORT_EVIDENCE);
      }
      return Promise.resolve(MOCK_COHORT_LEGACY);
    });

    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue(null);
    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue(null);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('Milestone 2: lists available synthetic presets and launches selected cohort without touching production batch', async () => {
    const mockStartRanking = vi.spyOn(rankingApi, 'startAsyncRanking');

    render(
      <AppProvider>
        <DemoIntegrationHarness />
      </AppProvider>
    );

    // Initial state
    expect(screen.getByTestId('is-demo-mode').textContent).toBe('no');

    // Switch to demo tab
    const { setActiveTab } = await import('../context/AppContext.jsx');

    // Render SyntheticPresetSelector directly
    const { rerender } = render(
      <AppProvider>
        <SyntheticPresetSelector />
      </AppProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Principal Distributed Storage Engineer')).toBeInTheDocument();
      expect(screen.getByText('Senior Event-Driven Python Architect')).toBeInTheDocument();
    });

    // Launch cohort for JD-BROAD-01
    const launchButtons = screen.getAllByRole('button', { name: /Launch Cohort/i });
    await act(async () => {
      fireEvent.click(launchButtons[0]);
    });

    // Verify fetchDemoCohort was called with JD-BROAD-01
    expect(demoApi.fetchDemoCohort).toHaveBeenCalledWith('JD-BROAD-01', 'legacy');

    // CRITICAL SAFETY ASSERTION: production ranking must NEVER be invoked!
    expect(mockStartRanking).not.toHaveBeenCalled();
  });

  it('Milestone 3: displays score deltas and toggles between Legacy and Evidence scoring', async () => {
    let contextRef = null;

    function TestDashboardWrapper() {
      const app = useApp();
      contextRef = app;
      return <RankingDashboardView />;
    }

    render(
      <AppProvider>
        <TestDashboardWrapper />
      </AppProvider>
    );

    // Enter demo mode with legacy scoring
    await act(async () => {
      await contextRef.enterDemoMode('JD-BROAD-01', 'legacy');
    });

    expect(screen.getByTestId('demo-ranking-banner')).toBeInTheDocument();
    expect(screen.getByText('Principal Distributed Storage Engineer')).toBeInTheDocument();

    // Verify Score Delta column is rendered in demo mode
    expect(screen.getByText('Score Delta (Δ)')).toBeInTheDocument();

    // Verify CAND-01 initial legacy score (82.50) and score delta (+8.75)
    expect(screen.getByTestId('score-CAND-01').textContent).toBe('82.50');
    expect(screen.getByTestId('delta-CAND-01').textContent).toBe('+8.75');

    // Verify CAND-16 zero delta (0.00)
    expect(screen.getByTestId('delta-CAND-16').textContent).toBe('0.00');

    // Toggle to Evidence-Based Mode
    const evidenceToggle = screen.getByTestId('toggle-mode-evidence');
    await act(async () => {
      fireEvent.click(evidenceToggle);
    });

    // Verify API called for evidence mode
    expect(demoApi.fetchDemoCohort).toHaveBeenCalledWith('JD-BROAD-01', 'evidence');

    // Candidate 1 score should now reflect Evidence score (91.25)
    await waitFor(() => {
      expect(screen.getByTestId('score-CAND-01').textContent).toBe('91.25');
    });

    // Toggle back to Legacy Mode
    const legacyToggle = screen.getByTestId('toggle-mode-legacy');
    await act(async () => {
      fireEvent.click(legacyToggle);
    });

    expect(demoApi.fetchDemoCohort).toHaveBeenCalledWith('JD-BROAD-01', 'legacy');
  });

  it('Milestone 3: explainability drawer shows dual scores, delta, and archetype', async () => {
    let contextRef = null;

    function TestDrawerWrapper() {
      const app = useApp();
      contextRef = app;
      return <RankingDashboardView />;
    }

    render(
      <AppProvider>
        <TestDrawerWrapper />
      </AppProvider>
    );

    await act(async () => {
      await contextRef.enterDemoMode('JD-BROAD-01', 'legacy');
    });

    // Click "Explain" on first candidate
    const explainButtons = screen.getAllByRole('button', { name: 'Explain' });
    await act(async () => {
      fireEvent.click(explainButtons[0]);
    });

    // Verify explainability drawer renders dual scoring card
    await waitFor(() => {
      expect(screen.getByTestId('synthetic-dual-scoring-card')).toBeInTheDocument();
      expect(screen.getByTestId('drawer-legacy-score').textContent).toBe('82.50');
      expect(screen.getByTestId('drawer-evidence-score').textContent).toBe('91.25');
      expect(screen.getByTestId('drawer-score-delta').textContent).toBe('+8.75');
      expect(screen.getAllByText('Senior Over-Saturated').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('Milestone 2 & 4: handles demo API error gracefully and allows clean demo exit', async () => {
    let contextRef = null;

    function ErrorTestWrapper() {
      const app = useApp();
      contextRef = app;
      return (
        <div>
          <RankingDashboardView />
          {app.systemError && <div data-testid="error-banner">{app.systemError}</div>}
        </div>
      );
    }

    render(
      <AppProvider>
        <ErrorTestWrapper />
      </AppProvider>
    );

    // Test error handling
    vi.spyOn(demoApi, 'fetchDemoCohort').mockRejectedValueOnce(new Error('Synthetic preset not found'));

    await act(async () => {
      try {
        await contextRef.enterDemoMode('JD-BROAD-INVALID', 'legacy');
      } catch (e) {
        // Expected
      }
    });

    expect(screen.getByTestId('error-banner').textContent).toContain('Synthetic preset not found');

    // Test clean exit from demo mode
    await act(async () => {
      contextRef.exitDemoMode();
    });

    expect(contextRef.isDemoMode).toBe(false);
    expect(contextRef.demoPresetId).toBe(null);
    expect(contextRef.activeTab).toBe('overview');
  });
});
