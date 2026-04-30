import React from 'react';
import { 
    Stack, TextField, Button, Box, Chip, FormControlLabel, Checkbox,
    Collapse, Typography, Alert, Paper, Autocomplete, Select, MenuItem, InputLabel, FormControl
} from '@mui/material';
import {
    RestartAlt as ResetIcon,
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    CallSplit as RoutingIcon,
    Warning as WarningIcon
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
    routedHistory,
    routingWarnings = [],
    typeFilters, toggleTypeFilter, getTypeColor,
    improveWithAI, setImproveWithAI,
    autoSaveAfterConsolidation, setAutoSaveAfterConsolidation,
    cacheOutputs, setCacheOutputs,
    showPrompt, setShowPrompt,
    systemPrompt, setSystemPrompt, resetPrompt,
    showConsolidationPrompt, setShowConsolidationPrompt,
    consolidationPrompt, setConsolidationPrompt, resetConsolidationPrompt,
    cachedRuns,
    resumeCacheId, setResumeCacheId,
    resumeFromStage, setResumeFromStage,
    clearBatchCache,
}) => {
    const parseCommitType = (subject) => {
        if (!subject || typeof subject !== 'string') return 'other';
        const match = subject.match(/^(\w+)(\(.*\))?:/);
        return match ? match[1].toLowerCase() : 'other';
    };

    const rawCommits = React.useMemo(() => {
        if (!history) return [];
        const flatList = [];
        Object.entries(history).forEach(([date, reposMap]) => {
            Object.entries(reposMap).forEach(([repo, commits]) => {
                commits.forEach(c => {
                    const type = parseCommitType(c.subject || c.message || '');
                    flatList.push({ ...c, date, repo, type });
                });
            });
        });
        return flatList.sort((a, b) => new Date(b.date) - new Date(a.date));
    }, [history]);

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

    const rawDayCount = React.useMemo(() => new Set(rawCommits.map((c) => c.date)).size, [rawCommits]);
    const filteredDayCount = React.useMemo(() => new Set(allCommits.map((c) => c.date)).size, [allCommits]);

    // Compute routing summary: submod → commit count
    const routingSummary = React.useMemo(() => {
        if (!routedHistory || Object.keys(routedHistory).length === 0) return null;
        const map = {};
        Object.values(routedHistory).forEach(submods => {
            Object.entries(submods).forEach(([submod, commits]) => {
                map[submod] = (map[submod] || 0) + (Array.isArray(commits) ? commits.length : 0);
            });
        });
        return map;
    }, [routedHistory]);

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

            {rawCommits.length > 0 && (
                <Alert severity="success" icon={false} sx={{ '& .MuiAlert-message': { width: '100%' }, py: 0.5 }}>
                    <Stack spacing={0.25}>
                        <Typography variant="body2" fontWeight={800}>
                            Raw git history: {rawDayCount} active days, {rawCommits.length} commits.
                        </Typography>
                        <Typography variant="caption" sx={{ opacity: 0.7 }}>
                            Current preview after filters: {filteredDayCount} days, {allCommits.length} commits.
                        </Typography>
                    </Stack>
                </Alert>
            )}

            {/* ROUTING DESTINATIONS PANEL */}
            {routingSummary && (
                <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'rgba(99,102,241,0.05)', borderColor: 'rgba(99,102,241,0.25)', borderRadius: 2 }}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                        <RoutingIcon sx={{ fontSize: 16, color: 'secondary.main' }} />
                        <Typography variant="caption" fontWeight={800} color="secondary" sx={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                            Routing Destinations
                        </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: routingWarnings.length > 0 ? 1 : 0 }}>
                        {Object.entries(routingSummary).map(([submod, count]) => (
                            <Chip
                                key={submod}
                                label={`${submod} — ${count} commit${count !== 1 ? 's' : ''}`}
                                size="small"
                                sx={{
                                    fontSize: '0.65rem',
                                    fontWeight: 800,
                                    bgcolor: 'rgba(99,102,241,0.15)',
                                    color: 'secondary.light',
                                    border: '1px solid rgba(99,102,241,0.3)',
                                }}
                            />
                        ))}
                    </Stack>
                    {routingWarnings.length > 0 && (
                        <Stack direction="row" spacing={0.5} alignItems="center">
                            <WarningIcon sx={{ fontSize: 13, color: 'warning.main' }} />
                            <Typography variant="caption" sx={{ color: 'warning.main', fontSize: '0.65rem' }}>
                                {routingWarnings.length} commit{routingWarnings.length !== 1 ? 's' : ''} could not be routed to a submod
                            </Typography>
                        </Stack>
                    )}
                </Paper>
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

                <FormControlLabel
                    control={<Checkbox checked={cacheOutputs} onChange={(e) => setCacheOutputs(e.target.checked)} />}
                    label={<Typography variant="body2" fontWeight={800}>Cache Stage outputs in local storage</Typography>}
                />

                <FormControlLabel
                    control={<Checkbox checked={autoSaveAfterConsolidation} onChange={(e) => setAutoSaveAfterConsolidation(e.target.checked)} />}
                    label={<Typography variant="body2" fontWeight={800}>Auto-save assembled update to manual/Lua after consolidation</Typography>}
                />

                <Stack direction="row" spacing={1.5} alignItems="center">
                    <FormControl size="small" sx={{ minWidth: 280 }}>
                        <InputLabel id="resume-cache-label">Resume from cache</InputLabel>
                        <Select
                            labelId="resume-cache-label"
                            value={resumeCacheId}
                            label="Resume from cache"
                            onChange={(e) => setResumeCacheId(e.target.value)}
                        >
                            <MenuItem value="">None</MenuItem>
                            {(cachedRuns || []).map((entry) => (
                                <MenuItem key={entry.batchId} value={entry.batchId}>
                                    {`${entry.module || 'Module'} | ${entry.branch || 'branch?'} | ${entry.since || '?'} -> ${entry.until || '?'} | S1:${entry.stage1Count}`}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl size="small" sx={{ minWidth: 180 }} disabled={!resumeCacheId}>
                        <InputLabel id="resume-stage-label">Resume stage</InputLabel>
                        <Select
                            labelId="resume-stage-label"
                            value={resumeFromStage}
                            label="Resume stage"
                            onChange={(e) => setResumeFromStage(Number(e.target.value))}
                        >
                            <MenuItem value={2}>Stage 2</MenuItem>
                            <MenuItem value={3}>Stage 3</MenuItem>
                        </Select>
                    </FormControl>

                    <Button
                        variant="outlined"
                        color="warning"
                        disabled={!resumeCacheId}
                        onClick={() => {
                            clearBatchCache(resumeCacheId);
                            setResumeCacheId('');
                        }}
                    >
                        Clear Selected Cache
                    </Button>
                </Stack>
                
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

                        <Button
                            size="small"
                            onClick={() => setShowConsolidationPrompt(!showConsolidationPrompt)}
                            startIcon={showConsolidationPrompt ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            sx={{ fontSize: '0.7rem', fontWeight: 800, mt: 1 }}
                        >
                            Consolidation Prompt
                        </Button>

                        <Collapse in={showConsolidationPrompt}>
                            <Stack spacing={1} sx={{ mt: 1, p: 2, bgcolor: 'rgba(33,150,243,0.05)', borderRadius: 2, border: '1px solid rgba(33,150,243,0.2)' }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" fontWeight={800}>THEMATIC CONSOLIDATION PROMPT</Typography>
                                    <Button size="small" startIcon={<ResetIcon />} onClick={resetConsolidationPrompt} sx={{ fontSize: '0.65rem' }}>Reset</Button>
                                </Box>
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={5}
                                    variant="filled"
                                    value={consolidationPrompt}
                                    onChange={(e) => setConsolidationPrompt(e.target.value)}
                                    sx={{ '& .MuiInputBase-input': { fontSize: '0.8rem', fontFamily: 'monospace' } }}
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
