import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { loadLLMConfig, saveLLMConfig, STORAGE_KEY } from '../utils/llmUtils';

const LLMContext = createContext(null);

export const LLMProvider = ({ children }) => {
  const [config, setConfigState] = useState(loadLLMConfig);

  const setConfig = useCallback((updater) => {
    setConfigState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      saveLLMConfig(next);
      return next;
    });
  }, []);

  // Sync across tabs
  useEffect(() => {
    const handler = (e) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        try {
          setConfigState(JSON.parse(e.newValue));
        } catch (e) {
          console.warn('Failed to sync LLM config:', e);
        }
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  return (
    <LLMContext.Provider value={{ config, setConfig }}>
      {children}
    </LLMContext.Provider>
  );
};

export const useLLMInternal = () => {
  const context = useContext(LLMContext);
  if (!context) {
    throw new Error('useLLMInternal must be used within an LLMProvider');
  }
  return context;
};
