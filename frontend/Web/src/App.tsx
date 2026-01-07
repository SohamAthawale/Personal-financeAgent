import { useState } from 'react';
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
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [showOnboarding, setShowOnboarding] = useState(true);

  if (!isAuthenticated) {
    if (showOnboarding) {
      return (
        <Onboarding />
      );
    } else {
      return <Login onSignupClick={() => setShowOnboarding(true)} />;
    }
  }

  return (
    <>
      <Navigation currentPage={currentPage} onPageChange={setCurrentPage} />
      <main>
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'analytics' && <Analytics />}
        {currentPage === 'insights' && <Insights />}
        {currentPage === 'goals' && <Goals />}
      </main>
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
