import { ReactNode } from 'react';
import { useAuth } from '../context/AuthContext';
import { Login } from '../pages/Login';

interface ProtectedRouteProps {
  children: ReactNode;
  onSignupClick: () => void;
}

export function ProtectedRoute({
  children,
  onSignupClick,
}: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Login onSignupClick={onSignupClick} />;
  }

  return <>{children}</>;
}
