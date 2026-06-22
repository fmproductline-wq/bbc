import React from 'react';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

export default function TitleBar({ status, onCheckStatus }) {
  const statusColor = status === 'online' ? 'bg-green-500' : status === 'checking' ? 'bg-yellow-400' : 'bg-red-500';
  const statusLabel = status === 'online' ? 'Online' : status === 'checking' ? 'Checking…' : 'Ollama Offline';

  return (
    <div className={`flex items-center justify-between h-10 bg-surface-800 border-b border-surface-600 px-3 flex-shrink-0 ${isElectron ? 'drag-region' : ''}`}>
      {/* Left: logo + status */}
      <div className={`flex items-center gap-3 ${isElectron ? 'no-drag' : ''}`}>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-brand-500 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <span className="text-white text-sm font-semibold tracking-tight">BestBrand AI</span>
        </div>

        <button
          onClick={onCheckStatus}
          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
          title="Click to refresh connection"
        >
          <span className={`w-1.5 h-1.5 rounded-full ${statusColor} ${status === 'checking' ? 'animate-pulse' : ''}`} />
          {statusLabel}
        </button>
      </div>

      {/* Center: title */}
      <span className="text-xs text-zinc-600 font-medium absolute left-1/2 -translate-x-1/2">
        Offline AI — Powered by Ollama
      </span>

      {/* Right: window controls (Electron only) */}
      {isElectron && (
        <div className="no-drag flex items-center gap-1">
          <button
            onClick={() => window.electronAPI.minimize()}
            className="w-7 h-7 rounded hover:bg-surface-600 flex items-center justify-center text-zinc-400 hover:text-white transition-colors"
          >
            <svg width="10" height="2" viewBox="0 0 10 2" fill="currentColor"><rect width="10" height="2"/></svg>
          </button>
          <button
            onClick={() => window.electronAPI.maximize()}
            className="w-7 h-7 rounded hover:bg-surface-600 flex items-center justify-center text-zinc-400 hover:text-white transition-colors"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="1" y="1" width="8" height="8"/></svg>
          </button>
          <button
            onClick={() => window.electronAPI.close()}
            className="w-7 h-7 rounded hover:bg-red-600 flex items-center justify-center text-zinc-400 hover:text-white transition-colors"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" strokeWidth="1.5"><line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/></svg>
          </button>
        </div>
      )}
    </div>
  );
}
