import React, { useState, useEffect } from 'react';
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

const BatchUpdateGenerator = ({ open, onClose, onComplete, branch = 'develop' }) => {
  const [since, setSince] = useState('2026-03-27');
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [status, setStatus] = useState({ type: '', message: '' });
  const [improveWithAI, setImproveWithAI] = useState(true);

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
        const dayData = history[date];
        setCurrentStep(`Processing ${date}...`);
        
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
                const rawCommits = Object.entries(dayData).map(([repo, commits]) => {
                    return `${repo}:\n${commits.map(c => `- ${c.subject}${c.body ? `\n  ${c.body.split('\n')[0]}` : ''}`).join('\n')}`;
                }).join('\n\n');
                
                const prompt = `Refine the following git commits into a clean, professional "What's New" bullet list for a Project Zomboid mod update. Group by module if appropriate.\n\nCommits for ${date}:\n${rawCommits}\n\nReturn ONLY the bullet points.`;
                const aiResponse = await window.puter.ai.chat(prompt);
                const refinedText = aiResponse?.message?.content?.trim() || '';
                
                pages[0].blocks.push({
                    type: "bullet_list",
                    items: refinedText.split('\n').filter(l => l.trim()).map(l => l.replace(/^[*-]\s*/, ''))
                });
            } else {
                // Manual grouping
                for (const [repo, commits] of Object.entries(dayData)) {
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

            await createManualDefinition(payload, 'updates', 'common');
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

          <FormControlLabel
            control={<Checkbox checked={improveWithAI} onChange={(e) => setImproveWithAI(e.target.checked)} disabled={processing} />}
            label="Batch improve commits using AI (Puter AI)"
          />

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
