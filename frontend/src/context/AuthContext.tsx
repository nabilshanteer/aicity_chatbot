import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import { authAPI } from '@/services/api';

interface AuthContextType {
  username: string | null;
  isLoggedIn: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { data: session, status } = useSession();

  const isLoggedIn = status === 'authenticated';
  const username = session?.user?.name ?? session?.user?.email ?? null;

  useEffect(() => {
    if (status === 'authenticated' && session?.user?.email) {
      authAPI.syncUser(
        session.user.email,
        session.user.name ?? null,
        null, // NextAuth doesn't expose the Google sub by default
      ).catch(console.error);
    }
  }, [status, session]);

  const login = () => signIn('google');
  const logout = () => signOut({ callbackUrl: '/login' });

  return (
    <AuthContext.Provider value={{ isLoggedIn, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
