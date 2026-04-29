import React, { useState, useEffect, useMemo, useRef } from 'react';
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
  LinearProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { getBatchedGitHistory, createManualDefinition, getDonatorsDefinition } from '../../services/api';
import { useGitAi } from '../../hooks/useGitAi';
import { ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon, RestartAlt as ResetIcon } from '@mui/icons-material';
import { Collapse, IconButton, Chip } from '@mui/material';

const BatchUpdateGenerator = ({ open, onClose, onComplete, branch = 'develop', module = '', targets = [], modules = [] }) => {
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState({ type: '', message: '' });
  const [showPrompt, setShowPrompt] = useState(false);
  const [since, setSince] = useState(() => localStorage.getItem('git_batch_since') || '2026-03-27');
  const [until, setUntil] = useState(new Date().toISOString().split('T')[0]);
  const [accumulatedPages, setAccumulatedPages] = useState(() => {
    const saved = localStorage.getItem('batch_accumulated_pages');
    return saved ? JSON.parse(saved) : [];
  });
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [improveWithAI, setImproveWithAI] = useState(() => localStorage.getItem('git_batch_improve_ai') === 'true');
  const [logs, setLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  const [resumeDate, setResumeDate] = useState(() => localStorage.getItem('batch_resume_date') || null);
  const [donators, setDonators] = useState(null);
  const scrollRef = useRef(null);

  const addLog = (type, content) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type, content }].slice(-100));
  };

  useEffect(() => {
    if (showLogs && scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, showLogs]);

  useEffect(() => {
    if (open) {
      getDonatorsDefinition().then(res => setDonators(res.data)).catch(() => {});
    }
  }, [open]);

  const moduleOptions = useMemo(() => {
    return modules.map(m => ({ value: m.id, label: m.name, repo: m.project_key }));
  }, [modules]);

  const activeModuleLabel = useMemo(() => {
    return moduleOptions.find(o => o.value === module)?.label || module;
  }, [moduleOptions, module]);

  const [typeFilters, setTypeFilters] = useState(() => {
    const saved = localStorage.getItem('git_ai_assistant_type_filters');
    return saved ? JSON.parse(saved) : ['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'other'];
  });

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

  const toggleTypeFilter = (type) => {
    setTypeFilters(prev => {
        const next = prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type];
        localStorage.setItem('git_ai_assistant_type_filters', JSON.stringify(next));
        return next;
    });
  };

  const updateSince = (val) => {
    setSince(val);
    localStorage.setItem('git_batch_since', val);
    // Clear resume if date changes significantly? 
    // Actually better to just let user decide.
  };

  const updateImproveWithAI = (val) => {
    setImproveWithAI(val);
    localStorage.setItem('git_batch_improve_ai', val);
  };

  const slugify = (value) => String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');

  const { systemPrompt, setSystemPrompt, resetPrompt, generateContent } = useGitAi({
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

  const validateAiContent = (text) => {
    if (!text || text.trim().length < 5) return false;
    if (text.trim() === '%ContextNotFound%') return true;
    const lines = text.split('\n');
    return lines.some(l => /^###\s+|^-|>\s+\[!|!\[/.test(l.trim()));
  };

  const getModulePrefix = (modId) => {
    if (!modId) return 'Upd_';
    // DynamicTradingCommon -> DTC
    const capitals = modId.replace(/[^A-Z]/g, '');
    return capitals ? `${capitals}_Upd_` : 'Upd_';
  };

  const getMonthName = (monthIndex) => {
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    return months[monthIndex];
  };

  const groupByMonth = (hist) => {
    const grouped = {};
    Object.entries(hist).forEach(([date, repos]) => {
      const [year, month] = date.split('-');
      const key = `${year}-${month}`;
      if (!grouped[key]) grouped[key] = {};
      grouped[key][date] = repos;
    });
    return grouped;
  };

  const fetchHistory = async () => {
    setLoading(true);
    setStatus({ type: '', message: '' });
    addLog('system', `Fetching history from ${since} to ${until}...`);
    try {
      const response = await getBatchedGitHistory(since, branch);
      const allHistory = response.data.history || {};
      
      // Filter keys within the [since, until] range
      const rangeDays = Object.keys(allHistory).filter(d => d >= since && d <= until);
      
      setHistory(allHistory);
      const dayCount = rangeDays.length;
      
      setStatus({ 
        type: 'info', 
        message: `Found ${dayCount} days with updates between ${since} and ${until}.` 
      });
      addLog('system', `Found ${dayCount} days in selected range.`);
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to fetch git history.' });
      addLog('error', `Failed to fetch history: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const startBatch = async (isResume = false) => {
    if (!history || !module) return;
    setProcessing(true);
    setProgress(0);
    
    let currentDonators = donators;
    if (!currentDonators) {
        addLog('system', 'Fetching live donator data for Hall of Fame...');
        try {
            const res = await getDonatorsDefinition();
            currentDonators = res.data;
            setDonators(res.data);
        } catch (e) {
            addLog('warning', 'Could not fetch donator data. Hall of Fame will be skipped.');
        }
    }

    if (!isResume) {
        setLogs([]);
        addLog('system', `Starting range-based aggregation: ${since} -> ${until}`);
    } else {
        addLog('system', `Resuming batch from ${resumeDate}...`);
    }

    const allDates = Object.keys(history).sort();
    // Filter dates within [since, until] range
    const rangeDates = allDates.filter(d => d >= since && d <= until);
    const prefix = getModulePrefix(module);
    
    let startIndex = 0;
    if (isResume && resumeDate) {
        startIndex = rangeDates.indexOf(resumeDate);
        if (startIndex === -1) startIndex = 0;
    }

    const total = rangeDates.length;
    let pages = [];
    
    if (isResume) {
        pages = [...accumulatedPages];
        // If we have a resume date, start from the NEXT one (since resumeDate was already added to pages)
        startIndex = rangeDates.indexOf(resumeDate) + 1;
        if (startIndex === -1 || startIndex >= total) {
            // If we were at the very end when it failed (e.g. save failed), 
            // startIndex will be total, meaning the loop won't run, 
            // which is correct because we just want to jump to the final save.
            startIndex = total;
        }
    } else {
        setAccumulatedPages([]);
        localStorage.removeItem('batch_accumulated_pages');
    }

    const volId = `${prefix}${until.replace(/-/g, '_')}`;

    for (let i = startIndex; i < total; i++) {
        const date = rangeDates[i];
        const dayRepos = history[date];
        const filteredDayData = {};
        let totalCommits = 0;
        
        for (const [repo, commits] of Object.entries(dayRepos)) {
            const filtered = commits.filter(c => {
                const type = parseCommitType(c.subject || c.message);
                return typeFilters.includes(type) || (typeFilters.includes('other') && !['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test'].includes(type));
            });
            if (filtered.length > 0) {
                filteredDayData[repo] = filtered;
                totalCommits += filtered.length;
            }
        }
        if (totalCommits === 0) {
            setProgress(Math.round(((i + 1) / total) * 100));
            continue;
        }

        setCurrentStep(`Processing Day: ${date}...`);
        addLog('system', `-> Building Page for ${date} (${totalCommits} commits)`);
        const pageId = date.replace(/-/g, '_');
        const page = {
            id: pageId,
            chapter_id: "release_notes",
            title: date,
            keywords: ["update", "release", date],
            blocks: [{ type: "heading", id: `heading_${pageId}`, level: 1, text: `Updates for ${date}` }]
        };

        if (improveWithAI && window.puter) {
            const refinedText = await generateContent({
                targetName: `Update ${date}`,
                branch,
                commits: filteredDayData,
                customInstructions: `Commits for ${date}:`
            });
            if (!validateAiContent(refinedText)) {
                addLog('error', `CRITICAL: AI content invalid for ${date}.`);
                setStatus({ type: 'error', message: `AI content invalid for ${date}.` });
                setProcessing(false);
                return;
            }
            if (refinedText.trim() === '%ContextNotFound%') {
                addLog('system', `   (Skipped ${date}: Trivial changes)`);
                setProgress(Math.round(((i + 1) / total) * 100));
                continue;
            }
            const lines = refinedText.split('\n');
            let curBlocks = [];
            const flush = () => { if (curBlocks.length > 0) { page.blocks.push({ type: "bullet_list", items: curBlocks }); curBlocks = []; } };
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                const hMatch = trimmed.match(/^###\s*(.*)/);
                if (hMatch) { flush(); page.blocks.push({ type: "heading", id: `ai_h_${pageId}_${slugify(hMatch[1])}`, level: 2, text: hMatch[1].slice(0, 25) }); continue; }
                const cMatch = trimmed.match(/^>\s*\[!(info|success|warning|danger)\]\s*(.*?)\s*\|\s*(.*)/i);
                if (cMatch) { flush(); page.blocks.push({ type: "callout", tone: cMatch[1].toLowerCase(), title: cMatch[2].slice(0, 25), text: cMatch[3] }); continue; }
                const iMatch = trimmed.match(/^!\[(.*?)\]\((.*?)\)/);
                if (iMatch) { flush(); page.blocks.push({ type: "image", caption: iMatch[1], path: iMatch[2] }); continue; }
                const bMatch = trimmed.match(/^[*-]\s*(.*)/);
                if (bMatch) { curBlocks.push(bMatch[1]); continue; }
                if (curBlocks.length > 0) curBlocks.push(trimmed);
                else page.blocks.push({ type: "paragraph", text: trimmed });
            }
            flush();
        } else {
            for (const [repo, commits] of Object.entries(filteredDayData)) {
                page.blocks.push({ type: "heading", id: `repo_${repo.toLowerCase()}_${pageId}`, level: 2, text: repo.slice(0, 25) });
                page.blocks.push({ type: "bullet_list", items: commits.map(c => c.subject) });
            }
        }
        pages.push(page);
        setAccumulatedPages([...pages]);
        localStorage.setItem('batch_accumulated_pages', JSON.stringify(pages));
        setResumeDate(date);
        localStorage.setItem('batch_resume_date', date);
        setProgress(Math.round(((i + 1) / total) * 100));
    }

    if (pages.length === 0) {
        addLog('system', 'No updates found in selected range.');
        setProcessing(false);
        return;
    }

    // Add Hall of Fame at the end
    if (currentDonators) {
        pages.push({
            id: "hall_of_fame",
            chapter_id: "release_notes",
            title: currentDonators.page_title || "Hall of Fame",
            keywords: ["support", "donators"],
            blocks: [{
                type: "supporter_carousel",
                title: currentDonators.block_title || "Hall of Fame",
                autoplay_ms: currentDonators.autoplay_ms || 4000,
                currency_symbol: currentDonators.currency_symbol || "$",
                thank_you_text: currentDonators.thank_you_text || "Thank you!",
                supporters: currentDonators.supporters || []
            }]
        });
    }

    const payload = {
        manual_id: volId,
        module: module,
        title: `Update: ${since.slice(5).replace(/-/g, '/')} - ${until.slice(5).replace(/-/g, '/')}`,
        description: `Consolidated updates from ${since} to ${until}`,
        start_page_id: pages[0].id,
        audiences: [module],
        sort_order: 5,
        release_version: until,
        popup_version: until,
        auto_open_on_update: true,
        is_whats_new: true,
        manual_type: "whats_new",
        show_in_library: false,
        chapters: [{ id: "release_notes", title: "Release Notes", description: `Changes from ${since} to ${until}` }],
        pages
    };

    try {
        await createManualDefinition(payload);
        addLog('success', `VOLUME SAVED: ${volId} (${pages.length} pages)`);
    } catch (error) {
        addLog('error', `Save Failed: ${error.message}`);
        setStatus({ type: 'error', message: `Failed to save unified volume.` });
        setProcessing(false);
        return;
    }

    addLog('success', 'BATCH COMPLETE: Point A to B volume generated.');
    setCurrentStep('Batch process finished.');
    setProcessing(false);
    setResumeDate(null);
    setAccumulatedPages([]);
    localStorage.removeItem('batch_resume_date');
    localStorage.removeItem('batch_accumulated_pages');
    if (onComplete) onComplete();
  };

  return (
    <Dialog open={open} onClose={processing ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Batch Generate Updates</span>
        <Button size="small" variant="text" onClick={() => setShowLogs(!showLogs)}>
           {showLogs ? 'Hide Console' : 'Show Console'}
        </Button>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Generating daily manuals for: <strong style={{ color: '#3b82f6' }}>{activeModuleLabel}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {resumeDate ? (
                <span>Paused at <strong>{resumeDate}</strong>. Next: <strong>{Object.keys(history || {}).sort()[Object.keys(history || {}).sort().indexOf(resumeDate) + 1] || 'None'}</strong></span>
              ) : (
                <span>History will be fetched from branch <strong>{branch}</strong>.</span>
              )}
            </Typography>
          </Box>

          {status.message && <Alert severity={status.type || 'info'}>{status.message}</Alert>}

          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              label="Since Date"
              type="date"
              size="small"
              value={since}
              onChange={(e) => updateSince(e.target.value)}
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
            <Button variant="outlined" onClick={fetchHistory} disabled={loading || processing}>
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
              control={<Checkbox checked={improveWithAI} onChange={(e) => updateImproveWithAI(e.target.checked)} disabled={processing} />}
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

          {processing && (
            <Box>
              <Typography variant="body2" gutterBottom>
                {currentStep} ({progress}%)
              </Typography>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          )}

          <Collapse in={showLogs}>
            <Box 
              ref={scrollRef}
              sx={{ 
                height: 240, 
                bgcolor: '#1e1e1e', 
                color: '#d4d4d4', 
                p: 2, 
                borderRadius: 2, 
                overflow: 'auto',
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                border: '1px solid #333'
              }}
            >
              {logs.length === 0 && <Typography variant="caption" color="gray">No logs yet. Start the batch process or fetch history.</Typography>}
              {logs.map((log, idx) => (
                <Box key={idx} sx={{ mb: 1, borderLeft: `2px solid ${log.type === 'error' ? '#f44336' : log.type === 'system' ? '#2196f3' : log.type.startsWith('ai') ? '#9c27b0' : '#4caf50'}`, pl: 1 }}>
                  <Typography variant="caption" sx={{ color: '#888', mr: 1, fontWeight: 800 }}>[{log.time}]</Typography>
                  <Typography variant="caption" sx={{ color: log.type === 'error' ? '#ef5350' : log.type === 'system' ? '#64b5f6' : log.type.startsWith('ai') ? '#ba68c8' : '#81c784', mr: 1, fontWeight: 800 }}>{log.type.toUpperCase()}:</Typography>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', display: 'inline' }}>{log.content}</pre>
                </Box>
              ))}
            </Box>
          </Collapse>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={processing}>Cancel</Button>
        {resumeDate && (
            <Button 
                variant="outlined" 
                color="secondary"
                onClick={() => startBatch(true)} 
                disabled={!history || processing || loading || !module}
            >
                Resume from {resumeDate}
            </Button>
        )}
        <Button 
          variant="contained" 
          onClick={() => startBatch(false)} 
          disabled={!history || processing || loading || !module}
        >
          {processing ? 'Processing...' : 'Start New Batch'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BatchUpdateGenerator;
