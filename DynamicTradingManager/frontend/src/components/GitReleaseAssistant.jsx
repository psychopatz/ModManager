import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormGroup,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { getGitBranches, getGitChanges, getWorkshopTargets } from '../services/api';

const defaultFilters = {
  feat: true,
  fix: true,
  refactor: false,
  chore: false,
  docs: false,
  other: false,
};

const GitReleaseAssistant = ({
  title = 'Git + AI Release Assistant',
  helperText = 'Generate release notes from git history.',
  outputLabel = 'Generated Output',
  outputValue,
  onOutputChange,
  promptStorageKey,
  defaultPrompt,
  selectedTarget,
  onTargetChange,
  availableTargets,
}) => {
  const [internalTargets, setInternalTargets] = useState([]);
  const [internalTarget, setInternalTarget] = useState('');
  const [branches, setBranches] = useState([]);
  const [branch, setBranch] = useState('develop');
  const [gitChanges, setGitChanges] = useState(null);
  const [filters, setFilters] = useState(defaultFilters);
  const [selectedHashes, setSelectedHashes] = useState(new Set());
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isGenerating, setIsGenerating] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState(() => {
    if (!promptStorageKey) return defaultPrompt || '';
    return localStorage.getItem(promptStorageKey) || defaultPrompt || '';
  });
  const [internalOutput, setInternalOutput] = useState('');

  const targets = availableTargets || internalTargets;
  const activeTarget = selectedTarget != null ? selectedTarget : internalTarget;
  const setActiveTarget = selectedTarget != null && onTargetChange ? onTargetChange : setInternalTarget;
  const output = outputValue != null ? outputValue : internalOutput;
  const setOutput = onOutputChange || setInternalOutput;

  const selectedTargetLabel = useMemo(
    () => targets.find((item) => item.key === activeTarget)?.name || activeTarget,
    [targets, activeTarget],
  );

  const filteredCommits = useMemo(() => {
    if (!gitChanges?.commits) return [];
    return gitChanges.commits.filter((row) => filters[row.type]);
  }, [gitChanges, filters]);

  useEffect(() => {
    if (!promptStorageKey) return;
    localStorage.setItem(promptStorageKey, systemPrompt);
  }, [systemPrompt, promptStorageKey]);

  useEffect(() => {
    if (availableTargets) return;

    const loadTargets = async () => {
      try {
        const response = await getWorkshopTargets();
        const discovered = response.data?.targets || [];
        const fallback = response.data?.default_target || discovered[0]?.key || '';
        setInternalTargets(discovered);
        setInternalTarget((current) => current || fallback);
      } catch (err) {
        setStatus({ type: 'error', message: err.response?.data?.detail || 'Failed to load project targets.' });
      }
    };

    loadTargets();
  }, [availableTargets]);

  useEffect(() => {
    const loadBranches = async () => {
      if (!activeTarget) return;
      try {
        const response = await getGitBranches(activeTarget);
        const available = response.data || [];
        setBranches(available);
        setBranch((current) => {
          if (available.includes(current)) return current;
          if (available.includes('develop')) return 'develop';
          return available[0] || '';
        });
      } catch (err) {
        setStatus({ type: 'error', message: err.response?.data?.detail || 'Failed to load branches.' });
      }
    };

    loadBranches();
  }, [activeTarget]);

  useEffect(() => {
    const loadChanges = async () => {
      if (!activeTarget || !branch) return;
      try {
        const response = await getGitChanges(branch, activeTarget);
        setGitChanges(response.data || null);
        setSelectedHashes(new Set());
      } catch (err) {
        setStatus({ type: 'error', message: err.response?.data?.detail || 'Failed to load git changes.' });
      }
    };

    loadChanges();
  }, [activeTarget, branch]);

  const refreshGit = async () => {
    if (!activeTarget || !branch) return;
    try {
      const response = await getGitChanges(branch, activeTarget);
      setGitChanges(response.data || null);
      setStatus({ type: 'success', message: 'Git data refreshed.' });
    } catch (err) {
      setStatus({ type: 'error', message: err.response?.data?.detail || 'Failed to refresh git changes.' });
    }
  };

  const toggleFilter = (key) => {
    setFilters((current) => ({ ...current, [key]: !current[key] }));
  };

  const toggleCommitSelection = (hash) => {
    setSelectedHashes((current) => {
      const next = new Set(current);
      if (next.has(hash)) next.delete(hash);
      else next.add(hash);
      return next;
    });
  };

  const copySelectedHistory = async () => {
    const rows = selectedHashes.size > 0
      ? filteredCommits.filter((row) => selectedHashes.has(row.hash))
      : filteredCommits;

    const text = `Selected Project History (${selectedTargetLabel || 'Project'} | Branch: ${branch})\n${rows.map((row) => row.raw).join('\n')}`;
    await navigator.clipboard.writeText(text);
    setStatus({ type: 'success', message: `Copied ${rows.length} commit lines.` });
  };

  const handleGenerate = async () => {
    if (!window.puter) {
      setStatus({ type: 'error', message: 'Puter.js is not loaded.' });
      return;
    }

    setIsGenerating(true);
    setStatus({ type: '', message: '' });

    try {
      const selectedRows = selectedHashes.size > 0
        ? filteredCommits.filter((row) => selectedHashes.has(row.hash))
        : filteredCommits;

      const prompt = `Project: ${selectedTargetLabel}\nBranch: ${branch}\n\nUncommitted Status:\n${gitChanges?.status || ''}\n\nDiff Summary:\n${gitChanges?.summary || ''}\n\nDiff Detail:\n${gitChanges?.detail || ''}\n\nSelected Commits:\n${selectedRows.map((row) => row.raw).join('\n')}\n\n${systemPrompt}`;
      const response = await window.puter.ai.chat(prompt);
      setOutput(response?.message?.content?.trim() || '');
      setStatus({ type: 'success', message: 'Generated output from selected git context.' });
    } catch (err) {
      setStatus({ type: 'error', message: err.message || 'Failed to generate output.' });
    } finally {
      setIsGenerating(false);
    }
  };

  const resetPromptRules = () => {
    const fallback = defaultPrompt || '';
    setSystemPrompt(fallback);
    if (promptStorageKey) {
      localStorage.setItem(promptStorageKey, fallback);
    }
    setStatus({ type: 'success', message: 'Prompt rules reset to default.' });
  };

  return (
    <Stack spacing={2}>
      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{title}</Typography>
          <Typography variant="body2" color="text.secondary">{helperText}</Typography>

          {status.message && <Alert severity={status.type || 'info'}>{status.message}</Alert>}

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel id="gra-target-label">Project</InputLabel>
              <Select
                labelId="gra-target-label"
                label="Project"
                value={activeTarget}
                onChange={(e) => setActiveTarget(e.target.value)}
              >
                {targets.map((item) => (
                  <MenuItem key={item.key} value={item.key}>{item.name}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="gra-branch-label">Branch</InputLabel>
              <Select
                labelId="gra-branch-label"
                label="Branch"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
              >
                {branches.map((item) => (
                  <MenuItem key={item} value={item}>{item}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button variant="outlined" onClick={refreshGit}>
              Refresh Git
            </Button>
          </Stack>

          <Paper variant="outlined" sx={{ p: 1.5, maxHeight: 260, overflow: 'auto' }}>
            <FormGroup row sx={{ mb: 1 }}>
              {Object.keys(filters).map((key) => (
                <FormControlLabel
                  key={key}
                  control={<Checkbox size="small" checked={filters[key]} onChange={() => toggleFilter(key)} />}
                  label={key.toUpperCase()}
                />
              ))}
            </FormGroup>

            <Stack spacing={0.5}>
              {filteredCommits.map((row) => (
                <Box key={row.hash} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Checkbox
                    size="small"
                    checked={selectedHashes.has(row.hash)}
                    onChange={() => toggleCommitSelection(row.hash)}
                  />
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{row.raw}</Typography>
                </Box>
              ))}
              {filteredCommits.length === 0 && (
                <Typography variant="body2" color="text.secondary">No commits match active filters.</Typography>
              )}
            </Stack>
          </Paper>

          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={copySelectedHistory} disabled={filteredCommits.length === 0}>
              Copy Selected Git
            </Button>
            <Button variant="outlined" color="error" onClick={() => setSelectedHashes(new Set())} disabled={selectedHashes.size === 0}>
              Clear Selection
            </Button>
          </Stack>

          <TextField
            label="AI Prompt Rules"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            multiline
            minRows={3}
          />

          <Stack direction="row" spacing={1}>
            <Button variant="outlined" color="warning" onClick={resetPromptRules}>
              Reset Prompt Rules
            </Button>
          </Stack>

          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={handleGenerate} disabled={isGenerating || !activeTarget}>
              {isGenerating ? 'Generating...' : 'Generate'}
            </Button>
            <Button variant="outlined" onClick={() => navigator.clipboard.writeText(output || '')} disabled={!output}>
              Copy Output
            </Button>
          </Stack>

          <TextField
            label={outputLabel}
            value={output || ''}
            onChange={(e) => setOutput(e.target.value)}
            multiline
            minRows={6}
          />
        </Stack>
      </Paper>
    </Stack>
  );
};

export default GitReleaseAssistant;
