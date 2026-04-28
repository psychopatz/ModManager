import React, { useState, useEffect, useMemo } from 'react';
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
import { getBatchedGitHistory, createManualDefinition } from '../../services/api';
import { useGitAi } from '../../hooks/useGitAi';
import { ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon, RestartAlt as ResetIcon } from '@mui/icons-material';
import { Collapse, IconButton, Chip } from '@mui/material';

const BatchUpdateGenerator = ({ open, onClose, onComplete, branch = 'develop', targets = [], modules = [] }) => {
  const [since, setSince] = useState('2026-03-27');
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState({ type: '', message: '' });
  const [showPrompt, setShowPrompt] = useState(false);
  const [selectedModule, setSelectedModule] = useState('');
  const [improveWithAI, setImproveWithAI] = useState(false);

  const moduleOptions = useMemo(() => {
    return modules.map(m => ({ value: m.id, label: m.name, repo: m.project_key }));
  }, [modules]);

  useEffect(() => {
      if (moduleOptions.length > 0 && !moduleOptions.some(o => o.value === selectedModule)) {
          setSelectedModule(moduleOptions[0].value);
      }
  }, [moduleOptions]);

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

  const { systemPrompt, setSystemPrompt, resetPrompt, generateContent } = useGitAi({
    storageKey: 'batch_update_system_prompt',
    defaultPrompt: 'Refine the following git commits into a clean, professional "What\'s New" bullet list for a Project Zomboid mod update. Group by module if appropriate.\n\nReturn ONLY the bullet points.',
  });

  const fetchHistory = async () => {
    setLoading(true);
    setStatus({ type: '', message: '' });
    try {
      const response = await getBatchedGitHistory(since, branch);
      setHistory(response.data.history);
      const dayCount = Object.keys(response.data.history || {}).length;
      setStatus({ type: 'info', message: `Found ${dayCount} days with updates on branch "${branch}".` });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to fetch git history.' });
    } finally {
      setLoading(false);
    }
  };

  const startBatch = async () => {
    if (!history) return;
    setProcessing(true);
    setProgress(0);
    const dates = Object.keys(history).sort();
    const total = dates.length;

    for (let i = 0; i < total; i++) {
        const date = dates[i];
        const dayRepos = history[date];
        
        // Filter dayData by repo and type
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

        setCurrentStep(`Processing ${date} (${totalCommits} commits)...`);
        
        try {
            let pageContent = '';
            const chapters = [
                {
                    id: "release_notes",
                    title: "Release Notes",
                    description: `Changes made on ${date}.`
                }
            ];
            
            const pages = [
                {
                    id: date.replace(/-/g, '_'),
                    chapter_id: "release_notes",
                    title: date,
                    keywords: ["update", "release", date],
                    blocks: [
                        {
                            type: "heading",
                            id: `heading_${date.replace(/-/g, '_')}`,
                            level: 1,
                            text: `Updates for ${date}`
                        }
                    ]
                }
            ];

            // Improvement with AI if checked
            if (improveWithAI && window.puter) {
                setCurrentStep(`Refining ${date} with AI...`);
                
                const refinedText = await generateContent({
                    targetName: `Update ${date}`,
                    branch,
                    commits: filteredDayData,
                    customInstructions: `Commits for ${date}:`
                });
                
                pages[0].blocks.push({
                    type: "bullet_list",
                    items: refinedText.split('\n').filter(l => l.trim()).map(l => l.replace(/^[*-]\s*/, ''))
                });
            } else {
                // Manual grouping
                for (const [repo, commits] of Object.entries(filteredDayData)) {
                    pages[0].blocks.push({
                        type: "heading",
                        id: `repo_${repo.toLowerCase()}_${date.replace(/-/g, '_')}`,
                        level: 2,
                        text: `${repo} Changes`
                    });
                    pages[0].blocks.push({
                        type: "bullet_list",
                        items: commits.map(c => `**${c.subject}**${c.body ? `\n${c.body.split('\n')[0]}` : ''}`)
                    });
                }
            }

            const payload = {
                manual_id: `dt_update_${date.replace(/-/g, '_')}`,
                module: "common",
                title: `Update: ${date}`,
                description: `Patch notes for ${date}`,
                start_page_id: date.replace(/-/g, '_'),
                audiences: ["common"],
                sort_order: 5,
                release_version: date,
                popup_version: date,
                auto_open_on_update: true,
                is_whats_new: true,
                manual_type: "whats_new",
                show_in_library: false,
                chapters,
                pages
            };

            await createManualDefinition(payload, 'updates', selectedModule);
        } catch (error) {
            console.error(`Error processing ${date}:`, error);
        }
        
        setProgress(Math.round(((i + 1) / total) * 100));
    }

    setProcessing(false);
    setCurrentStep('Done!');
    setStatus({ type: 'success', message: `Successfully generated ${total} daily manuals.` });
    if (onComplete) onComplete();
  };

  return (
    <Dialog open={open} onClose={processing ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Batch Generate Updates</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Group git commits by day and create individual manuals. 
            History will be fetched from branch <strong>{branch}</strong>.
          </Typography>

          {status.message && <Alert severity={status.type || 'info'}>{status.message}</Alert>}

          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              label="Since Date"
              type="date"
              size="small"
              value={since}
              onChange={(e) => setSince(e.target.value)}
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

          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="subtitle2">Target Module:</Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
                {moduleOptions.map((opt) => (
                    <Chip
                        key={opt.value}
                        label={opt.label}
                        size="small"
                        clickable
                        color={selectedModule === opt.value ? 'primary' : 'default'}
                        onClick={() => setSelectedModule(opt.value)}
                    />
                ))}
            </Stack>
          </Stack>

          <Stack spacing={1}>
            <FormControlLabel
              control={<Checkbox checked={improveWithAI} onChange={(e) => setImproveWithAI(e.target.checked)} disabled={processing} />}
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
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={processing}>Cancel</Button>
        <Button 
          variant="contained" 
          onClick={startBatch} 
          disabled={!history || processing || loading}
        >
          {processing ? 'Processing...' : 'Start Batch Process'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BatchUpdateGenerator;
