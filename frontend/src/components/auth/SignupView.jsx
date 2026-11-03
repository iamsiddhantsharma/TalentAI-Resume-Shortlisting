import React, { useState } from 'react';
import { authApi } from '../../api/authApi.js';

export default function SignupView({ onNavigateToLogin, onSignupSuccess }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage(null);

    const nameTrimmed = name.trim();
    const emailTrimmed = email.trim();

    if (!nameTrimmed) {
      setErrorMessage('Please enter your full name.');
      return;
    }

    if (!emailTrimmed) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    if (!emailPattern.test(emailTrimmed)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please verify your password confirmation.');
      return;
    }

    setLoading(true);

    try {
      const res = await authApi.signup({
        name: nameTrimmed,
        email: emailTrimmed,
        password,
        confirmPassword,
      });

      if (onSignupSuccess) {
        onSignupSuccess({
          email: emailTrimmed,
          message: res?.message || 'Account created successfully! You can now sign in with your credentials.',
        });
      } else if (onNavigateToLogin) {
        onNavigateToLogin();
      }
    } catch (err) {
      if (err.status === 409) {
        setErrorMessage(
          err.message || 'An account with this email address already exists. Please sign in instead.'
        );
      } else if (err.status === 403) {
        setErrorMessage(
          err.message || 'Public account registration is disabled. Please contact your administrator.'
        );
      } else {
        setErrorMessage(err.message || 'Failed to create HR account. Please check your inputs and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--bg-primary, #090d16)',
        backgroundImage: 'radial-gradient(circle at 50% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 60%)',
        padding: '1.5rem',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '2.25rem',
          backgroundColor: 'var(--bg-secondary, #0f172a)',
          border: '1px solid var(--border-color, #1e293b)',
          borderRadius: 'var(--radius-xl, 1rem)',
          boxShadow: '0 20px 40px -15px rgba(0, 0, 0, 0.6)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              backgroundColor: 'var(--primary-600, #4f46e5)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
              fontWeight: 800,
              margin: '0 auto 1rem',
              boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
            }}
          >
            T
          </div>
          <h1
            style={{
              fontSize: '1.4rem',
              fontWeight: 700,
              color: 'var(--text-primary, #f8fafc)',
              margin: '0 0 0.35rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            TalentAI
            <span
              style={{
                fontSize: '0.65rem',
                padding: '0.15rem 0.45rem',
                borderRadius: '6px',
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                color: 'var(--primary-400, #818cf8)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                fontWeight: 600,
              }}
            >
              HR Suite
            </span>
          </h1>
          <p
            style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary, #94a3b8)',
              margin: 0,
            }}
          >
            Create an HR account to access the recruitment workspace
          </p>
        </div>

        {errorMessage && (
          <div
            className="alert alert-danger"
            role="alert"
            data-testid="signup-error"
            style={{
              fontSize: '0.82rem',
              padding: '0.65rem 0.85rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <svg style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label
              htmlFor="signup-name"
              style={{
                display: 'block',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: 'var(--text-secondary, #94a3b8)',
                marginBottom: '0.35rem',
              }}
            >
              Full Name
            </label>
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              className="form-control"
              placeholder="e.g. Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              data-testid="signup-name"
              style={{ width: '100%', fontSize: '0.9rem' }}
              required
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label
              htmlFor="signup-email"
              style={{
                display: 'block',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: 'var(--text-secondary, #94a3b8)',
                marginBottom: '0.35rem',
              }}
            >
              Work Email
            </label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              className="form-control"
              placeholder="e.g. jane@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              data-testid="signup-email"
              style={{ width: '100%', fontSize: '0.9rem' }}
              required
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
              <label
                htmlFor="signup-password"
                style={{
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary, #94a3b8)',
                  margin: 0,
                }}
              >
                Password
              </label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted, #64748b)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              id="signup-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              className="form-control"
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              data-testid="signup-password"
              style={{ width: '100%', fontSize: '0.9rem' }}
              minLength={8}
              required
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label
              htmlFor="signup-confirm-password"
              style={{
                display: 'block',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: 'var(--text-secondary, #94a3b8)',
                marginBottom: '0.35rem',
              }}
            >
              Confirm Password
            </label>
            <input
              id="signup-confirm-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              className="form-control"
              placeholder="Re-enter password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={loading}
              data-testid="signup-confirm-password"
              style={{ width: '100%', fontSize: '0.9rem' }}
              minLength={8}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            data-testid="signup-submit"
            style={{
              width: '100%',
              padding: '0.65rem 1rem',
              fontSize: '0.9rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            {loading ? (
              <>
                <svg className="spinner" style={{ width: '16px', height: '16px' }} fill="none" viewBox="0 0 24 24">
                  <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Creating Account...
              </>
            ) : (
              'Create HR Account'
            )}
          </button>
        </form>

        <div
          style={{
            marginTop: '1.25rem',
            textAlign: 'center',
            fontSize: '0.82rem',
            color: 'var(--text-secondary, #94a3b8)',
          }}
        >
          Already have an HR account?{' '}
          <button
            type="button"
            onClick={onNavigateToLogin}
            data-testid="navigate-to-login"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--primary-400, #818cf8)',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'underline',
              padding: 0,
              fontSize: 'inherit',
            }}
          >
            Sign in
          </button>
        </div>

        <div
          style={{
            marginTop: '1.5rem',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-color, #1e293b)',
            textAlign: 'center',
            fontSize: '0.72rem',
            color: 'var(--text-muted, #64748b)',
            lineHeight: 1.45,
          }}
        >
          🔒 Restricted to verified HR team members. All accounts receive access to candidate shortlisting and recruitment intelligence tools.
        </div>
      </div>
    </div>
  );
}
