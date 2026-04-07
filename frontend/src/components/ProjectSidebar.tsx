import { useState, useRef, useEffect } from 'react';
import { Plus, FolderOpen, Trash2, Pencil, LogOut, Sun, Moon, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useDarkMode } from '@/hooks/useDarkMode';

export interface Project {
  id: string;
  name: string;
}

interface Props {
  projects: Project[];
  activeProjectId: string | null;
  onSelectProject: (id: string) => void;
  onNewProject: (name: string) => void;
  onDeleteProject: (id: string) => void;
  onRenameProject: (id: string, name: string) => void;
}

export default function ProjectSidebar({
  projects,
  activeProjectId,
  onSelectProject,
  onNewProject,
  onDeleteProject,
  onRenameProject,
}: Props) {
  const { username, logout } = useAuth();
  const { dark, toggle } = useDarkMode();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [search, setSearch] = useState('');
  const [creatingName, setCreatingName] = useState('');
  const [showNewForm, setShowNewForm] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const newInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (showNewForm) newInputRef.current?.focus();
  }, [showNewForm]);

  useEffect(() => {
    if (editingId) inputRef.current?.focus();
  }, [editingId]);

  const startEdit = (id: string, name: string) => {
    setEditingId(id);
    setEditValue(name);
  };

  const commitEdit = () => {
    if (editingId && editValue.trim()) {
      onRenameProject(editingId, editValue.trim());
    }
    setEditingId(null);
  };

  return (
    <div className="w-64 bg-gray-200 dark:bg-gray-900 flex flex-col h-screen shrink-0 border-r border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="px-4 pt-5 pb-2 space-y-3">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Cases</p>

        {/* Search */}
        <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 focus-within:border-gray-400 dark:focus-within:border-gray-500 transition">
          <Search size={13} className="text-gray-400 dark:text-gray-500 shrink-0" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cases..."
            className="flex-1 bg-transparent text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 outline-none"
          />
        </div>

        {showNewForm ? (
          <div className="space-y-1.5">
            <input
              ref={newInputRef}
              type="text"
              value={creatingName}
              onChange={(e) => setCreatingName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && creatingName.trim()) {
                  onNewProject(creatingName.trim());
                  setCreatingName('');
                  setShowNewForm(false);
                }
                if (e.key === 'Escape') {
                  setCreatingName('');
                  setShowNewForm(false);
                }
              }}
              placeholder="Case name..."
              className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 text-sm rounded-lg px-3 py-2 outline-none focus:border-blue-500"
            />
            <div className="flex gap-1.5">
              <button
                onClick={() => {
                  if (creatingName.trim()) {
                    onNewProject(creatingName.trim());
                    setCreatingName('');
                    setShowNewForm(false);
                  }
                }}
                className="flex-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-1.5 transition"
              >
                Create
              </button>
              <button
                onClick={() => { setCreatingName(''); setShowNewForm(false); }}
                className="flex-1 text-xs bg-gray-300 dark:bg-gray-700 hover:bg-gray-400 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg py-1.5 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowNewForm(true)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-700 transition text-sm font-medium"
          >
            <Plus size={15} />
            New Case
          </button>
        )}
      </div>

      {/* Project list */}
      <div className="flex-1 overflow-y-auto px-3 mt-2 space-y-0.5">
        {projects.length === 0 ? (
          <p className="text-gray-400 dark:text-gray-500 text-xs text-center mt-8 px-4">
            No cases yet. Create one to get started.
          </p>
        ) : (
          projects
          .filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
          .map((project) => (
            <div
              key={project.id}
              onClick={() => { if (editingId !== project.id) onSelectProject(project.id); }}
              className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition text-sm ${
                activeProjectId === project.id
                  ? 'bg-gray-300 dark:bg-gray-700 text-gray-900 dark:text-white'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <FolderOpen size={14} className="shrink-0 text-gray-400" />

              {editingId === project.id ? (
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
                  className="flex-1 bg-gray-200 dark:bg-gray-600 text-gray-900 dark:text-white text-sm rounded px-1.5 py-0.5 outline-none focus:ring-1 focus:ring-blue-500 min-w-0"
                />
              ) : (
                <span className="flex-1 truncate">{project.name}</span>
              )}

              {confirmDeleteId === project.id ? (
                <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <span className="text-xs text-gray-400">Delete?</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteProject(project.id); setConfirmDeleteId(null); }}
                    className="text-xs text-red-500 hover:text-red-400 font-medium transition"
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
                    onClick={(e) => { e.stopPropagation(); startEdit(project.id, project.name); }}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-500 transition shrink-0"
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(project.id); }}
                    className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition shrink-0"
                  >
                    <Trash2 size={13} />
                  </button>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* User footer */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-300">
          <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
            {username?.charAt(0).toUpperCase() ?? 'U'}
          </div>
          <span className="flex-1 truncate text-sm">{username ?? 'User'}</span>
          <button onClick={toggle} className="text-gray-400 hover:text-gray-700 dark:hover:text-white transition" title="Toggle dark mode">
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          <button onClick={logout} className="text-gray-400 hover:text-gray-700 dark:hover:text-white transition" title="Log out">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
