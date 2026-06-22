import React, { useState, useMemo } from 'react';
import { marked } from 'marked';

// Custom renderer to add code header with language + copy button hook
const renderer = new marked.Renderer();
renderer.code = function(code, lang) {
  const langLabel = lang || 'code';
  const escaped = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return `<pre data-lang="${langLabel}"><div class="code-header"><span>${langLabel}</span><button class="copy-code-btn" data-code="${encodeURIComponent(code)}">Copy</button></div><code>${escaped}</code></pre>`;
};

marked.use({ renderer, breaks: true, gfm: true });

function parseMarkdown(text) {
  return marked.parse(text || '');
}

export default function MessageBubble({ message, streaming, isLast }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const html = useMemo(() => isUser ? null : parseMarkdown(message.content), [message.content, isUser]);

  function copyMessage() {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Handle copy-code button clicks (event delegation)
  function handleClick(e) {
    const btn = e.target.closest('.copy-code-btn');
    if (!btn) return;
    const code = decodeURIComponent(btn.dataset.code || '');
    navigator.clipboard.writeText(code);
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
  }

  if (isUser) {
    return (
      <div className="flex justify-end mb-6 animate-fadeup">
        <div className="max-w-[75%]">
          <div className="bg-[#2f2f2f] border border-white/8 text-[#ececec] text-sm px-5 py-3.5 rounded-3xl rounded-br-md leading-relaxed whitespace-pre-wrap">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 mb-6 animate-fadeup group">
      {/* AI Avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        <p className="text-[11px] font-semibold text-violet-400 mb-2 tracking-wide">BestBrand AI</p>

        <div
          className={`prose text-sm${streaming ? ' cursor' : ''}`}
          dangerouslySetInnerHTML={{ __html: html }}
          onClick={handleClick}
        />

        {/* Action row */}
        {!streaming && message.content && (
          <div className="flex items-center gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <ActionBtn onClick={copyMessage} title={copied ? 'Copied!' : 'Copy'}>
              {copied ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20,6 9,17 4,12"/></svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              )}
            </ActionBtn>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionBtn({ onClick, title, children }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="p-1.5 rounded-lg text-[#555] hover:text-[#aaa] hover:bg-white/6 transition-all"
    >
      {children}
    </button>
  );
}
