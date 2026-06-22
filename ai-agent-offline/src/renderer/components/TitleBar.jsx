import React from 'react';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

export default function TitleBar({ status, onCheckStatus, minimal }) {
  if (minimal) {
    return (
      <div className={`h-10 bg-[#212121] flex items-center px-4 flex-shrink-0 ${isElectron ? 'drag-region' : ''}`}>
        <div className={`flex items-center gap-2 ${isElectron ? 'no-drag' : ''}`}>
          <Logo />
          <span className="text-sm font-semibold text-white">BestBrand AI</span>
        </div>
        {isElectron && <WinControls />}
      </div>
    );
  }

  return (
    <div className={`h-10 bg-[#212121] border-b border-white/5 flex items-center justify-between px-3 flex-shrink-0 ${isElectron ? 'drag-region' : ''}`}>
      <div className={`flex items-center gap-2 ${isElectron ? 'no-drag' : ''}`}>
        <Logo />
        <span className="text-sm font-semibold text-white">BestBrand AI</span>
      </div>

      <div className={`flex items-center gap-3 ${isElectron ? 'no-drag' : ''}`}>
        {status && (
          <button
            onClick={onCheckStatus}
            className="flex items-center gap-1.5 text-xs text-[#666] hover:text-[#aaa] transition-colors"
          >
            <span className={`w-1.5 h-1.5 rounded-full transition-colors ${
              status === 'online' ? 'bg-green-500' :
              status === 'checking' ? 'bg-amber-400 animate-pulse' :
              'bg-red-500'
            }`} />
            {status === 'online' ? 'Connected' : status === 'checking' ? 'Checking…' : 'Offline'}
          </button>
        )}
        {isElectron && <WinControls />}
      </div>
    </div>
  );
}

function Logo() {
  return (
    <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
    </div>
  );
}

function WinControls() {
  return (
    <div className="no-drag flex items-center gap-0.5">
      <button
        onClick={() => window.electronAPI.minimize()}
        className="w-8 h-8 flex items-center justify-center rounded-lg text-[#555] hover:text-white hover:bg-white/8 transition-all"
      >
        <svg width="10" height="1" viewBox="0 0 10 1" fill="currentColor"><rect width="10" height="1"/></svg>
      </button>
      <button
        onClick={() => window.electronAPI.maximize()}
        className="w-8 h-8 flex items-center justify-center rounded-lg text-[#555] hover:text-white hover:bg-white/8 transition-all"
      >
        <svg width="9" height="9" viewBox="0 0 9 9" fill="none" stroke="currentColor" strokeWidth="1.2"><rect x="0.6" y="0.6" width="7.8" height="7.8"/></svg>
      </button>
      <button
        onClick={() => window.electronAPI.close()}
        className="w-8 h-8 flex items-center justify-center rounded-lg text-[#555] hover:text-white hover:bg-red-600/80 transition-all"
      >
        <svg width="9" height="9" viewBox="0 0 9 9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"><line x1="1" y1="1" x2="8" y2="8"/><line x1="8" y1="1" x2="1" y2="8"/></svg>
      </button>
    </div>
  );
}
