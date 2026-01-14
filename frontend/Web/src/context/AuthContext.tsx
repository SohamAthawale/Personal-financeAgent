import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from 'react';

/* =========================
   Storage key
   ========================= */
const AUTH_KEY = 'auth';

/* =========================
   Types
   ========================= */
type User = {
  id: number;
  email: string;
};

type AuthState = {
  token: string;
  user: User;
};

interface AuthContextType {
  auth: AuthState | null;
  setAuth: (auth: AuthState | null) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

/* =========================
   Context
   ========================= */
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/* =========================
   Provider
   ========================= */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuthState] = useState<AuthState | null>(() => {
    const stored = localStorage.getItem(AUTH_KEY);
    return stored ? JSON.parse(stored) : null;
  });

  const setAuth = useCallback((newAuth: AuthState | null) => {
    setAuthState(newAuth);

    if (newAuth) {
      localStorage.setItem(AUTH_KEY, JSON.stringify(newAuth));
    } else {
      localStorage.removeItem(AUTH_KEY);
    }
  }, []);

  const logout = useCallback(() => {
    setAuth(null);
  }, [setAuth]);

  // 🔁 Sync login/logout across tabs
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === AUTH_KEY) {
        setAuthState(e.newValue ? JSON.parse(e.newValue) : null);
      }
    };

    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        auth,
        setAuth,
        logout,
        isAuthenticated: Boolean(auth),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* =========================
   Hook
   ========================= */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
