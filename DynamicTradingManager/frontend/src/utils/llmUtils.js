export const STORAGE_KEY = 'llm_provider_config';

export const DEFAULT_CONFIG = {
  activeProvider: 'puter',
  thinking: false,
  providers: {
    puter: {
      id: 'puter',
      label: 'Puter AI (Browser)',
      base_url: '',
      api_key: '',
      model: '',
      supports_thinking: false,
      is_browser_only: true,
    },
    lmstudio: {
      id: 'lmstudio',
      label: 'LM Studio (Local)',
      base_url: 'http://localhost:1234/v1',
      api_key: 'lm-studio',
      model: '',
      supports_thinking: false,
      is_browser_only: false,
    },
    nvidia: {
      id: 'nvidia',
      label: 'NVIDIA NIM',
      base_url: 'https://integrate.api.nvidia.com/v1',
      api_key: '',
      model: '', // Removed hardcoded default
      supports_thinking: false,
      is_browser_only: false,
    },
  },
};

/**
 * Load the full LLM config from localStorage.
 */
export const loadLLMConfig = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      // Merge with defaults to pick up new providers
      return {
        ...DEFAULT_CONFIG,
        ...parsed,
        providers: { ...DEFAULT_CONFIG.providers, ...parsed.providers },
      };
    }
  } catch { /* ignore */ }
  return { ...DEFAULT_CONFIG };
};

/**
 * Save the full LLM config to localStorage.
 */
export const saveLLMConfig = (config) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
};
