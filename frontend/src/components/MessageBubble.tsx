import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Link } from 'lucide-react';

interface Props {
  role: 'user' | 'assistant';
  content: string;
}

function processSourceLinks(content: string): string {
  return content.replace(/\[Source:\s*(https?:\/\/[^\]]+)\]/g, '[SRCLNK]($1)');
}

function isSrcLink(children: React.ReactNode): boolean {
  if (Array.isArray(children)) return String(children[0]).trim() === 'SRCLNK';
  return String(children).trim() === 'SRCLNK';
}

export default function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow-sm">
          <p className="whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 px-4 py-2">
      <div className="w-7 h-7 rounded-full overflow-hidden shrink-0 mt-1">
        <img src="/logo.png" alt="Citizens Advice" className="w-full h-full object-contain" />
      </div>
      <div className="flex-1 min-w-0">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-lg font-bold text-gray-900 dark:text-gray-50 mt-4 mb-2 first:mt-0">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-base font-bold text-gray-800 dark:text-gray-100 mt-4 mb-1.5 first:mt-0">{children}</h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mt-3 mb-1 first:mt-0">{children}</h3>
            ),
            p: ({ children }) => (
              <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed mb-2 last:mb-0">{children}</p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="italic text-gray-700 dark:text-gray-300">{children}</em>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-outside pl-5 mb-2 space-y-1 text-sm text-gray-700 dark:text-gray-200">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-outside pl-5 mb-2 space-y-1 text-sm text-gray-700 dark:text-gray-200">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="leading-relaxed">{children}</li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-blue-300 dark:border-blue-600 pl-3 my-2 text-sm text-gray-600 dark:text-gray-400 italic">{children}</blockquote>
            ),
            code: ({ children }) => (
              <code className="bg-gray-100 dark:bg-gray-700 rounded px-1 py-0.5 text-xs font-mono text-gray-800 dark:text-gray-200">{children}</code>
            ),
            hr: () => (
              <hr className="my-3 border-gray-200 dark:border-gray-600" />
            ),
            a: ({ href, children }) => {
              if (isSrcLink(children) && href) {
                return (
                  <span className="relative inline-flex group align-middle mx-0.5">
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center justify-center w-4 h-4 rounded bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition cursor-pointer"
                    >
                      <Link size={13} />
                    </a>
                    <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 text-xs text-white bg-gray-900/80 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 max-w-[260px] truncate">
                      {href}
                    </span>
                  </span>
                );
              }
              return (
                <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  {children}
                </a>
              );
            },
          }}
        >
          {processSourceLinks(content)}
        </ReactMarkdown>
      </div>
    </div>
  );
}
