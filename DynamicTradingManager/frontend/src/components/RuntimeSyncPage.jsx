import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { applyRuntimeRules, getRuntimeDTItems, getRuntimeRules, getRuntimeHeuristics } from '../services/api';

const RuntimeSyncPage = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [applyStatus, setApplyStatus] = useState(null);
  const [applying, setApplying] = useState(false);
  const [search, setSearch] = useState('');
  const [dtItems, setDtItems] = useState({ path: '', text: '', line_count: 0 });
  const [rules, setRules] = useState({ path: '', text: '', blacklist: [], whitelist: [], overrides: [] });
  const [heuristics, setHeuristics] = useState({ path: '', text: '', line_count: 0 });

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      const [dumpRes, rulesRes, heuristicsRes] = await Promise.all([
        getRuntimeDTItems(),
        getRuntimeRules(),
        getRuntimeHeuristics(),
      ]);

      setDtItems(dumpRes.data || { path: '', text: '', line_count: 0 });
      setRules(rulesRes.data || { path: '', text: '', blacklist: [], whitelist: [], overrides: [] });
      setHeuristics(heuristicsRes.data || { path: '', text: '', line_count: 0 });
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load runtime files.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleApplyRuntimeRules = async () => {
    setApplying(true);
    setError('');
    try {
      const res = await applyRuntimeRules();
      const data = res?.data || {};
      setApplyStatus({
        ok: true,
        message: data.message || 'Applied runtime rules file from manager JSON.',
        path: data?.runtime_rules_sync?.path || '',
        counts: {
          blacklist: data.blacklist_count || 0,
          whitelist: data.whitelist_count || 0,
          overrides: data.override_count || 0,
        },
      });
      await refresh();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to apply runtime rules.';
      setApplyStatus({ ok: false, message: detail, path: '', counts: null });
      setError(detail);
    } finally {
      setApplying(false);
    }
  };

  const tabData = useMemo(() => [
    {
      label: `DT_Items (${dtItems.line_count || 0})`,
      path: dtItems.path,
      text: dtItems.text || '',
      tone: { bg: 'hsla(202, 82%, 52%, 0.12)', border: 'hsla(202, 88%, 67%, 0.38)', text: 'hsl(202, 88%, 82%)' },
    },
    {
      label: `Rules (${(rules.blacklist || []).length + (rules.whitelist || []).length + (rules.overrides || []).length})`,
      path: rules.path,
      text: rules.text || '',
      tone: { bg: 'hsla(34, 82%, 52%, 0.12)', border: 'hsla(34, 88%, 67%, 0.38)', text: 'hsl(34, 88%, 82%)' },
    },
    {
      label: `Heuristics Source (${heuristics.line_count || 0})`,
      path: heuristics.path,
      text: heuristics.text || '',
      tone: { bg: 'hsla(126, 72%, 44%, 0.12)', border: 'hsla(126, 78%, 61%, 0.38)', text: 'hsl(126, 82%, 78%)' },
    },
  ], [dtItems, rules, heuristics]);

  const current = tabData[activeTab] || tabData[0];
  const filteredText = useMemo(() => {
    const raw = current?.text || '';
    const query = search.trim().toLowerCase();
    if (!query) {
      return raw;
    }
    const lines = raw.split('\n');
    return lines.filter((line) => line.toLowerCase().includes(query)).join('\n');
  }, [current, search]);

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '0.95fr 1.25fr' }, gap: 3 }}>
      <Paper elevation={3} sx={{ p: 3, minHeight: 760, display: 'flex', flexDirection: 'column' }}>
        <Stack spacing={2}>
          <Box>
            <Typography variant="h4" gutterBottom>
              Runtime Sync
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Same visual workflow as Tag Pricing, but focused on runtime data flow: generated DT_Items database, active rules, and heuristics source.
            </Typography>
          </Box>

          {error ? <Alert severity="error">{error}</Alert> : null}
          {applyStatus ? (
            <Alert severity={applyStatus.ok ? 'success' : 'error'}>
              {applyStatus.message}
              {applyStatus.path ? ` (${applyStatus.path})` : ''}
            </Alert>
          ) : null}

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`Generated database lines ${dtItems.line_count || 0}`} variant="outlined" />
            <Chip label={`Blacklisted ${(rules.blacklist || []).length}`} color="error" variant="outlined" />
            <Chip label={`Whitelisted ${(rules.whitelist || []).length}`} color="info" variant="outlined" />
            <Chip label={`Overrides ${(rules.overrides || []).length}`} color="warning" variant="outlined" />
          </Stack>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.2}>
            <Button variant="contained" color="warning" onClick={handleApplyRuntimeRules} disabled={loading || applying}>
              {applying ? 'Applying Manager Rules...' : 'Apply Existing JSON To In-Game Rules'}
            </Button>
            <Button variant="outlined" onClick={refresh} disabled={loading || applying}>
            {loading ? 'Refreshing Runtime Files...' : 'Refresh Runtime Files'}
            </Button>
          </Stack>

          <Paper sx={{ p: 1, bgcolor: 'rgba(255,255,255,0.03)' }}>
            <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)} variant="scrollable" scrollButtons="auto">
              {tabData.map((tab) => (
                <Tab key={tab.label} label={tab.label} />
              ))}
            </Tabs>
          </Paper>

          <TextField
            label="Filter current pane lines"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="type tag, item id, or field"
          />
        </Stack>

        <Box sx={{ mt: 2, flexGrow: 1, borderRadius: 2, overflow: 'hidden', bgcolor: 'rgba(255,255,255,0.03)', p: 2 }}>
          <Typography variant="caption" color="text.secondary">
            {current?.path || 'No path resolved'}
          </Typography>
          <Divider sx={{ my: 1.2 }} />
          {loading ? (
            <Box sx={{ height: '100%', minHeight: 320, display: 'grid', placeItems: 'center' }}>
              <CircularProgress size={28} />
            </Box>
          ) : (
            <TextField
              multiline
              minRows={26}
              maxRows={26}
              value={filteredText}
              fullWidth
              InputProps={{ readOnly: true }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: current?.tone?.bg,
                  borderColor: current?.tone?.border,
                },
                '& .MuiInputBase-input': {
                  fontFamily: 'Consolas, Monaco, monospace',
                  fontSize: '0.78rem',
                  lineHeight: 1.35,
                  color: current?.tone?.text,
                },
              }}
            />
          )}
        </Box>
      </Paper>

      <Stack spacing={3}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>Runtime Rules Summary</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Blacklist, whitelist, and item overrides are now synchronized through one shared rules dataset.
          </Typography>

          <Stack spacing={1}>
            <Box sx={{ p: 1.2, borderRadius: 2, bgcolor: 'hsla(0, 80%, 54%, 0.12)', border: '1px solid hsla(0, 80%, 68%, 0.3)' }}>
              <Typography variant="subtitle2" color="error.light">Blacklist</Typography>
              <Typography variant="body2" color="text.secondary">{(rules.blacklist || []).length} entries</Typography>
            </Box>
            <Box sx={{ p: 1.2, borderRadius: 2, bgcolor: 'hsla(202, 82%, 52%, 0.12)', border: '1px solid hsla(202, 82%, 68%, 0.3)' }}>
              <Typography variant="subtitle2" color="info.light">Whitelist</Typography>
              <Typography variant="body2" color="text.secondary">{(rules.whitelist || []).length} entries</Typography>
            </Box>
            <Box sx={{ p: 1.2, borderRadius: 2, bgcolor: 'hsla(34, 82%, 52%, 0.12)', border: '1px solid hsla(34, 82%, 68%, 0.3)' }}>
              <Typography variant="subtitle2" color="warning.light">Overrides</Typography>
              <Typography variant="body2" color="text.secondary">{(rules.overrides || []).length} entries</Typography>
            </Box>
          </Stack>

          {applyStatus?.counts ? (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
              Last Apply Snapshot: BL {applyStatus.counts.blacklist} | WL {applyStatus.counts.whitelist} | OV {applyStatus.counts.overrides}
            </Typography>
          ) : null}
        </Paper>

        <Paper elevation={3} sx={{ p: 3, minHeight: 240 }}>
          <Typography variant="h6" gutterBottom>Runtime Source</Typography>
          <Typography variant="body2" color="text.secondary">
            Tag Pricing now resolves against the generated DT_Items database data instead of manual vanilla item parsing, so preview/counters reflect actual item coverage logic.
          </Typography>
        </Paper>
      </Stack>
    </Box>
  );
};

export default RuntimeSyncPage;
