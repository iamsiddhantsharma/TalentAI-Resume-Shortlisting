import { apiFetch } from './client.js';

/**
 * HR Authentication API Client
 */
export const authApi = {
  /**
   * Register a new HR team member account.
   */
  async signup({ name, email, password, confirmPassword }) {
    return apiFetch('/auth/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: name.trim(),
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
      }),
    });
  },

  /**
   * Authenticate HR team member credentials.
   * On success, sets HttpOnly session cookie on the browser.
   */
  async login({ username, password }) {
    return apiFetch('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.trim(),
        password,
      }),
    });
  },

  /**
   * Log out current HR session and clear server session cookie.
   */
  async logout() {
    return apiFetch('/auth/logout', {
      method: 'POST',
    });
  },

  /**
   * Retrieve current authenticated HR user profile.
   * Throws 401 if unauthenticated or session expired.
   */
  async getCurrentUser() {
    return apiFetch('/auth/me', {
      method: 'GET',
    });
  },
};
