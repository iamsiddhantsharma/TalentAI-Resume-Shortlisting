/**
 * TalentAI — Dedicated Synthetic Demo API Client
 * 
 * Interacts exclusively with /demo/* backend sandbox endpoints.
 * Never calls live active-batch, MongoDB, or resume ingestion endpoints.
 */

import { apiFetch } from './client';

/**
 * Fetch list of all 12 broad synthetic presets across 6 technical strata.
 * @returns {Promise<{ total_presets: number, presets: Array, is_synthetic_demo: boolean }>}
 */
export async function fetchDemoPresets() {
  return await apiFetch('/demo/presets');
}

/**
 * Fetch structured data for a single synthetic preset.
 * @param {string} jdId - e.g. "JD-BROAD-01"
 * @returns {Promise<Object>}
 */
export async function fetchDemoPreset(jdId) {
  if (!jdId) {
    throw new Error('Synthetic preset ID is required.');
  }
  return await apiFetch(`/demo/presets/${encodeURIComponent(jdId)}`);
}

/**
 * Fetch and score the 20 synthetic candidates for a preset under the given scoring mode.
 * Evaluates both Legacy and Evidence-Based engines in-memory, returning dual breakdowns and score deltas.
 * 
 * @param {string} jdId - e.g. "JD-BROAD-01"
 * @param {"legacy" | "evidence"} scoringMode - Scoring engine mode
 * @returns {Promise<Object>}
 */
export async function fetchDemoCohort(jdId, scoringMode = 'legacy') {
  if (!jdId) {
    throw new Error('Synthetic preset ID is required.');
  }
  const mode = scoringMode === 'evidence' ? 'evidence' : 'legacy';
  return await apiFetch(`/demo/cohort/${encodeURIComponent(jdId)}?scoring_mode=${mode}`);
}

/**
 * POST variant for ranking the synthetic cohort with custom parameters.
 * @param {string} jdId
 * @param {{ scoring_mode?: "legacy" | "evidence" }} options
 * @returns {Promise<Object>}
 */
export async function rankDemoCohort(jdId, options = {}) {
  if (!jdId) {
    throw new Error('Synthetic preset ID is required.');
  }
  const mode = options.scoring_mode === 'evidence' ? 'evidence' : 'legacy';
  return await apiFetch(`/demo/cohort/${encodeURIComponent(jdId)}/rank`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scoring_mode: mode }),
  });
}
