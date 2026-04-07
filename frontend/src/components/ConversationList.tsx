import { useState, useRef, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Pencil } from 'lucide-react';

export interface Conversation {
  id: string;
  title: string;
  caseId?: string; // Backend case ID for RAG queries
}

interface Props {
  projectName: string;
  conversations: Conversation[];
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
}

export default function ConversationList({
  projectName,
  conversations,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId) inputRef.current?.focus();
  }, [editingId]);

  const startEdit = (id: string, title: string) => {
    setEditingId(id);
    setEditValue(title);
  };

  const commitEdit = () => {
    if (editingId && editValue.trim()) {
      onRenameConversation(editingId, editValue.trim());
    }
    setEditingId(null);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="shrink-0 px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">{projectName}</h2>
          <p className="text-xs text-gray-400 mt-0.5">Select a conversation or start a new one</p>
        </div>
        <button
          onClick={onNewConversation}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition"
        >
          <Plus size={15} />
          New Conversation
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageSquare size={40} className="text-gray-200 mb-3" />
            <p className="text-gray-500 font-medium">No conversations yet</p>
            <p className="text-gray-400 text-sm mt-1">Start a new conversation for this case.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => { if (editingId !== conv.id) onSelectConversation(conv.id); }}
                className="group flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-sm cursor-pointer transition"
              >
                <MessageSquare size={16} className="text-gray-400 shrink-0" />

                {editingId === conv.id ? (
                  <input
                    ref={inputRef}
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={commitEdit}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitEdit();
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="flex-1 bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100 text-sm rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-blue-500 min-w-0"
                  />
                ) : (
                  <span className="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate">{conv.title}</span>
                )}

                {confirmDeleteId === conv.id ? (
                  <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <span className="text-xs text-gray-400">Delete?</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDeleteConversation(conv.id); setConfirmDeleteId(null); }}
                      className="text-xs text-red-400 hover:text-red-500 font-medium transition"
                    >
                      Yes
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={(e) => { e.stopPropagation(); startEdit(conv.id, conv.title); }}
                      className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-blue-400 transition shrink-0"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(conv.id); }}
                      className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition shrink-0"
                    >
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
