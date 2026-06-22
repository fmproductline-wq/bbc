import React, { useState, useEffect } from 'react';
import { useStore } from '../hooks/useStore';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

export default function Settings({ selectedModel, onModelChange, models }) {
  const [systemPrompt, setSystemPrompt] = useStore('systemPrompt', '');
  const [temperature, setTemperature] = useStore('temperature', 0.7);
  const [version, setVersion] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isElectron) window.electronAPI.getVersion().then(setVersion);
  }, []);

  function save() { setSaved(true); setTimeout(() => setSaved(false), 2000); }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-xl mx-auto">
        <h1 className="text-xl font-bold text-white mb-1">Settings</h1>
        <p className="text-sm text-[#666] mb-8">Customize your AI assistant.</p>

        <Sect title="Model">
          <label className="block text-xs text-[#666] mb-2">Active Model</label>
          <select
            value={selectedModel}
            onChange={e => onModelChange(e.target.value)}
            className="w-full bg-white/5 border border-white/10 focus:border-white/25 text-white text-sm rounded-2xl px-4 py-3 outline-none transition-colors"
          >
            {models.length === 0 && <option value="">No models installed</option>}
            {models.map(m => <option key={m.name} value={m.name} className="bg-[#2a2a2a]">{m.name}</option>)}
          </select>
        </Sect>

        <Sect title="Instructions">
          <label className="block text-xs text-[#666] mb-2">System prompt — given to the AI before every conversation</label>
          <textarea
            value={systemPrompt}
            onChange={e => setSystemPrompt(e.target.value)}
            placeholder="e.g. You are a senior software engineer. Always explain your reasoning."
            rows={4}
            className="w-full bg-white/5 border border-white/10 focus:border-white/25 text-white placeholder-[#444] text-sm rounded-2xl px-4 py-3 outline-none transition-colors resize-none leading-relaxed"
          />
          <p className="text-xs text-[#444] mt-1.5">Leave blank to use the default assistant persona.</p>
        </Sect>

        <Sect title="Creativity">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="text-[#666]">Temperature · controls how creative responses are</span>
            <span className="text-white font-mono bg-white/8 px-2 py-0.5 rounded-lg">{temperature}</span>
          </div>
          <input
            type="range" min={0} max={2} step={0.05}
            value={temperature}
            onChange={e => setTemperature(parseFloat(e.target.value))}
            className="w-full accent-violet-500 mb-2"
          />
          <div className="flex justify-between text-[10px] text-[#444]">
            <span>Focused / Precise</span>
            <span>Balanced</span>
            <span>Creative / Random</span>
          </div>
        </Sect>

        <Sect title="Privacy">
          <div className="grid grid-cols-2 gap-2">
            {[
              { icon: '🔒', t: '100% Offline', d: 'No internet needed after setup' },
              { icon: '🚫', t: 'Zero Tracking', d: 'No analytics or telemetry' },
              { icon: '💾', t: 'Local Storage', d: 'Chats saved on your device only' },
              { icon: '🤖', t: 'Open Source', d: 'Free AI models, no subscriptions' },
            ].map(f => (
              <div key={f.t} className="flex items-start gap-2.5 px-3.5 py-3 bg-white/4 border border-white/8 rounded-2xl">
                <span className="text-base">{f.icon}</span>
                <div>
                  <p className="text-xs font-semibold text-white">{f.t}</p>
                  <p className="text-[11px] text-[#555] leading-snug">{f.d}</p>
                </div>
              </div>
            ))}
          </div>
        </Sect>

        <div className="flex items-center justify-between">
          <button
            onClick={save}
            className={`px-6 py-2.5 rounded-2xl font-medium text-sm transition-all ${
              saved
                ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                : 'bg-violet-600 hover:bg-violet-500 text-white'
            }`}
          >
            {saved ? '✓ Saved' : 'Save'}
          </button>
          {version && <span className="text-xs text-[#444]">v{version}</span>}
        </div>

        {isElectron && (
          <Sect title="Files">
            <button
              onClick={() => window.electronAPI.openModelsFolder()}
              className="flex items-center gap-2 text-sm text-[#666] hover:text-[#aaa] transition-colors"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              Open Models Folder
            </button>
          </Sect>
        )}
      </div>
    </div>
  );
}

function Sect({ title, children }) {
  return (
    <div className="mb-8">
      <h2 className="text-sm font-semibold text-[#888] mb-3">{title}</h2>
      {children}
    </div>
  );
}
