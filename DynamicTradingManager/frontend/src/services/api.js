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
export const getArchetypeEditorData = () => api.get('/archetypes/editor');
export const saveArchetypeDefinition = (archetypeId, payload) => api.put(`/archetypes/${archetypeId}/allocations`, payload);
export const getManualEditorData = (scope = 'manuals', module = 'common') => api.get('/manuals/editor', { params: { scope, module } });
export const createManualDefinition = (payload, scope = 'manuals', module = 'common') => api.post('/manuals', payload, { params: { scope, module } });
export const saveManualDefinition = (manualId, payload, scope = 'manuals', module = 'common') => api.put(`/manuals/${manualId}`, payload, { params: { scope, module } });
export const deleteManualDefinition = (manualId, scope = 'manuals', module = 'common') => api.delete(`/manuals/${manualId}`, { params: { scope, module } });
export const uploadManualImage = (formData) => api.post('/manuals/images', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});

// Workshop
export const triggerWorkshopPrepare = (target) => api.post('/workshop/prepare', null, { params: { target } });
export const triggerWorkshopPush = (payload) => api.post('/workshop/push', payload);
export const getWorkshopTargets = () => api.get('/workshop/targets');
export const getWorkshopMetadata = (target) => api.get('/workshop/metadata', { params: { target } });
export const getWorkshopSync = (target, itemId) => api.get('/workshop/sync', { params: { target, item_id: itemId } });
export const uploadWorkshopImage = (formData, target) => api.post('/workshop/image', formData, {
  params: { target },
  headers: { 'Content-Type': 'multipart/form-data' }
});

// Git
export const getGitChanges = (branch, target) => api.get('/git/changes', { params: { branch, target } });
export const getGitBranches = (target) => api.get('/git/branches', { params: { target } });

export default api;
