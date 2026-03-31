import { Plus, MessageSquare, Trash2, LogOut } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export interface Chat {
  id: string;
  title: string;
}

interface Props {
  chats: Chat[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
}

export default function ChatSidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
}: Props) {
  const { username, logout } = useAuth();

  return (
    <div className="w-64 bg-gray-900 flex flex-col h-screen shrink-0">
      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-gray-600 text-gray-200 hover:bg-gray-700 transition text-sm font-medium"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto px-3 space-y-0.5">
        {chats.length === 0 ? (
          <p className="text-gray-500 text-xs text-center mt-8 px-4">
            No chats yet. Start a new conversation.
          </p>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => onSelectChat(chat.id)}
              className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition text-sm ${
                activeChatId === chat.id
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <MessageSquare size={14} className="shrink-0 text-gray-400" />
              <span className="flex-1 truncate">{chat.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteChat(chat.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition shrink-0"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))
        )}
      </div>

      {/* User footer */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-300">
          <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
            {username?.charAt(0).toUpperCase() ?? 'U'}
          </div>
          <span className="flex-1 truncate text-sm">{username ?? 'User'}</span>
          <button
            onClick={logout}
            className="text-gray-400 hover:text-white transition"
            title="Log out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
