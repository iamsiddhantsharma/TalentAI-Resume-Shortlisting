import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext.jsx';
import Navbar from './components/layout/Navbar.jsx';
import Header from './components/layout/Header.jsx';
import OverviewView from './components/overview/OverviewView.jsx';
import UploadWorkflowView from './components/upload/UploadWorkflowView.jsx';
import RankingDashboardView from './components/ranking/RankingDashboardView.jsx';
import IncompleteCandidatesPanel from './components/ranking/IncompleteCandidatesPanel.jsx';

import LoginView from './components/auth/LoginView.jsx';
import SignupView from './components/auth/SignupView.jsx';

function MainContent() {
  const { activeTab, isInitializing } = useApp();

  if (isInitializing) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '1rem' }}>
        <svg className="spinner" style={{ width: '36px', height: '36px', color: 'var(--primary-500)' }} fill="none" viewBox="0 0 24 24">
          <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Loading active recruitment workspace...
        </div>
      </div>
    );
  }

  switch (activeTab) {
    case 'upload':
      return <UploadWorkflowView />;
    case 'ranking':
      return <RankingDashboardView />;
    case 'incomplete':
      return <IncompleteCandidatesPanel />;
    case 'overview':
    default:
      return <OverviewView />;
  }
}

function AppLayout() {
  const { isCheckingAuth, isAuthenticated, authNotice } = useApp();
  const [authView, setAuthView] = useState('login'); // 'login' | 'signup'
  const [signupSuccessInfo, setSignupSuccessInfo] = useState(null); // { email, message }

  const handleNavigateToSignup = () => {
    setSignupSuccessInfo(null);
    setAuthView('signup');
  };

  const handleNavigateToLogin = () => {
    setAuthView('login');
  };

  const handleSignupSuccess = ({ email, message }) => {
    setSignupSuccessInfo({ email, message });
    setAuthView('login');
  };

  if (isCheckingAuth) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          gap: '1rem',
          backgroundColor: 'var(--bg-primary, #090d16)',
        }}
      >
        <svg className="spinner" style={{ width: '40px', height: '40px', color: 'var(--primary-500, #6366f1)' }} fill="none" viewBox="0 0 24 24">
          <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <div style={{ color: 'var(--text-secondary, #94a3b8)', fontSize: '0.9rem' }}>
          Verifying TalentAI HR authorization...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        {authNotice && (
          <div style={{ position: 'fixed', top: '1rem', left: '50%', transform: 'translateX(-50%)', zIndex: 9999 }}>
            <div className="alert alert-warning" role="alert" style={{ boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}>
              {authNotice}
            </div>
          </div>
        )}
        {authView === 'signup' ? (
          <SignupView
            onNavigateToLogin={handleNavigateToLogin}
            onSignupSuccess={handleSignupSuccess}
          />
        ) : (
          <LoginView
            onNavigateToSignup={handleNavigateToSignup}
            initialEmail={signupSuccessInfo?.email || ''}
            initialSuccessMessage={signupSuccessInfo?.message || null}
          />
        )}
      </>
    );
  }

  return (
    <div className="app-container">
      <Navbar />
      <div className="main-wrapper">
        <Header />
        <main>
          <MainContent />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppLayout />
    </AppProvider>
  );
}
