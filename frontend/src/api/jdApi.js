import { apiFetch } from './client.js';

/**
 * Upload a Job Description file (PDF, DOCX, TXT).
 * @param {File} file
 * @returns {Promise<JobDescription>}
 */
export async function uploadJdFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  return apiFetch('/job-description/file', {
    method: 'POST',
    body: formData,
    timeout: 60000,
  });
}

/**
 * Submit Job Description as raw plain text.
 * @param {string} text
 * @returns {Promise<JobDescription>}
 */
export async function submitJdRawText(text) {
  return apiFetch('/job-description/raw', {
    method: 'POST',
    headers: {
      'Content-Type': 'text/plain',
    },
    body: text,
    timeout: 60000,
  });
}

/**
 * Submit Job Description as structured JSON text.
 * @param {string} text
 * @returns {Promise<JobDescription>}
 */
export async function submitJdJson(text) {
  return apiFetch('/job-description/text', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
    timeout: 60000,
  });
}

/**
 * Retrieve the active Job Description from MongoDB.
 * Under TalentAI rules, at most one active JD exists at any time.
 * @returns {Promise<any | null>}
 */
export async function getActiveJd() {
  try {
    const res = await apiFetch('/results/mongodb/job-descriptions');
    if (res && res.job_descriptions && res.job_descriptions.length > 0) {
      return res.job_descriptions[0];
    }
    return null;
  } catch (err) {
    if (err.status === 404) return null;
    throw err;
  }
}

/**
 * Retrieve specific JD by its ID from in-memory cache.
 * @param {string} jdId
 */
export async function getJdById(jdId) {
  return apiFetch(`/results/job-descriptions/${encodeURIComponent(jdId)}`);
}
