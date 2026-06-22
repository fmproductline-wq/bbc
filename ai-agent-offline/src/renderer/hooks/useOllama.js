import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = 'http://127.0.0.1:11434';

async function getServerPort() {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return window.electronAPI.getServerPort();
  }
  return null;
}

export function useOllama() {
  const [status, setStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
  const [models, setModels] = useState([]);
  const portRef = useRef(null);

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tags`);
      if (!res.ok) throw new Error('Not ok');
      const data = await res.json();
      const list = (data.models || []).sort((a, b) => a.name.localeCompare(b.name));
      setModels(list);
      setStatus('online');
    } catch {
      setStatus('offline');
      setModels([]);
    }
  }, []);

  const checkStatus = useCallback(async () => {
    setStatus('checking');
    await fetchModels();
  }, [fetchModels]);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(fetchModels, 10000);
    return () => clearInterval(interval);
  }, []);

  return { status, models, checkStatus };
}

export async function streamChat({ model, messages, onChunk, onDone, onError, signal }) {
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages, stream: true }),
      signal,
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(err || `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n').filter(Boolean);

      for (const line of lines) {
        try {
          const json = JSON.parse(line);
          if (json.message?.content) {
            fullText += json.message.content;
            onChunk(json.message.content, fullText);
          }
          if (json.done) {
            onDone(fullText);
            return;
          }
        } catch {}
      }
    }
    onDone(fullText);
  } catch (err) {
    if (err.name !== 'AbortError') onError(err);
  }
}

export async function pullModel(modelName, onProgress) {
  const res = await fetch(`${API_BASE}/api/pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: modelName, stream: true }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n').filter(Boolean);
    for (const line of lines) {
      try {
        const json = JSON.parse(line);
        onProgress(json);
      } catch {}
    }
  }
}

export async function deleteModel(modelName) {
  const res = await fetch(`${API_BASE}/api/delete`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: modelName }),
  });
  if (!res.ok) throw new Error(`Failed to delete: ${res.status}`);
}
