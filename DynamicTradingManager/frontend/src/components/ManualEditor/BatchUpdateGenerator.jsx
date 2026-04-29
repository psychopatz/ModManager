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
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress
} from '@mui/material';
import { 
  ExpandMore as ExpandMoreIcon, 
  ExpandLess as ExpandLessIcon, 
  RestartAlt as ResetIcon,
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  AutoAwesome as AiStatusIcon,
  HourglassEmpty as PendingIcon,
  Terminal as ConsoleIcon,
  SkipNext as SkipNextIcon,
  PauseCircle as PauseIcon,
  PlayCircle as PlayIcon,
  Refresh as RefreshIcon,
  DeleteForever as DiscardIcon
} from '@mui/icons-material';
import { getBatchedGitHistory } from '../../services/api';
import { useGitAi } from '../../hooks/useGitAi';
import { useBatchSystem } from '../../context/BatchContext';
import { useLLM } from '../../hooks/useLLM';

const BatchUpdateGenerator = ({ open, onClose, onComplete, branch = 'develop', module = '', targets = [], modules = [], attachedBatchId = null }) => {
  const { batches, spawnBatch, openBatchId, closeFullView, removeBatch, skipBatchItem, pauseBatch, resumeBatch, restartBatch, retryDay } = useBatchSystem();
  const { activeProvider } = useLLM();
  
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
  
  const [showConsole, setShowConsole] = useState(false);
  const [confirmData, setConfirmData] = useState(null); // { title, message, onConfirm }
  const [autoScroll, setAutoScroll] = useState(true);
  
  const logEndRef = useRef(null);
  const listScrollRef = useRef(null);

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
1. Use '### Heading' for feature names (Keep headings concise but descriptive).
2. Use '- Bullet' for changes (Gameplay impact focused).
3. Use '> [!tone] Title | Body' for Callouts. Tones: info, success, warning, danger.
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

  useEffect(() => {
    if (autoScroll && attachedBatch?.currentStep && listScrollRef.current) {
        // Find the processing item
        const processingEl = listScrollRef.current.querySelector('.batch-item-processing');
        if (processingEl) {
            processingEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }
  }, [attachedBatch?.currentStep, attachedBatch?.streamingData, autoScroll]);

  const getDayList = (s, u) => {
    const dates = [];
    let curr = new Date(s);
    const end = new Date(u);
    while (curr <= end) {
      dates.push(curr.toISOString().split('T')[0]);
      curr.setDate(curr.getDate() + 1);
    }
    return dates.sort().reverse();
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


  const confirm = (title, message, onConfirm) => {
    setConfirmData({ title, message, onConfirm });
  };

  const handleDiscard = () => {
    confirm(
        "Discard Batch Task?",
        "This will permanently stop the process and remove all current progress data. You cannot undo this.",
        () => {
            removeBatch(attachedBatch.id);
            if (isAttached) closeFullView();
            else onClose?.();
        }
    );
  };

  const handleRestart = () => {
    confirm(
        "Restart Batch?",
        "This will clear all currently generated pages and logs for this batch and start over. Are you sure?",
        () => restartBatch(attachedBatch.id)
    );
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
        <Stack direction="row" spacing={1} alignItems="center">
            {isAttached && (
                <>
                    {attachedBatch.status === 'processing' && (
                        <Button 
                            size="small" 
                            color={attachedBatch.paused ? "success" : "warning"}
                            variant="outlined"
                            startIcon={attachedBatch.paused ? <PlayIcon /> : <PauseIcon />}
                            onClick={() => attachedBatch.paused ? resumeBatch(attachedBatch.id) : pauseBatch(attachedBatch.id)}
                            sx={{ fontSize: '0.65rem', height: 24 }}
                        >
                            {attachedBatch.paused ? 'Resume' : 'Pause'}
                        </Button>
                    )}
                    <Button 
                        size="small" 
                        color="inherit"
                        variant="outlined"
                        startIcon={<RefreshIcon />}
                        onClick={handleRestart}
                        sx={{ fontSize: '0.65rem', height: 24, opacity: 0.7 }}
                    >
                        Restart
                    </Button>
                    <Button 
                        size="small" 
                        color="error"
                        variant="outlined"
                        startIcon={<DiscardIcon />}
                        onClick={handleDiscard}
                        sx={{ fontSize: '0.65rem', height: 24 }}
                    >
                        Discard
                    </Button>
                </>
            )}
            <IconButton onClick={handleClose} size="small" sx={{ ml: 1 }}>
                <CloseIcon />
            </IconButton>
        </Stack>
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

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'primary.main', display: 'flex', alignItems: 'center', gap: 1 }}>
                            <AiStatusIcon sx={{ fontSize: 18 }} /> AI GENERATIONS
                        </Typography>
                        <FormControlLabel
                            control={<Checkbox size="small" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />}
                            label={<Typography variant="caption">Auto-scroll</Typography>}
                            sx={{ ml: 1 }}
                        />
                    </Stack>
                    <Button 
                        size="small" 
                        startIcon={<ConsoleIcon />} 
                        onClick={() => setShowConsole(!showConsole)}
                        sx={{ fontSize: '0.65rem', textTransform: 'none' }}
                    >
                        {showConsole ? 'Hide Console' : 'Show Console'}
                    </Button>
                </Box>

                <Collapse in={showConsole}>
                    <Box sx={{ 
                        bgcolor: '#0d1117', 
                        borderRadius: 2, 
                        p: 2, 
                        height: 200, 
                        overflowY: 'auto',
                        border: '1px solid rgba(255,255,255,0.1)',
                        display: 'flex',
                        flexDirection: 'column',
                        mb: 2
                    }}>
                        <Stack spacing={0.5}>
                            {attachedBatch.logs.map((log, i) => {
                                const type = log[1];
                                let color = '#c9d1d9';
                                const typeMap = {
                                    'success': '#3fb950', 'error': '#f85149', 'warning': '#d29922', 'system': '#58a6ff',
                                    'feat': '#3b82f6', 'fix': '#ef4444', 'refactor': '#f59e0b', 'perf': '#8b5cf6',
                                    'docs': '#10b981', 'chore': '#6b7280', 'style': '#ec4899', 'test': '#6366f1'
                                };
                                if (typeMap[type]) color = typeMap[type];
                                return (
                                    <Typography key={i} variant="caption" sx={{ fontFamily: 'monospace', color, fontSize: '0.7rem' }}>
                                        <span style={{ opacity: 0.4, marginRight: 8 }}>[{log[0]}]</span>
                                        {log[2]}
                                    </Typography>
                                );
                            })}
                            <div ref={logEndRef} />
                        </Stack>
                    </Box>
                </Collapse>

                <Box 
                    ref={listScrollRef}
                    sx={{ 
                        flexGrow: 1, 
                        overflowY: 'auto', 
                        maxHeight: showConsole ? 300 : 500,
                        pr: 1,
                        position: 'relative',
                        '&::-webkit-scrollbar': { width: '4px' },
                        '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.1)', borderRadius: '10px' }
                    }}
                >
                    <Stack spacing={1}>
                        {(attachedBatch.config?.since ? 
                            getDayList(attachedBatch.config.since, attachedBatch.config.until)
                            : attachedBatch.pages.map(p => p.title).reverse()
                        ).map(date => {
                            const page = attachedBatch.pages.find(p => p.title === date);
                            const stream = attachedBatch.streamingData?.[date];
                            const isProcessing = attachedBatch.currentStep.includes(date) || (stream?.status === 'streaming');
                            const isCompleted = !!page || stream?.status === 'completed';
                            
                            return (
                                <Accordion 
                                    key={date}
                                    className={isProcessing ? 'batch-item-processing' : ''}
                                    sx={{ 
                                        bgcolor: isProcessing ? 'rgba(30, 41, 59, 1)' : 'rgba(255,255,255,0.02)',
                                        border: '1px solid',
                                        borderColor: isProcessing ? 'primary.main' : 'rgba(255,255,255,0.05)',
                                        borderRadius: '8px !important',
                                        mb: 1,
                                        position: isProcessing ? 'sticky' : 'relative',
                                        top: isProcessing ? 0 : 'auto',
                                        zIndex: isProcessing ? 10 : 1,
                                        '&:before': { display: 'none' }
                                    }}
                                    defaultExpanded={isProcessing}
                                >
                                    <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: 16 }} />}>
                                        <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%', pr: 2 }}>
                                            {isCompleted ? <SuccessIcon sx={{ color: 'success.main', fontSize: 16 }} /> : 
                                             isProcessing ? <CircularProgress size={14} thickness={6} /> : 
                                             <PendingIcon sx={{ color: 'text.disabled', fontSize: 16 }} />}
                                            <Typography variant="body2" sx={{ fontWeight: 800, flexGrow: 1 }}>{date}</Typography>
                                            {isProcessing && (
                                                <Stack direction="row" alignItems="center" spacing={0.5}>
                                                    <Chip label="PROCESSING" color="primary" size="small" sx={{ height: 16, fontSize: '0.6rem' }} />
                                                    <IconButton 
                                                        size="small" 
                                                        color="primary" 
                                                        title="Force Restart AI"
                                                        onClick={(e) => { e.stopPropagation(); retryDay(attachedBatch.id, date); }}
                                                        sx={{ p: 0.5, bgcolor: 'rgba(59, 130, 246, 0.1)', '&:hover': { bgcolor: 'rgba(59, 130, 246, 0.2)' } }}
                                                    >
                                                        <RefreshIcon sx={{ fontSize: '1rem' }} />
                                                    </IconButton>
                                                    <IconButton 
                                                        size="small" 
                                                        color="warning" 
                                                        title="Skip AI & Use Raw Commits"
                                                        onClick={(e) => { e.stopPropagation(); skipBatchItem(attachedBatch.id); }}
                                                        sx={{ p: 0.5, bgcolor: 'rgba(237, 108, 2, 0.1)', '&:hover': { bgcolor: 'rgba(237, 108, 2, 0.2)' } }}
                                                    >
                                                        <SkipNextIcon sx={{ fontSize: '1rem' }} />
                                                    </IconButton>
                                                </Stack>
                                            )}
                                            {isCompleted && (
                                                <Stack direction="row" spacing={1}>
                                                    <Chip label="READY" variant="outlined" color="success" size="small" sx={{ height: 16, fontSize: '0.6rem' }} />
                                                    <IconButton 
                                                        size="small" 
                                                        color="primary" 
                                                        title="Retry AI Refinement"
                                                        onClick={(e) => { e.stopPropagation(); retryDay(attachedBatch.id, date); }}
                                                        sx={{ p: 0.5, bgcolor: 'rgba(59, 130, 246, 0.1)', '&:hover': { bgcolor: 'rgba(59, 130, 246, 0.2)' } }}
                                                    >
                                                        <RefreshIcon sx={{ fontSize: '1rem' }} />
                                                    </IconButton>
                                                </Stack>
                                            )}
                                        </Stack>
                                    </AccordionSummary>
                                    <AccordionDetails sx={{ pt: 0 }}>
                                        {stream?.thinking && (
                                            <Box sx={{ 
                                                mb: 2, p: 1.5, borderRadius: 2, bgcolor: 'rgba(0,0,0,0.3)', 
                                                borderLeft: '3px solid #666', fontSize: '0.75rem', color: 'text.secondary',
                                                fontFamily: 'monospace', whiteSpace: 'pre-wrap'
                                            }}>
                                                <Typography variant="caption" sx={{ fontWeight: 800, display: 'block', mb: 0.5, color: '#aaa' }}>REASONING</Typography>
                                                {stream.thinking}
                                            </Box>
                                        )}
                                        <Box sx={{ 
                                            p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.03)',
                                            fontSize: '0.8rem', lineHeight: 1.6, color: 'text.primary',
                                            maxHeight: 400, overflowY: 'auto'
                                        }}>
                                            {stream?.content ? (
                                                <Typography variant="body2" sx={{ fontFamily: 'serif', whiteSpace: 'pre-wrap' }}>
                                                    {stream.content}
                                                </Typography>
                                            ) : page ? (
                                                <Stack spacing={1.5}>
                                                    {page.blocks.map((block, bi) => {
                                                        if (block.type === 'heading') return <Typography key={bi} variant={block.level === 1 ? 'h6' : 'subtitle2'} sx={{ fontWeight: 800, mt: 1 }}>{block.text}</Typography>;
                                                        if (block.type === 'bullet_list') return (
                                                            <ul key={bi} style={{ margin: 0, paddingLeft: 20 }}>
                                                                {block.items.map((it, ii) => <li key={ii}><Typography variant="body2">{it}</Typography></li>)}
                                                            </ul>
                                                        );
                                                        if (block.type === 'callout') return (
                                                            <Box key={bi} sx={{ p: 1, borderRadius: 1, bgcolor: 'rgba(255,255,255,0.05)', borderLeft: '3px solid', borderColor: 'primary.main' }}>
                                                                <Typography variant="caption" sx={{ fontWeight: 800, display: 'block' }}>{block.title}</Typography>
                                                                <Typography variant="body2" sx={{ opacity: 0.8 }}>{block.text}</Typography>
                                                            </Box>
                                                        );
                                                        return <Typography key={bi} variant="body2">{block.text}</Typography>;
                                                    })}
                                                </Stack>
                                            ) : (
                                                <Typography variant="body2" sx={{ opacity: 0.5, fontStyle: 'italic' }}>
                                                    {isProcessing ? 'Streaming AI refinement...' : 'Waiting to process...'}
                                                </Typography>
                                            )}
                                        </Box>
                                    </AccordionDetails>
                                </Accordion>
                            );
                        })}
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
                        label="Batch improve commits using AI"
                    />
                    
                    {improveWithAI && (
                        <Box sx={{ ml: 4, mt: -1, mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="caption" color="text.secondary">using</Typography>
                            <Chip 
                                label={activeProvider.label || activeProvider.id} 
                                size="small" 
                                color="primary" 
                                variant="outlined"
                                sx={{ height: 20, fontSize: '0.7rem', fontWeight: 800 }}
                            />
                            {activeProvider.model && (
                                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                                    ({activeProvider.model})
                                </Typography>
                            )}
                        </Box>
                    )}
                    
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
                <Typography variant="caption" sx={{ flexGrow: 1, ml: 2, opacity: 0.5 }}>
                    ID: {attachedBatch.id}
                </Typography>
                {attachedBatch.status === 'success' && (
                    <Button onClick={handleClose} variant="contained" color="success">Finish & Close</Button>
                )}
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

      {/* Confirmation Modal */}
      <Dialog open={!!confirmData} onClose={() => setConfirmData(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{confirmData?.title}</DialogTitle>
        <DialogContent>
            <Typography variant="body2">{confirmData?.message}</Typography>
        </DialogContent>
        <DialogActions>
            <Button onClick={() => setConfirmData(null)}>Cancel</Button>
            <Button 
                variant="contained" 
                color={confirmData?.title?.includes('Discard') ? "error" : "primary"}
                onClick={() => {
                    confirmData?.onConfirm();
                    setConfirmData(null);
                }}
            >
                Confirm
            </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};

export default BatchUpdateGenerator;
