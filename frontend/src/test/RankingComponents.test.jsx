import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CandidateDetailDrawer from '../components/ranking/CandidateDetailDrawer.jsx';
import IncompleteCandidatesPanel from '../components/ranking/IncompleteCandidatesPanel.jsx';
import RankingDashboardView from '../components/ranking/RankingDashboardView.jsx';
import * as AppContextModule from '../context/AppContext.jsx';

describe('Ranking Views & Candidate Explainability', () => {
  const mockCandidate = {
    upload_id: 'batch_test_001',
    filename: 'Senior_ML_Engineer.pdf',
    jd_id: 'jd_test_001',
    rank: 1,
    status: 'complete',
    final_score: 87.5,
    component_scores: {
      required_skills: 100.0,
      responsibilities: 85.0,
      tools_and_technologies: 90.0,
      experience_relevance: 82.5,
    },
    breakdown: {
      required_skills: {
        category: 'required_skills',
        score: 100.0,
        original_weight: 0.25,
        normalized_weight: 0.25,
        evidence: [
          { required_skill: 'Python', matched: true, matched_resume_skill: 'Python 3.11' },
          { required_skill: 'FastAPI', matched: true, matched_resume_skill: 'FastAPI' },
        ],
      },
      responsibilities: {
        category: 'responsibilities',
        score: 85.0,
        original_weight: 0.30,
        normalized_weight: 0.30,
        evidence: [
          {
            requirement_text: 'Build scalable APIs',
            qualifies: true,
            best_matching_passage: 'Designed distributed backend handling 20k RPS',
            raw_similarity: 0.84,
            normalized_relevance: 0.54,
          },
        ],
      },
      tools_and_technologies: {
        category: 'tools_and_technologies',
        score: 90.0,
        original_weight: 0.10,
        normalized_weight: 0.10,
        evidence: [
          { requirement_text: 'Docker', qualifies: true, best_matching_passage: 'Containerized all microservices' },
        ],
      },
      experience_relevance: {
        category: 'experience_relevance',
        score: 82.5,
        original_weight: 0.35,
        normalized_weight: 0.35,
        evidence: [
          {
            criterion: 'Distributed Systems',
            supporting_decision: 'RELEVANT',
            supporting_role: 'Lead Architect',
            supporting_company: 'TechCorp',
            reason: 'Direct relevant architecture experience',
          },
        ],
      },
    },
    experience_diagnostic: {
      minimum_years: 4.0,
      relevant_duration_years: 5.2,
      minimum_duration_satisfied: true,
      diagnostic_message: 'Candidate has 5.2 years of relevant experience.',
    },
    warnings: [],
    errors: [],
  };

  it('renders CandidateDetailDrawer with ethical AI disclaimer and component breakdown', () => {
    const mockSetCandidate = vi.fn();
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      selectedCandidate: mockCandidate,
      setSelectedCandidate: mockSetCandidate,
    });

    render(<CandidateDetailDrawer />);

    // Candidate title and score
    expect(screen.getByText('Senior_ML_Engineer.pdf')).toBeInTheDocument();
    expect(screen.getByText('87.50')).toBeInTheDocument();

    // Ethical AI Disclaimer must be explicitly present
    expect(
      screen.getByText(/does not represent a statistical probability of hiring success/i)
    ).toBeInTheDocument();

    // Verify component score values
    expect(screen.getByText('100.0')).toBeInTheDocument();
    expect(screen.getByText('85.0')).toBeInTheDocument();
    expect(screen.getByText('90.0')).toBeInTheDocument();
    expect(screen.getByText('82.5')).toBeInTheDocument();

    // Verify experience duration diagnostic
    expect(screen.getAllByText(/5.2/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Duration Satisfied/i)).toBeInTheDocument();
  });

  it('renders IncompleteCandidatesPanel with score withheld and never an unfair zero', () => {
    const mockIncompleteCandidate = {
      upload_id: 'batch_test_001',
      filename: 'Corrupted_Resume.pdf',
      jd_id: 'jd_test_001',
      rank: null,
      status: 'incomplete',
      final_score: null,
      component_scores: {
        required_skills: null,
        responsibilities: null,
        tools_and_technologies: null,
        experience_relevance: null,
      },
      errors: ['Ollama model timeout during required skills assessment.'],
    };

    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      rankingResult: {
        ranked_candidates: [],
        unranked_candidates: [mockIncompleteCandidate],
        ranked_count: 0,
        unranked_count: 1,
      },
      setRankingResult: vi.fn(),
      activeJd: { jd_id: 'jd_test_001' },
    });

    render(<IncompleteCandidatesPanel />);

    // Filename displayed
    expect(screen.getByText('Corrupted_Resume.pdf')).toBeInTheDocument();

    // Score explicitly displayed as withheld, not 0 or 0.00
    expect(screen.getByText('Score Withheld')).toBeInTheDocument();
    expect(screen.queryByText('0.00')).not.toBeInTheDocument();

    // Safe error message displayed
    expect(
      screen.getByText('Ollama model timeout during required skills assessment.')
    ).toBeInTheDocument();
  });

  it('renders active ranking progress tracker with job ID and percentage in RankingDashboardView', () => {
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      rankingJob: {
        job_id: 'job_async_998877',
        status: 'processing',
        progress_percentage: 65.0,
        completed_count: 13,
        total_eligible: 20,
      },
      rankingResult: null,
      isRankingActive: true,
      rankingSubmitting: false,
      triggerRanking: vi.fn(),
      setSelectedCandidate: vi.fn(),
      setActiveTab: vi.fn(),
      systemError: null,
    });

    render(<RankingDashboardView />);

    expect(screen.getByText(/Background Ranking Job in Progress/i)).toBeInTheDocument();
    expect(screen.getByText(/job_async_998877/i)).toBeInTheDocument();
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('13 / 20 Candidates Evaluated')).toBeInTheDocument();
  });

  it('closes CandidateDetailDrawer when user presses the Escape key', () => {
    const mockSetCandidate = vi.fn();
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      selectedCandidate: mockCandidate,
      setSelectedCandidate: mockSetCandidate,
    });

    render(<CandidateDetailDrawer />);

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(mockSetCandidate).toHaveBeenCalledWith(null);
  });

  it('filters and sorts candidates correctly in RankingDashboardView', () => {
    const candidateA = {
      ...mockCandidate,
      filename: 'Alice_Python_Dev.pdf',
      rank: 2,
      final_score: 72.0,
    };
    const candidateB = {
      ...mockCandidate,
      filename: 'Bob_FastAPI_Lead.pdf',
      rank: 1,
      final_score: 91.0,
    };

    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      rankingJob: null,
      rankingResult: {
        ranked_candidates: [candidateA, candidateB],
        unranked_candidates: [],
        ranked_count: 2,
        unranked_count: 0,
      },
      isRankingActive: false,
      rankingSubmitting: false,
      triggerRanking: vi.fn(),
      setSelectedCandidate: vi.fn(),
      setActiveTab: vi.fn(),
      systemError: null,
    });

    render(<RankingDashboardView />);

    // Both candidates displayed initially
    expect(screen.getByText('Alice_Python_Dev.pdf')).toBeInTheDocument();
    expect(screen.getByText('Bob_FastAPI_Lead.pdf')).toBeInTheDocument();

    // Search filter
    const searchInput = screen.getByPlaceholderText('Search candidate filename...');
    fireEvent.change(searchInput, { target: { value: 'Bob' } });

    expect(screen.queryByText('Alice_Python_Dev.pdf')).not.toBeInTheDocument();
    expect(screen.getByText('Bob_FastAPI_Lead.pdf')).toBeInTheDocument();
  });

  it('renders null scores as Unavailable rather than 0 in CandidateDetailDrawer', () => {
    const candidateWithNullScore = {
      ...mockCandidate,
      final_score: null,
      component_scores: {
        required_skills: null,
        responsibilities: null,
        tools_and_technologies: null,
        experience_relevance: null,
      },
    };

    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      selectedCandidate: candidateWithNullScore,
      setSelectedCandidate: vi.fn(),
    });

    render(<CandidateDetailDrawer />);

    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.queryByText('0.00')).not.toBeInTheDocument();
  });

  describe('Phase 10.1 — Section-Routing Explainability Callout', () => {
    const candidateToolsInExpOnly = {
      upload_id: 'batch_test_001',
      filename: 'cand_06_tools_in_exp_only.pdf',
      jd_id: 'jd_test_001',
      rank: 3,
      status: 'complete',
      final_score: 61.93,
      component_scores: {
        required_skills: 100.0,
        responsibilities: 85.0,
        tools_and_technologies: 0.0,
        experience_relevance: 82.5,
      },
      breakdown: {
        tools_and_technologies: {
          category: 'tools_and_technologies',
          score: 0.0,
          original_weight: 0.10,
          normalized_weight: 0.10,
          total_criteria_count: 3,
          qualifying_criteria_count: 0,
          notes: 'Tools mentioned in employment history but not in project portfolio.',
          evidence: [
            { requirement_text: 'Docker', qualifies: false, best_matching_passage: null },
            { requirement_text: 'Kubernetes', qualifies: false, best_matching_passage: null },
            { requirement_text: 'PostgreSQL', qualifies: false, best_matching_passage: null },
          ],
        },
      },
    };

    const candidateToolsAbsentEverywhere = {
      upload_id: 'batch_test_001',
      filename: 'cand_04_zero.pdf',
      jd_id: 'jd_test_001',
      rank: 9,
      status: 'complete',
      final_score: 0.0,
      component_scores: {
        required_skills: 0.0,
        responsibilities: 0.0,
        tools_and_technologies: 0.0,
        experience_relevance: 0.0,
      },
      breakdown: {
        tools_and_technologies: {
          category: 'tools_and_technologies',
          score: 0.0,
          original_weight: 0.10,
          normalized_weight: 0.10,
          total_criteria_count: 3,
          qualifying_criteria_count: 0,
          notes: 'No qualifying project evidence found for defined tools and technologies.',
          evidence: [
            { requirement_text: 'Docker', qualifies: false, best_matching_passage: null },
          ],
        },
      },
    };

    it('renders the section-routing callout when tools are found in employment history but not projects', () => {
      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateToolsInExpOnly,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      // Switch to Tools & Technologies tab
      const toolsTab = screen.getByRole('button', { name: /Tools & Technologies/i });
      fireEvent.click(toolsTab);

      // Verify the required callout title appears
      expect(
        screen.getByText('Tools mentioned in employment history but not in project portfolio.')
      ).toBeInTheDocument();

      // Verify informational, neutral explanation explaining section routing
      expect(
        screen.getByText(/TalentAI evaluates tools and technologies specifically against project portfolio evidence/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/missing project documentation rather than an absence of technical proficiency/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/does not by itself indicate the candidate is unqualified/i)
      ).toBeInTheDocument();

      // Verify accessible region role
      const calloutRegion = screen.getByRole('region', { name: /Section routing explainability callout/i });
      expect(calloutRegion).toBeInTheDocument();

      // Component score remains accurately 0.0
      expect(screen.getByText('0.0')).toBeInTheDocument();
      expect(screen.getByText('61.93')).toBeInTheDocument();
    });

    it('does NOT render the callout when tools are absent from both sections (standard zero score)', () => {
      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateToolsAbsentEverywhere,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      // Switch to Tools & Technologies tab
      const toolsTab = screen.getByRole('button', { name: /Tools & Technologies/i });
      fireEvent.click(toolsTab);

      // Verify callout does NOT appear for standard zero candidate
      expect(
        screen.queryByText('Tools mentioned in employment history but not in project portfolio.')
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('region', { name: /Section routing explainability callout/i })
      ).not.toBeInTheDocument();
    });

    it('does NOT render the callout when candidate has qualifying project tools evidence', () => {
      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: mockCandidate, // has tools_and_technologies: 90.0
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      // Switch to Tools & Technologies tab
      const toolsTab = screen.getByRole('button', { name: /Tools & Technologies/i });
      fireEvent.click(toolsTab);

      expect(
        screen.queryByText('Tools mentioned in employment history but not in project portfolio.')
      ).not.toBeInTheDocument();
    });
  });

  describe('Phase 10.3 Category Diagnostics & Error Rendering', () => {
    it('displays backend diagnostic note for a valid zero-score category with no evidence', () => {
      const candidateZeroResp = {
        upload_id: 'batch_test_001',
        filename: 'Zero_Resp_Candidate.pdf',
        rank: 5,
        final_score: 45.0,
        component_scores: {
          required_skills: 60.0,
          responsibilities: 0.0,
          tools_and_technologies: 50.0,
          experience_relevance: 40.0,
        },
        breakdown: {
          responsibilities: {
            category: 'responsibilities',
            status: 'complete',
            score: 0.0,
            original_weight: 0.30,
            normalized_weight: 0.30,
            total_criteria_count: 2,
            qualifying_criteria_count: 0,
            notes: 'No qualifying passage found for defined responsibilities (all below 0.65 threshold).',
            evidence: [],
          },
        },
        warnings: [],
        errors: [],
      };

      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateZeroResp,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      const respTab = screen.getByRole('button', { name: /Responsibilities/i });
      fireEvent.click(respTab);

      expect(screen.getByText('Zero Alignment')).toBeInTheDocument();
      expect(screen.getByText('No Qualifying Evidence')).toBeInTheDocument();
      expect(
        screen.getByText('No qualifying passage found for defined responsibilities (all below 0.65 threshold).')
      ).toBeInTheDocument();
    });

    it('clearly distinguishes a not-applicable category from a valid zero score', () => {
      const candidateNotApplicable = {
        upload_id: 'batch_test_001',
        filename: 'No_Tools_Candidate.pdf',
        rank: 2,
        final_score: 75.0,
        component_scores: {
          required_skills: 80.0,
          responsibilities: 70.0,
          tools_and_technologies: null,
          experience_relevance: 75.0,
        },
        breakdown: {
          tools_and_technologies: {
            category: 'tools_and_technologies',
            status: 'not_applicable',
            score: null,
            original_weight: 0.10,
            normalized_weight: 0.0,
            total_criteria_count: 0,
            qualifying_criteria_count: 0,
            notes: 'Job Description defines no tools and technologies requirements.',
            evidence: [],
          },
        },
        warnings: [],
        errors: [],
      };

      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateNotApplicable,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      const toolsTab = screen.getByRole('button', { name: /Tools & Technologies/i });
      fireEvent.click(toolsTab);

      // Must clearly show Not Applicable and Excluded from Evaluation, not Zero Alignment
      expect(screen.getByText('Not Applicable')).toBeInTheDocument();
      expect(screen.getByText('Excluded from Evaluation')).toBeInTheDocument();
      expect(
        screen.getByText('Job Description defines no tools and technologies requirements.')
      ).toBeInTheDocument();
      expect(screen.queryByText('Zero Alignment')).not.toBeInTheDocument();
    });

    it('displays an unavailable category note explaining failure without claiming candidate lacks skill', () => {
      const candidateUnavailable = {
        upload_id: 'batch_test_001',
        filename: 'Service_Failure_Candidate.pdf',
        rank: null,
        final_score: null,
        component_scores: {
          required_skills: null,
          responsibilities: 70.0,
          tools_and_technologies: 50.0,
          experience_relevance: 60.0,
        },
        breakdown: {
          required_skills: {
            category: 'required_skills',
            status: 'unavailable',
            score: null,
            original_weight: 0.25,
            normalized_weight: 0.0,
            total_criteria_count: 3,
            qualifying_criteria_count: 0,
            notes: 'Required skills matching service failure: Inference slot timeout occurred.',
            evidence: [],
          },
        },
        warnings: [],
        errors: ["Category 'required_skills' is technically unavailable due to service failure."],
      };

      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateUnavailable,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      // Required Skills tab is active by default
      expect(screen.getByText('Evaluation Unavailable')).toBeInTheDocument();
      expect(screen.getByText('Technical Service Failure')).toBeInTheDocument();
      expect(
        screen.getByText('Required skills matching service failure: Inference slot timeout occurred.')
      ).toBeInTheDocument();
      expect(
        screen.getByText(/This score is withheld due to a technical evaluation failure; it does not indicate that the candidate lacks this qualification/i)
      ).toBeInTheDocument();
    });

    it('renders candidate errors accessibly alongside diagnostics', () => {
      const candidateWithErrors = {
        upload_id: 'batch_test_001',
        filename: 'Error_Diagnostic_Candidate.pdf',
        rank: null,
        final_score: null,
        component_scores: {},
        breakdown: {},
        warnings: ['Experience diagnostic: ambiguous_dates in employment history.'],
        errors: [
          "Category 'required_skills' is technically unavailable due to service failure.",
          'Retrieval worker connection timeout on port 6333.',
        ],
      };

      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateWithErrors,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      // Accessible alert region for technical errors
      const errorAlert = screen.getByRole('alert');
      expect(errorAlert).toBeInTheDocument();
      expect(screen.getByText('Technical Evaluation Errors')).toBeInTheDocument();
      expect(
        screen.getByText("Category 'required_skills' is technically unavailable due to service failure.")
      ).toBeInTheDocument();
      expect(
        screen.getByText('Retrieval worker connection timeout on port 6333.')
      ).toBeInTheDocument();

      // Warnings header and content
      expect(screen.getByText('Evaluation Diagnostics')).toBeInTheDocument();
      expect(
        screen.getByText('Experience diagnostic: ambiguous_dates in employment history.')
      ).toBeInTheDocument();
    });

    it('renders section-routing callout without relying on legacy tools_in_experience_only or has_experience_mentions attributes', () => {
      const pureSchemaCandidate = {
        upload_id: 'batch_test_001',
        filename: 'Pure_Schema_Candidate.pdf',
        rank: 3,
        final_score: 55.0,
        component_scores: {
          required_skills: 80.0,
          responsibilities: 60.0,
          tools_and_technologies: 0.0,
          experience_relevance: 50.0,
        },
        breakdown: {
          tools_and_technologies: {
            category: 'tools_and_technologies',
            status: 'complete',
            score: 0.0,
            original_weight: 0.10,
            normalized_weight: 0.10,
            total_criteria_count: 2,
            qualifying_criteria_count: 0,
            notes: 'Tools mentioned in employment history but not in project portfolio.',
            evidence: [],
          },
        },
        warnings: [],
        errors: [],
      };

      // Explicitly ensure legacy attributes are undefined
      expect(pureSchemaCandidate.tools_in_experience_only).toBeUndefined();
      expect(pureSchemaCandidate.breakdown.tools_and_technologies.has_experience_mentions).toBeUndefined();

      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: pureSchemaCandidate,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      const toolsTab = screen.getByRole('button', { name: /Tools & Technologies/i });
      fireEvent.click(toolsTab);

      // Verify callout renders properly based on notes alone
      expect(
        screen.getByText('Tools mentioned in employment history but not in project portfolio.')
      ).toBeInTheDocument();
      expect(
        screen.getByRole('region', { name: /Section routing explainability callout/i })
      ).toBeInTheDocument();
    });

    it('displays fallback message when category has no evidence and no diagnostic note', () => {
      const candidateNoNotes = {
        upload_id: 'batch_test_001',
        filename: 'No_Notes_Candidate.pdf',
        rank: 1,
        final_score: 80.0,
        component_scores: {
          required_skills: 80.0,
          responsibilities: 80.0,
          tools_and_technologies: 80.0,
          experience_relevance: 80.0,
        },
        breakdown: {
          responsibilities: {
            category: 'responsibilities',
            status: 'complete',
            score: 80.0,
            original_weight: 0.30,
            normalized_weight: 0.30,
            total_criteria_count: 0,
            qualifying_criteria_count: 0,
            notes: null,
            evidence: [],
          },
        },
        warnings: [],
        errors: [],
      };

      vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
        selectedCandidate: candidateNoNotes,
        setSelectedCandidate: vi.fn(),
      });

      render(<CandidateDetailDrawer />);

      const respTab = screen.getByRole('button', { name: /Responsibilities/i });
      fireEvent.click(respTab);

      expect(screen.getByText('No responsibilities evidence recorded.')).toBeInTheDocument();
    });

    // =========================================================================
    // STAGE 5D: EVIDENCE-BASED EXPERIENCE EXPLAINABILITY TESTS
    // =========================================================================
    describe('Stage 5D Experience Explainability & Recruiter UI', () => {
      it('renders evidence-based experience explainability with all provenance metrics and disclosure', () => {
        const evidenceBasedCandidate = {
          upload_id: 'batch_5d_001',
          filename: 'Fintech_Lead.pdf',
          rank: 1,
          final_score: 67.71,
          component_scores: {
            required_skills: 100.0,
            responsibilities: 48.57,
            tools_and_technologies: 71.43,
            experience_relevance: 60.0,
          },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 60.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 21.0,
              total_criteria_count: 2,
              qualifying_criteria_count: 1,
              notes:
                'Evidence-based experience score E = 100 * S_agg (0.7500) * D_global (0.8000) = 60.00. Scoring method: evidence_based. Diagnostic status: duration_calculated.',
              evidence: [
                {
                  criterion: 'Fintech',
                  calibrated_similarity: 0.75,
                  best_relevance_score: 0.75,
                  qualifies: true,
                  supporting_role: 'Senior Backend Engineer',
                  supporting_company: 'Tech Corp',
                  supporting_decision: 'RELEVANT',
                  relevance_ratio: 1.0,
                  relevant_duration_years: 4.0,
                  relevant_work_summary:
                    'Architected low latency payment processing gateways.',
                  reason: 'Calibrated semantic similarity: 0.75 from role Senior Backend Engineer.',
                },
                {
                  criterion: 'Healthcare',
                  calibrated_similarity: 0.0,
                  best_relevance_score: 0.0,
                  qualifies: false,
                  supporting_role: null,
                  supporting_company: null,
                  supporting_decision: null,
                  relevance_ratio: 0.0,
                  relevant_duration_years: 0.0,
                  relevant_work_summary: null,
                  reason:
                    'No candidate experience qualified for preferred domain Healthcare.',
                },
              ],
            },
          },
          experience_diagnostic: {
            minimum_years: 3.0,
            maximum_years: 5.0,
            relevant_duration_years: 4.0,
            minimum_duration_satisfied: true,
            maximum_duration_exceeded: false,
            diagnostic_status: 'duration_calculated',
            diagnostic_message:
              'Relevant experience duration successfully calculated (4.0 years).',
            duration_factor: 0.8,
            saturation_target_years: 5.0,
            range_status: 'bounded',
          },
          warnings: [],
          errors: [],
        };

        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: evidenceBasedCandidate,
          setSelectedCandidate: vi.fn(),
        });

        render(<CandidateDetailDrawer />);

        // Switch to Experience tab
        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // 1. Scoring Method Badge
        expect(screen.getByText('Evidence-Based Scoring')).toBeInTheDocument();
        expect(
          screen.getByText(/Formula: E = 100 × S_agg × D_global/i)
        ).toBeInTheDocument();

        // 2. Component Score & Weighted Contribution
        expect(screen.getAllByText('60.0').length).toBeGreaterThan(0);
        expect(screen.getByText('21.00')).toBeInTheDocument();

        // 3. Dual Metrics: S_agg and D_global
        expect(screen.getByText('0.750')).toBeInTheDocument();
        expect(screen.getByText('0.800')).toBeInTheDocument();

        // 4. Global Duration Disclosure (Correction 3 exact wording)
        expect(
          screen.getByText(
            /Duration is pooled across relevant experience roles under the approved global duration formula\. It is not independently calculated for each JD domain\. Strong tenure in one domain can influence the global duration factor applied to aggregate domain similarity\./i
          )
        ).toBeInTheDocument();

        // 5. Domain Breakdown
        expect(screen.getByText('Fintech')).toBeInTheDocument();
        expect(screen.getByText('S_m = 0.750')).toBeInTheDocument();
        expect(screen.getByText(/Senior Backend Engineer • Tech Corp/i)).toBeInTheDocument();

        // 6. Unsupported Domain receives 0.000
        expect(screen.getByText('Healthcare')).toBeInTheDocument();
        expect(screen.getByText('S_m = 0.000')).toBeInTheDocument();
        expect(
          screen.getByText(/No supporting relevant role in resume/i)
        ).toBeInTheDocument();

        // 7. Verified Work Summary
        expect(
          screen.getByText(
            /"Architected low latency payment processing gateways\."/i
          )
        ).toBeInTheDocument();
      });

      it('renders legacy presentation when scoring method is legacy or missing marker', () => {
        const legacyCandidate = {
          upload_id: 'batch_5d_002',
          filename: 'Legacy_Dev.pdf',
          rank: 2,
          final_score: 85.0,
          component_scores: {
            required_skills: 85.0,
            responsibilities: 85.0,
            tools_and_technologies: 85.0,
            experience_relevance: 100.0,
          },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 100.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 35.0,
              total_criteria_count: 1,
              qualifying_criteria_count: 1,
              notes: null, // Legacy: no evidence-based marker
              evidence: [
                {
                  criterion: 'Fintech',
                  supporting_role: 'Lead Developer',
                  supporting_company: 'Global Bank',
                  supporting_decision: 'RELEVANT',
                  reason: 'Demonstrated extensive fintech experience.',
                },
              ],
            },
          },
          experience_diagnostic: {
            relevant_duration_years: 5.0,
            minimum_duration_satisfied: true,
          },
          warnings: [],
          errors: [],
        };

        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: legacyCandidate,
          setSelectedCandidate: vi.fn(),
        });

        render(<CandidateDetailDrawer />);

        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // Verify Legacy Badge is rendered
        expect(screen.getByText('Legacy Categorical Scoring')).toBeInTheDocument();
        // Verify Evidence-Based badge is NOT rendered
        expect(screen.queryByText('Evidence-Based Scoring')).not.toBeInTheDocument();
        // Verify formula is NOT rendered
        expect(screen.queryByText(/Formula: E = 100 × S_agg × D_global/i)).not.toBeInTheDocument();

        // Verify legacy evidence card renders
        expect(screen.getByText('Fintech')).toBeInTheDocument();
        expect(screen.getByText(/Lead Developer • Global Bank/i)).toBeInTheDocument();
        expect(screen.getByText('Demonstrated extensive fintech experience.')).toBeInTheDocument();
      });

      // -----------------------------------------------------------------------
      // STAGE 5D.1 REQUIRED TESTS: MISSING VS ZERO DURATION & WEIGHTS
      // -----------------------------------------------------------------------

      it('Test 1 & 2: distinguishes genuine duration factor zero from missing duration factor', () => {
        // Case 1: Genuine 0.0 duration factor
        const candidateZeroD = {
          upload_id: 'b_5d1_1',
          filename: 'Zero_D.pdf',
          rank: 1,
          final_score: 0.0,
          component_scores: { experience_relevance: 0.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 0.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 0.0,
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
          experience_diagnostic: {
            duration_factor: 0.0, // Genuine numeric zero
            relevant_duration_years: 0.0,
          },
          warnings: [],
          errors: [],
        };

        const { rerender } = render(<CandidateDetailDrawer />);
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateZeroD,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // Genuine zero displays 0.000
        expect(screen.getByText('0.000')).toBeInTheDocument();

        // Case 2: Missing duration factor (null / undefined)
        const candidateMissingD = {
          ...candidateZeroD,
          experience_diagnostic: {
            duration_factor: null, // Missing / unavailable
            relevant_duration_years: 0.0,
          },
        };
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateMissingD,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        // Missing duration factor displays Unavailable
        expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
      });

      it('Test 3 & 4: distinguishes genuine relevant duration zero from missing relevant duration', () => {
        // Case 3: Genuine 0.0 relevant duration
        const candidateZeroDuration = {
          upload_id: 'b_5d1_2',
          filename: 'Zero_Dur.pdf',
          rank: 1,
          final_score: 0.0,
          component_scores: { experience_relevance: 0.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 0.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 0.0,
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
          experience_diagnostic: {
            duration_factor: 0.0,
            relevant_duration_years: 0.0, // Genuine 0.0
          },
          warnings: [],
          errors: [],
        };

        const { rerender } = render(<CandidateDetailDrawer />);
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateZeroDuration,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // Genuine 0.0 displays 0.0 yrs
        expect(screen.getByText('0.0 yrs')).toBeInTheDocument();

        // Case 4: Missing relevant duration (null / undefined)
        const candidateMissingDuration = {
          ...candidateZeroDuration,
          experience_diagnostic: {
            duration_factor: 0.0,
            relevant_duration_years: null, // Missing
          },
        };
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateMissingDuration,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
      });

      it('Test 5: missing saturation target displays Unavailable and never Unbounded', () => {
        const candidateMissingTarget = {
          upload_id: 'b_5d1_3',
          filename: 'Missing_Target.pdf',
          rank: 1,
          final_score: 50.0,
          component_scores: { experience_relevance: 50.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 50.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 17.5,
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
          experience_diagnostic: {
            duration_factor: 0.5,
            relevant_duration_years: 2.5,
            saturation_target_years: null, // Missing saturation target
            range_status: null,
          },
          warnings: [],
          errors: [],
        };

        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateMissingTarget,
          setSelectedCandidate: vi.fn(),
        });

        render(<CandidateDetailDrawer />);
        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // Target must NOT display "Unbounded"
        expect(screen.queryByText(/Unbounded/i)).not.toBeInTheDocument();
        // Target must display "Unavailable"
        expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
      });

      it('Test 6 & 7: explicit G1-C unbounded range vs missing range status', () => {
        // Case 6: Explicit range_status = "unspecified"
        const candidateG1C = {
          upload_id: 'b_5d1_4',
          filename: 'G1C_Candidate.pdf',
          rank: 1,
          final_score: 0.0,
          component_scores: { experience_relevance: 0.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 0.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 0.0,
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
          experience_diagnostic: {
            duration_factor: 0.0,
            relevant_duration_years: 4.0,
            saturation_target_years: null,
            range_status: 'unspecified', // Explicit G1-C
          },
          warnings: [],
          errors: [],
        };

        const { rerender } = render(<CandidateDetailDrawer />);
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateG1C,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // Explicit G1-C displays badge and notice
        expect(screen.getByText('unspecified')).toBeInTheDocument();
        expect(screen.getByText(/Gate 1 \(G1-C\) Unspecified Target:/i)).toBeInTheDocument();

        // Case 7: Missing range_status (null)
        const candidateMissingRange = {
          ...candidateG1C,
          experience_diagnostic: {
            ...candidateG1C.experience_diagnostic,
            range_status: null, // Missing!
          },
        };
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateMissingRange,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        // When range_status is missing, do NOT infer "unspecified" or show G1-C alert!
        expect(screen.queryByText(/Gate 1 \(G1-C\) Unspecified Target:/i)).not.toBeInTheDocument();
      });

      it('Test 8, 9, 10: original vs normalized weights and actual backend weighted contribution', () => {
        // Case 8: Original weight 35% and normalized weight 35%
        const candidateEqualWeights = {
          upload_id: 'b_5d1_5',
          filename: 'Equal_Weights.pdf',
          rank: 1,
          final_score: 70.0,
          component_scores: { experience_relevance: 70.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 70.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 24.5, // Actual backend value
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
          experience_diagnostic: {
            duration_factor: 1.0,
            relevant_duration_years: 5.0,
          },
          warnings: [],
          errors: [],
        };

        const { rerender } = render(<CandidateDetailDrawer />);
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateEqualWeights,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        expect(screen.getByText('Applied Weight')).toBeInTheDocument();
        expect(screen.getByText('Original configured weight: 35%')).toBeInTheDocument();
        expect(screen.getByText('24.50')).toBeInTheDocument();

        // Case 9 & 10: Original 35% and Renormalized 38.89%, actual contribution used
        const candidateRenormalized = {
          ...candidateEqualWeights,
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 60.0,
              original_weight: 0.35,
              normalized_weight: 0.388889, // Tools absent -> 38.89%
              weighted_contribution: 23.33, // Actual backend value
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
        };
        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateRenormalized,
          setSelectedCandidate: vi.fn(),
        });
        rerender(<CandidateDetailDrawer />);

        // Displays Applied Weight 38.89%
        expect(screen.getByText('38.89%')).toBeInTheDocument();
        // Displays both original and note clearly
        expect(screen.getByText(/Original:/i)).toBeInTheDocument();
        expect(screen.getByText('35%')).toBeInTheDocument();
        expect(screen.getByText(/Renormalized based on JD applicability/i)).toBeInTheDocument();
        // Verifies actual backend contribution is displayed directly
        expect(screen.getByText('23.33')).toBeInTheDocument();
      });

      it('Test 11: missing weight fields display Unavailable', () => {
        const candidateMissingWeights = {
          upload_id: 'b_5d1_6',
          filename: 'Missing_Weights.pdf',
          rank: 1,
          final_score: 50.0,
          component_scores: { experience_relevance: 50.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 50.0,
              original_weight: null, // Missing
              normalized_weight: null, // Missing
              weighted_contribution: null, // Missing
              notes: 'Scoring method: evidence_based',
              evidence: [],
            },
          },
          experience_diagnostic: {
            duration_factor: 1.0,
            relevant_duration_years: 5.0,
          },
          warnings: [],
          errors: [],
        };

        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: candidateMissingWeights,
          setSelectedCandidate: vi.fn(),
        });

        render(<CandidateDetailDrawer />);
        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        expect(screen.getAllByText('Unavailable').length).toBeGreaterThanOrEqual(2);
      });

      it('renders layout elements with responsive container structure', () => {
        const testCandidate = {
          upload_id: 'batch_5d_005',
          filename: 'Responsive_Candidate.pdf',
          rank: 1,
          final_score: 70.0,
          component_scores: { experience_relevance: 70.0 },
          breakdown: {
            experience_relevance: {
              category: 'experience_relevance',
              status: 'complete',
              score: 70.0,
              original_weight: 0.35,
              normalized_weight: 0.35,
              weighted_contribution: 24.5,
              notes: 'Scoring method: evidence_based',
              evidence: [
                {
                  criterion: 'Fintech',
                  calibrated_similarity: 0.7,
                  qualifies: true,
                  supporting_role: 'Engineer',
                },
              ],
            },
          },
          experience_diagnostic: {
            duration_factor: 1.0,
            relevant_duration_years: 5.0,
            minimum_duration_satisfied: true,
          },
          warnings: [],
          errors: [],
        };

        vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
          selectedCandidate: testCandidate,
          setSelectedCandidate: vi.fn(),
        });

        const { container } = render(<CandidateDetailDrawer />);

        const expTab = screen.getByRole('button', { name: /Experience Evidence/i });
        fireEvent.click(expTab);

        // Verify responsive containers exist in DOM
        const expContainer = container.querySelector('.evidence-based-experience-container');
        expect(expContainer).toBeInTheDocument();

        const summaryGrid = container.querySelector('.experience-score-summary-grid');
        expect(summaryGrid).toBeInTheDocument();

        const dualMetricsGrid = container.querySelector('.dual-metrics-grid');
        expect(dualMetricsGrid).toBeInTheDocument();

        const disclosureBanner = container.querySelector('.duration-disclosure-banner');
        expect(disclosureBanner).toBeInTheDocument();
      });
    });
  });
});

