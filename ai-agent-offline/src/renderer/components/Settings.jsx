import React, { useState, useEffect } from 'react';
import { useStore } from '../hooks/useStore';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

export default function Settings({ selectedModel, onModelChange, models }) {
  const [systemPrompt, setSystemPrompt] = useStore('systemPrompt', '');
  const [temperature, setTemperature] = useStore('temperature', 0.7);
  const [theme, setTheme] = useStore('theme', 'dark');
  const [version, setVersion] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isElectron) {
      window.electronAPI.getVersion().then(setVersion);
    }
  }, []);

  function save() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-xl mx-auto">
        <h1 className="text-xl font-semibold text-white mb-1">Settings</h1>
        <p className="text-sm text-zinc-500 mb-8">Customize your AI agent experience.</p>

        <Section title="Model">
          <label className="block text-xs text-zinc-500 mb-1.5">Active Model</label>
          <select
            value={selectedModel}
            onChange={e => onModelChange(e.target.value)}
            className="w-full bg-surface-700 border border-surface-500 focus:border-brand-500 text-white text-sm rounded-xl px-4 py-2.5 outline-none transition-colors"
          >
            {models.length === 0 && <option value="">No models installed</option>}
            {models.map(m => <option key={m.name} value={m.name} className="bg-surface-700">{m.name}</option>)}
          </select>
        </Section>

        <Section title="System Prompt">
          <label className="block text-xs text-zinc-500 mb-1.5">
            Custom instructions given to the AI at the start of every conversation
          </label>
          <textarea
            value={systemPrompt}
            onChange={e => setSystemPrompt(e.target.value)}
            placeholder="e.g. You are a coding assistant. Always write clean, commented code."
            rows={4}
            className="w-full bg-surface-700 border border-surface-500 focus:border-brand-500 text-white placeholder-zinc-600 text-sm rounded-xl px-4 py-3 outline-none transition-colors resize-none"
          />
          <p className="text-xs text-zinc-600 mt-1">Leave blank to use the default assistant persona.</p>
        </Section>

        <Section title="Generation">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs text-zinc-500">Temperature: {temperature}</label>
            <span className="text-xs text-zinc-600">{temperature < 0.4 ? 'More focused' : temperature > 0.8 ? 'More creative' : 'Balanced'}</span>
          </div>
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={temperature}
            onChange={e => setTemperature(parseFloat(e.target.value))}
            className="w-full accent-brand-500"
          />
          <div className="flex justify-between text-xs text-zinc-700 mt-1">
            <span>0 — Precise</span>
            <span>1 — Default</span>
            <span>2 — Wild</span>
          </div>
        </Section>

        <Section title="Data & Privacy">
          <div className="space-y-2">
            <PrivacyBadge icon="🔒" label="100% Offline" desc="No internet connection used during chat" />
            <PrivacyBadge icon="🚫" label="No Tracking" desc="Zero analytics, telemetry, or data collection" />
            <PrivacyBadge icon="💾" label="Local Storage Only" desc="Conversations saved on your device only" />
            <PrivacyBadge icon="🤖" label="Open Source Models" desc="Free, open-source AI models via Ollama" />
          </div>
        </Section>

        <div className="flex items-center justify-between">
          <button
            onClick={save}
            className="px-6 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium transition-colors"
          >
            {saved ? '✓ Saved' : 'Save Settings'}
          </button>

          {version && (
            <span className="text-xs text-zinc-700">BestBrand AI v{version}</span>
          )}
        </div>

        {isElectron && (
          <Section title="Files">
            <button
              onClick={() => window.electronAPI.openModelsFolder()}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              Open Models Folder
            </button>
          </Section>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-8">
      <h2 className="text-sm font-semibold text-zinc-300 mb-3">{title}</h2>
      {children}
    </div>
  );
}

function PrivacyBadge({ icon, label, desc }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 bg-surface-700 border border-surface-500 rounded-lg">
      <span className="text-base">{icon}</span>
      <div>
        <p className="text-xs font-medium text-white">{label}</p>
        <p className="text-xs text-zinc-500">{desc}</p>
      </div>
    </div>
  );
}
