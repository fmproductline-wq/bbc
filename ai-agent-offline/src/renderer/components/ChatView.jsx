import React, { useState, useRef, useEffect, useCallback } from 'react';
import { streamChat } from '../hooks/useOllama';
import MessageBubble from './MessageBubble';

const SYSTEM_PROMPT = `You are a helpful, knowledgeable AI assistant. You give clear, accurate, and concise answers. You can help with coding, writing, analysis, math, and general questions. You run fully offline and privately — no data leaves the device.`;

export default function ChatView({ conversation, model, models, onModelChange, onUpdateConv }) {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  const messages = conversation?.messages || [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  useEffect(() => {
    if (!isStreaming) textareaRef.current?.focus();
  }, [isStreaming]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming || !model) return;

    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    const userMsg = { role: 'user', content: text, id: crypto.randomUUID() };

    onUpdateConv(conv => {
      const title = conv.messages.length === 0
        ? text.slice(0, 40) + (text.length > 40 ? '…' : '')
        : conv.title;
      return { ...conv, title, messages: [...conv.messages, userMsg] };
    });

    const historyMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...messages.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: text },
    ];

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    await streamChat({
      model,
      messages: historyMessages,
      signal: ctrl.signal,
      onChunk: (_, full) => setStreamingContent(full),
      onDone: (full) => {
        const assistantMsg = { role: 'assistant', content: full, id: crypto.randomUUID() };
        onUpdateConv(conv => ({ ...conv, messages: [...conv.messages, assistantMsg] }));
        setStreamingContent('');
        setIsStreaming(false);
      },
      onError: (err) => {
        const errMsg = { role: 'assistant', content: `Error: ${err.message}`, id: crypto.randomUUID(), isError: true };
        onUpdateConv(conv => ({ ...conv, messages: [...conv.messages, errMsg] }));
        setStreamingContent('');
        setIsStreaming(false);
      },
    });
  }, [input, isStreaming, model, messages, onUpdateConv]);

  function stopStreaming() {
    abortRef.current?.abort();
    setIsStreaming(false);
    setStreamingContent('');
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex flex-col h-full">
      {/* Model selector bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-surface-600 bg-surface-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
          <select
            value={model}
            onChange={e => onModelChange(e.target.value)}
            className="bg-transparent text-sm text-white border-none outline-none cursor-pointer"
          >
            {models.length === 0 && <option value="">No models installed</option>}
            {models.map(m => (
              <option key={m.name} value={m.name} className="bg-surface-700">
                {m.name}
              </option>
            ))}
          </select>
        </div>
        <span className="text-xs text-zinc-600">100% Offline · Private</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {isEmpty && (
          <div className="flex flex-col items-center justify-center h-full gap-6 animate-fadein">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="1.5" strokeLinecap="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div className="text-center">
              <h2 className="text-xl font-semibold text-white mb-2">BestBrand AI Agent</h2>
              <p className="text-sm text-zinc-500 max-w-sm">
                Your private, offline AI assistant. Ask anything — no internet, no tracking, no data leaves your device.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 max-w-md w-full">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="text-left text-xs text-zinc-400 bg-surface-700 hover:bg-surface-600 border border-surface-500 rounded-lg px-3 py-2.5 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isStreaming && streamingContent && (
          <MessageBubble message={{ role: 'assistant', content: streamingContent }} streaming />
        )}

        {isStreaming && !streamingContent && (
          <div className="flex items-center gap-3 mb-4 animate-fadein">
            <div className="w-7 h-7 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center flex-shrink-0">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            </div>
            <div className="flex gap-1.5 py-3">
              <span className="typing-dot w-1.5 h-1.5 bg-zinc-500 rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-zinc-500 rounded-full" />
              <span className="typing-dot w-1.5 h-1.5 bg-zinc-500 rounded-full" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-surface-600 bg-surface-800 flex-shrink-0">
        {!model && (
          <p className="text-xs text-amber-400 mb-2 text-center">
            No model selected. Go to <strong>Models</strong> to download one.
          </p>
        )}
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={model ? `Message ${model}… (Enter to send, Shift+Enter for newline)` : 'Install a model first…'}
              disabled={!model || isStreaming}
              rows={1}
              className="w-full bg-surface-700 border border-surface-500 focus:border-brand-500 text-white placeholder-zinc-600 text-sm rounded-xl px-4 py-3 resize-none outline-none transition-colors disabled:opacity-50"
              style={{ maxHeight: '150px', overflowY: 'auto' }}
              onInput={e => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
              }}
            />
          </div>

          {isStreaming ? (
            <button
              onClick={stopStreaming}
              className="w-10 h-10 rounded-xl bg-red-600 hover:bg-red-500 flex items-center justify-center flex-shrink-0 transition-colors"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="white"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
            </button>
          ) : (
            <button
              onClick={send}
              disabled={!input.trim() || !model}
              className="w-10 h-10 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center flex-shrink-0 transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22,2 15,22 11,13 2,9"/>
              </svg>
            </button>
          )}
        </div>
        <p className="text-xs text-zinc-700 mt-2 text-center">
          Running locally · No data sent anywhere · {model || 'No model selected'}
        </p>
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  'Explain quantum computing simply',
  'Write a Python function to sort a list',
  'What are the best practices for REST APIs?',
  'Help me write a professional email',
];
