import React, { useState } from 'react';
import { pullModel, deleteModel } from '../hooks/useOllama';

const RECOMMENDED = [
  { name: 'llama3.2:3b', size: '~2 GB', desc: 'Fast & smart. Best for most tasks.' },
  { name: 'llama3.2:1b', size: '~1.3 GB', desc: 'Lightweight, very fast.' },
  { name: 'mistral:7b', size: '~4.1 GB', desc: 'Excellent reasoning, coding.' },
  { name: 'phi3.5:3.8b', size: '~2.2 GB', desc: 'Microsoft Phi-3.5, great quality.' },
  { name: 'gemma2:2b', size: '~1.6 GB', desc: 'Google Gemma 2, efficient.' },
  { name: 'qwen2.5:3b', size: '~1.9 GB', desc: 'Alibaba Qwen, multilingual.' },
  { name: 'deepseek-r1:7b', size: '~4.7 GB', desc: 'DeepSeek R1, reasoning model.' },
  { name: 'codellama:7b', size: '~3.8 GB', desc: 'Best for coding tasks.' },
];

export default function ModelManager({ models, onRefresh, selectedModel, onSelectModel }) {
  const [pulling, setPulling] = useState(null); // { name, progress, status }
  const [deleting, setDeleting] = useState(null);
  const [customModel, setCustomModel] = useState('');
  const [error, setError] = useState('');

  const installedNames = new Set(models.map(m => m.name));

  async function handlePull(modelName) {
    setPulling({ name: modelName, progress: 0, status: 'Starting download…' });
    setError('');
    try {
      await pullModel(modelName, (data) => {
        const pct = data.total ? Math.round((data.completed / data.total) * 100) : 0;
        setPulling({ name: modelName, progress: pct, status: data.status || 'Downloading…' });
      });
      await onRefresh();
      onSelectModel(modelName);
    } catch (e) {
      setError(`Failed to pull ${modelName}: ${e.message}`);
    } finally {
      setPulling(null);
    }
  }

  async function handleDelete(modelName) {
    if (!confirm(`Delete ${modelName}? This cannot be undone.`)) return;
    setDeleting(modelName);
    try {
      await deleteModel(modelName);
      if (selectedModel === modelName) onSelectModel('');
      await onRefresh();
    } catch (e) {
      setError(`Failed to delete: ${e.message}`);
    } finally {
      setDeleting(null);
    }
  }

  function formatSize(bytes) {
    if (!bytes) return '';
    const gb = bytes / 1e9;
    return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1e6).toFixed(0)} MB`;
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-semibold text-white mb-1">Model Manager</h1>
        <p className="text-sm text-zinc-500 mb-6">
          Download free, open-source AI models. They run entirely on your device — no internet needed after download.
        </p>

        {error && (
          <div className="mb-4 px-4 py-3 bg-red-900/20 border border-red-800/40 rounded-lg text-sm text-red-300">
            {error}
            <button onClick={() => setError('')} className="ml-2 underline text-red-400">Dismiss</button>
          </div>
        )}

        {/* Installed models */}
        {models.length > 0 && (
          <section className="mb-8">
            <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-wider">Installed</h2>
            <div className="space-y-2">
              {models.map(m => (
                <div key={m.name} className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors ${
                  selectedModel === m.name
                    ? 'bg-brand-500/10 border-brand-500/30'
                    : 'bg-surface-700 border-surface-500'
                }`}>
                  <div className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{m.name}</p>
                    <p className="text-xs text-zinc-500">{formatSize(m.size)}</p>
                  </div>
                  <button
                    onClick={() => onSelectModel(m.name)}
                    className={`text-xs px-3 py-1 rounded-lg transition-colors ${
                      selectedModel === m.name
                        ? 'bg-brand-500 text-white'
                        : 'bg-surface-600 text-zinc-400 hover:text-white hover:bg-surface-500'
                    }`}
                  >
                    {selectedModel === m.name ? 'Active' : 'Use'}
                  </button>
                  <button
                    onClick={() => handleDelete(m.name)}
                    disabled={deleting === m.name}
                    className="text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-50"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <polyline points="3,6 5,6 21,6"/><path d="M19,6l-1,14H6L5,6"/>
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Download progress */}
        {pulling && (
          <div className="mb-6 px-4 py-4 bg-surface-700 border border-surface-500 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">Downloading {pulling.name}</span>
              <span className="text-xs text-zinc-400">{pulling.progress}%</span>
            </div>
            <div className="w-full bg-surface-500 rounded-full h-1.5 mb-2">
              <div
                className="bg-brand-500 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${pulling.progress}%` }}
              />
            </div>
            <p className="text-xs text-zinc-500">{pulling.status}</p>
          </div>
        )}

        {/* Recommended models */}
        <section className="mb-8">
          <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-wider">Recommended Models</h2>
          <div className="space-y-2">
            {RECOMMENDED.map(rec => {
              const installed = installedNames.has(rec.name);
              const isPulling = pulling?.name === rec.name;
              return (
                <div key={rec.name} className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-700 border border-surface-500">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${installed ? 'bg-green-500' : 'bg-zinc-600'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white">{rec.name}</p>
                    <p className="text-xs text-zinc-500">{rec.desc} · {rec.size}</p>
                  </div>
                  {installed ? (
                    <span className="text-xs text-green-500 font-medium">Installed</span>
                  ) : isPulling ? (
                    <span className="text-xs text-brand-400 animate-pulse">Downloading…</span>
                  ) : (
                    <button
                      onClick={() => handlePull(rec.name)}
                      disabled={!!pulling}
                      className="text-xs px-3 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
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
          <h2 className="text-sm font-medium text-zinc-400 mb-3 uppercase tracking-wider">Custom Model</h2>
          <div className="flex gap-2">
            <input
              value={customModel}
              onChange={e => setCustomModel(e.target.value)}
              placeholder="e.g. llama3.2:latest"
              className="flex-1 bg-surface-700 border border-surface-500 focus:border-brand-500 text-white placeholder-zinc-600 text-sm rounded-xl px-4 py-2.5 outline-none transition-colors"
            />
            <button
              onClick={() => { if (customModel.trim()) handlePull(customModel.trim()); }}
              disabled={!customModel.trim() || !!pulling}
              className="px-4 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium transition-colors disabled:opacity-40"
            >
              Pull
            </button>
          </div>
          <p className="text-xs text-zinc-600 mt-2">
            Any model from <span className="text-zinc-500">ollama.com/library</span> works here.
          </p>
        </section>
      </div>
    </div>
  );
}
