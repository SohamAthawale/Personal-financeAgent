import React, { createContext, useContext, useState, useCallback } from 'react';

interface AuthContextType {
  phone: string | null;
  setPhone: (phone: string | null) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [phone, setPhoneState] = useState<string | null>(() => {
    return localStorage.getItem('userPhone');
  });

  const setPhone = useCallback((newPhone: string | null) => {
    setPhoneState(newPhone);
    if (newPhone) {
      localStorage.setItem('userPhone', newPhone);
    } else {
      localStorage.removeItem('userPhone');
    }
  }, []);

  const logout = useCallback(() => {
    setPhone(null);
  }, [setPhone]);

  const isAuthenticated = !!phone;

  return (
    <AuthContext.Provider value={{ phone, setPhone, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
