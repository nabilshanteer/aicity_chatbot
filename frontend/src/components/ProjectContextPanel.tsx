import { useState, useRef } from 'react';
import { Plus, Trash2, FileText, Globe } from 'lucide-react';

export type DepthMode = 'quick' | 'balanced' | 'deep';

export interface CaseDocument {
  id: string;
  name: string;
}

export interface WebSource {
  id: string;
  title: string;
  url: string;
}

interface Props {
  documents: CaseDocument[];
  sources: WebSource[];
  onAddDocument: (file: File) => void;
  onDeleteDocument: (id: string) => void;
  onAddSource: (title: string, url: string) => void;
  onDeleteSource: (id: string) => void;
}

const DEPTH_OPTIONS: { value: DepthMode; label: string; description: string }[] = [
  { value: 'quick', label: 'Quick', description: 'Fast lookups' },
  { value: 'balanced', label: 'Balanced', description: 'Standard queries' },
  { value: 'deep', label: 'Deep Dive', description: 'Complex research' },
];

export default function ProjectContextPanel({
  documents,
  sources,
  onAddDocument,
  onDeleteDocument,
  onAddSource,
  onDeleteSource,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [sourceForm, setSourceForm] = useState({ title: '', url: '' });
  const [showSourceForm, setShowSourceForm] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onAddDocument(file);
    e.target.value = '';
  };

  const handleAddSource = () => {
    if (!sourceForm.title.trim() || !sourceForm.url.trim()) return;
    onAddSource(sourceForm.title.trim(), sourceForm.url.trim());
    setSourceForm({ title: '', url: '' });
    setShowSourceForm(false);
  };

  return (
    <div className="w-72 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex flex-col h-full overflow-y-auto shrink-0">
      <div className="p-4 space-y-6">

        {/* ── Field 1: Case Documents ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <FileText size={15} className="text-gray-500 dark:text-gray-400" />
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Case Documents</h3>
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-400 font-medium"
            >
              <Plus size={13} /> Add
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {documents.length === 0 ? (
            <p className="text-xs text-gray-400 italic">No documents added yet.</p>
          ) : (
            <ul className="space-y-1.5">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center gap-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2">
                  <FileText size={13} className="text-blue-500 shrink-0" />
                  <span className="flex-1 text-xs text-gray-700 dark:text-gray-200 truncate">{doc.name}</span>
                  <button onClick={() => onDeleteDocument(doc.id)} className="text-gray-300 hover:text-red-400 transition shrink-0">
                    <Trash2 size={13} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <hr className="border-gray-200 dark:border-gray-700" />

        {/* ── Field 2: Web Sources ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Globe size={15} className="text-gray-500 dark:text-gray-400" />
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Web Sources</h3>
            </div>
            <button
              onClick={() => setShowSourceForm((v) => !v)}
              className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-400 font-medium"
            >
              <Plus size={13} /> Add
            </button>
          </div>

          {showSourceForm && (
            <div className="mb-3 space-y-2">
              <input
                type="text"
                placeholder="Title"
                value={sourceForm.title}
                onChange={(e) => setSourceForm((p) => ({ ...p, title: e.target.value }))}
                className="w-full text-xs px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-400 rounded-lg outline-none focus:border-blue-500"
              />
              <input
                type="url"
                placeholder="https://..."
                value={sourceForm.url}
                onChange={(e) => setSourceForm((p) => ({ ...p, url: e.target.value }))}
                className="w-full text-xs px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-400 rounded-lg outline-none focus:border-blue-500"
              />
              <div className="flex gap-2">
                <button onClick={handleAddSource} className="flex-1 text-xs bg-blue-600 text-white rounded-lg py-1.5 hover:bg-blue-700 transition">Save</button>
                <button onClick={() => setShowSourceForm(false)} className="flex-1 text-xs bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-200 rounded-lg py-1.5 hover:bg-gray-200 dark:hover:bg-gray-500 transition">Cancel</button>
              </div>
            </div>
          )}

          {sources.length === 0 ? (
            <p className="text-xs text-gray-400 italic">No web sources added yet.</p>
          ) : (
            <ul className="space-y-1.5">
              {sources.map((src) => (
                <li key={src.id} className="flex items-start gap-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2">
                  <Globe size={13} className="text-green-500 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-700 dark:text-gray-200 truncate">{src.title}</p>
                    <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:underline truncate block">{src.url}</a>
                  </div>
                  <button onClick={() => onDeleteSource(src.id)} className="text-gray-300 hover:text-red-400 transition shrink-0 mt-0.5">
                    <Trash2 size={13} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

      </div>
    </div>
  );
}
