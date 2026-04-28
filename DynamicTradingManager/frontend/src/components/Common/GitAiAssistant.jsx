import React, { useState, useEffect, useMemo } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormGroup,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  AutoAwesome as AiIcon,
  ContentCopy as CopyIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material';
import { getGitChanges, getSuiteGitLog, getGitBranches, getSuiteBranches } from '../../services/api';
import { useGitAi } from '../../hooks/useGitAi';

/**
 * GitAiAssistant
 * Modular component for git history selection and AI generation.
 */
const GitAiAssistant = ({
  title = 'Git + AI Assistant',
  helperText = 'Select changes to generate release notes.',
  defaultPrompt = '',
  storageKey = 'git_ai_assistant',
  onOutputChange,
  outputValue = '',
  selectedTarget = '',
  availableTargets = [],
  onTargetChange,
  suiteMode: initialSuiteMode = false,
  showSuiteToggle = true,
  onLatestHash,
}) => {
  const [suiteMode, setSuiteMode] = useState(initialSuiteMode);
  const [branch, setBranch] = useState('develop');

  useEffect(() => {
    if (suiteMode) {
      if (branch !== 'develop' && branch !== 'main') {
        setBranch('develop');
      }
    }
  }, [suiteMode]); // eslint-disable-line react-hooks/exhaustive-deps
  const [branches, setBranches] = useState(['develop', 'main']);
  const [commits, setCommits] = useState([]);
  const [suiteHistory, setSuiteHistory] = useState(null);
  const [selectedHashes, setSelectedHashes] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [sinceDate, setSinceDate] = useState('');
  
  const filterStorageKey = storageKey ? `${storageKey}_type_filters` : null;
  const [typeFilters, setTypeFilters] = useState(() => {
    const saved = filterStorageKey ? localStorage.getItem(filterStorageKey) : null;
    return saved ? JSON.parse(saved) : ['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test', 'other'];
  });

  useEffect(() => {
    if (filterStorageKey) {
      localStorage.setItem(filterStorageKey, JSON.stringify(typeFilters));
    }
  }, [typeFilters, filterStorageKey]);
  
  // Storage key for the last published commit hash for this specific target/context
  const lastHashKey = storageKey ? `${storageKey}_last_hash` : null;
  const [lastHash, setLastHash] = useState(() => lastHashKey ? localStorage.getItem(lastHashKey) : '');

  const { systemPrompt, setSystemPrompt, resetPrompt, generateContent } = useGitAi({
    storageKey,
    defaultPrompt,
  });

  const selectedTargetInfo = useMemo(
    () => availableTargets.find(t => t.key === selectedTarget) || null,
    [availableTargets, selectedTarget]
  );

  const activeTargetName = useMemo(() => {
    if (suiteMode) return 'Full Suite';
    return selectedTargetInfo?.name || selectedTarget;
  }, [suiteMode, selectedTargetInfo, selectedTarget]);

  const isGitRepo = suiteMode || selectedTargetInfo?.has_git !== false;
  // If we don't have target info yet, we assume it might have git (loading state)
  const showGitContent = isGitRepo || !selectedTargetInfo;

  // Load branches
  useEffect(() => {
    if (suiteMode) {
      getSuiteBranches()
        .then(res => setBranches(res.data))
        .catch(() => setStatus({ type: 'error', message: 'Failed to load suite branches.' }));
      return;
    }
    const target = selectedTarget || (availableTargets[0]?.key);
    if (!target) return;
    getGitBranches(target)
      .then(res => setBranches(res.data))
      .catch(() => setStatus({ type: 'error', message: 'Failed to load branches.' }));
  }, [selectedTarget, availableTargets, suiteMode]);

  // Load commits
  const fetchHistory = async () => {
    if (!showGitContent) {
        setCommits([]);
        setSuiteHistory(null);
        return;
    }
    setLoading(true);
    setStatus({ type: '', message: '' });
    try {
      if (suiteMode) {
        const res = await getSuiteGitLog(branch);
        setSuiteHistory(res.data);
        setCommits([]); // We use suiteHistory in suite mode
      } else {
        const res = await getGitChanges(branch, selectedTarget, sinceDate);
        if (res.data.error) {
          throw new Error(res.data.error);
        }
        setCommits(res.data.commits || []);
        setSuiteHistory(null);
      }
      setSelectedHashes(new Set());
      if (!suiteMode && res.data.commits?.length > 0 && onLatestHash) {
        onLatestHash(res.data.commits[0].hash);
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to load git history.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [selectedTarget, branch, suiteMode, sinceDate]);

  // Update lastHash when localStorage changes (optional but good for consistency)
  useEffect(() => {
    if (lastHashKey) {
        const h = localStorage.getItem(lastHashKey);
        if (h) setLastHash(h);
    }
  }, [lastHashKey, outputValue]); // Re-check when output changes to see if parent saved it

  const parseCommitType = (subject) => {
    if (!subject || typeof subject !== 'string') return 'other';
    const match = subject.match(/^(\w+)(\(.*\))?:/);
    return match ? match[1].toLowerCase() : 'other';
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'feat': return '#3b82f6';
      case 'fix': return '#ef4444';
      case 'refactor': return '#f59e0b';
      case 'perf': return '#8b5cf6';
      case 'docs': return '#10b981';
      case 'chore': return '#6b7280';
      case 'style': return '#ec4899';
      case 'test': return '#6366f1';
      default: return '#9ca3af';
    }
  };

  const filteredCommits = useMemo(() => {
    if (suiteMode) {
        // Flatten suiteHistory for simplified filtering if needed elsewhere, 
        // but currently we use it as a map in the render block.
        return []; 
    }
    return commits.filter(c => {
      const subject = c.subject || c.message || '';
      const type = parseCommitType(subject);
      return typeFilters.includes(type) || (typeFilters.includes('other') && !['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test'].includes(type));
    });
  }, [commits, suiteMode, typeFilters]);

  const toggleTypeFilter = (type) => {
    setTypeFilters(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
  };

  const toggleCommitSelection = (hash) => {
    setSelectedHashes(prev => {
      const next = new Set(prev);
      if (next.has(hash)) next.delete(hash);
      else next.add(hash);
      return next;
    });
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setStatus({ type: '', message: '' });
    try {
      const selectedList = suiteMode 
        ? suiteHistory 
        : filteredCommits.filter(c => selectedHashes.size === 0 || selectedHashes.has(c.hash));

      let customInstructions = '';
      if (selectedTargetInfo?.sub_mods?.length > 1) {
        const modNames = selectedTargetInfo.sub_mods.map(m => m.name).join(', ');
        customInstructions = `NOTE: This repository contains multiple sub-mods: ${modNames}. Please group the changes accordingly if detected in the commit messages or paths.`;
      }

      const result = await generateContent({
        targetName: activeTargetName,
        branch,
        commits: selectedList,
        customInstructions
      });
      onOutputChange(result);
      setStatus({ type: 'success', message: 'Generated notes with smart grouping.' });
    } catch (error) {
      setStatus({ type: 'error', message: error.message || 'Generation failed.' });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Paper sx={{ p: 3, borderRadius: 4, border: '1px solid', borderColor: 'divider' }}>
      <Stack spacing={2.5}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h6" fontWeight={900}>{title}</Typography>
            <Typography variant="body2" color="text.secondary">{helperText}</Typography>
          </Box>
          {status.message && <Alert severity={status.type} sx={{ py: 0 }}>{status.message}</Alert>}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Stack direction="row" spacing={2} alignItems="center">
            {showSuiteToggle && (
              <FormControlLabel
                control={<Checkbox checked={suiteMode} onChange={(e) => setSuiteMode(e.target.checked)} />}
                label={
                  <Tooltip title="When enabled, fetches and summarizes commits from all mod repositories (Trading, Colonies, etc.) simultaneously." arrow>
                    <Typography variant="body2" sx={{ fontWeight: 800 }}>Suite Mode</Typography>
                  </Tooltip>
                }
              />
            )}
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Project</InputLabel>
              <Select 
                value={suiteMode ? 'suite' : selectedTarget} 
                label="Project" 
                onChange={(e) => onTargetChange(e.target.value)}
                disabled={suiteMode}
              >
                {suiteMode ? (
                  <MenuItem value="suite">All Projects (Suite)</MenuItem>
                ) : (
                  availableTargets.map(t => <MenuItem key={t.key} value={t.key}>{t.name}</MenuItem>)
                )}
              </Select>
            </FormControl>

          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Branch</InputLabel>
            <Select 
              value={branches.includes(branch) ? branch : (branches[0] || 'develop')} 
              label="Branch" 
              onChange={(e) => setBranch(e.target.value)}
            >
              {branches.map(b => (
                <MenuItem key={b} value={b}>{b}</MenuItem>
              ))}
              {!branches.includes(branch) && branch && (
                <MenuItem value={branch}>{branch}</MenuItem>
              )}
            </Select>
          </FormControl>

          <IconButton onClick={fetchHistory} disabled={loading} color="primary">
            <RefreshIcon />
          </IconButton>
          
          <TextField
            label="Since"
            type="date"
            size="small"
            value={sinceDate}
            onChange={(e) => setSinceDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 150 }}
            placeholder="yyyy-mm-dd"
          />
        </Stack>
      </Box>

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', px: 1 }}>
        {['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test', 'other'].map(type => (
          <Chip
            key={type}
            label={type.toUpperCase()}
            size="small"
            clickable
            onClick={() => toggleTypeFilter(type)}
            sx={{ 
                fontSize: '0.65rem', 
                height: 20, 
                fontWeight: 800,
                bgcolor: typeFilters.includes(type) ? getTypeColor(type) : 'transparent',
                color: typeFilters.includes(type) ? '#fff' : 'text.secondary',
                border: '1px solid',
                borderColor: typeFilters.includes(type) ? getTypeColor(type) : 'divider',
                '&:hover': {
                    bgcolor: typeFilters.includes(type) ? getTypeColor(type) : 'rgba(0,0,0,0.04)',
                    opacity: 0.9
                }
            }}
          />
        ))}
      </Box>
      
      {lastHash && (
        <Box sx={{ px: 1 }}>
          <Alert 
            severity="info" 
            sx={{ py: 0, '& .MuiAlert-message': { fontSize: '0.75rem', py: 0.5 } }}
            action={
              <Button size="small" onClick={() => setSinceDate('')}>Clear</Button>
            }
          >
            Last update point: <strong>{lastHash.substring(0, 8)}</strong>. Use "Since" date to filter.
          </Alert>
        </Box>
      )}

      <Paper variant="outlined" sx={{ maxHeight: 200, overflow: 'auto', p: 1, bgcolor: 'rgba(0,0,0,0.02)' }}>
          {!showGitContent ? (
            <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body2" color="warning.main" gutterBottom fontWeight={800}>
                    Git Repository Not Found
                </Typography>
                <Typography variant="caption" color="text.secondary">
                    This project is not currently managed with Git. Connect a .git repository to use this assistant.
                </Typography>
            </Box>
          ) : suiteMode ? (
            <Stack spacing={2}>
               {suiteHistory && Object.entries(suiteHistory).map(([repo, list]) => {
                 const repoCommits = list.filter(c => {
                    const subject = c.subject || c.message || '';
                    const type = parseCommitType(subject);
                    return typeFilters.includes(type) || (typeFilters.includes('other') && !['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test'].includes(type));
                 });
                 if (repoCommits.length === 0) return null;
                 return (
                   <Box key={repo}>
                     <Typography variant="caption" sx={{ fontWeight: 900, color: 'primary.main', mb: 0.5, display: 'block', textTransform: 'uppercase' }}>
                       {repo}
                     </Typography>
                     <Stack spacing={0.5}>
                       {repoCommits.map(commit => (
                         <Box key={commit.hash} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Checkbox 
                                size="small" 
                                checked={selectedHashes.has(commit.hash)} 
                                onChange={() => toggleCommitSelection(commit.hash)} 
                                sx={{ p: 0.5 }}
                            />
                            <Box sx={{ width: 4, height: 16, bgcolor: getTypeColor(parseCommitType(commit.subject || commit.message)), borderRadius: 1, flexShrink: 0 }} />
                            <Typography variant="body2" sx={{ fontSize: '0.75rem', fontFamily: 'monospace' }} noWrap>
                                {commit.subject || commit.message}
                            </Typography>
                         </Box>
                       ))}
                     </Stack>
                   </Box>
                 );
               })}
            </Stack>
          ) : (
            <Stack spacing={0.5}>
              {filteredCommits.map(commit => (
                <Box key={commit.hash} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Checkbox 
                    size="small" 
                    checked={selectedHashes.has(commit.hash)} 
                    onChange={() => toggleCommitSelection(commit.hash)} 
                    sx={{ p: 0.5 }}
                  />
                  <Box sx={{ width: 4, height: 16, bgcolor: getTypeColor(parseCommitType(commit.subject || commit.message || '')), borderRadius: 1, flexShrink: 0 }} />
                  <Typography variant="body2" sx={{ fontSize: '0.75rem', fontFamily: 'monospace' }} noWrap>
                    {commit.subject || commit.message}
                  </Typography>
                </Box>
              ))}
              {filteredCommits.length === 0 && !loading && (
                <Typography variant="body2" sx={{ textAlign: 'center', py: 2, color: 'text.secondary', fontStyle: 'italic' }}>
                  No commits match the current filters.
                </Typography>
              )}
            </Stack>
          )}
        </Paper>

        <Stack spacing={1}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" fontWeight={800}>AI SYSTEM PROMPT</Typography>
            <Button size="small" startIcon={<ResetIcon />} onClick={resetPrompt} sx={{ fontSize: '0.65rem' }}>Reset Default</Button>
          </Box>
          <TextField
            fullWidth
            multiline
            rows={3}
            variant="filled"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            sx={{ '& .MuiInputBase-input': { fontSize: '0.85rem' } }}
          />
        </Stack>

        <Stack direction="row" spacing={2}>
          <Button 
            variant="contained" 
            startIcon={<AiIcon />} 
            onClick={handleGenerate} 
            disabled={isGenerating || loading}
            sx={{ flex: 1, fontWeight: 900 }}
          >
            {isGenerating ? 'GENEVATING...' : 'GENERATE WITH AI'}
          </Button>
          <Button 
            variant="outlined" 
            startIcon={<CopyIcon />} 
            onClick={() => navigator.clipboard.writeText(outputValue)}
            disabled={!outputValue}
          >
            Copy
          </Button>
        </Stack>

        <TextField
          label="Generated Output"
          fullWidth
          multiline
          rows={6}
          value={outputValue}
          onChange={(e) => onOutputChange(e.target.value)}
          sx={{ '& .MuiInputBase-input': { fontSize: '0.9rem', fontFamily: 'monospace' } }}
        />
      </Stack>
    </Paper>
  );
};

export default GitAiAssistant;
