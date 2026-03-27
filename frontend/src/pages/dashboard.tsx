import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { Layout } from '@/components/Layout';
import { useAuthSafe } from '@/hooks/useAuthSafe';
import { MessageSquare, FileText } from 'lucide-react';

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
          <Link href="/chat">
            <div className="bg-white rounded-lg shadow-lg hover:shadow-xl transition cursor-pointer p-6 group">
              <div className="flex items-center gap-4 mb-4">
                <div className="bg-blue-100 p-3 rounded-lg group-hover:bg-blue-200 transition">
                  <MessageSquare className="text-blue-600" size={28} />
                </div>
                <h2 className="text-2xl font-bold text-gray-800">Chat</h2>
              </div>
              <p className="text-gray-600 mb-6">
                Ask questions about Citizens Advice policies and get instant answers powered by AI.
              </p>
              <div className="inline-block bg-blue-600 group-hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition">
                Start Chat →
              </div>
            </div>
          </Link>

          {/* Documents Section */}
          <Link href="/documents">
            <div className="bg-white rounded-lg shadow-lg hover:shadow-xl transition cursor-pointer p-6 group">
              <div className="flex items-center gap-4 mb-4">
                <div className="bg-green-100 p-3 rounded-lg group-hover:bg-green-200 transition">
                  <FileText className="text-green-600" size={28} />
                </div>
                <h2 className="text-2xl font-bold text-gray-800">Documents</h2>
              </div>
              <p className="text-gray-600 mb-6">
                Upload and manage reference documents for the knowledge base.
              </p>
              <div className="inline-block bg-green-600 group-hover:bg-green-700 text-white font-semibold py-2 px-6 rounded-lg transition">
                Manage Documents →
              </div>
            </div>
          </Link>
        </div>

        {/* Info Card */}
        <div className="mt-12 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-3">Welcome to Citizens Advice AI</h3>
          <p className="text-gray-700 text-lg leading-relaxed">
            This tool provides an AI-powered advisory assistant to help staff quickly find accurate information
            from trusted source documents. Start by uploading documents to the knowledge base, then use the chat
            interface to ask questions and get AI-powered responses.
          </p>
        </div>
      </div>
    </Layout>
  );
}
