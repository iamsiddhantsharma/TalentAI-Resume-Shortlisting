import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext.jsx';
import { uploadJdFile, submitJdRawText } from '../../api/jdApi.js';
import { uploadResumes, getUploadStatus } from '../../api/uploadApi.js';
import { activateBatch } from '../../api/batchApi.js';
import SyntheticPresetSelector from '../demo/SyntheticPresetSelector.jsx';

export default function UploadWorkflowView() {
  const { refreshSystemState, setActiveTab, triggerRanking } = useApp();

  // Primary Tab: 'jd' | 'resumes' | 'demo'
  const [activeUploadTab, setActiveUploadTab] = useState('jd');

  // JD Intake State
  const [jdMode, setJdMode] = useState('file'); // 'file' | 'text'
  const [jdRawText, setJdRawText] = useState('');
  const [jdFile, setJdFile] = useState(null);
  const [isJdUploading, setIsJdUploading] = useState(false);
  const [jdResult, setJdResult] = useState(null);
  const [jdError, setJdError] = useState(null);

  // Resume Intake State
  const [resumeFiles, setResumeFiles] = useState([]);
  const [autoActivate, setAutoActivate] = useState(true);
  const [isResumeUploading, setIsResumeUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [resumeError, setResumeError] = useState(null);

  const fileInputRef = useRef(null);
  const jdFileInputRef = useRef(null);
  const pollTimerRef = useRef(null);

  // Poll upload progress
  const pollIngestionStatus = async (uploadId) => {
    try {
      const statusData = await getUploadStatus(uploadId);
      setUploadProgress(statusData);

      if (statusData.processing > 0) {
        pollTimerRef.current = setTimeout(() => pollIngestionStatus(uploadId), 2000);
      } else {
        // Extraction complete
        await refreshSystemState();
      }
    } catch (err) {
      console.warn('Ingestion status poll failed:', err);
    }
  };

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, []);

  // Handle JD Submission
  const handleJdSubmit = async (e) => {
    e.preventDefault();
    setIsJdUploading(true);
    setJdError(null);
    setJdResult(null);

    try {
      let result;
      if (jdMode === 'file') {
        if (!jdFile) throw new Error('Please select a Job Description file (.pdf, .docx, .txt).');
        result = await uploadJdFile(jdFile);
      } else {
        if (!jdRawText.trim()) throw new Error('Please enter the Job Description text.');
        result = await submitJdRawText(jdRawText);
      }
      setJdResult(result);
      await refreshSystemState();
    } catch (err) {
      setJdError(err.message || 'Failed to process Job Description.');
    } finally {
      setIsJdUploading(false);
    }
  };

  // Handle Resume Upload
  const handleResumeSubmit = async (e) => {
    e.preventDefault();
    if (resumeFiles.length === 0) {
      setResumeError('Please select at least one resume file or a ZIP archive.');
      return;
    }

    setIsResumeUploading(true);
    setResumeError(null);
    setUploadProgress(null);

    try {
      const uploadRes = await uploadResumes(resumeFiles, autoActivate);
      setUploadProgress({
        upload_id: uploadRes.upload_id,
        batch_id: uploadRes.batch_id,
        batch_status: uploadRes.batch_status,
        total: uploadRes.total_files_received,
        completed: 0,
        processing: uploadRes.supported_files,
        failed: uploadRes.failed_files,
        results: [],
      });

      // Start polling extraction status
      pollIngestionStatus(uploadRes.upload_id);
    } catch (err) {
      setResumeError(err.message || 'Failed to upload resume files.');
      setIsResumeUploading(false);
    }
  };

  const handleActivateBatch = async (batchId) => {
    try {
      await activateBatch(batchId);
      await refreshSystemState();
    } catch (err) {
      setResumeError(err.message || 'Failed to activate batch.');
    }
  };

  return (
    <div className="page-body">
      <div className="page-header">
        <div>
          <h1 className="page-title">Candidate & Criteria Ingestion</h1>
          <p className="page-description">
            Upload Job Descriptions and batch candidate resumes (PDF, DOCX, TXT, or ZIP).
          </p>
        </div>
      </div>

      {/* Synthetic Demo Banner Callout */}
      <div
        className="alert alert-info"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.25rem',
          background: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🧪</span>
          <div>
            <strong>Need safe test data without uploading real resumes?</strong>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
              Explore the Synthetic Demo Sandbox featuring 12 pre-configured industry JDs and 240 synthetic candidate profiles.
            </div>
          </div>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setActiveUploadTab('demo')}
        >
          Open Synthetic Demo &rarr;
        </button>
      </div>

      {/* Workflow Tabs */}
      <div className="tab-list">
        <button
          type="button"
          className={`tab-btn ${activeUploadTab === 'jd' ? 'active' : ''}`}
          onClick={() => setActiveUploadTab('jd')}
        >
          1. Job Description Setup
        </button>
        <button
          type="button"
          className={`tab-btn ${activeUploadTab === 'resumes' ? 'active' : ''}`}
          onClick={() => setActiveUploadTab('resumes')}
        >
          2. Candidate Batch Upload
        </button>
        <button
          type="button"
          className={`tab-btn ${activeUploadTab === 'demo' ? 'active' : ''}`}
          onClick={() => setActiveUploadTab('demo')}
        >
          🧪 3. Synthetic Demo Sandbox
        </button>
      </div>

      {/* TAB 1: Job Description */}
      {activeUploadTab === 'jd' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Establish Active Role Requirements</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                className={`btn btn-sm ${jdMode === 'file' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setJdMode('file')}
              >
                Upload File
              </button>
              <button
                type="button"
                className={`btn btn-sm ${jdMode === 'text' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setJdMode('text')}
              >
                Paste Text
              </button>
            </div>
          </div>
          <div className="card-body">
            {jdError && (
              <div className="alert alert-danger" role="alert">
                {jdError}
              </div>
            )}

            {jdResult && (
              <div className="alert alert-info">
                <div>
                  <strong>Job Description Successfully Extracted!</strong>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                    Extracted {jdResult.structured_data?.required_skills?.length ?? 0} required skills and{' '}
                    {jdResult.structured_data?.responsibilities?.length ?? 0} responsibilities. This is now the active role criteria.
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleJdSubmit}>
              {jdMode === 'file' ? (
                <div
                  className="dropzone"
                  onClick={() => jdFileInputRef.current?.click()}
                  style={{ marginBottom: '1.25rem' }}
                >
                  <input
                    type="file"
                    ref={jdFileInputRef}
                    accept=".pdf,.docx,.txt"
                    style={{ display: 'none' }}
                    onChange={(e) => setJdFile(e.target.files[0] || null)}
                  />
                  <svg className="dropzone-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                    {jdFile ? jdFile.name : 'Click or Drag & Drop Job Description file'}
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                    Supports PDF, DOCX, and TXT files
                  </div>
                </div>
              ) : (
                <div className="form-group">
                  <label className="form-label" htmlFor="jd-raw-text">Paste Job Description Text</label>
                  <textarea
                    id="jd-raw-text"
                    className="form-control"
                    placeholder="Paste the full job posting including required skills, responsibilities, and experience requirements..."
                    value={jdRawText}
                    onChange={(e) => setJdRawText(e.target.value)}
                    rows={8}
                  />
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary"
                disabled={isJdUploading || (jdMode === 'file' && !jdFile) || (jdMode === 'text' && !jdRawText.trim())}
              >
                {isJdUploading ? 'Extracting Criteria with AI...' : 'Parse & Set Active JD'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: Resume Ingestion */}
      {activeUploadTab === 'resumes' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Upload Resumes or ZIP Archive</span>
          </div>
          <div className="card-body">
            {resumeError && (
              <div className="alert alert-danger" role="alert">
                {resumeError}
              </div>
            )}

            <form onSubmit={handleResumeSubmit}>
              <div
                className="dropzone"
                onClick={() => fileInputRef.current?.click()}
                style={{ marginBottom: '1.25rem' }}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  multiple
                  accept=".pdf,.docx,.txt,.zip"
                  style={{ display: 'none' }}
                  onChange={(e) => setResumeFiles(Array.from(e.target.files || []))}
                />
                <svg className="dropzone-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                  {resumeFiles.length > 0
                    ? `${resumeFiles.length} file(s) selected`
                    : 'Click to select individual resumes or a ZIP archive'}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                  PDF, DOCX, TXT, or ZIP container with resumes
                </div>
              </div>

              <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  id="auto-activate-toggle"
                  checked={autoActivate}
                  onChange={(e) => setAutoActivate(e.target.checked)}
                />
                <label htmlFor="auto-activate-toggle" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Automatically set this batch as the active candidate pool upon completion
                </label>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={isResumeUploading || resumeFiles.length === 0}
              >
                {isResumeUploading ? 'Uploading & Enqueuing...' : 'Upload & Process Batch'}
              </button>
            </form>

            {/* Ingestion Progress Monitor */}
            {uploadProgress && (
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
                <div className="progress-header">
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                    Batch Parsing Progress ({uploadProgress.completed} of {uploadProgress.total} completed)
                  </span>
                  <span className="badge badge-info">
                    {uploadProgress.processing > 0 ? 'Parsing in Background' : 'Batch Ready'}
                  </span>
                </div>

                <div className="progress-track" style={{ marginBottom: '1rem' }}>
                  <div
                    className="progress-fill"
                    style={{
                      width: `${uploadProgress.total > 0 ? (uploadProgress.completed / uploadProgress.total) * 100 : 0}%`,
                    }}
                  />
                </div>

                {uploadProgress.processing === 0 && (
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                    {!uploadProgress.is_active && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleActivateBatch(uploadProgress.batch_id)}
                      >
                        Activate This Batch
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        setActiveTab('ranking');
                        triggerRanking();
                      }}
                    >
                      Rank Candidates Now &rarr;
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Synthetic Demo Sandbox */}
      {activeUploadTab === 'demo' && (
        <SyntheticPresetSelector />
      )}
    </div>
  );
}
