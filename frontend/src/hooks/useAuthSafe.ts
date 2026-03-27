import { useAuth } from '@/context/AuthContext';

// Re-export — AuthProvider (inside MsalProvider) in _app.tsx makes it safe to use
export const useAuthSafe = useAuth;
