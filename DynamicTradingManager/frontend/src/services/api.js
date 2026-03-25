import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
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

// Workshop
export const triggerWorkshopPrepare = () => api.post('/workshop/prepare');
export const triggerWorkshopPush = (payload) => api.post('/workshop/push', payload);
export const getWorkshopMetadata = () => api.get('/workshop/metadata');
export const getWorkshopSync = () => api.get('/workshop/sync');
export const uploadWorkshopImage = (formData) => api.post('/workshop/image', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});

// Git
export const getGitChanges = (branch) => api.get(`/git/changes${branch ? `?branch=${branch}` : ''}`);
export const getGitBranches = () => api.get('/git/branches');

export default api;
