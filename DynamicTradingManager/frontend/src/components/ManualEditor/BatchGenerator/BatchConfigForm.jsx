import React from 'react';
import { 
    Stack, TextField, Button, Box, Chip, FormControlLabel, Checkbox, 
    Collapse, Typography, Alert, Paper, Autocomplete
} from '@mui/material';
import {
    RestartAlt as ResetIcon,
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon
} from '@mui/icons-material';

const BatchConfigForm = ({
    status,
    module,
    since, setSince,
    until, setUntil,
    branchName, setBranchName,
    availableBranches = [],
    loading, fetchHistory,
    history,
    typeFilters, toggleTypeFilter, getTypeColor,
    improveWithAI, setImproveWithAI,
    showPrompt, setShowPrompt,
    systemPrompt, setSystemPrompt, resetPrompt,
}) => {
    const parseCommitType = (subject) => {
        if (!subject || typeof subject !== 'string') return 'other';
        const match = subject.match(/^(\w+)(\(.*\))?:/);
        return match ? match[1].toLowerCase() : 'other';
    };

    const allCommits = React.useMemo(() => {
        if (!history) return [];
        const flatList = [];
        Object.entries(history).forEach(([date, reposMap]) => {
            Object.entries(reposMap).forEach(([repo, commits]) => {
                commits.forEach(c => {
                    const type = parseCommitType(c.subject || c.message || '');
                    const isOther = !['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test'].includes(type);
                    
                    if (typeFilters.includes(type) || (typeFilters.includes('other') && isOther)) {
                        flatList.push({ ...c, date, repo, type });
                    }
                });
            });
        });
        return flatList.sort((a, b) => new Date(b.date) - new Date(a.date));
    }, [history, typeFilters]);

    return (
        <Stack spacing={3}>
            {/* Context Header */}
            <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 2, display: 'flex', gap: 3 }}>
               <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 800, display: 'block', textTransform: 'uppercase', mb: 0.5 }}>Module</Typography>
                  <Typography variant="body2" fontWeight={800} color="primary">{module}</Typography>
               </Box>
               <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 800, display: 'block', textTransform: 'uppercase', mb: 0.5 }}>Branch</Typography>
                  <Typography variant="body2" fontWeight={800} color="secondary">{branchName}</Typography>
               </Box>
            </Paper>

            {status.message && status.type !== 'success' && <Alert severity={status.type || 'info'}>{status.message}</Alert>}

            {allCommits.length > 0 && (
                <Alert severity="success" icon={false} sx={{ '& .MuiAlert-message': { width: '100%' }, py: 0.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" fontWeight={800}>
                            {new Set(allCommits.map(c => c.date)).size} days of activity found ({allCommits.length} total commits).
                        </Typography>
                        <Typography variant="caption" sx={{ opacity: 0.7 }}>(Filtered results)</Typography>
                    </Box>
                </Alert>
            )}

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
                <TextField
                    label="Until Date"
                    type="date"
                    size="small"
                    value={until}
                    onChange={(e) => setUntil(e.target.value)}
                    InputLabelProps={{ shrink: true }}
                    sx={{ flex: 1 }}
                />
                <Autocomplete
                    size="small"
                    options={availableBranches}
                    value={branchName}
                    onChange={(e, newValue) => {
                        if (newValue) setBranchName(newValue);
                    }}
                    onInputChange={(e, newInputValue) => {
                        setBranchName(newInputValue);
                    }}
                    freeSolo
                    sx={{ flex: 1 }}
                    renderInput={(params) => (
                        <TextField
                            {...params}
                            label="Branch"
                            placeholder="develop"
                        />
                    )}
                />
                <Button variant="outlined" onClick={fetchHistory} disabled={loading} sx={{ fontWeight: 800 }}>
                    {loading ? 'Fetching...' : 'CHECK HISTORY'}
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

            {/* Commit List Preview */}
            {allCommits.length > 0 && (
                <Stack spacing={1}>
                    <Typography variant="caption" fontWeight={800} sx={{ opacity: 0.6 }}>FOUND CHANGES PREVIEW</Typography>
                    <Paper variant="outlined" sx={{ maxHeight: 250, overflow: 'auto', p: 1, bgcolor: 'rgba(0,0,0,0.02)', borderColor: 'divider' }}>
                        <Stack spacing={0.5}>
                            {allCommits.map((commit, idx) => {
                                const type = parseCommitType(commit.subject || commit.message || '');
                                return (
                                    <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 0.2 }}>
                                        <Box sx={{ width: 3, height: 14, bgcolor: getTypeColor(type), borderRadius: 1, flexShrink: 0 }} />
                                        <Typography variant="caption" color="text.secondary" sx={{ minWidth: 100, opacity: 0.5, fontFamily: 'monospace', textTransform: 'uppercase', fontSize: '0.6rem' }} noWrap>
                                            {commit.repo}
                                        </Typography>
                                        <Typography variant="body2" sx={{ fontSize: '0.75rem', fontFamily: 'monospace' }} noWrap>
                                            {commit.subject || commit.message}
                                        </Typography>
                                        <Typography variant="caption" sx={{ ml: 'auto', opacity: 0.4, fontSize: '0.65rem', minWidth: 80, textAlign: 'right' }}>
                                            {new Date(commit.date).toLocaleDateString()}
                                        </Typography>
                                    </Box>
                                );
                            })}
                        </Stack>
                    </Paper>
                </Stack>
            )}

            <Stack spacing={1}>
                <FormControlLabel
                    control={<Checkbox checked={improveWithAI} onChange={(e) => setImproveWithAI(e.target.checked)} />}
                    label={<Typography variant="body2" fontWeight={800}>Batch improve commits using AI</Typography>}
                />
                
                {improveWithAI && (
                    <Box>
                        <Button 
                            size="small" 
                            onClick={() => setShowPrompt(!showPrompt)}
                            startIcon={showPrompt ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            sx={{ fontSize: '0.7rem', fontWeight: 800 }}
                        >
                            Daily Refinement Prompt
                        </Button>
                        <Collapse in={showPrompt}>
                            <Stack spacing={1} sx={{ mt: 1, p: 2, bgcolor: 'rgba(0,0,0,0.03)', borderRadius: 2 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" fontWeight={800}>DAILY REFINEMENT SYSTEM PROMPT</Typography>
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
        </Stack>
    );
};

export default BatchConfigForm;
