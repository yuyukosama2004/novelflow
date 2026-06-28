import { useEffect, useRef, useState } from 'react';
import { Send, Sparkles } from 'lucide-react';

import type { InterviewMessage } from '../../types/entities';

interface Props {
  messages: InterviewMessage[];
  onSend: (content: string) => void;
  onExtract: () => void;
  isSending: boolean;
  isExtracting: boolean;
  disabled?: boolean;
}

export function InterviewChat({
  messages,
  onSend,
  onExtract,
  isSending,
  isExtracting,
  disabled,
}: Props) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSubmit() {
    const trimmed = input.trim();
    if (!trimmed || isSending || disabled) return;
    onSend(trimmed);
    setInput('');
  }

  const displayMessages = messages.filter((m) => m.role !== 'system');

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-900">创作访谈</h3>
        <button
          onClick={onExtract}
          disabled={isExtracting || disabled || displayMessages.length < 2}
          className="flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
        >
          <Sparkles size={13} />
          {isExtracting ? '提取中…' : '提取候选设定'}
        </button>
      </div>

      <div className="flex-1 overflow-auto space-y-3 mb-3 min-h-0">
        {displayMessages.length === 0 ? (
          <p className="text-center text-sm text-slate-400 py-12">
            等待访谈开始…
          </p>
        ) : (
          displayMessages.map((msg, i) => (
            <div
              key={msg.timestamp ?? `${msg.role}-${i}`}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-white border border-slate-200 text-slate-800'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        {isSending && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-white border border-slate-200 px-4 py-2.5 text-sm text-slate-400">
              思考中…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="输入你的回答…（Enter 发送）"
          disabled={disabled || isSending}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-600 disabled:bg-slate-100"
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isSending || disabled}
          className="rounded-md bg-emerald-600 px-3 py-2 text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
