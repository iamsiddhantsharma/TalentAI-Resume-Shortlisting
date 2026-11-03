import { apiFetch } from './client.js';

/**
 * Queue an asynchronous batch ranking job across eligible candidates in the active batch.
 * @param {object} params
 * @param {string} [params.upload_id]
 * @param {string} [params.jd_id]
 * @param {number|null} [params.limit=null]
 * @param {number} [params.skip=0]
 * @returns {Promise<RankingJobStatusResponse>}
 */
export async function startAsyncRanking({ upload_id = null, jd_id = null, limit = null, skip = 0, use_evidence_based_experience = null } = {}) {
  const body = {};
  if (upload_id) body.upload_id = upload_id;
  if (jd_id) body.jd_id = jd_id;
  if (use_evidence_based_experience !== null) body.use_evidence_based_experience = use_evidence_based_experience;
  if (limit !== null && limit !== undefined) body.limit = limit;
  if (skip) body.skip = skip;

  return apiFetch('/ranking/rank-batch-async', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}

/**
 * Poll execution status, progress, and results of an asynchronous ranking job.
 * @param {string} jobId
 * @returns {Promise<RankingJobStatusResponse>}
 */
export async function getRankingJobStatus(jobId) {
  return apiFetch(`/ranking/jobs/${encodeURIComponent(jobId)}`);
}

/**
 * Score and explain a single candidate resume against the active Job Description.
 * @param {string} uploadId
 * @param {string} filename
 * @param {string} [jdId]
 * @param {boolean} [useEvidenceBasedExperience=null]
 * @returns {Promise<CandidateRankingResult>}
 */
export async function rankResume(uploadId, filename, jdId = null, useEvidenceBasedExperience = null) {
  const body = {
    upload_id: uploadId,
    filename,
  };
  if (jdId) body.jd_id = jdId;
  if (useEvidenceBasedExperience !== null) body.use_evidence_based_experience = useEvidenceBasedExperience;

  return apiFetch('/ranking/rank-resume', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    timeout: 60000,
  });
}

/**
 * Synchronous batch ranking fallback.
 * @param {object} params
 */
export async function rankBatchSync({ upload_id = null, jd_id = null, limit = null, skip = 0, use_evidence_based_experience = null } = {}) {
  const body = {};
  if (upload_id) body.upload_id = upload_id;
  if (jd_id) body.jd_id = jd_id;
  if (use_evidence_based_experience !== null) body.use_evidence_based_experience = use_evidence_based_experience;
  if (limit !== null && limit !== undefined) body.limit = limit;
  if (skip) body.skip = skip;

  return apiFetch('/ranking/rank-batch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    timeout: 180000,
  });
}
