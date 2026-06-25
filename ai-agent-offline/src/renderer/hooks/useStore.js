import { useState, useEffect, useCallback } from 'react';

const isElectron = typeof window !== 'undefined' && window.electronAPI;
const memCache = {};

export function useStore(key, defaultValue) {
  const [state, setState] = useState({
    value: memCache[key] !== undefined ? memCache[key] : defaultValue,
    hydrated: memCache[key] !== undefined, // already in cache = already hydrated
  });

  useEffect(() => {
    if (isElectron) {
      window.electronAPI.getStore(key).then(v => {
        const value = v !== undefined ? v : defaultValue;
        memCache[key] = value;
        setState({ value, hydrated: true });
      });
    } else {
      try {
        const stored = localStorage.getItem(`bb_ai_${key}`);
        const value = stored !== null ? JSON.parse(stored) : defaultValue;
        memCache[key] = value;
        setState({ value, hydrated: true });
      } catch {
        setState(s => ({ ...s, hydrated: true }));
      }
    }
  }, [key]);

  const set = useCallback((updaterOrValue) => {
    setState(prev => {
      const next = typeof updaterOrValue === 'function' ? updaterOrValue(prev.value) : updaterOrValue;
      memCache[key] = next;
      if (isElectron) {
        window.electronAPI.setStore(key, next);
      } else {
        try { localStorage.setItem(`bb_ai_${key}`, JSON.stringify(next)); } catch {}
      }
      return { value: next, hydrated: true };
    });
  }, [key]);

  return [state.value, set, state.hydrated];
}
