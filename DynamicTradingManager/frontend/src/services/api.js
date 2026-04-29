import axios from 'axios';

const resolveApiBaseUrl = () => {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured) {
    return configured;
  }

  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000/api';
  }

  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1') {
    return 'http://127.0.0.1:8000/api';
  }

  return `${window.location.origin}/api`;
};

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
});

// Stats & Items
export const getStats = () => api.get('/stats');
export const getItems = (params) => api.get('/items', { params });
export const getTags = () => api.get('/tags');

// Actions
export const triggerUpdate = () => api.post('/actions/update');
export const triggerAdd = (batchSize) => api.post('/actions/add', { batch_size: batchSize });
export const triggerReset = () => api.post('/actions/reset');
export const triggerListProperties = (minUsage) => api.post('/actions/list-properties', { min_usage: minUsage });
export const triggerFindProperty = (propName, valueFilter) => api.post('/actions/find-property', { property_name: propName, value_filter: valueFilter });
export const triggerAnalyzeSpawns = () => api.post('/actions/analyze-spawns');
export const triggerRarityStats = () => api.post('/actions/rarity-stats');
export const triggerGenerateDocs = () => api.post('/actions/generate-docs');

// Tasks & Logs
export const getTasks = () => api.get('/tasks');
export const getTaskStatus = (id) => api.get(`/tasks/${id}`);
export const getTaskLogs = (id, since = 0) => api.get(`/tasks/${id}/logs`, { params: { since } });

// Misc
export const getBlacklist = () => api.get('/blacklist');
export const addBlacklistItem = (itemId) => api.post('/blacklist/item', { item_id: itemId });
export const getOverrides = () => api.get('/overrides');
export const saveItemOverride = (payload) => api.put('/overrides/item', payload);
export const deleteItemOverride = (itemId) => api.delete(`/overrides/item/${itemId}`);

export const getSimulationData = () => api.get('/simulation/data');
export const getDebugLogs = (params) => api.get('/debug/logs', { params });
export const getPricingConfig = () => api.get('/pricing/config');
export const savePricingConfig = (config) => api.put('/pricing/config', { config });
export const previewPricing = (payload) => api.post('/pricing/preview', payload);
export const getPricingAudit = (params) => api.get('/pricing/audit', { params });
export const getPricingTags = () => api.get('/pricing/tags');
export const previewPricingTag = (payload) => api.post('/pricing/tags/preview', payload);
export const getArchetypeEditorData = (module = 'DynamicTradingCommon') => api.get('/archetypes/editor', { params: { module } });
export const saveArchetypeDefinition = (archetypeId, payload, module = 'DynamicTradingCommon') => api.put(`/archetypes/${archetypeId}/allocations`, payload, { params: { module } });
export const getDonatorsDefinition = () => api.get('/donators');
export const saveDonatorsDefinition = (payload) => api.put('/donators', payload);
export const uploadDonatorImage = (formData) => api.post('/donators/images', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
export const getManualEditorData = (scope = 'manuals', module = 'common') => api.get('/manuals/editor', { params: { scope, module } });
export const createManualDefinition = (payload, scope = 'manuals', module = 'common') => api.post('/manuals', payload, { params: { scope, module } });
export const saveManualDefinition = (manualId, payload, scope = 'manuals', module = 'common') => api.put(`/manuals/${manualId}`, payload, { params: { scope, module } });
export const deleteManualDefinition = (manualId, scope = 'manuals', module = 'common') => api.delete(`/manuals/${manualId}`, { params: { scope, module } });
export const uploadManualImage = (formData) => api.post('/manuals/images', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
export const getBatchedGitHistory = (since, branch = 'develop') => api.get('/manuals/batch/git-history', { params: { since, branch } });

// Workshop
export const triggerWorkshopPrepare = (target) => api.post('/workshop/prepare', null, { params: { target } });
export const triggerWorkshopPush = (payload) => api.post('/workshop/push', payload);
export const getWorkshopTargets = () => api.get('/workshop/targets');
export const getWorkshopMetadata = (target) => api.get('/workshop/metadata', { params: { target } });
export const getWorkshopSync = (target, itemId) => api.get('/workshop/sync', { params: { target, item_id: itemId } });
export const getWorkshopVersions = (target) => api.get('/workshop/versions', { params: { target } });
export const incrementWorkshopVersion = (payload) => api.post('/workshop/versions/increment', payload);
export const uploadWorkshopImage = (formData, target) => api.post('/workshop/image', formData, {
  params: { target },
  headers: { 'Content-Type': 'multipart/form-data' }
});

// Git
export const getGitChanges = (branch, target, since = '') => api.get('/git/changes', { params: { branch, target, since } });
export const getGitBranches = (target) => api.get('/git/branches', { params: { target } });
export const getSuiteGitLog = (branch, limit = 100) => api.get('/git/suite/log', { params: { branch, limit } });
export const getSuiteBranches = () => api.get('/git/suite/branches');

// LLM
export const getLLMProviders = () => api.get('/llm/providers');
export const llmChat = (payload) => api.post('/llm/chat', payload);
export const llmListModels = (payload) => api.post('/llm/models', payload);

/**
 * Streaming chat completion. 
 * Uses native fetch because axios handles streams differently in browsers.
 */
export const llmChatStream = async (payload, signal) => {
  const baseUrl = resolveApiBaseUrl();
  const response = await fetch(`${baseUrl}/llm/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Stream request failed with status ${response.status}`);
  }

  return response.body; // Returns a ReadableStream
};

export default api;
