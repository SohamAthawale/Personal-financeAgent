import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from 'react';

const AUTH_PHONE_KEY = 'userPhone';

interface AuthContextType {
  phone: string | null;
  setPhone: (phone: string | null) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [phone, setPhoneState] = useState<string | null>(() => {
    return localStorage.getItem(AUTH_PHONE_KEY);
  });

  const setPhone = useCallback((newPhone: string | null) => {
    setPhoneState(newPhone);

    if (newPhone) {
      localStorage.setItem(AUTH_PHONE_KEY, newPhone);
    } else {
      localStorage.removeItem(AUTH_PHONE_KEY);
    }
  }, []);

  const logout = useCallback(() => {
    setPhone(null);
  }, [setPhone]);

  // Optional: sync logout across tabs
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === AUTH_PHONE_KEY) {
        setPhoneState(e.newValue);
      }
    };

    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const isAuthenticated = Boolean(phone);

  return (
    <AuthContext.Provider
      value={{
        phone,
        setPhone,
        logout,
        isAuthenticated,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
