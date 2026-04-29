import React, { useState, useEffect, useMemo } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import {
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useLLM } from '../../hooks/useLLM';
import { loadLLMConfig, saveLLMConfig } from '../../utils/llmUtils';
import { llmChat, llmListModels } from '../../services/api';

const LLMSettingsPanel = ({ open, onClose }) => {
  const { config, setConfig } = useLLM();
  const [localConfig, setLocalConfig] = useState(() => loadLLMConfig());
  const [testStatus, setTestStatus] = useState(null);
  const [testing, setTesting] = useState(false);
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [newProviderId, setNewProviderId] = useState('');

  // Sync from hook when dialog opens
  useEffect(() => {
    if (open) setLocalConfig(loadLLMConfig());
  }, [open]);

  const providerIds = useMemo(() => Object.keys(localConfig.providers), [localConfig]);
  const activeProvider = localConfig.providers[localConfig.activeProvider] || {};

  const updateProvider = (field, value) => {
    setLocalConfig(prev => ({
      ...prev,
      providers: {
        ...prev.providers,
        [prev.activeProvider]: {
          ...prev.providers[prev.activeProvider],
          [field]: value,
        }
      }
    }));
  };

  const handleSave = () => {
    saveLLMConfig(localConfig);
    setConfig(localConfig);
    onClose?.();
  };

  const handleTest = async () => {
    setTesting(true);
    setTestStatus(null);
    try {
      const provider = localConfig.providers[localConfig.activeProvider];
      if (provider.is_browser_only) {
        if (!window.puter) throw new Error('Puter.js not available.');
        const res = await window.puter.ai.chat('Say "Connection OK" in exactly two words.');
        setTestStatus({ type: 'success', message: `Puter AI responded: ${res?.toString()?.slice(0, 60)}` });
      } else {
        const res = await llmChat({
          base_url: provider.base_url,
          api_key: provider.api_key,
          model: provider.model,
          messages: [{ role: 'user', content: 'Say "Connection OK" in exactly two words.' }],
        });
        setTestStatus({ type: 'success', message: `${res.data.model} responded: ${res.data.content.slice(0, 60)}` });
      }
    } catch (err) {
      setTestStatus({ type: 'error', message: err?.response?.data?.detail || err.message });
    } finally {
      setTesting(false);
    }
  };

  const handleFetchModels = async () => {
    const provider = localConfig.providers[localConfig.activeProvider];
    if (!provider.base_url) return;
    setLoadingModels(true);
    try {
      const res = await llmListModels({ base_url: provider.base_url, api_key: provider.api_key });
      setModels(res.data || []);
    } catch {
      setModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleAddCustom = () => {
    const id = newProviderId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');
    if (!id || localConfig.providers[id]) return;
    setLocalConfig(prev => ({
      ...prev,
      activeProvider: id,
      providers: {
        ...prev.providers,
        [id]: {
          id,
          label: newProviderId.trim(),
          base_url: 'http://localhost:8080/v1',
          api_key: '',
          model: '',
          supports_thinking: false,
          is_browser_only: false,
        },
      },
    }));
    setNewProviderId('');
  };

  const handleDeleteProvider = (providerId) => {
    if (['puter', 'lmstudio', 'nvidia'].includes(providerId)) return;
    setLocalConfig(prev => {
      const next = { ...prev, providers: { ...prev.providers } };
      delete next.providers[providerId];
      if (next.activeProvider === providerId) next.activeProvider = 'puter';
      return next;
    });
  };

  const isBrowserOnly = activeProvider.is_browser_only === true;
  const isBuiltIn = ['puter', 'lmstudio', 'nvidia'].includes(localConfig.activeProvider);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" sx={{ fontWeight: 700 }}>LLM Provider Settings</Typography>
        <IconButton onClick={onClose} size="small"><CloseIcon /></IconButton>
      </DialogTitle>

      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>

          {/* Provider Selector */}
          <TextField
            select
            label="Active Provider"
            size="small"
            value={localConfig.activeProvider}
            onChange={(e) => {
              setLocalConfig(prev => ({ ...prev, activeProvider: e.target.value }));
              setModels([]);
              setTestStatus(null);
            }}
            fullWidth
          >
            {providerIds.map(id => (
              <MenuItem key={id} value={id}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ width: '100%' }}>
                  <span>{localConfig.providers[id]?.label || id}</span>
                  {localConfig.providers[id]?.is_browser_only && (
                    <Chip label="BROWSER" size="small" sx={{ height: 16, fontSize: '0.6rem' }} />
                  )}
                  {localConfig.providers[id]?.is_local && (
                    <Chip label="LOCAL" size="small" color="success" sx={{ height: 16, fontSize: '0.6rem' }} />
                  )}
                </Stack>
              </MenuItem>
            ))}
          </TextField>

          {/* Add Custom Provider */}
          <Stack direction="row" spacing={1} alignItems="center">
            <TextField
              label="Custom Provider Name"
              size="small"
              value={newProviderId}
              onChange={(e) => setNewProviderId(e.target.value)}
              sx={{ flex: 1 }}
              placeholder="e.g. Ollama, Groq, Together AI"
            />
            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={handleAddCustom}
              disabled={!newProviderId.trim()}
            >
              Add
            </Button>
          </Stack>

          <Divider />

          {/* Provider Config */}
          {isBrowserOnly ? (
            <Alert severity="info">
              Puter AI runs directly in your browser. No configuration needed.
            </Alert>
          ) : (
            <Stack spacing={2}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>
                  {activeProvider.label || localConfig.activeProvider}
                </Typography>
                {!isBuiltIn && (
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => handleDeleteProvider(localConfig.activeProvider)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                )}
              </Stack>

              <TextField
                label="Base URL"
                size="small"
                value={activeProvider.base_url || ''}
                onChange={(e) => updateProvider('base_url', e.target.value)}
                fullWidth
                placeholder="http://localhost:1234/v1"
              />

              <TextField
                label="API Key"
                size="small"
                type="password"
                value={activeProvider.api_key || ''}
                onChange={(e) => updateProvider('api_key', e.target.value)}
                fullWidth
                placeholder="Enter API key"
              />

              <Stack direction="row" spacing={1} alignItems="flex-end">
                <TextField
                  label="Model"
                  size="small"
                  value={activeProvider.model || ''}
                  onChange={(e) => updateProvider('model', e.target.value)}
                  fullWidth
                  placeholder="e.g. gpt-4, llama-3"
                  select={models.length > 0}
                >
                  {models.map(m => (
                    <MenuItem key={m.id} value={m.id}>{m.name || m.id}</MenuItem>
                  ))}
                </TextField>
                <Button
                  size="small"
                  startIcon={loadingModels ? <CircularProgress size={14} /> : <RefreshIcon />}
                  onClick={handleFetchModels}
                  disabled={loadingModels || !activeProvider.base_url}
                  sx={{ whiteSpace: 'nowrap' }}
                >
                  Fetch
                </Button>
              </Stack>

              <FormControlLabel
                control={
                  <Checkbox
                    checked={activeProvider.supports_thinking === true}
                    onChange={(e) => updateProvider('supports_thinking', e.target.checked)}
                  />
                }
                label="Enable Thinking / Reasoning Mode"
              />
            </Stack>
          )}

          {/* Test Connection */}
          {testStatus && (
            <Alert
              severity={testStatus.type}
              icon={testStatus.type === 'success' ? <SuccessIcon /> : <ErrorIcon />}
            >
              {testStatus.message}
            </Alert>
          )}
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleTest} disabled={testing} variant="outlined">
          {testing ? 'Testing...' : 'Test Connection'}
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">Save</Button>
      </DialogActions>
    </Dialog>
  );
};

export default LLMSettingsPanel;
