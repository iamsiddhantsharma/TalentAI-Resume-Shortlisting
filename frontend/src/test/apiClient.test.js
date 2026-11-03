import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiFetch, ApiError } from '../api/client.js';

describe('Centralized API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('successfully returns parsed JSON data on 200 OK', async () => {
    const mockData = { status: 'running', queue_size: 0 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => mockData,
    });

    const result = await apiFetch('/status/');
    expect(result).toEqual(mockData);
  });

  it('sanitizes raw Python tracebacks into friendly HR messages without leaking stack traces', async () => {
    const rawTraceback = `Traceback (most recent call last):\n  File "ranking_service.py", line 42, in rank_batch\nValueError: Database connection failed`;
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: rawTraceback }),
    });

    await expect(apiFetch('/ranking/rank-batch-async')).rejects.toThrow(
      'An internal processing error occurred. Please retry or contact support.'
    );
  });

  it('preserves clean user-facing detail messages', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: 'No active recruitment batch found.' }),
    });

    await expect(apiFetch('/ranking/rank-batch-async')).rejects.toThrow(
      'No active recruitment batch found.'
    );
  });

  it('normalizes HTTP 404 into friendly HR message if no detail provided', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: () => 'application/json' },
      json: async () => ({}),
    });

    await expect(apiFetch('/batches/active')).rejects.toThrow(
      'The requested resource was not found.'
    );
  });
});
