export function buildActiveLLMConfig(config) {
  const activeProvider = config?.providers?.[config?.activeProvider] || config?.providers?.puter;
  if (!activeProvider || activeProvider.is_browser_only) {
    return null;
  }

  const baseUrl = String(activeProvider.base_url || '').trim();
  const model = String(activeProvider.model || '').trim();
  if (!baseUrl || !model) {
    return null;
  }

  return {
    base_url: baseUrl,
    api_key: String(activeProvider.api_key || ''),
    model,
    thinking: Boolean(config?.thinking),
    reasoning_effort: String(config?.reasoningEffort || 'medium'),
  };
}

export function renderRegistryLabel(status) {
  const state = status?.state || 'unknown';
  if (state === 'added') return 'Already Added';
  if (state === 'outdated') return 'Needs Update';
  if (state === 'partial') return 'Partially Added';
  if (state === 'not_added') return 'Not Added';
  return 'Unknown';
}

export function getRegistryChipColor(status) {
  const state = status?.state || 'unknown';
  if (state === 'added') return 'success';
  if (state === 'outdated') return 'warning';
  if (state === 'partial') return 'secondary';
  return 'default';
}

export function countByState(items, state) {
  return items.filter((item) => (item.registry_status?.state || 'unknown') === state).length;
}

export function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return String(value || '');
  }
}

export function formatPoiSecondary(poi) {
  const source = poi?.metadata?.source || 'unknown';
  const method = poi?.metadata?.label_method || 'unknown';
  return `${poi.type} | ${poi.x}, ${poi.y} | ${source} | ${method}`;
}

/**
 * Safely formats a backend error (string or JSON/Pydantic detail) for UI rendering.
 * @param {any} err - The error data from the backend response.
 */
export function formatErrorMessage(err) {
  if (!err) return '';
  if (typeof err === 'string') return err;
  
  if (Array.isArray(err)) {
    return err.map(e => {
      if (typeof e === 'object' && e !== null) {
        const loc = Array.isArray(e.loc) ? e.loc.filter(l => l !== 'body' && l !== 'query').join(' > ') : '';
        const msg = e.msg || JSON.stringify(e);
        return loc ? `${loc}: ${msg}` : msg;
      }
      return String(e);
    }).join(' | ');
  }
  
  if (typeof err === 'object' && err !== null) {
    return err.message || err.detail || JSON.stringify(err);
  }
  
  return String(err);
}
