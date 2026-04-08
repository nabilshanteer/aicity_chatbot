import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useSession } from 'next-auth/react';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react';

import ChatInput from '@/components/ChatInput';
import ChatWindow, { Message } from '@/components/ChatWindow';
import ConversationList, { Conversation } from '@/components/ConversationList';
import DepthSlider from '@/components/DepthSlider';
import ProjectContextPanel, {
  CaseDocument,
  DepthMode,
  Region,
  WebSource,
} from '@/components/ProjectContextPanel';
import ProjectSidebar, { Project } from '@/components/ProjectSidebar';
import { useAuthSafe } from '@/hooks/useAuthSafe';
import { chatAPI } from '@/services/api';

interface ProjectData {
  id: string;
  name: string;
  documents: CaseDocument[];
  sources: WebSource[];
  depth: DepthMode;
  region: Region;
  conversations: Conversation[];
  notes: string[];
}

type ProjectStore = Record<string, ProjectData>;

const EMPTY_PROJECT: ProjectData = {
  id: '__draft__',
  name: 'New Case Workspace',
  documents: [],
  sources: [],
  depth: 'balanced',
  region: 'England',
  conversations: [],
  notes: [],
};

const newId = () => `${Date.now()}`;

export default function ChatPage() {
  const { isLoggedIn } = useAuthSafe();
  const { data: session } = useSession();
  const router = useRouter();

  const [projects, setProjects] = useState<ProjectStore>({});
  const [projectList, setProjectList] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messagesByConv, setMessagesByConv] = useState<Record<string, Message[]>>({});
  const [loading, setLoading] = useState(false);
  const [casesLoading, setCasesLoading] = useState(false);
  const [creatingCase, setCreatingCase] = useState(false);
  const [inputVisible, setInputVisible] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);

  useEffect(() => {
    if (!isLoggedIn) router.push('/login');
  }, [isLoggedIn, router]);

  useEffect(() => {
    if (!isLoggedIn) return;

    setCasesLoading(true);
    chatAPI.getCases()
      .then(({ cases }) => {
        const store: ProjectStore = {};
        const list: Project[] = [];

        cases.forEach((c) => {
          const name = c.title || 'Untitled Case';
          const conv: Conversation = { id: c.id, title: name, caseId: c.id };
          store[c.id] = {
            id: c.id,
            name,
            depth: 'balanced',
            region: 'England',
            documents: [],
            sources: Array.isArray(c.sources) ? c.sources : [],
            conversations: [conv],
            notes: Array.isArray(c.notes) ? c.notes : [],
          };
          list.push({ id: c.id, name });
        });

        setProjects(store);
        setProjectList(list);
      })
      .catch(() => {
        setProjects({});
        setProjectList([]);
      })
      .finally(() => setCasesLoading(false));
  }, [isLoggedIn]);

  useEffect(() => {
    if (activeProjectId || projectList.length === 0) return;

    const firstProjectId = projectList[0].id;
    setActiveProjectId(firstProjectId);
    const conv = projects[firstProjectId]?.conversations[0];
    setActiveConvId(conv?.id ?? null);
  }, [activeProjectId, projectList, projects]);

  useEffect(() => {
    if (!activeProjectId || messagesByConv[activeProjectId] !== undefined) return;

    chatAPI.getMessages(activeProjectId)
      .then(({ messages }) => {
        setMessagesByConv((prev) => ({
          ...prev,
          [activeProjectId]: messages.map((m) => ({
            role: (m.role === 'advisor' ? 'user' : 'assistant') as 'user' | 'assistant',
            content: m.content,
          })),
        }));
      })
      .catch(() => {
        setMessagesByConv((prev) => ({ ...prev, [activeProjectId]: [] }));
      });
  }, [activeProjectId, messagesByConv]);

  const activeProject = activeProjectId ? projects[activeProjectId] : null;
  const workspaceProject = activeProject ?? EMPTY_PROJECT;
  const activeMessages: Message[] = messagesByConv[activeConvId ?? ''] ?? [];
  const activeCaseId = activeProjectId;

  const handleNewProject = async (name: string) => {
    try {
      setCreatingCase(true);
      const userId = session?.user?.email ?? undefined;
      const { case_id } = await chatAPI.createCase(userId);
      await chatAPI.updateTitle(case_id, name);

      const conv: Conversation = { id: case_id, title: name, caseId: case_id };
      const newProject: ProjectData = {
        id: case_id,
        name,
        depth: 'balanced',
        region: 'England',
        documents: [],
        sources: [],
        conversations: [conv],
        notes: [],
      };

      setProjects((prev) => ({ ...prev, [case_id]: newProject }));
      setProjectList((prev) => [{ id: case_id, name }, ...prev]);
      setMessagesByConv((prev) => ({ ...prev, [case_id]: [] }));
      setActiveProjectId(case_id);
      setActiveConvId(case_id);
    } catch (err) {
      console.error('Failed to create case:', err);
    } finally {
      setCreatingCase(false);
    }
  };

  const handleDeleteProject = (id: string) => {
    setProjects((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setProjectList((prev) => prev.filter((item) => item.id !== id));
    if (activeProjectId === id) {
      setActiveProjectId(null);
      setActiveConvId(null);
    }
  };

  const handleRenameProject = (id: string, name: string) => {
    setProjects((prev) => ({ ...prev, [id]: { ...prev[id], name } }));
    setProjectList((prev) => prev.map((item) => (item.id === id ? { ...item, name } : item)));
  };

  const updateProject = (id: string, patch: Partial<ProjectData>) => {
    setProjects((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  };

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
      documents: activeProject?.documents.filter((doc) => doc.id !== docId) ?? [],
    });
  };

  const handleNotesChange = (notes: string[]) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, { notes });
  };

  const handleRegionChange = (region: Region) => {
    if (!activeProjectId) return;
    updateProject(activeProjectId, { region });
  };

  const handleAddSource = (title: string, url: string) => {
    if (!activeProjectId) return;
    const src: WebSource = { id: newId(), title, url };
    const updated = [...(activeProject?.sources ?? []), src];
    updateProject(activeProjectId, { sources: updated });
    chatAPI.saveSources(activeProjectId, updated).catch(console.error);
  };

  const handleDeleteSource = (srcId: string) => {
    if (!activeProjectId) return;
    const updated = activeProject?.sources.filter((s) => s.id !== srcId) ?? [];
    updateProject(activeProjectId, { sources: updated });
    chatAPI.saveSources(activeProjectId, updated).catch(console.error);
  };

  const handleNewConversation = async () => {
    if (!activeProjectId) return;

    const id = newId();
    let caseId = id;

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
      conversations: activeProject?.conversations.filter((conv) => conv.id !== convId) ?? [],
    });
    if (activeConvId === convId) setActiveConvId(null);
  };

  const handleRenameConversation = (convId: string, title: string) => {
    if (!activeProjectId || !activeProject) return;

    updateProject(activeProjectId, {
      conversations: activeProject.conversations.map((conv) =>
        conv.id === convId ? { ...conv, title } : conv,
      ),
    });
  };

  const handleSend = async (text: string) => {
    if (!activeConvId || !activeProjectId || !activeProject) return;

    const userMsg: Message = { role: 'user', content: text };
    setMessagesByConv((prev) => ({
      ...prev,
      [activeConvId]: [...(prev[activeConvId] ?? []), userMsg],
    }));

    const conv = activeProject.conversations.find((item) => item.id === activeConvId);
    const isFirstMessage = (messagesByConv[activeConvId] ?? []).length === 0;

    if (isFirstMessage) {
      const projectId = activeProjectId;
      const conversationId = activeConvId;
      chatAPI.generateTitle(text).then((title) => {
        setProjects((prev) => ({
          ...prev,
          [projectId]: {
            ...prev[projectId],
            name: title,
            conversations: prev[projectId]?.conversations.map((item) =>
              item.id === conversationId ? { ...item, title } : item,
            ) ?? [],
          },
        }));
        setProjectList((prev) => prev.map((item) => (item.id === projectId ? { ...item, name: title } : item)));
        chatAPI.updateTitle(projectId, title);
      });
    }

    setMessagesByConv((prev) => ({
      ...prev,
      [activeConvId]: [...(prev[activeConvId] ?? []), { role: 'assistant', content: '' }],
    }));
    setLoading(true);

    try {
      let caseId = conv?.caseId;

      if (!caseId) {
        const userId = session?.user?.email ?? undefined;
        const { case_id } = await chatAPI.createCase(userId);
        caseId = case_id;

        updateProject(activeProjectId, {
          conversations: activeProject.conversations.map((item) =>
            item.id === activeConvId ? { ...item, caseId } : item,
          ),
        });
      }

      const currentConvId = activeConvId;
      const currentSources = activeProject.sources;

      const response = await chatAPI.sendMessage(
        caseId,
        text,
        activeProject.depth ?? 'balanced',
        activeProject.notes ?? [],
        activeProject.sources.map((source) => source.url) ?? [],
        activeProject.documents.map((document) => document.name) ?? [],
        activeProject.region ?? 'England',
        (() => {
          let buffer = '';
          let timerId: ReturnType<typeof setTimeout> | null = null;

          return (token: string) => {
            buffer += token;
            if (timerId) return;

            timerId = setTimeout(() => {
              const chunk = buffer;
              buffer = '';
              timerId = null;

              setMessagesByConv((prev) => {
                const msgs = [...(prev[currentConvId] ?? [])];
                const last = msgs[msgs.length - 1];
                if (last?.role === 'assistant') {
                  msgs[msgs.length - 1] = { ...last, content: last.content + chunk };
                }
                return { ...prev, [currentConvId]: msgs };
              });
            }, 50);
          };
        })(),
      );

      if (response.message.sources?.length) {
        const existingUrls = new Set(currentSources.map((source) => source.url));
        const newSources = response.message.sources
          .filter((url) => url !== 'Unknown' && !existingUrls.has(url))
          .map((url) => {
            let title = url;
            try {
              title = new URL(url).hostname.replace('www.', '');
            } catch {
              title = url;
            }

            return { id: newId(), title, url };
          });

        if (newSources.length > 0) {
          const updatedSources = [...(activeProject?.sources ?? []), ...newSources];
          updateProject(activeProjectId, { sources: updatedSources });
          chatAPI.saveSources(activeProjectId, updatedSources).catch(console.error);
        }
      }
    } catch {
      setMessagesByConv((prev) => {
        const msgs = [...(prev[activeConvId] ?? [])];
        const last = msgs[msgs.length - 1];
        if (last?.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, content: 'Something went wrong. Please try again.' };
        }
        return { ...prev, [activeConvId]: msgs };
      });
    } finally {
      setLoading(false);
    }
  };

  if (!isLoggedIn) return null;

  return (
    <div className="flex h-screen bg-white dark:bg-gray-900 overflow-hidden">
      <ProjectSidebar
        projects={projectList}
        activeProjectId={activeProjectId}
        onSelectProject={(id) => {
          setActiveProjectId(id);
          const conv = projects[id]?.conversations[0];
          setActiveConvId(conv?.id ?? null);
        }}
        onNewProject={handleNewProject}
        onDeleteProject={handleDeleteProject}
        onRenameProject={handleRenameProject}
      />

      <div className={`transition-[width] duration-300 overflow-hidden shrink-0 ${panelOpen ? 'w-72' : 'w-0'}`}>
        <ProjectContextPanel
          documents={workspaceProject.documents}
          sources={workspaceProject.sources}
          onAddDocument={handleAddDocument}
          onDeleteDocument={handleDeleteDocument}
          onAddSource={handleAddSource}
          onDeleteSource={handleDeleteSource}
          chatId={activeProjectId}
          activeCaseId={activeCaseId}
          projectName={workspaceProject.name}
          conversationContext={activeMessages.slice(-6).map((m) => `${m.role}: ${m.content}`).join(' ')}
          initialNotes={workspaceProject.notes}
          onNotesChange={handleNotesChange}
          region={workspaceProject.region}
          onRegionChange={handleRegionChange}
        />
      </div>

      <button
        onClick={() => setPanelOpen((prev) => !prev)}
        className="shrink-0 self-stretch w-5 flex items-center justify-center bg-white dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition"
        title={panelOpen ? 'Hide panel' : 'Show panel'}
      >
        {panelOpen
          ? <ChevronLeft size={13} className="text-gray-400" />
          : <ChevronRight size={13} className="text-gray-400" />}
      </button>

      {!activeProject ? (
        <div className="flex flex-col flex-1 overflow-hidden bg-white dark:bg-gray-900">
          <div className="flex-1 flex items-center justify-center px-6">
            <div className="max-w-xl text-center">
              {casesLoading ? (
                <p className="text-gray-400 text-lg font-medium">Loading cases...</p>
              ) : (
                <>
                  <p className="text-3xl font-semibold text-gray-800 dark:text-white">Your workspace is ready</p>
                  <p className="text-gray-400 text-sm mt-3 leading-6">
                    Documents, sources, smart notes, and depth settings are available on the left.
                    Create a case to start chatting and save everything properly.
                  </p>
                  <div className="mt-6 flex items-center justify-center gap-3">
                    <button
                      onClick={() => void handleNewProject('Untitled Case')}
                      disabled={creatingCase}
                      className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium transition"
                    >
                      {creatingCase ? 'Creating case...' : 'Create First Case'}
                    </button>
                    <p className="text-xs text-gray-500 dark:text-gray-400">or use New Case in the sidebar</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      ) : !activeConvId ? (
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
          <div className="shrink-0 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex items-center gap-3">
            <button
              onClick={() => setActiveConvId(null)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
            >
              <ArrowLeft size={18} />
            </button>
            <p className="text-sm font-medium text-gray-700 dark:text-white">
              {activeProject.conversations.find((conv) => conv.id === activeConvId)?.title ?? 'Conversation'}
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
                    onChange={(depth) => updateProject(activeProjectId!, { depth })}
                  />
                </div>
              </div>
            </div>
          ) : (
            <>
              <ChatWindow
                messages={activeMessages}
                loading={loading && activeMessages[activeMessages.length - 1]?.content === ''}
              />

              <div className="shrink-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-center py-1">
                  <button
                    onClick={() => setInputVisible((prev) => !prev)}
                    className="text-xs text-gray-300 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-300 transition px-3 py-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    {inputVisible ? '▼ hide' : '▲ show'}
                  </button>
                </div>

                <div
                  className={`overflow-hidden transition-all duration-300 ease-in-out ${
                    inputVisible ? 'max-h-64' : 'max-h-0'
                  }`}
                >
                  <ChatInput onSend={handleSend} loading={loading} />
                  <div className="pb-2 dark:bg-gray-900">
                    <DepthSlider
                      depth={activeProject.depth}
                      onChange={(depth) => updateProject(activeProjectId!, { depth })}
                    />
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
