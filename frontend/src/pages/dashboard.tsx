import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { useAuthSafe } from '@/hooks/useAuthSafe';

export default function DashboardPage() {
  const { isLoggedIn } = useAuthSafe();
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, router]);

  if (!isLoggedIn) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Chat Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Chat</h2>
            <p className="text-gray-600 mb-4">
              Ask questions about Citizens Advice policies and get instant answers powered by AI.
            </p>
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition">
              Start Chat
            </button>
          </div>

          {/* Documents Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Documents</h2>
            <p className="text-gray-600 mb-4">
              Upload and manage reference documents for the knowledge base.
            </p>
            <button className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-lg transition">
              Manage Documents
            </button>
          </div>
        </div>

        {/* Info Card */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-2">Welcome to Citizens Advice AI</h3>
          <p className="text-gray-700">
            This tool provides an AI-powered advisory assistant to help staff quickly find accurate information
            from trusted source documents. More features coming soon!
          </p>
        </div>
      </div>
    </Layout>
  );
}
