import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, Loader } from 'lucide-react';

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
}

const MAX_HEIGHT = 160; // px — roughly 6 lines

export default function ChatInput({ onSend, loading }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Grow the textarea to fit content, capped at MAX_HEIGHT
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden';
  }, [value]);

  const handleSubmit = () => {
    if (!value.trim() || loading) return;
    onSend(value.trim());
    setValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 px-4 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-800 rounded-xl shadow-sm px-4 py-3 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder="Message Citizens Advice AI..."
            className="flex-1 resize-none outline-none text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-400 bg-transparent disabled:opacity-50"
          />
          <button
            onClick={handleSubmit}
            disabled={!value.trim() || loading}
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {loading ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
