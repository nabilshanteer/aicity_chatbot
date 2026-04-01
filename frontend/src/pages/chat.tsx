import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useSession } from 'next-auth/react';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuthSafe } from '@/hooks/useAuthSafe';
import { chatAPI } from '@/services/api';
import ProjectSidebar, { Project } from '@/components/ProjectSidebar';
import ProjectContextPanel, { CaseDocument, WebSource, DepthMode } from '@/components/ProjectContextPanel';
import ConversationList, { Conversation } from '@/components/ConversationList';
import ChatWindow, { Message } from '@/components/ChatWindow';
import ChatInput from '@/components/ChatInput';
import DepthSlider from '@/components/DepthSlider';

// ── Types ──────────────────────────────────────────────────────────────────
interface ProjectData {
  id: string;
  name: string;
  documents: CaseDocument[];
  sources: WebSource[];
  depth: DepthMode;
  conversations: Conversation[];
  notes: string[];
}

type ProjectStore = Record<string, ProjectData>;

// ── Stub data ──────────────────────────────────────────────────────────────
const STUB_PROJECTS: ProjectStore = {
  'p1': {
    id: 'p1', name: 'Case 1 — Housing Benefit', depth: 'balanced',
    documents: [{ id: 'd1', name: 'Housing Act 1996.pdf' }],
    sources: [{ id: 's1', title: 'GOV.UK Housing Benefit', url: 'https://www.gov.uk/housing-benefit' }],
    conversations: [{ id: 'c1', title: 'Eligibility query', caseId: undefined }],
    notes: [],
  },
  'p2': {
    id: 'p2', name: 'Case 2 — Universal Credit', depth: 'quick',
    documents: [],
    sources: [],
    conversations: [],
    notes: [],
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────
const newId = () => `${Date.now()}`;


// ── Page ───────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const { isLoggedIn } = useAuthSafe();
  const { data: session } = useSession();
  const router = useRouter();

  const [projects, setProjects] = useState<ProjectStore>(STUB_PROJECTS);
  const [projectList, setProjectList] = useState<Project[]>(
    Object.values(STUB_PROJECTS).map(({ id, name }) => ({ id, name })),
  );
  const [activeProjectId, setActiveProjectId] = useState<string | null>('p1');
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messagesByConv, setMessagesByConv] = useState<Record<string, Message[]>>({});
  const [loading, setLoading] = useState(false);
  const [inputVisible, setInputVisible] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);

  useEffect(() => {
    if (!isLoggedIn) router.push('/login');
  }, [isLoggedIn, router]);


  const activeProject = activeProjectId ? projects[activeProjectId] : null;
  const activeMessages: Message[] = messagesByConv[activeConvId ?? ''] ?? [];

  // ── Project actions ──────────────────────────────────────────────────────
  const handleNewProject = (name: string) => {
    const id = newId();
    const newProject: ProjectData = {
      id, name, depth: 'balanced',
      documents: [], sources: [], conversations: [], notes: [],
    };
    setProjects((p) => ({ ...p, [id]: newProject }));
    setProjectList((p) => [{ id, name }, ...p]);
    setActiveProjectId(id);
    setActiveConvId(null);
  };

  const handleDeleteProject = (id: string) => {
    setProjects((p) => { const u = { ...p }; delete u[id]; return u; });
    setProjectList((p) => p.filter((x) => x.id !== id));
    if (activeProjectId === id) { setActiveProjectId(null); setActiveConvId(null); }
  };

  const handleRenameProject = (id: string, name: string) => {
    setProjects((p) => ({ ...p, [id]: { ...p[id], name } }));
    setProjectList((p) => p.map((x) => (x.id === id ? { ...x, name } : x)));
  };

  const updateProject = (id: string, patch: Partial<ProjectData>) =>
    setProjects((p) => ({ ...p, [id]: { ...p[id], ...patch } }));

  // ── Document actions ─────────────────────────────────────────────────────
  const handleAddDocument = (file: File) => {
    if (!activeProjectId) return;
    const doc: CaseDocument = { id: newId(), name: file.name };
    updateProject(activeProjectId, {
      documents: [...(activeProject?.documents ?? []), doc],
    });
  };

  const handleDeleteDocument = (docId: string) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, {
      documents: activeProject?.documents.filter((d) => d.id !== docId) ?? [],
    });
  };

  // ── Notes actions ────────────────────────────────────────────────────────
  const handleNotesChange = (notes: string[]) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, { notes });
  };

  // ── Source actions ───────────────────────────────────────────────────────
  const handleAddSource = (title: string, url: string) => {
    if (!activeProjectId) return;
    const src: WebSource = { id: newId(), title, url };
    updateProject(activeProjectId, {
      sources: [...(activeProject?.sources ?? []), src],
    });
  };

  const handleDeleteSource = (srcId: string) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, {
      sources: activeProject?.sources.filter((s) => s.id !== srcId) ?? [],
    });
  };

  // ── Conversation actions ─────────────────────────────────────────────────
  const handleNewConversation = async () => {
    if (!activeProjectId) return;
    const id = newId();
    
    // Create a case in the backend RAG system
    let caseId = id; // fallback to local ID if backend fails
    try {
      const userId = session?.user?.email ?? undefined;
      const { case_id } = await chatAPI.createCase(userId);
      caseId = case_id;
    } catch (error) {
      console.error('Failed to create backend case:', error);
    }
    
    const conv: Conversation = { id, title: 'New Conversation', caseId };
    updateProject(activeProjectId, {
      conversations: [...(activeProject?.conversations ?? []), conv],
    });
    setActiveConvId(id);
  };

  const handleDeleteConversation = (convId: string) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, {
      conversations: activeProject?.conversations.filter((c) => c.id !== convId) ?? [],
    });
    if (activeConvId === convId) setActiveConvId(null);
  };

  const handleRenameConversation = (convId: string, title: string) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, {
      conversations: activeProject!.conversations.map((c) =>
        c.id === convId ? { ...c, title } : c,
      ),
    });
  };

  // ── Chat actions ─────────────────────────────────────────────────────────
  const handleSend = async (text: string) => {
    if (!activeConvId || !activeProjectId) return;

    const userMsg: Message = { role: 'user', content: text };
    setMessagesByConv((prev) => ({
      ...prev,
      [activeConvId]: [...(prev[activeConvId] ?? []), userMsg],
    }));

    // Auto-title the conversation from first message using Claude
    const conv = activeProject?.conversations.find((c) => c.id === activeConvId);
    if (conv?.title === 'New Conversation') {
      const pid = activeProjectId;
      const cid = activeConvId;
      chatAPI.generateTitle(text).then((title) => {
        updateProject(pid, {
          conversations: projects[pid]?.conversations.map((c) =>
            c.id === cid ? { ...c, title } : c,
          ) ?? [],
        });
      });
    }

    setLoading(true);
    try {
      let caseId = conv?.caseId;
      
      // If no case ID, create one before sending message
      if (!caseId) {
        console.log('Creating backend case for conversation...');
        const userId = session?.user?.email ?? undefined;
        const { case_id } = await chatAPI.createCase(userId);
        caseId = case_id;
        
        // Update conversation with the new case ID
        updateProject(activeProjectId, {
          conversations: activeProject!.conversations.map((c) =>
            c.id === activeConvId ? { ...c, caseId } : c,
          ),
        });
      }
      
      const response = await chatAPI.sendMessage(
        caseId,
        text,
        activeProject?.depth ?? 'balanced',
        activeProject?.notes ?? [],
        activeProject?.sources.map((source) => source.url) ?? [],
        activeProject?.documents.map((document) => document.name) ?? [],
      );
      setMessagesByConv((prev) => ({
        ...prev,
        [activeConvId]: [
          ...(prev[activeConvId] ?? []),
          { role: 'assistant', content: response.message?.content ?? 'No response received.' },
        ],
      }));
    } catch {
      setMessagesByConv((prev) => ({
        ...prev,
        [activeConvId]: [
          ...(prev[activeConvId] ?? []),
          { role: 'assistant', content: 'Something went wrong. Please try again.' },
        ],
      }));
    } finally {
      setLoading(false);
    }
  };

  if (!isLoggedIn) return null;

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 overflow-hidden">

      {/* Col 1 — Projects sidebar */}
      <ProjectSidebar
        projects={projectList}
        activeProjectId={activeProjectId}
        onSelectProject={(id) => { setActiveProjectId(id); setActiveConvId(null); }}
        onNewProject={handleNewProject}
        onDeleteProject={handleDeleteProject}
        onRenameProject={handleRenameProject}
      />

      {!activeProject ? (
        /* No project selected */
        <div className="flex-1 flex items-center justify-center text-center">
          <div>
            <p className="text-gray-400 text-lg font-medium">Select a case to get started</p>
            <p className="text-gray-300 text-sm mt-1">or create a new one from the sidebar</p>
          </div>
        </div>
      ) : (
        <>
          {/* Col 2 — Project context panel (collapsible) */}
          <div className={`transition-[width] duration-300 overflow-hidden shrink-0 ${panelOpen ? 'w-72' : 'w-0'}`}>
            <ProjectContextPanel
              documents={activeProject.documents}
              sources={activeProject.sources}
              onAddDocument={handleAddDocument}
              onDeleteDocument={handleDeleteDocument}
              onAddSource={handleAddSource}
              onDeleteSource={handleDeleteSource}
              chatId={activeProjectId}
              projectName={activeProject.name}
              conversationContext={activeMessages.slice(-6).map((m) => `${m.role}: ${m.content}`).join(' ')}
              initialNotes={activeProject.notes}
              onNotesChange={handleNotesChange}
            />
          </div>

          {/* Panel toggle strip */}
          <button
            onClick={() => setPanelOpen((v) => !v)}
            className="shrink-0 self-stretch w-5 flex items-center justify-center bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border-r border-gray-200 dark:border-gray-700 transition"
            title={panelOpen ? 'Hide panel' : 'Show panel'}
          >
            {panelOpen
              ? <ChevronLeft size={13} className="text-gray-400" />
              : <ChevronRight size={13} className="text-gray-400" />}
          </button>

          {/* Col 3 — Conversations list or active chat */}
          {!activeConvId ? (
            <ConversationList
              projectName={activeProject.name}
              conversations={activeProject.conversations}
              onNewConversation={handleNewConversation}
              onSelectConversation={setActiveConvId}
              onDeleteConversation={handleDeleteConversation}
              onRenameConversation={handleRenameConversation}
            />
          ) : (
            <div className="flex flex-col flex-1 overflow-hidden bg-white dark:bg-gray-900">
              {/* Top bar with back button */}
              <div className="shrink-0 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex items-center gap-3">
                <button
                  onClick={() => setActiveConvId(null)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
                >
                  <ArrowLeft size={18} />
                </button>
                <p className="text-sm font-medium text-gray-700 dark:text-white">
                  {activeProject.conversations.find((c) => c.id === activeConvId)?.title ?? 'Conversation'}
                </p>
              </div>

              {activeMessages.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center px-4 bg-white dark:bg-gray-900">
                  <h2 className="text-2xl font-semibold text-gray-700 dark:text-white mb-2">How can I help you today?</h2>
                  <p className="text-gray-400 text-sm mb-8">Ask me anything about Citizens Advice guidance.</p>
                  <div className="w-full max-w-2xl">
                    <ChatInput onSend={handleSend} loading={loading} />
                    <div className="mt-4">
                      <DepthSlider
                        depth={activeProject.depth}
                        onChange={(d) => updateProject(activeProjectId!, { depth: d })}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  {/* Chat window — flex-1 so it fills all space freed by the panel */}
                  <ChatWindow
                    messages={activeMessages}
                    loading={loading}
                  />

                  {/* Bottom dock — always pinned to bottom */}
                  <div className="shrink-0 bg-white dark:bg-gray-700 border-t border-gray-100 dark:border-gray-600">

                    {/* Toggle button — always visible */}
                    <div className="flex items-center justify-center py-1">
                      <button
                        onClick={() => setInputVisible((v) => !v)}
                        className="text-xs text-gray-300 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-300 transition px-3 py-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-600"
                      >
                        {inputVisible ? '▼ hide' : '▲ show'}
                      </button>
                    </div>

                    {/* Collapsing panel */}
                    <div
                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                        inputVisible ? 'max-h-64' : 'max-h-0'
                      }`}
                    >
                      <ChatInput onSend={handleSend} loading={loading} />
                      <div className="pb-2 dark:bg-gray-700">
                        <DepthSlider
                          depth={activeProject.depth}
                          onChange={(d) => updateProject(activeProjectId!, { depth: d })}
                        />
                      </div>
                    </div>

                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
