import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import OverviewView from '../components/overview/OverviewView.jsx';
import UploadWorkflowView from '../components/upload/UploadWorkflowView.jsx';
import * as AppContextModule from '../context/AppContext.jsx';

describe('Overview & Upload Workflow Views', () => {
  it('displays Setup Required alert in OverviewView when no JD or batch is loaded', () => {
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      activeJd: null,
      activeBatch: null,
      rankingResult: null,
      setActiveTab: vi.fn(),
      triggerRanking: vi.fn(),
      isRankingActive: false,
      rankingSubmitting: false,
    });

    render(<OverviewView />);

    expect(screen.getByText(/Setup Required/i)).toBeInTheDocument();
    expect(screen.getByText(/Please upload a Job Description and a candidate resume batch/i)).toBeInTheDocument();
  });

  it('displays Ready for Ranking and criteria tags in OverviewView when active JD and batch exist', () => {
    const mockJd = {
      jd_id: 'jd_live_1234',
      filename: 'Staff_Software_Engineer.pdf',
      structured_data: {
        required_skills: ['Python', 'FastAPI', 'Distributed Systems'],
        responsibilities: ['Design microservices'],
        tools_and_technologies: ['Docker', 'Kubernetes'],
        experience_requirements: [
          {
            minimum_years: 5.0,
            maximum_years: 8.0,
            preferred_domains: ['Fintech'],
          },
        ],
      },
    };

    const mockBatch = {
      batch_id: 'batch_live_5678',
      batch_name: 'Q4_Engineering_Candidates.zip',
      status: 'active',
      total_files: 12,
      completed_count: 12,
    };

    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      activeJd: mockJd,
      activeBatch: mockBatch,
      rankingResult: null,
      setActiveTab: vi.fn(),
      triggerRanking: vi.fn(),
      isRankingActive: false,
      rankingSubmitting: false,
    });

    render(<OverviewView />);

    expect(screen.getByText(/Ready for Ranking/i)).toBeInTheDocument();
    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('FastAPI')).toBeInTheDocument();
    expect(screen.getByText('Distributed Systems')).toBeInTheDocument();
    expect(screen.getByText(/years minimum/i)).toBeInTheDocument();
    expect(screen.getByText('Q4_Engineering_Candidates.zip')).toBeInTheDocument();
  });

  it('allows switching between File and Text intake tabs in UploadWorkflowView', () => {
    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      refreshSystemState: vi.fn(),
      setActiveTab: vi.fn(),
      triggerRanking: vi.fn(),
    });

    render(<UploadWorkflowView />);

    // Default tab is 1. Job Description Setup with Upload File
    expect(screen.getByText(/Click or Drag & Drop Job Description file/i)).toBeInTheDocument();

    // Switch to Paste Text
    const pasteTextBtn = screen.getByRole('button', { name: /Paste Text/i });
    fireEvent.click(pasteTextBtn);

    expect(screen.getByLabelText(/Paste Job Description Text/i)).toBeInTheDocument();

    // Switch to Candidate Batch Upload tab
    const batchTabBtn = screen.getByRole('button', { name: /2\. Candidate Batch Upload/i });
    fireEvent.click(batchTabBtn);

    expect(screen.getByText(/Click to select individual resumes or a ZIP archive/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Automatically set this batch as the active candidate pool/i)).toBeInTheDocument();
  });
});
