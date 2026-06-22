import { useState, useEffect, useCallback } from 'react';

const isElectron = typeof window !== 'undefined' && window.electronAPI;

const memCache = {};

export function useStore(key, defaultValue) {
  const [value, setValue] = useState(() => {
    if (memCache[key] !== undefined) return memCache[key];
    return defaultValue;
  });

  useEffect(() => {
    if (isElectron) {
      window.electronAPI.getStore(key).then(v => {
        if (v !== undefined) {
          memCache[key] = v;
          setValue(v);
        }
      });
    } else {
      try {
        const stored = localStorage.getItem(`bb_ai_${key}`);
        if (stored !== null) {
          const parsed = JSON.parse(stored);
          memCache[key] = parsed;
          setValue(parsed);
        }
      } catch {}
    }
  }, [key]);

  const set = useCallback((updaterOrValue) => {
    setValue(prev => {
      const next = typeof updaterOrValue === 'function' ? updaterOrValue(prev) : updaterOrValue;
      memCache[key] = next;
      if (isElectron) {
        window.electronAPI.setStore(key, next);
      } else {
        try { localStorage.setItem(`bb_ai_${key}`, JSON.stringify(next)); } catch {}
      }
      return next;
    });
  }, [key]);

  return [value, set];
}
