import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  messages: Message[];
  loading: boolean;
}

export default function ChatWindow({ messages, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto bg-white dark:bg-gray-900">
      <div className="w-full max-w-4xl mx-auto px-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-4 px-4 py-6 bg-gray-50 dark:bg-gray-800">
            <div className="w-8 h-8 rounded-full overflow-hidden shrink-0">
              <img src="/logo.png" alt="Citizens Advice" className="w-full h-full object-contain" />
            </div>
            <div className="flex items-center gap-1 pt-2">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
