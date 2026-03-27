import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/Layout';
import { useAuthSafe } from '@/hooks/useAuthSafe';
import { documentsAPI } from '@/services/api';
import { Upload, Trash2, FileText, AlertCircle, CheckCircle, Loader } from 'lucide-react';

interface Document {
  name: string;
  page_count: number;
  chunk_count: number;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { isLoggedIn, username } = useAuthSafe();
  const router = useRouter();

  // Redirect if not logged in
  useEffect(() => {
    if (!isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, router]);

  // Load documents on mount
  useEffect(() => {
    if (isLoggedIn) {
      loadDocuments();
    }
  }, [isLoggedIn]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await documentsAPI.listDocuments();
      setDocuments(response.documents || []);
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to load documents. Please try again.';
      setError(message);
      console.error('Error loading documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError('');
      setSuccess('');
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a file to upload');
      return;
    }

    try {
      setUploading(true);
      setError('');
      setSuccess('');

      await documentsAPI.uploadDocument(selectedFile);

      setSuccess(`Successfully uploaded "${selectedFile.name}". Processing document...`);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Reload documents after a short delay to let backend process
      setTimeout(loadDocuments, 1000);
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Upload failed. Please try again.';
      setError(message);
      console.error('Error uploading document:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${documentName}"? This cannot be undone.`)) {
      return;
    }

    try {
      setError('');
      setSuccess('');
      await documentsAPI.deleteDocument(documentName);
      setSuccess(`Successfully deleted "${documentName}". Refreshing document list...`);
      
      // Reload documents after a short delay
      setTimeout(() => {
        loadDocuments();
      }, 500);
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Failed to delete document. Please try again.';
      setError(message);
      console.error('Error deleting document:', error);
    }
  };

  if (!isLoggedIn) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Document Management</h1>
          <p className="text-lg text-gray-600">
            Upload and manage documents for the knowledge base. These documents power the AI assistant's responses.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Section */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6 sticky top-8">
              <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <Upload size={24} className="text-blue-600" />
                Add Document
              </h2>

              <form onSubmit={handleUpload} className="space-y-4">
                {/* File Input */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Select File
                  </label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileSelect}
                    disabled={uploading}
                    accept=".pdf,.docx,.txt,.md"
                    className="block w-full text-sm text-gray-500
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-semibold
                      file:bg-blue-50 file:text-blue-700
                      hover:file:bg-blue-100
                      disabled:opacity-50 disabled:cursor-not-allowed
                      cursor-pointer"
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Supported: PDF, DOCX, TXT, MD
                  </p>
                </div>

                {/* Selected File Info */}
                {selectedFile && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm font-medium text-blue-900 truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-blue-700">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                )}

                {/* Upload Button */}
                <button
                  type="submit"
                  disabled={!selectedFile || uploading}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <Loader size={18} className="animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload size={18} />
                      Upload Document
                    </>
                  )}
                </button>
              </form>

              {/* Messages */}
              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex gap-2">
                  <AlertCircle className="text-red-600 flex-shrink-0" size={18} />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {success && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg flex gap-2">
                  <CheckCircle className="text-green-600 flex-shrink-0" size={18} />
                  <p className="text-sm text-green-700">{success}</p>
                </div>
              )}
            </div>
          </div>

          {/* Documents List */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <FileText size={24} className="text-green-600" />
                  Knowledge Base Documents
                </h2>
              </div>

              {loading ? (
                <div className="p-12 flex flex-col items-center justify-center">
                  <Loader className="animate-spin text-blue-600 mb-4" size={32} />
                  <p className="text-gray-600">Loading documents...</p>
                </div>
              ) : documents.length === 0 ? (
                <div className="p-12 text-center">
                  <FileText className="mx-auto text-gray-400 mb-4" size={48} />
                  <p className="text-gray-600 text-lg">No documents uploaded yet</p>
                  <p className="text-gray-500 text-sm mt-2">
                    Upload your first document to get started
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                          Document Name
                        </th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                          Pages
                        </th>
                        <th className="px-6 py-3 text-left text-sm font-semibold text-gray-700">
                          Chunks
                        </th>
                        <th className="px-6 py-3 text-right text-sm font-semibold text-gray-700">
                          Action
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc, idx) => (
                        <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50 transition">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <FileText className="text-blue-500" size={20} />
                              <span className="text-gray-900 font-medium truncate">
                                {doc.name}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-gray-700">{doc.page_count}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="inline-block bg-blue-100 text-blue-800 text-sm font-medium px-3 py-1 rounded-full">
                              {doc.chunk_count}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button
                              onClick={() => handleDelete(doc.name)}
                              className="text-red-600 hover:text-red-900 hover:bg-red-50 p-2 rounded-lg transition inline-flex items-center gap-2"
                              title="Delete document"
                            >
                              <Trash2 size={18} />
                              <span className="text-sm font-medium">Delete</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Summary Card */}
        {documents.length > 0 && (
          <div className="mt-8 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg p-6 border border-blue-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-gray-600">Total Documents</p>
                <p className="text-2xl font-bold text-gray-900">{documents.length}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Pages</p>
                <p className="text-2xl font-bold text-gray-900">
                  {documents.reduce((sum, doc) => sum + doc.page_count, 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Chunks</p>
                <p className="text-2xl font-bold text-gray-900">
                  {documents.reduce((sum, doc) => sum + doc.chunk_count, 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Status</p>
                <p className="text-2xl font-bold text-green-600">Active</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
