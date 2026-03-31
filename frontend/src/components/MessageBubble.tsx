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
        <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}
