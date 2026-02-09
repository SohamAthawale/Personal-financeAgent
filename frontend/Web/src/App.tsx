import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Onboarding } from './pages/Onboarding';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Analytics } from './pages/Analytics';
import { Insights } from './pages/Insights';
import { Goals } from './pages/Goals';
import { Navigation } from './components/Navigation';

function AppContent() {
  const { isAuthenticated } = useAuth();

  const [currentPage, setCurrentPage] = useState<'dashboard' | 'analytics' | 'insights' | 'goals'>('dashboard');
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  // ✅ FIX: Always land on Dashboard after login
  useEffect(() => {
    if (isAuthenticated) {
      setCurrentPage('dashboard');
    }
  }, [isAuthenticated]);

  // 🔐 Auth Gate
  if (!isAuthenticated) {
    return authMode === 'signup' ? (
      <Onboarding onBackToLogin={() => setAuthMode('login')} />
    ) : (
      <Login onSignupClick={() => setAuthMode('signup')} />
    );
  }

  return (
    <div className="app-shell">
      <Navigation
        currentPage={currentPage}
        onPageChange={setCurrentPage}
      />

      <main className="app-main">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'analytics' && <Analytics />}
        {currentPage === 'insights' && <Insights />}
        {currentPage === 'goals' && <Goals />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
