import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useSession } from 'next-auth/react';
import { useAuth } from '@/context/AuthContext';
import { Loader } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'authenticated') {
      router.push('/chat');
    }
  }, [status, router]);

  if (status === 'loading' || status === 'authenticated') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="animate-spin text-blue-600" size={32} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md text-center">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Citizens Advice</h1>
          <p className="text-gray-600">AI-Powered Advisory Assistant</p>
        </div>

        <div className="mb-8 p-4 bg-blue-50 rounded-lg text-sm text-gray-700">
          Sign in with your Google account to access the assistant.
        </div>

        <button
          onClick={login}
          className="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-300 hover:border-blue-500 text-gray-700 font-semibold py-3 px-6 rounded-lg transition shadow-sm hover:shadow"
        >
          {/* Google logo SVG */}
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.86l6.08-6.08C34.46 3.04 29.5 1 24 1 14.82 1 7.07 6.48 3.64 14.24l7.08 5.5C12.4 13.67 17.73 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.14 24.5c0-1.64-.15-3.22-.42-4.74H24v8.98h12.44c-.54 2.9-2.17 5.36-4.63 7.02l7.08 5.5C43.14 37.3 46.14 31.38 46.14 24.5z"/>
            <path fill="#FBBC05" d="M10.72 28.26A14.57 14.57 0 0 1 9.5 24c0-1.48.26-2.91.72-4.26l-7.08-5.5A23.94 23.94 0 0 0 0 24c0 3.86.92 7.5 2.56 10.74l8.16-6.48z"/>
            <path fill="#34A853" d="M24 47c5.5 0 10.12-1.82 13.5-4.96l-7.08-5.5c-1.82 1.22-4.15 1.96-6.42 1.96-6.27 0-11.6-4.17-13.28-9.74l-8.16 6.48C7.07 41.52 14.82 47 24 47z"/>
          </svg>
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
