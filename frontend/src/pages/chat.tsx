import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { useAuthSafe } from '@/hooks/useAuthSafe';
import { chatAPI } from '@/services/api';
import { Send, Loader, MessageCircle, AlertCircle } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isLoggedIn } = useAuthSafe();
  const router = useRouter();

  // Redirect if not logged in
  useEffect(() => {
    if (!isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, router]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize session
  useEffect(() => {
    if (isLoggedIn) {
      // Generate a simple session ID if not exists
      const id = `session_${Date.now()}`;
      setSessionId(id);

      // Add welcome message
      setMessages([
        {
          role: 'assistant',
          content:
            'Hello! I am the Citizens Advice AI Assistant. I can help you find information from the knowledge base. How can I assist you today?',
        },
      ]);
    }
  }, [isLoggedIn]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !sessionId) return;

    // Add user message
    const userMessage = inputValue.trim();
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setInputValue('');
    setError('');

    try {
      setLoading(true);

      const response = await chatAPI.sendMessage(sessionId, userMessage, 'standard');

      // Add assistant response
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.message?.content || 'No response received',
        },
      ]);
    } catch (err: any) {
      const message =
        err.response?.data?.detail || 'Failed to send message. Please try again.';
      setError(message);
      console.error('Error sending message:', err);

      // Add error message to chat
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isLoggedIn) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto h-screen flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6 rounded-lg mb-4">
          <div className="flex items-center gap-3">
            <MessageCircle size={28} />
            <div>
              <h1 className="text-3xl font-bold">Citizens Advice AI Chat</h1>
              <p className="text-blue-100">Get instant answers powered by AI</p>
            </div>
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto bg-white rounded-lg shadow-md p-6 mb-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <MessageCircle className="text-blue-300 mb-4" size={64} />
              <p className="text-gray-600 text-lg">No messages yet</p>
              <p className="text-gray-500">Start a conversation below</p>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xl px-4 py-3 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-gray-100 text-gray-900 rounded-bl-none'
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex gap-3">
            <AlertCircle className="text-red-600 flex-shrink-0" size={20} />
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleSendMessage} className="space-y-3">
          <div className="flex gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={loading}
              placeholder="Type your question here..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || loading}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader size={20} className="animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send size={20} />
                  Send
                </>
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 text-center">
            Responses are generated from the documents in your knowledge base
          </p>
        </form>
      </div>
    </Layout>
  );
}
