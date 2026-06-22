import React, { useState } from 'react';
import { pullModel, deleteModel } from '../hooks/useOllama';

const RECOMMENDED = [
  { name: 'llama3.2:3b',   size: '~2 GB',   badge: 'Best Overall', desc: 'Fast, smart, great for everyday tasks.' },
  { name: 'llama3.2:1b',   size: '~1.3 GB', badge: 'Fastest',      desc: 'Instant responses, lower quality.' },
  { name: 'mistral:7b',    size: '~4.1 GB', badge: 'Powerful',     desc: 'Excellent reasoning and writing.' },
  { name: 'phi3.5:3.8b',   size: '~2.2 GB', badge: 'Smart',        desc: 'Microsoft Phi-3.5, strong reasoning.' },
  { name: 'gemma2:2b',     size: '~1.6 GB', badge: 'Efficient',    desc: 'Google Gemma 2, compact & capable.' },
  { name: 'qwen2.5:3b',    size: '~1.9 GB', badge: 'Multilingual', desc: 'Supports many languages well.' },
  { name: 'deepseek-r1:7b',size: '~4.7 GB', badge: 'Reasoning',    desc: 'DeepSeek R1 — thinks step by step.' },
  { name: 'codellama:7b',  size: '~3.8 GB', badge: 'Code',         desc: 'Best for programming tasks.' },
];

const BADGE_COLORS = {
  'Best Overall': 'bg-violet-600/25 text-violet-300',
  'Fastest':      'bg-green-600/25 text-green-300',
  'Powerful':     'bg-orange-600/25 text-orange-300',
  'Smart':        'bg-blue-600/25 text-blue-300',
  'Efficient':    'bg-teal-600/25 text-teal-300',
  'Multilingual': 'bg-pink-600/25 text-pink-300',
  'Reasoning':    'bg-amber-600/25 text-amber-300',
  'Code':         'bg-cyan-600/25 text-cyan-300',
};

export default function ModelManager({ models, onRefresh, selectedModel, onSelectModel }) {
  const [pulling, setPulling] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [customModel, setCustomModel] = useState('');
  const [error, setError] = useState('');

  const installed = new Set(models.map(m => m.name));

  async function handlePull(name) {
    setPulling({ name, pct: 0, status: 'Starting…' });
    setError('');
    try {
      await pullModel(name, d => {
        const pct = d.total ? Math.round((d.completed / d.total) * 100) : 0;
        setPulling({ name, pct, status: d.status || 'Downloading…' });
      });
      await onRefresh();
      onSelectModel(name);
    } catch (e) {
      setError(`Failed to pull ${name}: ${e.message}`);
    } finally {
      setPulling(null);
    }
  }

  async function handleDelete(name) {
    if (!confirm(`Delete model "${name}"? This frees disk space but you'll need to re-download it.`)) return;
    setDeleting(name);
    try {
      await deleteModel(name);
      if (selectedModel === name) onSelectModel('');
      await onRefresh();
    } catch (e) {
      setError(`Failed to delete: ${e.message}`);
    } finally {
      setDeleting(null);
    }
  }

  function fmt(b) {
    if (!b) return '';
    return b >= 1e9 ? `${(b / 1e9).toFixed(1)} GB` : `${(b / 1e6).toFixed(0)} MB`;
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-white mb-1">Models</h1>
        <p className="text-sm text-[#666] mb-6">Download free, open-source AI models. They run entirely on your device.</p>

        {error && (
          <div className="mb-5 px-4 py-3 bg-red-900/20 border border-red-700/30 rounded-2xl text-sm text-red-300 flex items-start justify-between gap-3">
            <span>{error}</span>
            <button onClick={() => setError('')} className="text-red-500 hover:text-red-300 flex-shrink-0">✕</button>
          </div>
        )}

        {/* Installed */}
        {models.length > 0 && (
          <section className="mb-8">
            <p className="text-xs font-semibold text-[#444] uppercase tracking-widest mb-3">Installed</p>
            <div className="space-y-2">
              {models.map(m => (
                <div
                  key={m.name}
                  className={`flex items-center gap-3 px-4 py-3.5 rounded-2xl border transition-all ${
                    selectedModel === m.name
                      ? 'bg-violet-600/10 border-violet-500/40'
                      : 'bg-white/4 border-white/8'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${selectedModel === m.name ? 'bg-violet-500' : 'bg-green-500'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{m.name}</p>
                    <p className="text-xs text-[#555]">{fmt(m.size)}</p>
                  </div>
                  <button
                    onClick={() => onSelectModel(m.name)}
                    className={`text-xs px-3 py-1.5 rounded-xl transition-all font-medium ${
                      selectedModel === m.name
                        ? 'bg-violet-600 text-white'
                        : 'bg-white/8 text-[#aaa] hover:bg-white/14 hover:text-white'
                    }`}
                  >
                    {selectedModel === m.name ? 'Active' : 'Use'}
                  </button>
                  <button
                    onClick={() => handleDelete(m.name)}
                    disabled={deleting === m.name}
                    className="text-[#444] hover:text-red-400 transition-colors p-1.5 rounded-lg hover:bg-red-500/10"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3,6 5,6 21,6"/><path d="M19,6l-1,14H6L5,6"/></svg>
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Download progress */}
        {pulling && (
          <div className="mb-6 px-4 py-4 bg-violet-600/8 border border-violet-500/20 rounded-2xl">
            <div className="flex justify-between text-xs text-[#aaa] mb-2">
              <span className="font-medium text-white">Downloading {pulling.name}</span>
              <span>{pulling.pct}%</span>
            </div>
            <div className="w-full bg-white/8 rounded-full h-1.5">
              <div
                className="bg-gradient-to-r from-violet-600 to-indigo-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${pulling.pct}%` }}
              />
            </div>
            <p className="text-xs text-[#555] mt-1.5">{pulling.status}</p>
          </div>
        )}

        {/* Available to download */}
        <section className="mb-8">
          <p className="text-xs font-semibold text-[#444] uppercase tracking-widest mb-3">Available Models</p>
          <div className="space-y-2">
            {RECOMMENDED.map(rec => {
              const isInstalled = installed.has(rec.name);
              const isPulling = pulling?.name === rec.name;
              return (
                <div key={rec.name} className="flex items-center gap-3 px-4 py-3.5 rounded-2xl bg-white/4 border border-white/8 hover:border-white/14 transition-all">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isInstalled ? 'bg-green-500' : 'bg-[#333]'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="text-sm font-medium text-white">{rec.name}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${BADGE_COLORS[rec.badge] || 'bg-white/10 text-white/60'}`}>
                        {rec.badge}
                      </span>
                    </div>
                    <p className="text-xs text-[#555]">{rec.desc} · {rec.size}</p>
                  </div>
                  {isInstalled ? (
                    <span className="text-xs text-green-500 font-medium flex-shrink-0">Installed</span>
                  ) : isPulling ? (
                    <span className="text-xs text-violet-400 animate-pulse flex-shrink-0">Downloading…</span>
                  ) : (
                    <button
                      onClick={() => handlePull(rec.name)}
                      disabled={!!pulling}
                      className="text-xs px-3 py-1.5 rounded-xl bg-white/8 hover:bg-white/14 text-[#aaa] hover:text-white transition-all font-medium disabled:opacity-40 flex-shrink-0"
                    >
                      Download
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Custom model */}
        <section>
          <p className="text-xs font-semibold text-[#444] uppercase tracking-widest mb-3">Custom Model</p>
          <div className="flex gap-2">
            <input
              value={customModel}
              onChange={e => setCustomModel(e.target.value)}
              placeholder="e.g. llama3.1:8b"
              onKeyDown={e => e.key === 'Enter' && customModel.trim() && handlePull(customModel.trim())}
              className="flex-1 bg-white/5 border border-white/10 focus:border-white/25 text-white placeholder-[#444] text-sm rounded-2xl px-4 py-2.5 outline-none transition-colors"
            />
            <button
              onClick={() => customModel.trim() && handlePull(customModel.trim())}
              disabled={!customModel.trim() || !!pulling}
              className="px-4 py-2.5 rounded-2xl bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium transition-colors disabled:opacity-40"
            >
              Pull
            </button>
          </div>
          <p className="text-xs text-[#444] mt-2">Any model from ollama.com/library works here.</p>
        </section>
      </div>
    </div>
  );
}
