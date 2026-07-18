import React, { useState, useEffect, useRef } from 'react';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

function openExternal(url) {
  if (isElectron && window.electronAPI.openExternal) {
    window.electronAPI.openExternal(url);
  } else {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}

const OLLAMA_API = 'http://127.0.0.1:11434';
const STEPS = ['welcome', 'installing', 'model', 'done'];

const STARTER_MODELS = [
  { id: 'llama3.2:3b',  label: 'Llama 3.2 · 3B',  size: '~2 GB',  badge: 'Recommended', desc: 'Best balance of speed and intelligence.' },
  { id: 'phi3.5:3.8b',  label: 'Phi 3.5 · 3.8B',  size: '~2.2 GB', badge: 'Smart',       desc: 'Microsoft model, great for reasoning.' },
  { id: 'llama3.2:1b',  label: 'Llama 3.2 · 1B',  size: '~1.3 GB', badge: 'Fast',        desc: 'Lightweight, instant responses.' },
  { id: 'mistral:7b',   label: 'Mistral · 7B',     size: '~4.1 GB', badge: 'Powerful',    desc: 'Larger model, best quality answers.' },
];

async function checkOllama() {
  try {
    const r = await fetch(`${OLLAMA_API}/api/tags`, { signal: AbortSignal.timeout(3000) });
    return r.ok;
  } catch { return false; }
}

async function getInstalledModels() {
  try {
    const r = await fetch(`${OLLAMA_API}/api/tags`, { signal: AbortSignal.timeout(3000) });
    const d = await r.json();
    return (d.models || []).map(m => m.name);
  } catch { return []; }
}

export default function FirstRunWizard({ onComplete, onSkip }) {
  const [step, setStep] = useState('welcome');
  const [ollamaReady, setOllamaReady] = useState(false);
  const [installLog, setInstallLog] = useState([]);
  const [installError, setInstallError] = useState('');
  const [selectedModel, setSelectedModel] = useState('llama3.2:3b');
  const [pullProgress, setPullProgress] = useState(null);
  const [pulling, setPulling] = useState(false);
  const [pulled, setPulled] = useState(false);
  const abortRef = useRef(null);
  const logRef = useRef(null);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [installLog]);

  function log(msg, type = 'info') {
    setInstallLog(prev => [...prev, { msg, type, t: Date.now() }]);
  }

  async function startInstall() {
    setStep('installing');
    setInstallError('');
    log('Checking if Ollama is already installed…');

    const alreadyRunning = await checkOllama();
    if (alreadyRunning) {
      log('Ollama is already running ✓', 'success');
      setOllamaReady(true);
      // If models are already installed, skip straight to done
      const existingModels = await getInstalledModels();
      if (existingModels.length > 0) {
        log(`Found ${existingModels.length} model(s) already installed ✓`, 'success');
        setTimeout(() => setStep('done'), 800);
      } else {
        setTimeout(() => setStep('model'), 800);
      }
      return;
    }

    const platform = navigator.platform?.toLowerCase() || '';
    const isWin = platform.includes('win');
    const isMac = platform.includes('mac');

    log('Ollama not found. Starting installation…');

    if (isWin) {
      log('Downloading Ollama installer for Windows…');
      log('Opening browser to ollama.com/download — install it then come back.');
      log('After installing Ollama, click "Check Again" below.', 'warn');
      openExternal('https://ollama.com/download');
      setInstallError('windows-manual');
      return;
    }

    if (isMac) {
      log('Opening Ollama download page for macOS…');
      log('Download and open the .pkg, then click "Check Again".', 'warn');
      openExternal('https://ollama.com/download');
      setInstallError('mac-manual');
      return;
    }

    // Linux — auto-install via curl
    log('Linux detected. Running Ollama install script…');
    log('This uses: curl -fsSL https://ollama.com/install.sh | sh');

    if (isElectron) {
      try {
        await window.electronAPI.installOllama((line) => log(line));
        log('Ollama installed successfully ✓', 'success');
        setOllamaReady(true);
        setTimeout(() => setStep('model'), 800);
      } catch (e) {
        setInstallError(e.message);
        log('Installation failed: ' + e.message, 'error');
      }
    } else {
      log('Please run: curl -fsSL https://ollama.com/install.sh | sh', 'warn');
      setInstallError('linux-manual');
    }
  }

  async function checkAgain() {
    log('Checking Ollama connection…');
    const ok = await checkOllama();
    if (ok) {
      log('Connected to Ollama ✓', 'success');
      setOllamaReady(true);
      setInstallError('');
      const existingModels = await getInstalledModels();
      if (existingModels.length > 0) {
        log(`Found ${existingModels.length} model(s) already installed ✓`, 'success');
        setTimeout(() => setStep('done'), 600);
      } else {
        setTimeout(() => setStep('model'), 600);
      }
    } else {
      log('Still not reachable. Make sure Ollama is running.', 'warn');
    }
  }

  async function pullModel() {
    setPulling(true);
    setPullProgress({ pct: 0, status: 'Starting download…' });

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch(`${OLLAMA_API}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selectedModel, stream: true }),
        signal: ctrl.signal,
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value, { stream: true }).split('\n').filter(Boolean);
        for (const line of lines) {
          try {
            const json = JSON.parse(line);
            const pct = json.total ? Math.round((json.completed / json.total) * 100) : 0;
            setPullProgress({
              pct,
              status: json.status || 'Downloading…',
              completed: json.completed || 0,
              total: json.total || 0,
            });
          } catch {}
        }
      }

      setPulled(true);
      setPullProgress({ pct: 100, status: 'Complete!', completed: 0, total: 0 });
      setTimeout(() => setStep('done'), 800);
    } catch (e) {
      if (e.name !== 'AbortError') {
        setPullProgress({ pct: 0, status: 'Error: ' + e.message, completed: 0, total: 0 });
        setPulling(false);
      }
    } finally {
      setPulling(false);
    }
  }

  function skipModel() { setStep('done'); }

  function formatBytes(b) {
    if (!b || b === 0) return '';
    return b > 1e9 ? `${(b / 1e9).toFixed(1)} GB` : `${(b / 1e6).toFixed(0)} MB`;
  }

  return (
    <div className="flex-1 flex items-center justify-center p-6 animate-fadein">
      <div className="w-full max-w-lg">

        {/* ── WELCOME ── */}
        {step === 'welcome' && (
          <div className="text-center animate-fadeup">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center mx-auto mb-6 shadow-2xl shadow-violet-900/40">
              <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-white mb-3">Welcome to BestBrand AI</h1>
            <p className="text-[#9a9a9a] text-base leading-relaxed mb-8 max-w-sm mx-auto">
              Your private AI assistant. Runs 100% on your device — no internet, no subscriptions, no data shared.
            </p>

            <div className="grid grid-cols-3 gap-3 mb-10 text-left">
              {[
                { icon: '🔒', t: 'Fully Private', d: 'Nothing leaves your device' },
                { icon: '📡', t: 'Works Offline', d: 'No internet after setup' },
                { icon: '🆓', t: 'Free Forever', d: 'Open-source AI models' },
              ].map(f => (
                <div key={f.t} className="bg-white/5 border border-white/8 rounded-2xl p-3.5">
                  <div className="text-xl mb-1.5">{f.icon}</div>
                  <p className="text-white text-xs font-semibold mb-0.5">{f.t}</p>
                  <p className="text-[#666] text-xs leading-snug">{f.d}</p>
                </div>
              ))}
            </div>

            <button
              onClick={startInstall}
              className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold text-base transition-all shadow-lg shadow-violet-900/30"
            >
              Get Started
            </button>
            <button
              onClick={() => { onSkip(); }}
              className="mt-3 text-sm text-[#555] hover:text-[#888] transition-colors"
            >
              Skip setup (Ollama already installed)
            </button>
          </div>
        )}

        {/* ── INSTALLING ── */}
        {step === 'installing' && (
          <div className="animate-fadeup">
            <h2 className="text-2xl font-bold text-white mb-1.5">Setting Up Ollama</h2>
            <p className="text-[#9a9a9a] text-sm mb-5">The free AI engine that powers your assistant.</p>

            <div
              ref={logRef}
              className="bg-[#161616] border border-[#2a2a2a] rounded-2xl p-4 h-48 overflow-y-auto font-mono text-xs space-y-1 mb-5"
            >
              {installLog.length === 0 && <span className="text-[#444]">Starting…</span>}
              {installLog.map((l, i) => (
                <div key={i} className={
                  l.type === 'success' ? 'text-green-400' :
                  l.type === 'error'   ? 'text-red-400' :
                  l.type === 'warn'    ? 'text-amber-400' :
                  'text-[#888]'
                }>
                  {l.type === 'success' ? '✓ ' : l.type === 'error' ? '✗ ' : l.type === 'warn' ? '⚠ ' : '› '}{l.msg}
                </div>
              ))}
            </div>

            {installError && (
              <div className="mb-5 bg-amber-500/8 border border-amber-500/20 rounded-2xl p-4">
                <p className="text-amber-300 text-sm font-medium mb-2">Manual Installation Required</p>
                <ol className="space-y-1.5 text-sm text-[#aaa]">
                  <li>1. Download &amp; install Ollama from <span className="text-violet-400">ollama.com/download</span></li>
                  <li>2. Launch Ollama — it runs in your system tray</li>
                  <li>3. Click "Check Again" below</li>
                </ol>
                <button
                  onClick={checkAgain}
                  className="mt-3 w-full py-2.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-medium transition-colors"
                >
                  Check Again
                </button>
              </div>
            )}

            {!installError && !ollamaReady && (
              <div className="flex items-center gap-3 text-sm text-[#666]">
                <div className="w-4 h-4 border-2 border-violet-600 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                Installing…
              </div>
            )}
          </div>
        )}

        {/* ── MODEL ── */}
        {step === 'model' && (
          <div className="animate-fadeup">
            <h2 className="text-2xl font-bold text-white mb-1.5">Choose an AI Model</h2>
            <p className="text-[#9a9a9a] text-sm mb-5">
              One-time download — after this, everything works offline forever.
            </p>

            <div className="space-y-2.5 mb-5">
              {STARTER_MODELS.map(m => (
                <button
                  key={m.id}
                  onClick={() => !pulling && setSelectedModel(m.id)}
                  disabled={pulling}
                  className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl border text-left transition-all ${
                    selectedModel === m.id
                      ? 'bg-violet-600/15 border-violet-500/50'
                      : 'bg-white/4 border-white/8 hover:bg-white/7 hover:border-white/15'
                  }`}
                >
                  <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                    selectedModel === m.id ? 'border-violet-500' : 'border-[#444]'
                  }`}>
                    {selectedModel === m.id && <div className="w-2 h-2 rounded-full bg-violet-500" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-semibold text-white">{m.label}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                        m.badge === 'Recommended' ? 'bg-violet-600/30 text-violet-300' :
                        m.badge === 'Fast'        ? 'bg-green-600/25 text-green-300' :
                        m.badge === 'Powerful'    ? 'bg-orange-600/25 text-orange-300' :
                        'bg-blue-600/25 text-blue-300'
                      }`}>{m.badge}</span>
                    </div>
                    <p className="text-xs text-[#777]">{m.desc}</p>
                  </div>
                  <span className="text-xs text-[#555] flex-shrink-0">{m.size}</span>
                </button>
              ))}
            </div>

            {pullProgress && (
              <div className="mb-5 bg-white/4 border border-white/8 rounded-2xl p-4">
                <div className="flex justify-between text-xs text-[#888] mb-2">
                  <span>{pullProgress.status}</span>
                  <span>{pullProgress.pct}%</span>
                </div>
                <div className="w-full bg-white/8 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-violet-600 to-indigo-500 rounded-full transition-all duration-500"
                    style={{ width: `${pullProgress.pct}%` }}
                  />
                </div>
                {pullProgress.total > 0 && (
                  <p className="text-[10px] text-[#555] mt-1.5">
                    {formatBytes(pullProgress.completed)} / {formatBytes(pullProgress.total)}
                  </p>
                )}
              </div>
            )}

            <button
              onClick={pullModel}
              disabled={pulling || pulled}
              className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm transition-all shadow-lg shadow-violet-900/20"
            >
              {pulling ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Downloading…
                </span>
              ) : pulled ? '✓ Downloaded' : `Download ${selectedModel}`}
            </button>
            <button
              onClick={skipModel}
              disabled={pulling}
              className="mt-3 w-full text-sm text-[#555] hover:text-[#888] transition-colors disabled:opacity-30"
            >
              Skip — I'll download a model later
            </button>
          </div>
        )}

        {/* ── DONE ── */}
        {step === 'done' && (
          <div className="text-center animate-fadeup">
            <div className="w-20 h-20 rounded-full bg-green-500/15 border border-green-500/30 flex items-center justify-center mx-auto mb-6">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20,6 9,17 4,12"/>
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-white mb-3">You're all set!</h2>
            <p className="text-[#9a9a9a] text-base mb-8">
              BestBrand AI is ready. Start a conversation — everything runs privately on your device.
            </p>
            <button
              onClick={onComplete}
              className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold text-base transition-all shadow-lg shadow-violet-900/30"
            >
              Start Chatting →
            </button>
          </div>
        )}

        {/* Step indicator dots */}
        <div className="flex items-center justify-center gap-2 mt-8">
          {STEPS.map(s => (
            <div key={s} className={`h-1.5 rounded-full transition-all duration-300 ${
              s === step ? 'w-6 bg-violet-500' : 'w-1.5 bg-white/15'
            }`} />
          ))}
        </div>
      </div>
    </div>
  );
}
