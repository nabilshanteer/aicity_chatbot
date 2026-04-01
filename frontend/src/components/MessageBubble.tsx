import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  role: 'user' | 'assistant';
  content: string;
}

export default function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user';

  return (
    <div className={`flex gap-4 px-4 py-6 ${
      isUser
        ? 'bg-transparent dark:bg-gray-600'
        : 'bg-gray-50 dark:bg-gray-800'
    }`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
          isUser ? 'bg-blue-600 text-white' : 'bg-green-600 text-white'
        }`}
      >
        {isUser ? 'You' : 'AI'}
      </div>

      {/* Content */}
      <div className="flex-1 pt-0.5">
        <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-1">
          {isUser ? 'You' : 'Citizens Advice AI'}
        </p>

        {isUser ? (
          <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
            {content}
          </p>
        ) : (
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
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{children}</a>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
