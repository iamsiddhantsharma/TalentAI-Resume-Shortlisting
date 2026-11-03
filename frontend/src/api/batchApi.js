import { apiFetch } from './client.js';

/**
 * List all recruitment batches.
 * @param {number} limit
 * @param {number} skip
 * @returns {Promise<BatchListResponse>}
 */
export async function listBatches(limit = 50, skip = 0) {
  return apiFetch(`/batches?limit=${limit}&skip=${skip}`);
}

/**
 * Get the currently active recruitment batch.
 * Returns null if no batch is active (HTTP 404).
 * @returns {Promise<any | null>}
 */
export async function getActiveBatch() {
  try {
    return await apiFetch('/batches/active');
  } catch (err) {
    if (err.status === 404) {
      return null;
    }
    throw err;
  }
}

/**
 * Get details for a specific batch.
 * @param {string} batchId
 */
export async function getBatch(batchId) {
  return apiFetch(`/batches/${encodeURIComponent(batchId)}`);
}

/**
 * Set a batch as the active candidate batch.
 * @param {string} batchId
 * @returns {Promise<BatchActivateResponse>}
 */
export async function activateBatch(batchId) {
  return apiFetch(`/batches/${encodeURIComponent(batchId)}/activate`, {
    method: 'POST',
  });
}

/**
 * Discard / delete a recruitment batch.
 * @param {string} batchId
 * @param {boolean} force
 */
export async function discardBatch(batchId, force = false) {
  const query = force ? '?force=true' : '';
  return apiFetch(`/batches/${encodeURIComponent(batchId)}/discard${query}`, {
    method: 'POST',
  });
}
