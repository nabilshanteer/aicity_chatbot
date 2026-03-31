// ---------------------------------------------------------------------------
// RAG-powered Citizens Advice Chatbot API
// Connected to FastAPI backend with Claude + FAISS vector search
// ---------------------------------------------------------------------------

import { getSession } from 'next-auth/react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

async function getAuthHeader() {
  const session = await getSession();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (session?.user?.email) {
    headers['X-User-ID'] = session.user.email as string;
  }
  return headers;
}

export const authAPI = {
  syncUser: async (email: string, name: string | null, googleId: string | null) => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/auth/sync`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ email, name, google_id: googleId }),
    });
    if (!res.ok) throw new Error('Failed to sync user');
    return res.json();
  },
};

export const chatAPI = {
  createCase: async (userId?: string): Promise<{ case_id: string }> => {
    try {
      const headers = await getAuthHeader();
      if (userId) {
        headers['X-User-ID'] = userId;
      }
      const res = await fetch(`${API_BASE}/api/cases/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify({}),
      });
      
      if (!res.ok) {
        throw new Error(`Failed to create case: ${res.statusText}`);
      }
      
      const data = await res.json();
      return { case_id: data.case_id };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to create case: ${errorMessage}`);
    }
  },

  getSessions: async (): Promise<{ sessions: string[] }> => {
    return { sessions: [] };
  },

  generateTitle: async (message: string): Promise<string> => {
    try {
      const headers = await getAuthHeader();
      const res = await fetch(`${API_BASE}/api/chat/title`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      return data.title;
    } catch {
      return message.trim().split(/\s+/).slice(0, 4).join(' ');
    }
  },

  sendMessage: async (
    sessionId: string,
    message: string,
    depth: string = 'standard',
  ): Promise<{ message: { content: string; sources?: string[] } }> => {
    try {
      const headers = await getAuthHeader();
      const res = await fetch(`${API_BASE}/api/cases/${sessionId}/query`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ query: message, depth }),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Backend error: ${res.statusText}`);
      }
      
      const data = await res.json();
      return {
        message: {
          content: data.answer || 'No response from AI',
          sources: data.sources || [],
        },
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to send message: ${errorMessage}`);
    }
  },
};

export const documentsAPI = {
  listDocuments: async (): Promise<{ documents: never[] }> => {
    return { documents: [] };
  },

  uploadDocument: async (_file: File): Promise<void> => {
    throw new Error('Backend not connected. Document upload is unavailable.');
  },

  deleteDocument: async (_documentName: string): Promise<void> => {
    throw new Error('Backend not connected. Document deletion is unavailable.');
  },
};

export const notesAPI = {
  suggest: async (
    fragments: string[],
    context: string,
  ): Promise<{ suggestions: Array<{ fragment: string; suggestion: string | null; full: string }> }> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/notes/suggest`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ fragments, context }),
    });
    if (!res.ok) throw new Error('Failed to get suggestions');
    return res.json();
  },

  summarise: async (transcript: string): Promise<Array<{ point: string; excerpt: string }>> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/notes/summarise`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ transcript }),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.points as Array<{ point: string; excerpt: string }>;
  },

  get: async (chatId: string): Promise<{ notes: string[] }> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/notes/${chatId}`, {
      headers,
    });
    if (!res.ok) throw new Error('Failed to load notes');
    return res.json();
  },

  save: async (chatId: string, notes: string[]): Promise<void> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_BASE}/api/notes/${chatId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ notes }),
    });
    if (!res.ok) throw new Error('Failed to save notes');
  },
};

export const scrapeAPI = {
  getWhitelist: async (): Promise<{ urls: never[] }> => {
    return { urls: [] };
  },

  triggerScrape: async (_urls: string[]): Promise<void> => {
    throw new Error('Backend not connected. Scraping is unavailable.');
  },
};
