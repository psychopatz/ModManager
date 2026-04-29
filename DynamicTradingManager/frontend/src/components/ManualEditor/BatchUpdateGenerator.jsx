import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  TextField,
  Typography,
  Collapse,
  Chip,
  LinearProgress,
  IconButton
} from '@mui/material';
import { 
  ExpandMore as ExpandMoreIcon, 
  ExpandLess as ExpandLessIcon, 
  RestartAlt as ResetIcon,
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { getBatchedGitHistory } from '../../services/api';
import { useGitAi } from '../../hooks/useGitAi';
import { useBatchSystem } from '../../context/BatchContext';

const BatchUpdateGenerator = ({ open, onClose, onComplete, branch = 'develop', module = '', targets = [], modules = [], attachedBatchId = null }) => {
  const { batches, spawnBatch, openBatchId, closeFullView, removeBatch } = useBatchSystem();
  
  // Detached mode detection
  const activeBatchId = attachedBatchId || openBatchId;
  const attachedBatch = useMemo(() => batches.find(b => b.id === activeBatchId), [batches, activeBatchId]);
  const isAttached = !!attachedBatch;

  const [status, setStatus] = useState({ type: '', message: '' });
  const [showPrompt, setShowPrompt] = useState(false);
  const [since, setSince] = useState(() => localStorage.getItem('git_batch_since') || '2026-03-27');
  const [until, setUntil] = useState(new Date().toISOString().split('T')[0]);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [improveWithAI, setImproveWithAI] = useState(() => localStorage.getItem('git_batch_improve_ai') === 'true');
  
  const logEndRef = useRef(null);

  useEffect(() => {
    if (logEndRef.current) {
        logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [attachedBatch?.logs]);

  const moduleOptions = useMemo(() => {
    return modules.map(m => ({ value: m.id, label: m.name, repo: m.project_key }));
  }, [modules]);

  const activeModuleLabel = useMemo(() => {
    if (isAttached) return attachedBatch.modName;
    return moduleOptions.find(o => o.value === module)?.label || module;
  }, [moduleOptions, module, isAttached, attachedBatch]);

  const [typeFilters, setTypeFilters] = useState(() => {
    const saved = localStorage.getItem('git_ai_assistant_type_filters');
    return saved ? JSON.parse(saved) : ['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'other'];
  });

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

  const toggleTypeFilter = (type) => {
    setTypeFilters(prev => {
        const next = prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type];
        localStorage.setItem('git_ai_assistant_type_filters', JSON.stringify(next));
        return next;
    });
  };

  const { systemPrompt, setSystemPrompt, resetPrompt } = useGitAi({
    storageKey: 'batch_update_system_prompt',
    defaultPrompt: `You are a professional Project Zomboid mod developer.
Transform the following daily git commits into polished, feature-grouped patch notes.

FORMAT RULES:
1. Use '### Heading' for feature names (Keep headings concise, max 25 chars).
2. Use '- Bullet' for changes (Gameplay impact focused).
3. Use '> [!tone] Title | Body' for Callouts. Tones: info, success, warning, danger. (Title max 25 chars).
4. Use '![Caption](path)' for images if applicable.
5. CONTEXT GUARD: If the commits are trivial (merge commits, bumps), return exactly: %ContextNotFound%

Return ONLY the Markdown content or the %ContextNotFound% signal.`,
  });

  const fetchHistory = async () => {
    setLoading(true);
    setStatus({ type: '', message: '' });
    try {
      const response = await getBatchedGitHistory(since, branch);
      const allHistory = response.data.history || {};
      const rangeDays = Object.keys(allHistory).filter(d => d >= since && d <= until);
      setHistory(allHistory);
      const dayCount = rangeDays.length;
      setStatus({ 
        type: 'info', 
        message: `Found ${dayCount} days with updates between ${since} and ${until}.` 
      });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to fetch git history.' });
    } finally {
      setLoading(false);
    }
  };

  const startBatch = async () => {
    if (!history || !module) return;
    
    spawnBatch({
        since,
        until,
        module,
        moduleLabel: activeModuleLabel,
        branch,
        improveWithAI,
        typeFilters,
        systemPrompt
    });

    onClose?.();
    onComplete?.();
  };

  const handleClose = () => {
    if (isAttached) {
        closeFullView();
    } else {
        onClose?.();
    }
  };

  const isDialogOpen = isAttached ? !!activeBatchId : open;

  return (
    <Dialog open={isDialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Stack direction="row" spacing={1} alignItems="center">
            <span>{isAttached ? 'Batch Status' : 'Batch Generate Updates'}</span>
            {isAttached && (
                <Chip 
                    label={attachedBatch.status.toUpperCase()} 
                    color={attachedBatch.status === 'success' ? 'success' : attachedBatch.status === 'error' ? 'error' : 'primary'}
                    size="small"
                    sx={{ height: 20, fontSize: '0.65rem', fontWeight: 800 }}
                />
            )}
        </Stack>
        <IconButton onClick={handleClose} size="small">
            <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {isAttached ? 'Monitoring background update for:' : 'Generating daily manuals for:'} <strong style={{ color: '#3b82f6' }}>{activeModuleLabel}</strong>
            </Typography>
          </Box>

          {isAttached ? (
            <Stack spacing={2}>
                 <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 800 }}>{attachedBatch.currentStep}</Typography>
                        <Typography variant="caption">{attachedBatch.progress}%</Typography>
                    </Box>
                    <LinearProgress 
                        variant="determinate" 
                        value={attachedBatch.progress} 
                        sx={{ height: 8, borderRadius: 4 }}
                        color={attachedBatch.status === 'success' ? 'success' : attachedBatch.status === 'error' ? 'error' : 'primary'}
                    />
                </Box>

                <Box sx={{ 
                    bgcolor: '#0d1117', // GitHub dark console color
                    borderRadius: 2, 
                    p: 2, 
                    height: 350, 
                    overflowY: 'auto',
                    border: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex',
                    flexDirection: 'column',
                    boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.5)'
                }}>
                    <Stack spacing={0.5}>
                        {attachedBatch.logs.map((log, i) => {
                            const type = log[1];
                            let color = '#c9d1d9'; // Default GitHub text
                            
                            const typeMap = {
                                'success': '#3fb950',
                                'error': '#f85149',
                                'warning': '#d29922',
                                'system': '#58a6ff',
                                'feat': '#3b82f6',
                                'fix': '#ef4444',
                                'refactor': '#f59e0b',
                                'perf': '#8b5cf6',
                                'docs': '#10b981',
                                'chore': '#6b7280',
                                'style': '#ec4899',
                                'test': '#6366f1'
                            };

                            if (typeMap[type]) color = typeMap[type];

                            return (
                                <Typography key={i} variant="caption" sx={{ 
                                    fontFamily: '"Fira Code", "Roboto Mono", monospace',
                                    color: color,
                                    fontSize: '0.75rem',
                                    lineHeight: 1.4
                                }}>
                                    <span style={{ opacity: 0.4, marginRight: 8 }}>[{log[0]}]</span>
                                    {log[2]}
                                </Typography>
                            );
                        })}
                        <div ref={logEndRef} />
                    </Stack>
                </Box>

                {attachedBatch.status === 'success' && (
                    <Alert severity="success" icon={<SuccessIcon />}>
                        Update successfully generated and saved to the backend. You can now close this monitor.
                    </Alert>
                )}

                {attachedBatch.status === 'error' && (
                    <Alert severity="error" icon={<ErrorIcon />}>
                        {attachedBatch.error}
                    </Alert>
                )}
            </Stack>
          ) : (
            <>
                {status.message && <Alert severity={status.type || 'info'}>{status.message}</Alert>}

                <Stack direction="row" spacing={2} alignItems="center">
                    <TextField
                    label="Since Date"
                    type="date"
                    size="small"
                    value={since}
                    onChange={(e) => {
                        setSince(e.target.value);
                        localStorage.setItem('git_batch_since', e.target.value);
                    }}
                    InputLabelProps={{ shrink: true }}
                    sx={{ flex: 1 }}
                    />
                    <TextField
                    label="Until Date"
                    type="date"
                    size="small"
                    value={until}
                    onChange={(e) => setUntil(e.target.value)}
                    InputLabelProps={{ shrink: true }}
                    sx={{ flex: 1 }}
                    />
                    <Button variant="outlined" onClick={fetchHistory} disabled={loading}>
                    {loading ? 'Fetching...' : 'Check History'}
                    </Button>
                </Stack>

                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
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

                <Stack spacing={1}>
                    <FormControlLabel
                    control={<Checkbox checked={improveWithAI} onChange={(e) => {
                        setImproveWithAI(e.target.checked);
                        localStorage.setItem('git_batch_improve_ai', e.target.checked);
                    }} />}
                    label="Batch improve commits using AI (Puter AI)"
                    />
                    
                    {improveWithAI && (
                    <Box>
                        <Button 
                        size="small" 
                        onClick={() => setShowPrompt(!showPrompt)}
                        startIcon={showPrompt ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        >
                        Edit Batch System Prompt
                        </Button>
                        <Collapse in={showPrompt}>
                        <Stack spacing={1} sx={{ mt: 1, p: 2, bgcolor: 'rgba(0,0,0,0.03)', borderRadius: 2 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="caption" fontWeight={800}>SYSTEM PROMPT</Typography>
                            <Button size="small" startIcon={<ResetIcon />} onClick={resetPrompt} sx={{ fontSize: '0.65rem' }}>Reset</Button>
                            </Box>
                            <TextField
                            fullWidth
                            multiline
                            rows={4}
                            variant="filled"
                            value={systemPrompt}
                            onChange={(e) => setSystemPrompt(e.target.value)}
                            sx={{ '& .MuiInputBase-input': { fontSize: '0.8rem' } }}
                            />
                        </Stack>
                        </Collapse>
                    </Box>
                    )}
                </Stack>
            </>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        {isAttached ? (
            <>
                {attachedBatch.status !== 'processing' && (
                    <Button onClick={() => removeBatch(attachedBatch.id)} color="error">Remove Task</Button>
                )}
                <Button onClick={handleClose} variant="contained">Close Monitor</Button>
            </>
        ) : (
            <>
                <Button onClick={onClose}>Cancel</Button>
                <Button 
                variant="contained" 
                onClick={startBatch} 
                disabled={!history || loading || !module}
                >
                Spawn Background Batch
                </Button>
            </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default BatchUpdateGenerator;
