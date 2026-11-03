import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App.jsx';
import LoginView from '../components/auth/LoginView.jsx';
import SignupView from '../components/auth/SignupView.jsx';
import * as AppContextModule from '../context/AppContext.jsx';
import { authApi } from '../api/authApi.js';
import * as jdApi from '../api/jdApi.js';
import * as batchApi from '../api/batchApi.js';

describe('HR Authentication & Route Access Workflow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    vi.spyOn(jdApi, 'getActiveJd').mockResolvedValue(null);
    vi.spyOn(batchApi, 'getActiveBatch').mockResolvedValue(null);
  });

  it('renders LoginView when no active HR session exists and includes Sign up link', async () => {
    vi.spyOn(authApi, 'getCurrentUser').mockRejectedValue(new Error('Unauthorized'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('login-username')).toBeInTheDocument();
      expect(screen.getByTestId('login-password')).toBeInTheDocument();
      expect(screen.getByTestId('login-submit')).toBeInTheDocument();
      expect(screen.getByTestId('navigate-to-signup')).toBeInTheDocument();
    });

    expect(screen.getByText(/Sign in with your authorized HR team account/i)).toBeInTheDocument();
    expect(screen.getByTestId('login-submit')).toHaveTextContent(/HR Suite/i);
    expect(screen.getByTestId('navigate-to-signup')).toHaveTextContent(/Sign up \/ Create account/i);
  });

  it('navigates to SignupView when clicking Sign up link, and returns to LoginView on Sign in click', async () => {
    vi.spyOn(authApi, 'getCurrentUser').mockRejectedValue(new Error('Unauthorized'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('navigate-to-signup')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('navigate-to-signup'));

    // Should now show SignupView
    await waitFor(() => {
      expect(screen.getByTestId('signup-name')).toBeInTheDocument();
      expect(screen.getByTestId('signup-email')).toBeInTheDocument();
      expect(screen.getByTestId('signup-password')).toBeInTheDocument();
      expect(screen.getByTestId('signup-confirm-password')).toBeInTheDocument();
      expect(screen.getByTestId('signup-submit')).toBeInTheDocument();
      expect(screen.getByTestId('navigate-to-login')).toBeInTheDocument();
    });

    // Navigate back to LoginView
    fireEvent.click(screen.getByTestId('navigate-to-login'));

    await waitFor(() => {
      expect(screen.getByTestId('login-username')).toBeInTheDocument();
    });
  });

  it('validates SignupView form inputs when passwords do not match', async () => {
    render(<SignupView onNavigateToLogin={vi.fn()} onSignupSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId('signup-name'), { target: { value: 'Alex Morgan' } });
    fireEvent.change(screen.getByTestId('signup-email'), { target: { value: 'alex@company.com' } });
    fireEvent.change(screen.getByTestId('signup-password'), { target: { value: 'Secret123!' } });
    fireEvent.change(screen.getByTestId('signup-confirm-password'), { target: { value: 'Different123!' } });
    fireEvent.click(screen.getByTestId('signup-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('signup-error')).toBeInTheDocument();
    });

    expect(screen.getByTestId('signup-error')).toHaveTextContent(/Passwords do not match/i);
  });

  it('successful signup calls authApi.signup and redirects to LoginView with success message and prefilled email', async () => {
    vi.spyOn(authApi, 'getCurrentUser').mockRejectedValue(new Error('Unauthorized'));
    const signupSpy = vi.spyOn(authApi, 'signup').mockResolvedValue({
      user: {
        user_id: 'user_alex_789',
        username: 'alex_morgan',
        full_name: 'Alex Morgan',
        email: 'alex@company.com',
        role: 'hr',
      },
      message: 'Account created successfully! You can now sign in with your email and password.',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('navigate-to-signup')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('navigate-to-signup'));

    await waitFor(() => {
      expect(screen.getByTestId('signup-name')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('signup-name'), { target: { value: 'Alex Morgan' } });
    fireEvent.change(screen.getByTestId('signup-email'), { target: { value: 'alex@company.com' } });
    fireEvent.change(screen.getByTestId('signup-password'), { target: { value: 'SecurePass!2026' } });
    fireEvent.change(screen.getByTestId('signup-confirm-password'), { target: { value: 'SecurePass!2026' } });
    fireEvent.click(screen.getByTestId('signup-submit'));

    await waitFor(() => {
      expect(signupSpy).toHaveBeenCalledWith({
        name: 'Alex Morgan',
        email: 'alex@company.com',
        password: 'SecurePass!2026',
        confirmPassword: 'SecurePass!2026',
      });
    });

    // Should redirect to LoginView with success alert and prefilled email
    await waitFor(() => {
      expect(screen.getByTestId('login-username')).toBeInTheDocument();
      expect(screen.getByTestId('login-success')).toBeInTheDocument();
    });

    expect(screen.getByTestId('login-username')).toHaveValue('alex@company.com');
    expect(screen.getByTestId('login-success')).toHaveTextContent(/Account created successfully/i);
  });

  it('successful login updates authentication state and reveals the HR Suite dashboard', async () => {
    // Initial check: unauthenticated
    vi.spyOn(authApi, 'getCurrentUser').mockRejectedValue(new Error('Unauthorized'));
    vi.spyOn(authApi, 'login').mockResolvedValue({
      user: {
        user_id: 'user_alice_123',
        username: 'alice_hr',
        full_name: 'Alice Johnson',
        email: 'alice@company.com',
        role: 'hr',
      },
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('login-username')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('login-username'), { target: { value: 'alice_hr' } });
    fireEvent.change(screen.getByTestId('login-password'), { target: { value: 'SecureHR!2026' } });
    fireEvent.click(screen.getByTestId('login-submit'));

    // Should transition to authenticated dashboard
    await waitFor(() => {
      expect(screen.getByTestId('current-user-chip')).toBeInTheDocument();
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      expect(screen.getByTestId('logout-button')).toBeInTheDocument();
    });

    // Main navigation and Overview are now visible
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Upload & Ingestion')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Ranked Shortlist/i })).toBeInTheDocument();
  });

  it('invalid credentials display clear error feedback and keep user on LoginView', async () => {
    const mockLogin = vi.fn().mockRejectedValue({
      status: 401,
      message: 'Invalid username or password.',
    });

    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      login: mockLogin,
      currentUser: null,
      isAuthenticated: false,
      isCheckingAuth: false,
      authNotice: null,
    });

    render(<LoginView />);

    fireEvent.change(screen.getByTestId('login-username'), { target: { value: 'bad_user' } });
    fireEvent.change(screen.getByTestId('login-password'), { target: { value: 'wrong_password' } });
    fireEvent.click(screen.getByTestId('login-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toBeInTheDocument();
    });

    expect(screen.getByText(/Invalid username or password/i)).toBeInTheDocument();
  });

  it('rate limiting lockout (HTTP 429) displays cooldown guidance', async () => {
    const mockLogin = vi.fn().mockRejectedValue({
      status: 429,
      message: 'Too many failed login attempts. Please try again in 15 minutes.',
    });

    vi.spyOn(AppContextModule, 'useApp').mockReturnValue({
      login: mockLogin,
      currentUser: null,
      isAuthenticated: false,
      isCheckingAuth: false,
      authNotice: null,
    });

    render(<LoginView />);

    fireEvent.change(screen.getByTestId('login-username'), { target: { value: 'locked_hr' } });
    fireEvent.change(screen.getByTestId('login-password'), { target: { value: 'wrong_pwd' } });
    fireEvent.click(screen.getByTestId('login-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent(/Too many failed login attempts/i);
    });
  });

  it('signing out calls authApi.logout and cleanly returns to LoginView', async () => {
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      user_id: 'user_bob_456',
      username: 'bob_hr',
      full_name: 'Bob Smith',
      email: 'bob@company.com',
      role: 'hr',
    });
    const logoutSpy = vi.spyOn(authApi, 'logout').mockResolvedValue({ message: 'Logged out' });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('logout-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('logout-button'));

    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalled();
      expect(screen.getByTestId('login-username')).toBeInTheDocument();
    });
  });
});
