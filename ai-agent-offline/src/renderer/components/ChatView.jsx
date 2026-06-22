import React, { useState, useRef, useEffect, useCallback } from 'react';
import { streamChat } from '../hooks/useOllama';
import MessageBubble from './MessageBubble';
import { useStore } from '../hooks/useStore';

export default function ChatView({ conversation, model, models, onModelChange, onUpdateConv, onNewChat }) {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [systemPrompt] = useStore('systemPrompt', '');
  const [temperature] = useStore('temperature', 0.7);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const messages = conversation?.messages || [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, streamingContent]);

  useEffect(() => {
    if (!isStreaming) {
      textareaRef.current?.focus();
    }
  }, [isStreaming, conversation?.id]);

  // Auto-resize textarea
  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming || !model) return;

    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setIsStreaming(true);
    setStreamingContent('');

    const userMsg = { role: 'user', content: text, id: crypto.randomUUID() };
    onUpdateConv(conv => ({
      ...conv,
      title: conv.messages.length === 0 ? text.slice(0, 45) + (text.length > 45 ? '…' : '') : conv.title,
      messages: [...conv.messages, userMsg],
    }));

    const sysContent = systemPrompt || 'You are a helpful, intelligent AI assistant. Give clear, accurate, well-formatted answers. Use markdown for code and structured content.';

    const apiMessages = [
      { role: 'system', content: sysContent },
      ...messages.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: text },
    ];

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    await streamChat({
      model,
      messages: apiMessages,
      signal: ctrl.signal,
      options: { temperature },
      onChunk: (_, full) => setStreamingContent(full),
      onDone: full => {
        const msg = { role: 'assistant', content: full, id: crypto.randomUUID() };
        onUpdateConv(conv => ({ ...conv, messages: [...conv.messages, msg] }));
        setStreamingContent('');
        setIsStreaming(false);
      },
      onError: err => {
        const msg = { role: 'assistant', content: `**Error:** ${err.message}\n\nMake sure Ollama is running and the model is installed.`, id: crypto.randomUUID(), isError: true };
        onUpdateConv(conv => ({ ...conv, messages: [...conv.messages, msg] }));
        setStreamingContent('');
        setIsStreaming(false);
      },
    });
  }, [input, isStreaming, model, messages, onUpdateConv, systemPrompt, temperature]);

  function stopStreaming() {
    abortRef.current?.abort();
    if (streamingContent) {
      const msg = { role: 'assistant', content: streamingContent, id: crypto.randomUUID() };
      onUpdateConv(conv => ({ ...conv, messages: [...conv.messages, msg] }));
    }
    setStreamingContent('');
    setIsStreaming(false);
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
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <EmptyState model={model} onPrompt={p => { setInput(p); textareaRef.current?.focus(); }} />
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 w-full">
            {messages.map((msg, i) => (
              <MessageBubble key={msg.id} message={msg} isLast={i === messages.length - 1 && !isStreaming} />
            ))}

            {isStreaming && !streamingContent && (
              <div className="flex gap-4 mb-6 animate-fadeup">
                <AIAvatar />
                <div className="flex items-center gap-1.5 pt-1">
                  <div className="w-2 h-2 bg-[#888] rounded-full dot-1" />
                  <div className="w-2 h-2 bg-[#888] rounded-full dot-2" />
                  <div className="w-2 h-2 bg-[#888] rounded-full dot-3" />
                </div>
              </div>
            )}

            {isStreaming && streamingContent && (
              <MessageBubble
                message={{ role: 'assistant', content: streamingContent }}
                streaming
              />
            )}

            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Input area — pinned bottom */}
      <div className="flex-shrink-0 pb-5 px-4">
        <div className="max-w-3xl mx-auto">
          {/* Model selector above input */}
          {models.length > 1 && (
            <div className="flex justify-center mb-2">
              <select
                value={model}
                onChange={e => onModelChange(e.target.value)}
                className="text-xs text-[#888] bg-transparent border-none outline-none cursor-pointer hover:text-white transition-colors"
              >
                {models.map(m => <option key={m.name} value={m.name} className="bg-[#2a2a2a]">{m.name}</option>)}
              </select>
            </div>
          )}

          <div className={`relative flex items-end gap-2 bg-[#2f2f2f] border rounded-3xl px-4 py-3 transition-all ${
            isStreaming ? 'border-white/10' : 'border-white/10 focus-within:border-white/25'
          }`}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => { setInput(e.target.value); autoResize(e.target); }}
              onKeyDown={handleKeyDown}
              placeholder={model ? 'Message BestBrand AI…' : 'Download a model first (go to Models)'}
              disabled={!model}
              rows={1}
              className="flex-1 bg-transparent text-[#ececec] placeholder-[#555] text-sm resize-none outline-none py-1 leading-relaxed"
              style={{ maxHeight: '200px' }}
            />

            <button
              onClick={isStreaming ? stopStreaming : send}
              disabled={!isStreaming && (!input.trim() || !model)}
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all mb-0.5 ${
                isStreaming
                  ? 'bg-white/90 hover:bg-white text-black'
                  : input.trim() && model
                  ? 'bg-white text-black hover:bg-white/90'
                  : 'bg-white/10 text-[#555] cursor-not-allowed'
              }`}
            >
              {isStreaming ? (
                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><rect width="10" height="10" rx="2"/></svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5,12 12,5 19,12"/>
                </svg>
              )}
            </button>
          </div>

          <p className="text-[10px] text-[#444] text-center mt-2">
            Running locally on your device · No data sent anywhere
          </p>
        </div>
      </div>
    </div>
  );
}

function AIAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center flex-shrink-0 mt-0.5">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    </div>
  );
}

function EmptyState({ model, onPrompt }) {
  const prompts = [
    { icon: '💡', text: 'Explain quantum computing in simple terms' },
    { icon: '🐍', text: 'Write a Python script to rename files in a folder' },
    { icon: '✍️', text: 'Help me write a professional cover letter' },
    { icon: '🔍', text: 'What are the pros and cons of React vs Vue?' },
    { icon: '📊', text: 'Give me a 7-day meal plan for weight loss' },
    { icon: '🛡️', text: 'What are common SQL injection vulnerabilities?' },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 animate-fadein">
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center mb-5 shadow-xl shadow-violet-900/30">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <h2 className="text-2xl font-bold text-white mb-1.5">How can I help you?</h2>
      <p className="text-[#666] text-sm mb-8">
        {model ? `Using ${model} · running locally` : 'No model selected — go to Models to download one'}
      </p>

      <div className="grid grid-cols-2 gap-2 max-w-lg w-full">
        {prompts.map(p => (
          <button
            key={p.text}
            onClick={() => onPrompt(p.text)}
            className="flex items-start gap-2.5 text-left px-4 py-3.5 rounded-2xl bg-white/5 border border-white/8 hover:bg-white/9 hover:border-white/14 transition-all text-sm text-[#ccc] hover:text-white"
          >
            <span className="text-base flex-shrink-0">{p.icon}</span>
            <span className="leading-snug text-xs">{p.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
