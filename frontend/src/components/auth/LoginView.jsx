import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext.jsx';

export default function LoginView({
  onNavigateToSignup,
  initialEmail = '',
  initialSuccessMessage = null,
}) {
  const { login } = useApp();
  const [username, setUsername] = useState(initialEmail || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(initialSuccessMessage);

  useEffect(() => {
    if (initialEmail) {
      setUsername(initialEmail);
    }
  }, [initialEmail]);

  useEffect(() => {
    if (initialSuccessMessage) {
      setSuccessMessage(initialSuccessMessage);
    }
  }, [initialSuccessMessage]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage('Please enter both username/email and password.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await login(username.trim(), password);
    } catch (err) {
      if (err.status === 429) {
        setErrorMessage(
          err.message || 'Too many failed login attempts. Please wait before trying again.'
        );
      } else if (err.status === 401) {
        setErrorMessage('Invalid username or password. Please verify your HR credentials.');
      } else {
        setErrorMessage(err.message || 'Unable to connect to authentication service.');
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
          maxWidth: '420px',
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
            Sign in with your authorized HR team account
          </p>
        </div>

        {successMessage && (
          <div
            className="alert alert-success"
            role="alert"
            data-testid="login-success"
            style={{
              fontSize: '0.82rem',
              padding: '0.65rem 0.85rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              backgroundColor: 'rgba(34, 197, 94, 0.15)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              color: '#4ade80',
              borderRadius: 'var(--radius-md, 0.5rem)',
            }}
          >
            <svg style={{ width: '16px', height: '16px', flexShrink: 0 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            <span>{successMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div
            className="alert alert-danger"
            role="alert"
            data-testid="login-error"
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
          <div style={{ marginBottom: '1.1rem' }}>
            <label
              htmlFor="login-username"
              style={{
                display: 'block',
                fontSize: '0.82rem',
                fontWeight: 600,
                color: 'var(--text-secondary, #94a3b8)',
                marginBottom: '0.4rem',
              }}
            >
              HR Username or Email
            </label>
            <input
              id="login-username"
              type="text"
              autoComplete="username"
              className="form-control"
              placeholder="e.g. hr_team or name@company.com"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              data-testid="login-username"
              style={{ width: '100%', fontSize: '0.9rem' }}
              required
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label
                htmlFor="login-password"
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
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              className="form-control"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              data-testid="login-password"
              style={{ width: '100%', fontSize: '0.9rem' }}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            data-testid="login-submit"
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
                Authenticating...
              </>
            ) : (
              'Sign In to HR Suite'
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
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onNavigateToSignup}
            data-testid="navigate-to-signup"
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
            Sign up / Create account
          </button>
        </div>

        <div
          style={{
            marginTop: '1.75rem',
            paddingTop: '1rem',
            borderTop: '1px solid var(--border-color, #1e293b)',
            textAlign: 'center',
            fontSize: '0.72rem',
            color: 'var(--text-muted, #64748b)',
            lineHeight: 1.45,
          }}
        >
          🔒 Restricted strictly to authorized TalentAI HR personnel. Candidate resumes, PII, and AI evaluations are protected by single-role enterprise security.
        </div>
      </div>
    </div>
  );
}
