import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RankingDashboardView from '../components/ranking/RankingDashboardView.jsx';
import * as AppContextModule from '../context/AppContext.jsx';

describe('Top-N Candidate Display and Pagination Controls (Single-HR UX)', () => {
  const generateMockCandidates = (count = 100) => {
    return Array.from({ length: count }, (_, idx) => {
      const rank = idx + 1;
      const score = Math.max(10, 95 - idx * 0.7);
      return {
        upload_id: 'batch_synthetic_test',
        filename: `candidate_${String(rank).padStart(3, '0')}.pdf`,
        jd_id: 'jd_synthetic_test',
        rank,
        status: 'complete',
        final_score: parseFloat(score.toFixed(2)),
        component_scores: {
          required_skills: 90.0,
          responsibilities: 85.0,
          tools_and_technologies: 80.0,
          experience_relevance: 75.0,
        },
        breakdown: {
          required_skills: {
            category: 'required_skills',
            score: 90.0,
            evidence: [{ required_skill: 'Python', matched: true, matched_resume_skill: 'Python' }],
          },
          responsibilities: { category: 'responsibilities', score: 85.0, evidence: [] },
          tools_and_technologies: { category: 'tools_and_technologies', score: 80.0, evidence: [] },
          experience_relevance: { category: 'experience_relevance', score: 75.0, evidence: [] },
        },
        experience_diagnostic: {
          minimum_years: 3.0,
          relevant_duration_years: 5.0,
          minimum_duration_satisfied: true,
          diagnostic_message: 'Candidate satisfies experience criteria.',
        },
        warnings: [],
        errors: [],
      };
    });
  };

  const defaultCandidates = generateMockCandidates(100);

  const createMockContext = (overrides = {}) => {
    const triggerRanking = vi.fn();
    const setSelectedCandidate = vi.fn();
    const setActiveTab = vi.fn();
    const setTopN = vi.fn();

    return {
      rankingJob: null,
      rankingResult: {
        jd_id: 'jd_synthetic_test',
        active_batch_id: 'batch_synthetic_test',
        total_eligible: defaultCandidates.length,
        ranked_count: defaultCandidates.length,
        unranked_count: 0,
        limit: null,
        skip: 0,
        has_more: false,
        ranked_candidates: defaultCandidates,
        unranked_candidates: [],
      },
      isRankingActive: false,
      rankingSubmitting: false,
      triggerRanking,
      selectedCandidate: null,
      setSelectedCandidate,
      setActiveTab,
      systemError: null,
      topN: 20,
      setTopN,
      isDemoMode: false,
      demoPresets: [],
      ...overrides,
    };
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders top N candidates in rank order with initial N=20 from context', () => {
    const mockContext = createMockContext({ topN: 20 });
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue(mockContext);

    render(<RankingDashboardView />);

    // Verify summary text shows 20 of 100
    expect(screen.getByText(/Showing 20 of 100 ranked candidates/i)).toBeInTheDocument();

    // Verify input value is 20
    const topNInput = screen.getByTestId('top-n-input');
    expect(topNInput).toBeInTheDocument();
    expect(topNInput.value).toBe('20');

    // First candidate (#1) should be visible
    expect(screen.getByText('candidate_001.pdf')).toBeInTheDocument();
    // 20th candidate (#20) should be visible
    expect(screen.getByText('candidate_020.pdf')).toBeInTheDocument();
    // 21st candidate (#21) should NOT be rendered in the table
    expect(screen.queryByText('candidate_021.pdf')).not.toBeInTheDocument();
    // 100th candidate should NOT be rendered
    expect(screen.queryByText('candidate_100.pdf')).not.toBeInTheDocument();
  });

  it('changing N via input updates displayed candidates without triggering ranking request or inference', () => {
    let currentTopN = 20;
    const mockContext = createMockContext({
      get topN() {
        return currentTopN;
      },
      setTopN: vi.fn((newN) => {
        currentTopN = newN;
      }),
    });
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue(mockContext);

    const { rerender } = render(<RankingDashboardView />);
    expect(screen.getByText(/Showing 20 of 100 ranked candidates/i)).toBeInTheDocument();

    const topNInput = screen.getByTestId('top-n-input');

    // Change N from 20 to 50
    fireEvent.change(topNInput, { target: { value: '50' } });

    // Verify context setTopN was called with 50
    expect(mockContext.setTopN).toHaveBeenCalledWith(50);

    // Verify triggerRanking was NEVER called
    expect(mockContext.triggerRanking).not.toHaveBeenCalled();

    // Rerender with updated topN=50
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      ...mockContext,
      topN: 50,
    });
    rerender(<RankingDashboardView />);

    // Now showing 50 of 100
    expect(screen.getByText(/Showing 50 of 100 ranked candidates/i)).toBeInTheDocument();
    // 50th candidate is now visible
    expect(screen.getByText('candidate_050.pdf')).toBeInTheDocument();
    // 51st candidate is NOT visible
    expect(screen.queryByText('candidate_051.pdf')).not.toBeInTheDocument();

    // Confirm triggerRanking remained uncalled throughout
    expect(mockContext.triggerRanking).not.toHaveBeenCalled();
  });

  it('quick preset buttons (10, 20, 50, 100, All) update display count smoothly', () => {
    let currentTopN = 20;
    const mockContext = createMockContext({
      get topN() {
        return currentTopN;
      },
      setTopN: vi.fn((newN) => {
        currentTopN = newN;
      }),
    });
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue(mockContext);

    const { rerender } = render(<RankingDashboardView />);

    // Click preset 10
    const btn10 = screen.getByTestId('quick-top-10');
    fireEvent.click(btn10);
    expect(mockContext.setTopN).toHaveBeenCalledWith(10);
    expect(mockContext.triggerRanking).not.toHaveBeenCalled();

    // Simulate context update to 10
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({ ...mockContext, topN: 10 });
    rerender(<RankingDashboardView />);
    expect(screen.getByText(/Showing 10 of 100 ranked candidates/i)).toBeInTheDocument();
    expect(screen.getByText('candidate_010.pdf')).toBeInTheDocument();
    expect(screen.queryByText('candidate_011.pdf')).not.toBeInTheDocument();

    // Click preset 'All'
    const btnAll = screen.getByTestId('quick-top-all');
    fireEvent.click(btnAll);
    expect(mockContext.setTopN).toHaveBeenCalledWith(100);

    // Simulate context update to 100
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({ ...mockContext, topN: 100 });
    rerender(<RankingDashboardView />);
    expect(screen.getByText(/Showing 100 of 100 ranked candidates/i)).toBeInTheDocument();
    expect(screen.getByText('candidate_100.pdf')).toBeInTheDocument();
  });

  it('safely clamps when N is greater than available ranked candidates', () => {
    const mockContext = createMockContext({ topN: 300 });
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue(mockContext);

    render(<RankingDashboardView />);

    // When N=300 and total=100, displays "Showing 100 of 100 ranked candidates"
    expect(screen.getByText(/Showing 100 of 100 ranked candidates/i)).toBeInTheDocument();

    // candidate 100 is visible and page does not crash
    expect(screen.getByText('candidate_100.pdf')).toBeInTheDocument();
    expect(mockContext.triggerRanking).not.toHaveBeenCalled();
  });

  it('safely handles invalid, zero, negative, or non-numeric N values with validation feedback', () => {
    const mockContext = createMockContext({ topN: 20 });
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue(mockContext);

    render(<RankingDashboardView />);
    const topNInput = screen.getByTestId('top-n-input');

    // Case A: Negative number (-5)
    fireEvent.change(topNInput, { target: { value: '-5' } });
    expect(screen.getByRole('alert')).toHaveTextContent(/Please enter a positive whole number/i);
    // Does not break: falls back to all candidates safely
    expect(screen.getByText('candidate_001.pdf')).toBeInTheDocument();

    // Case B: Zero (0)
    fireEvent.change(topNInput, { target: { value: '0' } });
    expect(screen.getByRole('alert')).toHaveTextContent(/Please enter a positive whole number/i);
    expect(screen.getByText('candidate_001.pdf')).toBeInTheDocument();

    // Case C: Non-numeric ("abc")
    fireEvent.change(topNInput, { target: { value: 'abc' } });
    expect(screen.getByRole('alert')).toHaveTextContent(/Please enter a positive whole number/i);
    expect(screen.getByText('candidate_001.pdf')).toBeInTheDocument();

    // Case D: Float ("15.5")
    fireEvent.change(topNInput, { target: { value: '15.5' } });
    expect(screen.getByRole('alert')).toHaveTextContent(/Please enter a positive whole number/i);

    // Case E: Recovery with valid positive integer ("25")
    fireEvent.change(topNInput, { target: { value: '25' } });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(mockContext.setTopN).toHaveBeenCalledWith(25);
  });

  it('clicking Explain for a candidate in the top-N view opens candidate detail drawer with complete breakdown', () => {
    const mockSetCandidate = vi.fn();
    const mockContext = createMockContext({
      topN: 10,
      setSelectedCandidate: mockSetCandidate,
    });
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue(mockContext);

    render(<RankingDashboardView />);

    // Click Explain button for candidate 1
    const explainBtns = screen.getAllByRole('button', { name: /explain/i });
    expect(explainBtns.length).toBeGreaterThan(0);
    fireEvent.click(explainBtns[0]);

    expect(mockSetCandidate).toHaveBeenCalledWith(
      expect.objectContaining({
        filename: 'candidate_001.pdf',
        rank: 1,
      })
    );
  });
});
