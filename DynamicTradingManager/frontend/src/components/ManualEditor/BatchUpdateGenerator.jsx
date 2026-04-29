import React, { useState, useMemo, useEffect } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
  IconButton,
  Chip
} from '@mui/material';
import { 
  Close as CloseIcon,
  RestartAlt as RefreshIcon,
  ContentCopy as CopyIcon
} from '@mui/icons-material';
import { getBatchedGitHistory, getSuiteBranches } from '../../services/api';
import { useBatchSystem } from '../../context/BatchContext';
import { useLLM } from '../../hooks/useLLM';

// New Modular Sub-components
import BatchConfigForm from './BatchGenerator/BatchConfigForm';
import BatchProcessMonitor from './BatchGenerator/BatchProcessMonitor';

const BatchUpdateGenerator = ({ open, onClose, onComplete, branch = 'develop', module = '', targets = [], modules = [], attachedBatchId = null }) => {
  const { batches, spawnBatch, openBatchId, closeFullView, retryDay, consolidateBatch, saveBatchVolume } = useBatchSystem();
  
  // State for Configuration
  const [since, setSince] = useState(localStorage.getItem('git_batch_since') || new Date(new Date().setDate(new Date().getDate() - 7)).toISOString().split('T')[0]);
  const [until, setUntil] = useState(localStorage.getItem('git_batch_until') || new Date().toISOString().split('T')[0]);
  const [branchName, setBranchName] = useState(branch || localStorage.getItem('git_batch_branch') || 'develop');
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  
  const initialFilters = useMemo(() => {
    try {
        const saved = localStorage.getItem('git_batch_type_filters');
        return saved ? JSON.parse(saved) : ['feat', 'fix', 'refactor', 'perf'];
    } catch (e) {
        return ['feat', 'fix', 'refactor', 'perf'];
    }
  }, []);
  const [typeFilters, setTypeFilters] = useState(initialFilters);
  const [improveWithAI, setImproveWithAI] = useState(localStorage.getItem('git_batch_improve_ai') === 'true');
  const [systemPrompt, setSystemPrompt] = useState(localStorage.getItem('git_batch_system_prompt') || "");
  const [consolidationPrompt, setConsolidationPrompt] = useState(localStorage.getItem('git_batch_consolidation_prompt') || "");
  const [showPrompt, setShowPrompt] = useState(false);
  const [showConsolidationSettings, setShowConsolidationSettings] = useState(false);
  const [sectionsExpanded, setSectionsExpanded] = useState({ daily: true, consolidation: false, workshop: false });
  const [availableBranches, setAvailableBranches] = useState([]);

  // Persistent state updates
  useEffect(() => {
    localStorage.setItem('git_batch_since', since);
    localStorage.setItem('git_batch_until', until);
    localStorage.setItem('git_batch_branch', branchName);
    localStorage.setItem('git_batch_improve_ai', improveWithAI);
    localStorage.setItem('git_batch_type_filters', JSON.stringify(typeFilters));
    if (systemPrompt) localStorage.setItem('git_batch_system_prompt', systemPrompt);
    if (consolidationPrompt) localStorage.setItem('git_batch_consolidation_prompt', consolidationPrompt);
  }, [since, until, branchName, improveWithAI, typeFilters, systemPrompt, consolidationPrompt]);

  // Sync with prop when it changes
  useEffect(() => {
    if (branch) setBranchName(branch);
  }, [branch]);

  // Fetch available branches
  useEffect(() => {
    const loadBranches = async () => {
        try {
            const res = await getSuiteBranches();
            if (Array.isArray(res.data)) {
                setAvailableBranches(res.data);
            }
        } catch (e) {
            console.error("Failed to load suite branches:", e);
        }
    };
    loadBranches();
  }, []);

  // Detached mode detection
  const activeBatchId = attachedBatchId || openBatchId;
  const attachedBatch = batches.find(b => b.id === activeBatchId);
  const isAttached = !!attachedBatch;

  // Sync prompts from localStorage or defaults
  const resetPrompt = () => setSystemPrompt("");
  const resetConsolidationPrompt = () => setConsolidationPrompt("");

  useEffect(() => {
    if (systemPrompt) localStorage.setItem('git_batch_system_prompt', systemPrompt);
    if (consolidationPrompt) localStorage.setItem('git_batch_consolidation_prompt', consolidationPrompt);
  }, [systemPrompt, consolidationPrompt]);

  const fetchHistory = async () => {
    setLoading(true);
    setStatus({ type: 'info', message: 'Fetching git history...' });
    try {
      const res = await getBatchedGitHistory(since, until, branchName, module || targets[0]);
      const historyData = res.data.history || {};
      setHistory(historyData);
      
      const totalDays = Object.keys(historyData).length;
      const totalCommits = Object.values(historyData).reduce((acc, reposMap) => {
        // reposMap is { "RepoName": [commits], ... }
        return acc + Object.values(reposMap).reduce((dayAcc, commits) => dayAcc + (commits?.length || 0), 0);
      }, 0);
      
      setStatus({ type: 'success', message: '' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  const startBatch = () => {
    if (!history) return;
    spawnBatch({
        since, 
        until, 
        module: module || targets[0] || 'DynamicTrading', 
        branch: branchName,
        history,
        typeFilters,
        improveWithAI,
        systemPrompt,
        consolidationPrompt
    });
    setSectionsExpanded({ daily: true, consolidation: false, workshop: false });
  };

  const getDayList = (s, u) => {
    const start = new Date(s);
    const end = new Date(u);
    const days = [];
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      days.unshift(new Date(d).toISOString().split('T')[0]);
    }
    return days;
  };

  const getTypeColor = (type) => {
    const colors = {
      feat: '#10b981', fix: '#ef4444', refactor: '#f59e0b',
      perf: '#3b82f6', docs: '#8b5cf6', chore: '#6b7280',
      style: '#ec4899', test: '#06b6d4', other: '#9ca3af'
    };
    return colors[type] || colors.other;
  };

  const toggleTypeFilter = (tag) => {
    setTypeFilters(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const handleClose = () => {
    if (isAttached) closeFullView();
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth sx={{ '& .MuiDialog-paper': { borderRadius: 3, bgcolor: '#0d1117', backgroundImage: 'none', border: '1px solid rgba(255,255,255,0.05)' } }}>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="h6" sx={{ fontWeight: 900, letterSpacing: '-0.02em', color: '#fff' }}>
                BATCH UPDATE GENERATOR
            </Typography>
            {isAttached && <Chip label={attachedBatch.id} size="small" sx={{ fontSize: '0.6rem', height: 18, bgcolor: 'rgba(255,255,255,0.05)', color: 'text.secondary' }} />}
        </Stack>
        <IconButton onClick={handleClose} size="small" sx={{ color: 'text.secondary' }}><CloseIcon /></IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
          {isAttached ? (
              <BatchProcessMonitor 
                attachedBatch={attachedBatch}
                sectionsExpanded={sectionsExpanded}
                setSectionsExpanded={setSectionsExpanded}
                getDayList={getDayList}
                history={history || attachedBatch.history}
                loading={loading}
                getTypeColor={getTypeColor}
                retryDay={retryDay}
                showConsolidationSettings={showConsolidationSettings}
                setShowConsolidationSettings={setShowConsolidationSettings}
                consolidationPrompt={consolidationPrompt}
                setConsolidationPrompt={setConsolidationPrompt}
                resetConsolidationPrompt={resetConsolidationPrompt}
                consolidateBatch={consolidateBatch}
                saveBatchVolume={saveBatchVolume}
                setStatus={setStatus}
                handleClose={handleClose}
              />
          ) : (
              <BatchConfigForm 
                status={status}
                module={module || targets[0] || 'DynamicTrading'}
                since={since} setSince={setSince}
                until={until} setUntil={setUntil}
                branchName={branchName} setBranchName={setBranchName}
                availableBranches={availableBranches}
                loading={loading} fetchHistory={fetchHistory}
                history={history}
                typeFilters={typeFilters} toggleTypeFilter={toggleTypeFilter} 
                getTypeColor={getTypeColor}
                improveWithAI={improveWithAI} setImproveWithAI={setImproveWithAI}
                showPrompt={showPrompt} setShowPrompt={setShowPrompt}
                systemPrompt={systemPrompt} setSystemPrompt={setSystemPrompt} 
                resetPrompt={resetPrompt}
              />
          )}
      </DialogContent>

      <DialogActions sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        {isAttached ? (
            <>
                <Typography variant="caption" sx={{ flexGrow: 1, ml: 1, opacity: 0.3, letterSpacing: '0.1em' }}>
                    {attachedBatch.status.toUpperCase()}
                </Typography>
                {attachedBatch.workshopMetadata && (
                    <Button 
                        size="small" 
                        variant="outlined"
                        startIcon={<RefreshIcon />} 
                        onClick={() => consolidateBatch(attachedBatch.id, consolidationPrompt)}
                        sx={{ mr: 1 }}
                    >
                        Rerun Consolidation
                    </Button>
                )}
                {attachedBatch.workshopMetadata && (
                    <Button 
                        size="small" 
                        variant="contained"
                        startIcon={<CopyIcon />} 
                        onClick={() => {
                            navigator.clipboard.writeText(attachedBatch.workshopMetadata);
                            setStatus({ type: 'success', message: 'Workshop BBCode copied!' });
                        }}
                    >
                        Copy Workshop Update
                    </Button>
                )}
                {attachedBatch.status === 'success' && (
                    <Button onClick={handleClose} variant="contained" color="success" sx={{ px: 4 }}>Close</Button>
                )}
            </>
        ) : (
            <>
                <Button onClick={onClose} sx={{ color: 'text.secondary' }}>Cancel</Button>
                <Button 
                    variant="contained" 
                    onClick={startBatch} 
                    disabled={!history || loading || !module}
                    sx={{ px: 4 }}
                >
                    Start Processing
                </Button>
            </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default BatchUpdateGenerator;
