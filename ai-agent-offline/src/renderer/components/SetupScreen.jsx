import React from 'react';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

export default function SetupScreen({ onRetry }) {
  const platform = navigator.platform?.toLowerCase() || '';
  const isMac = platform.includes('mac');
  const isWin = platform.includes('win');

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 animate-fadein">
      <div className="max-w-md w-full">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mb-6 mx-auto">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>

        <h2 className="text-xl font-semibold text-white text-center mb-2">Ollama Required</h2>
        <p className="text-sm text-zinc-500 text-center mb-8">
          BestBrand AI Agent needs <strong className="text-zinc-300">Ollama</strong> to run AI models locally on your device. It's free and takes 2 minutes to set up.
        </p>

        <div className="space-y-4 mb-8">
          <Step n={1} title="Download Ollama (free)">
            <a
              href="https://ollama.com/download"
              target="_blank"
              rel="noopener"
              className="inline-flex items-center gap-1.5 text-brand-400 hover:text-brand-300 underline text-sm"
            >
              ollama.com/download
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15,3 21,3 21,9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
          </Step>

          <Step n={2} title="Install and launch it">
            <p className="text-xs text-zinc-500 mt-0.5">
              {isMac && 'Open the .dmg and drag Ollama to Applications, then open it.'}
              {isWin && 'Run the installer and Ollama will start automatically.'}
              {!isMac && !isWin && 'Install Ollama and run: ollama serve'}
            </p>
          </Step>

          <Step n={3} title="Download a model (in your terminal)">
            <div className="mt-1 bg-surface-700 border border-surface-500 rounded-lg px-3 py-2 font-mono text-xs text-zinc-300">
              ollama pull llama3.2:3b
            </div>
            <p className="text-xs text-zinc-600 mt-1">~2 GB. Runs fast on any modern PC.</p>
          </Step>

          <Step n={4} title="Come back here and click Retry">
            <p className="text-xs text-zinc-500 mt-0.5">The agent will connect automatically.</p>
          </Step>
        </div>

        <button
          onClick={onRetry}
          className="w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-medium transition-colors"
        >
          Retry Connection
        </button>

        <p className="text-xs text-zinc-700 text-center mt-4">
          Once installed, everything works 100% offline. No accounts. No data sent anywhere.
        </p>
      </div>
    </div>
  );
}

function Step({ n, title, children }) {
  return (
    <div className="flex gap-3">
      <div className="w-6 h-6 rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center flex-shrink-0 text-xs font-bold text-brand-400">
        {n}
      </div>
      <div>
        <p className="text-sm font-medium text-white">{title}</p>
        {children}
      </div>
    </div>
  );
}
