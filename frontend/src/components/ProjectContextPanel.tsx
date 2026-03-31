import { useState, useRef, useEffect } from 'react';
import { Plus, Trash2, FileText, Globe, NotebookPen, Check, X, Loader, Download, Lightbulb, LightbulbOff } from 'lucide-react';
import { notesAPI } from '@/services/api';

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

interface Suggestion {
  id: string;
  fragment: string;
  suggestion: string;
  full: string;
}

interface Props {
  documents: CaseDocument[];
  sources: WebSource[];
  onAddDocument: (file: File) => void;
  onDeleteDocument: (id: string) => void;
  onAddSource: (title: string, url: string) => void;
  onDeleteSource: (id: string) => void;
  chatId?: string | null;
  projectName?: string;
  conversationContext?: string;
  initialNotes?: string[];
  onNotesChange?: (notes: string[]) => void;
}

export default function ProjectContextPanel({
  documents,
  sources,
  onAddDocument,
  onDeleteDocument,
  onAddSource,
  onDeleteSource,
  chatId,
  projectName = '',
  conversationContext = '',
  initialNotes = [],
  onNotesChange,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [sourceForm, setSourceForm] = useState({ title: '', url: '' });
  const [showSourceForm, setShowSourceForm] = useState(false);

  // ── Smart Notes state ─────────────────────────────────────────────────────
  const [noteText, setNoteText] = useState(initialNotes.join('\n'));
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestionsEnabled, setSuggestionsEnabled] = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const exportNotes = () => {
    const blob = new Blob([noteText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectName || 'notes'}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Reset when active case changes
  useEffect(() => {
    setNoteText(initialNotes.join('\n'));
    setSuggestions([]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId]);

  // Notify parent of note lines whenever text changes
  useEffect(() => {
    const lines = noteText.split('\n').map((l) => l.trim()).filter(Boolean);
    onNotesChange?.(lines);
  }, [noteText, onNotesChange]);

  // Debounce: 800ms after typing stops, send non-empty lines to Claude
  useEffect(() => {
    if (!suggestionsEnabled) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      const fragments = noteText.split('\n').map((l) => l.trim()).filter(Boolean);
      if (fragments.length === 0) { setSuggestions([]); return; }

      // Only re-suggest if there are lines not already suggested or confirmed
      const alreadySuggested = new Set(suggestions.map((s) => s.fragment));
      const newFragments = fragments.filter((f) => !alreadySuggested.has(f));
      if (newFragments.length === 0) return;

      setSuggesting(true);
      try {
        const context = [
          projectName && `Case: ${projectName}`,
          conversationContext && `Recent conversation: ${conversationContext}`,
        ].filter(Boolean).join('. ');

        const { suggestions: hits } = await notesAPI.suggest(newFragments, context);

        setSuggestions((prev) => [
          ...prev,
          ...hits
            .filter((h) => h.suggestion !== null)
            .map((h) => ({
              id: `${Date.now()}-${Math.random()}`,
              fragment: h.fragment,
              suggestion: h.suggestion!,
              full: h.full,
            })),
        ]);
      } catch {
        // silently fail — notes still work without suggestions
      } finally {
        setSuggesting(false);
      }
    }, 800);

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noteText, suggestionsEnabled]);

  const confirmSuggestion = (s: Suggestion) => {
    // Replace the fragment in the textarea with the full suggested text
    setNoteText((prev) =>
      prev
        .split('\n')
        .map((line) => (line.trim() === s.fragment ? s.full : line))
        .join('\n')
    );
    setSuggestions((prev) => prev.filter((x) => x.id !== s.id));
  };

  const dismissSuggestion = (id: string) => {
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  };

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
    <div className="w-72 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex flex-col h-full shrink-0">

      {/* ── Scrollable top: Documents + Sources ── */}
      <div className="overflow-y-auto p-4 space-y-5" style={{ maxHeight: '45%' }}>

        {/* Case Documents */}
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

        {/* Web Sources */}
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

      {/* ── Smart Notes — fills remaining screen height ── */}
      <div className="flex-1 flex flex-col min-h-0 border-t border-gray-200 dark:border-gray-700">

        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-3 pb-2 shrink-0">
          <div className="flex items-center gap-2">
            <NotebookPen size={15} className="text-gray-500 dark:text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">Smart Notes</h3>
            {suggesting && <Loader size={12} className="animate-spin text-blue-400" />}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={exportNotes}
              disabled={!noteText.trim()}
              className="text-gray-400 hover:text-blue-400 disabled:opacity-30 transition"
              title="Export notes as .txt"
            >
              <Download size={14} />
            </button>
            <button
              onClick={() => { setSuggestionsEnabled((v) => !v); setSuggestions([]); }}
              className={`transition ${suggestionsEnabled ? 'text-blue-400 hover:text-blue-300' : 'text-gray-400 hover:text-gray-300'}`}
              title={suggestionsEnabled ? 'Disable AI suggestions' : 'Enable AI suggestions'}
            >
              {suggestionsEnabled ? <Lightbulb size={14} /> : <LightbulbOff size={14} />}
            </button>
          </div>
        </div>

        {/* Textarea — grows to fill all remaining space */}
        <textarea
          value={noteText}
          onChange={(e) => {
            setNoteText(e.target.value);
            // Clear suggestions for lines that have been edited/removed
            const currentLines = new Set(e.target.value.split('\n').map((l) => l.trim()).filter(Boolean));
            setSuggestions((prev) => prev.filter((s) => currentLines.has(s.fragment)));
          }}
          placeholder={"Jot notes as you go...\n\ne.g.\n2 years\nchild\nno notice"}
          className="flex-1 resize-none w-full px-4 py-2 text-xs text-gray-700 dark:text-gray-200 bg-transparent placeholder-gray-400 dark:placeholder-gray-500 outline-none font-mono leading-relaxed"
        />

        {/* Suggestions strip */}
        {suggestions.length > 0 && (
          <div className="shrink-0 border-t border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950 px-3 py-2 space-y-1.5 max-h-40 overflow-y-auto">
            <p className="text-xs text-blue-400 font-medium mb-1">Grok suggestions</p>
            {suggestions.map((s) => (
              <div key={s.id} className="flex items-center gap-1.5 text-xs flex-wrap">
                <span className="text-gray-600 dark:text-gray-300">{s.fragment}</span>
                <span className="text-blue-500">[{s.suggestion}?</span>
                <button
                  onClick={() => confirmSuggestion(s)}
                  className="text-green-500 hover:text-green-400 transition font-semibold"
                  title="Yes"
                >
                  <Check size={13} />
                </button>
                <button
                  onClick={() => dismissSuggestion(s.id)}
                  className="text-red-400 hover:text-red-300 transition"
                  title="No"
                >
                  <X size={13} />
                </button>
                <span className="text-blue-500">]</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
