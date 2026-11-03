import { apiFetch } from './client.js';

/**
 * Upload one or multiple resumes / ZIP archive.
 * @param {File[]} files
 * @param {boolean} autoActivate
 * @returns {Promise<UploadResponse>}
 */
export async function uploadResumes(files, autoActivate = false) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const query = autoActivate ? '?auto_activate=true' : '?auto_activate=false';
  return apiFetch(`/upload/resumes${query}`, {
    method: 'POST',
    body: formData,
    timeout: 120000, // 2 minutes for large uploads
  });
}

/**
 * Poll parsing progress for an upload job.
 * @param {string} uploadId
 * @returns {Promise<any>}
 */
export async function getUploadStatus(uploadId) {
  return apiFetch(`/status/upload/${encodeURIComponent(uploadId)}`);
}

/**
 * Retrieve queue size and system status.
 */
export async function getQueueStatus() {
  return apiFetch('/status/queue');
}
