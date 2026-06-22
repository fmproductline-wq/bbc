import React, { useState } from 'react';
import { marked } from 'marked';

marked.setOptions({ breaks: true, gfm: true });

export default function MessageBubble({ message, streaming }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  function copy() {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const html = isUser ? null : marked.parse(message.content || '');

  return (
    <div className={`flex gap-3 mb-5 animate-fadein group ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
        isUser
          ? 'bg-zinc-700 text-zinc-300'
          : 'bg-brand-500/20 border border-brand-500/30'
      }`}>
        {isUser ? (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
        ) : (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        )}
      </div>

      {/* Bubble */}
      <div className={`flex-1 max-w-[85%] ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div className={`text-xs font-medium mb-1 ${isUser ? 'text-zinc-500' : 'text-brand-400'}`}>
          {isUser ? 'You' : 'AI Agent'}
          {streaming && <span className="ml-1 text-zinc-600 animate-pulse">●</span>}
        </div>

        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed relative ${
          isUser
            ? 'bg-brand-500/15 border border-brand-500/20 text-white'
            : message.isError
            ? 'bg-red-900/20 border border-red-800/30 text-red-300'
            : 'bg-surface-700 border border-surface-500 text-zinc-100'
        }`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div
              className="prose-dark"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          )}
        </div>

        {/* Copy button */}
        {!isUser && message.content && (
          <button
            onClick={copy}
            className="mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-zinc-600 hover:text-zinc-400 flex items-center gap-1"
          >
            {copied ? (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20,6 9,17 4,12"/></svg>
                Copied
              </>
            ) : (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                Copy
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
