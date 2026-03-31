import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { supabase } from '@/lib/supabaseClient';
import { authAPI } from '@/services/api';
import { Loader } from 'lucide-react';

export default function AuthCallback() {
  const router = useRouter();
  const [message, setMessage] = useState('Confirming your account...');

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session?.user) {
        // Sync into our public.users table now, before NextAuth login
        await authAPI.syncUser(
          session.user.email!,
          session.user.user_metadata?.full_name ?? null,
          null,
        ).catch(console.error);

        setMessage('Email confirmed! Redirecting to sign in...');
        setTimeout(() => router.push('/login?confirmed=true'), 1500);
      } else {
        setMessage('Confirmation failed. Please try signing up again.');
        setTimeout(() => router.push('/signup'), 2500);
      }
    });
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-2xl p-8 text-center">
        <Loader className="animate-spin text-blue-600 mx-auto mb-4" size={32} />
        <p className="text-gray-700 font-medium">{message}</p>
      </div>
    </div>
  );
}
