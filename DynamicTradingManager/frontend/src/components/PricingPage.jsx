import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { getPricingAudit, getPricingConfig, previewPricing, savePricingConfig } from '../services/api';

const prettyValue = (value) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return String(value ?? '');
  return num.toFixed(Math.abs(num) >= 10 ? 1 : 3).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
};

const PricingPage = () => {
  const [configText, setConfigText] = useState('');
  const [status, setStatus] = useState({ type: '', message: '' });
  const [previewItemId, setPreviewItemId] = useState('Bandage');
  const [previewData, setPreviewData] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const loadConfig = async () => {
    setLoadingConfig(true);
    setStatus({ type: '', message: '' });
    try {
      const res = await getPricingConfig();
      setConfigText(JSON.stringify(res.data, null, 2));
    } catch (err) {
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to load pricing config.' });
    } finally {
      setLoadingConfig(false);
    }
  };

  useEffect(() => {
    loadConfig();
    loadAudit();
  }, []);

  const loadAudit = async () => {
    setLoadingAudit(true);
    try {
      const res = await getPricingAudit({ limit: 15 });
      setAuditData(res.data);
    } catch (err) {
      setStatus((current) => ({
        ...current,
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to load pricing audit.',
      }));
    } finally {
      setLoadingAudit(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setStatus({ type: '', message: '' });
    try {
      const parsed = JSON.parse(configText);
      const res = await savePricingConfig(parsed);
      setConfigText(JSON.stringify(res.data, null, 2));
      setStatus({ type: 'success', message: 'Pricing config saved. New previews will use it immediately.' });
      loadAudit();
    } catch (err) {
      const message = err instanceof SyntaxError
        ? err.message
        : err?.response?.data?.detail || 'Failed to save pricing config.';
      setStatus({ type: 'error', message });
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    if (!previewItemId.trim()) return;
    setPreviewing(true);
    setStatus({ type: '', message: '' });
    try {
      const res = await previewPricing({ item_id: previewItemId.trim() });
      setPreviewData(res.data);
    } catch (err) {
      setPreviewData(null);
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to preview item pricing.' });
    } finally {
      setPreviewing(false);
    }
  };

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1.3fr 0.9fr' }, gap: 3 }}>
      <Paper elevation={3} sx={{ p: 3, minHeight: 700 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              Pricing Model
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Runtime-editable config for category heuristics, multipliers, and clamps.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={() => { loadConfig(); loadAudit(); }} disabled={loadingConfig || saving}>
              Reload
            </Button>
            <Button variant="contained" onClick={handleSave} disabled={loadingConfig || saving}>
              {saving ? 'Saving...' : 'Save Config'}
            </Button>
          </Stack>
        </Stack>

        {status.message ? (
          <Alert severity={status.type || 'info'} sx={{ mb: 2 }}>
            {status.message}
          </Alert>
        ) : null}

        <TextField
          fullWidth
          multiline
          minRows={28}
          maxRows={36}
          value={configText}
          onChange={(event) => setConfigText(event.target.value)}
          disabled={loadingConfig}
          placeholder={loadingConfig ? 'Loading pricing config...' : 'Pricing config JSON'}
          InputProps={{
            sx: {
              fontFamily: 'monospace',
              alignItems: 'flex-start',
            },
          }}
        />
      </Paper>

      <Stack spacing={3}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Preview
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Inspect how the current config prices a vanilla item.
          </Typography>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <TextField
              fullWidth
              label="Item ID"
              value={previewItemId}
              onChange={(event) => setPreviewItemId(event.target.value)}
              placeholder="Bandage"
            />
            <Button variant="contained" onClick={handlePreview} disabled={previewing}>
              {previewing ? 'Checking...' : 'Preview'}
            </Button>
          </Stack>
        </Paper>

        <Paper elevation={3} sx={{ p: 3, minHeight: 420 }}>
          {previewData ? (
            <Stack spacing={2}>
              <Box>
                <Typography variant="h5">{previewData.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {previewData.item_id}
                </Typography>
              </Box>

              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {(previewData.tags || []).map((tag) => (
                  <Chip key={tag} label={tag} size="small" variant="outlined" />
                ))}
              </Stack>

              <Box>
                <Typography variant="overline" color="text.secondary">Final Price</Typography>
                <Typography variant="h3">${previewData.price}</Typography>
                {previewData.details?.global_price_clamped && previewData.details?.global_price_clamp === 'max' ? (
                  <Typography variant="body2" color="warning.main">
                    Uncapped result was ${prettyValue(previewData.details.pre_global_clamp_price)} but the global {previewData.details.global_price_clamp} price clamp forced it to ${previewData.price}.
                  </Typography>
                ) : null}
                <Typography variant="body2" color="text.secondary">
                  Category: {previewData.details?.category || 'Unknown'}
                </Typography>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle1" gutterBottom>Heuristic Components</Typography>
                <Stack spacing={1}>
                  {(previewData.details?.components || []).map((component, index) => (
                    <Box key={`${component.label}-${index}`} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                      <Typography variant="body2">{component.label}</Typography>
                      <Typography variant="body2" color="text.secondary">{prettyValue(component.value)}</Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle1" gutterBottom>Applied Multipliers</Typography>
                <Stack spacing={1}>
                  {(previewData.details?.adjustments || []).length ? (
                    (previewData.details.adjustments || []).map((component, index) => (
                      <Box key={`${component.label}-${index}`} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                        <Typography variant="body2">{component.label}</Typography>
                        <Typography variant="body2" color="text.secondary">{prettyValue(component.value)}</Typography>
                      </Box>
                    ))
                  ) : (
                    <Typography variant="body2" color="text.secondary">No extra multipliers applied.</Typography>
                  )}
                </Stack>
              </Box>
            </Stack>
          ) : (
            <Typography color="text.secondary">
              Run a preview to inspect the current pricing breakdown.
            </Typography>
          )}
        </Paper>

        <Paper elevation={3} sx={{ p: 3, minHeight: 420 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Box>
              <Typography variant="h5">Audit</Typography>
              <Typography variant="body2" color="text.secondary">
                Anchor baskets and current high-price outliers from the live pricing config.
              </Typography>
            </Box>
            <Button variant="outlined" onClick={loadAudit} disabled={loadingAudit}>
              {loadingAudit ? 'Refreshing...' : 'Refresh Audit'}
            </Button>
          </Stack>

          {auditData ? (
            <Stack spacing={2.5}>
              <Box>
                <Typography variant="subtitle1" gutterBottom>Anchor Baskets</Typography>
                <Stack spacing={1.25}>
                  {Object.entries(auditData.anchors || {}).map(([label, rows]) => (
                    <Box key={label}>
                      <Typography variant="body2" sx={{ fontWeight: 700, mb: 0.5 }}>{label}</Typography>
                      <Stack spacing={0.5}>
                        {(rows || []).map((row) => (
                          <Box key={row.item_id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                            <Typography variant="body2">{row.name}</Typography>
                            <Typography variant="body2" color="text.secondary">{row.price}</Typography>
                          </Box>
                        ))}
                      </Stack>
                    </Box>
                  ))}
                </Stack>
              </Box>

              <Divider />

              <Box>
                <Typography variant="subtitle1" gutterBottom>Top Outliers</Typography>
                <Stack spacing={0.75}>
                  {(auditData.outliers || []).map((row) => (
                    <Box key={row.item_id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                      <Box>
                        <Typography variant="body2">{row.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{row.category}</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">{row.price}</Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            </Stack>
          ) : (
            <Typography color="text.secondary">
              Load the audit to inspect anchor prices and current outliers.
            </Typography>
          )}
        </Paper>
      </Stack>
    </Box>
  );
};

export default PricingPage;
