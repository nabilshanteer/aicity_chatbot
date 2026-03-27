import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { LogOut } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { username, isLoggedIn, logout } = useAuth();

  if (!isLoggedIn) return null;

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/dashboard" className="font-bold text-xl hover:opacity-80">
            Citizens Advice Chatbot
          </Link>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center font-bold">
                {username?.charAt(0).toUpperCase() ?? 'U'}
              </div>
              <span className="text-sm font-medium">{username}</span>
            </div>

            <button
              onClick={logout}
              className="flex items-center gap-2 bg-blue-500 hover:bg-blue-700 px-4 py-2 rounded-md text-sm font-medium transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};
