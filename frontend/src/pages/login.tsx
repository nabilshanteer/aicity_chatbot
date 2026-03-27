import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useSession, signIn } from 'next-auth/react';
import { useAuth } from '@/context/AuthContext';
import { Loader } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const { status } = useSession();
  const router = useRouter();

  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (status === 'authenticated') {
      router.push('/chat');
    }
  }, [status, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleCredentialsLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await signIn('credentials', {
      redirect: false,
      email: form.email,
      password: form.password,
    });

    setLoading(false);
    if (result?.error) {
      setError('Invalid email or password.');
    }
  };

  if (status === 'loading' || status === 'authenticated') {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="animate-spin text-blue-600" size={32} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Citizens Advice</h1>
          <p className="text-gray-600">AI-Powered Advisory Assistant</p>
        </div>

        {router.query.registered && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm text-center">
            Account created! Please check your email to confirm, then sign in.
          </div>
        )}

        {router.query.confirmed && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm text-center">
            Email confirmed! You can now sign in.
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Email / password form */}
        <form onSubmit={handleCredentialsLogin} className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="Your password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? <><Loader size={18} className="animate-spin" /> Signing in...</> : 'Sign In'}
          </button>
        </form>

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-white text-gray-500">or</span>
          </div>
        </div>

        {/* Google sign in */}
        <button
          onClick={login}
          className="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-300 hover:border-blue-500 text-gray-700 font-semibold py-3 px-6 rounded-lg transition shadow-sm hover:shadow"
        >
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.86l6.08-6.08C34.46 3.04 29.5 1 24 1 14.82 1 7.07 6.48 3.64 14.24l7.08 5.5C12.4 13.67 17.73 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.14 24.5c0-1.64-.15-3.22-.42-4.74H24v8.98h12.44c-.54 2.9-2.17 5.36-4.63 7.02l7.08 5.5C43.14 37.3 46.14 31.38 46.14 24.5z"/>
            <path fill="#FBBC05" d="M10.72 28.26A14.57 14.57 0 0 1 9.5 24c0-1.48.26-2.91.72-4.26l-7.08-5.5A23.94 23.94 0 0 0 0 24c0 3.86.92 7.5 2.56 10.74l8.16-6.48z"/>
            <path fill="#34A853" d="M24 47c5.5 0 10.12-1.82 13.5-4.96l-7.08-5.5c-1.82 1.22-4.15 1.96-6.42 1.96-6.27 0-11.6-4.17-13.28-9.74l-8.16 6.48C7.07 41.52 14.82 47 24 47z"/>
          </svg>
          Sign in with Google
        </button>

        <p className="mt-6 text-center text-sm text-gray-600">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="text-blue-600 hover:underline font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
