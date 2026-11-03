/**
 * TalentAI Centralized API Fetch Client
 * Handles base URLs, JSON parsing, and sanitized error normalization for HR users.
 */

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

/**
 * Cleanly sanitize backend error messages to prevent exposing internal stack traces.
 */
function sanitizeErrorMessage(status, rawDetail) {
  if (typeof rawDetail === 'string' && rawDetail.trim()) {
    // If it contains raw Python traceback syntax, replace with safe user message
    if (rawDetail.includes('Traceback (most recent call last)') || rawDetail.includes('File "')) {
      return 'An internal processing error occurred. Please retry or contact support.';
    }
    return rawDetail;
  }
  
  switch (status) {
    case 400:
      return 'The request was invalid or missing required criteria.';
    case 404:
      return 'The requested resource was not found.';
    case 422:
      return 'Unable to process data. Please verify the file or input format.';
    case 500:
      return 'The server encountered an error while processing the request.';
    default:
      return `Server returned status ${status}.`;
  }
}

let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

/**
 * Execute an HTTP request with error handling and optional timeout.
 */
export async function apiFetch(url, options = {}) {
  const { timeout = 30000, signal: externalSignal, ...fetchOptions } = options;

  let controller = null;
  let timeoutId = null;

  if (externalSignal) {
    fetchOptions.signal = externalSignal;
  } else if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    try {
      fetchOptions.signal = AbortSignal.timeout(timeout);
    } catch {
      // Fallback if environment throws on AbortSignal.timeout
    }
  } else if (typeof AbortController !== 'undefined') {
    try {
      controller = new AbortController();
      timeoutId = setTimeout(() => controller.abort(), timeout);
      fetchOptions.signal = controller.signal;
    } catch {
      // Fallback without abort signal
    }
  }

  try {
    const response = await fetch(url, {
      credentials: 'include',
      ...fetchOptions,
    });

    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    if (response.status === 401 && typeof unauthorizedHandler === 'function') {
      // Notify auth context of expired or invalid session, except during initial auth check
      if (!url.includes('/auth/login') && !url.includes('/auth/me')) {
        unauthorizedHandler();
      }
    }

    // If 204 No Content
    if (response.status === 204) {
      return null;
    }

    const contentType = response.headers.get('content-type') || '';
    let data = null;

    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }

    if (!response.ok) {
      const detail = data && typeof data === 'object' && data.detail ? data.detail : data;
      const safeMessage = sanitizeErrorMessage(response.status, detail);
      throw new ApiError(safeMessage, response.status, detail);
    }

    return data;
  } catch (err) {
    clearTimeout(timeoutId);

    if (err.name === 'AbortError') {
      throw new ApiError('The request timed out. Please check server connectivity.', 408);
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(err.message || 'Network connection failed.', 0, err);
  }
}
