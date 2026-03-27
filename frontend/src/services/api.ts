// ---------------------------------------------------------------------------
// Stub API — backend not yet connected.
// Replace these with real implementations when the new backend is ready.
// ---------------------------------------------------------------------------

export const chatAPI = {
  getSessions: async (): Promise<{ sessions: string[] }> => {
    return { sessions: [] };
  },

  sendMessage: async (
    _sessionId: string,
    _message: string,
    _depth: string = 'standard',
  ): Promise<{ message: { content: string } }> => {
    return {
      message: {
        content: 'The backend is not connected yet. Please check back soon.',
      },
    };
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

export const scrapeAPI = {
  getWhitelist: async (): Promise<{ urls: never[] }> => {
    return { urls: [] };
  },

  triggerScrape: async (_urls: string[]): Promise<void> => {
    throw new Error('Backend not connected. Scraping is unavailable.');
  },
};
