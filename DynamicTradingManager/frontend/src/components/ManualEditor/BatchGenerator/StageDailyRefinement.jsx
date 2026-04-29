import React from 'react';
import { 
    Box, Typography, Stack, Collapse, Accordion, AccordionSummary, AccordionDetails, 
    IconButton, CircularProgress, Chip
} from '@mui/material';
import {
    RestartAlt as RefreshIcon,
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    History as DailyIcon,
    CheckCircle as SuccessIcon,
    Psychology as ThinkingIcon
} from '@mui/icons-material';

const StageDailyRefinement = ({
    attachedBatch,
    sectionsExpanded,
    setSectionsExpanded,
    getDayList,
    history,
    loading,
    getTypeColor,
    retryDay,
}) => {
    const days = getDayList(attachedBatch.config.since, attachedBatch.config.until);
    
    return (
        <Box sx={{ bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1.5, mb: 1, border: '1px solid rgba(255,255,255,0.05)' }}>
            <Box 
                sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', p: 1 }}
                onClick={() => setSectionsExpanded(prev => ({ ...prev, daily: !prev.daily }))}
            >
                <Stack direction="row" spacing={1} alignItems="center">
                    {sectionsExpanded.daily ? <ExpandLessIcon sx={{ fontSize: 18 }} /> : <ExpandMoreIcon sx={{ fontSize: 18 }} />}
                    <DailyIcon sx={{ fontSize: 18, color: 'primary.main' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 800, letterSpacing: '0.05em' }}>STAGE 1: DAILY REFINEMENT</Typography>
                </Stack>
                <Typography variant="caption" sx={{ fontWeight: 800, bgcolor: 'rgba(255,255,255,0.05)', px: 1, borderRadius: 1 }}>
                    {days.length} DAYS
                </Typography>
            </Box>

            <Collapse in={sectionsExpanded.daily}>
                <Box sx={{ pl: 2, pb: 1, pr: 1 }}>
                    <Stack spacing={0.5}>
                        {days.map(date => {
                            const page = attachedBatch.pages.find(p => p.date === date);
                            const stage1Item = (attachedBatch.stage1Items || []).find(i => i.date === date);
                            const stream = attachedBatch.streamingData?.[date];
                            const isProcessing = attachedBatch.currentStep.includes(date) || (stream?.status === 'streaming');
                            
                            return (
                                <Accordion key={date} expanded={true} sx={{ bgcolor: 'transparent', boxShadow: 'none', border: '1px solid rgba(255,255,255,0.03)' }}>
                                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                        <Stack direction="row" spacing={1} alignItems="center" sx={{ width: '100%' }}>
                                            {page ? <SuccessIcon sx={{ fontSize: 14, color: 'success.main' }} /> : isProcessing ? <CircularProgress size={12} /> : <Box sx={{ width: 14 }} />}
                                            <Typography variant="caption" sx={{ fontWeight: 800, opacity: page ? 1 : 0.5, flexGrow: 1 }}>
                                                {date}
                                                {stage1Item?.title && stage1Item.title !== date ? ` — ${stage1Item.title}` : ''}
                                            </Typography>
                                            {stage1Item?.parseWarnings?.length > 0 && (
                                                <Chip label="WARN" size="small" color="warning" sx={{ height: 14, fontSize: '0.55rem' }} />
                                            )}
                                            <IconButton size="small" onClick={(e) => { e.stopPropagation(); retryDay(attachedBatch.id, date); }}>
                                                <RefreshIcon sx={{ fontSize: 12 }} />
                                            </IconButton>
                                        </Stack>
                                    </AccordionSummary>
                                    <AccordionDetails>
                                        <Stack spacing={2}>
                                            {/* RAW COMMITS VIEW */}
                                            <Box>
                                                <Typography variant="caption" sx={{ fontWeight: 800, opacity: 0.5, display: 'block', mb: 1 }}>RAW GIT COMMITS</Typography>
                                                <Stack spacing={0.5}>
                                                    {history?.[date] ? Object.entries(history[date]).map(([repo, commits]) => (
                                                        <Box key={repo}>
                                                            <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main', fontSize: '0.6rem' }}>{repo.toUpperCase()}</Typography>
                                                            {commits.map((c, i) => (
                                                                <Typography key={i} variant="caption" sx={{ display: 'block', pl: 1, borderLeft: '1px solid rgba(255,255,255,0.1)', mb: 0.5 }}>
                                                                    • <span style={{ color: getTypeColor(c.type), fontWeight: 800 }}>{c.type}</span>: {c.subject}
                                                                </Typography>
                                                            ))}
                                                        </Box>
                                                    )) : (
                                                        <Typography variant="caption" color="text.disabled" sx={{ fontStyle: 'italic' }}>Loading git history...</Typography>
                                                    )}
                                                </Stack>
                                            </Box>

                                            {/* LIVE LLM STREAM for this day */}
                                            {(isProcessing || stream?.content) && (
                                                <Box sx={{ p: 1.5, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 1.5, border: '1px solid rgba(99,102,241,0.25)' }}>
                                                    <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main', display: 'block', mb: 1 }}>
                                                        {stream?.status === 'streaming' ? '⟳ LLM RAW OUTPUT (streaming...)' : 'LLM RAW OUTPUT'}
                                                    </Typography>
                                                    {stream?.thinking && (
                                                        <Box sx={{ mb: 1, p: 1, bgcolor: 'rgba(99,102,241,0.06)', borderRadius: 1, borderLeft: '2px solid rgba(99,102,241,0.4)' }}>
                                                            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                                                                <ThinkingIcon sx={{ fontSize: 12, color: 'secondary.main' }} />
                                                                <Typography variant="caption" sx={{ fontWeight: 800, color: 'secondary.main', fontSize: '0.6rem' }}>THINKING</Typography>
                                                            </Stack>
                                                            <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem', color: 'text.secondary', whiteSpace: 'pre-wrap', display: 'block', maxHeight: 120, overflowY: 'auto' }}>
                                                                {stream.thinking}
                                                            </Typography>
                                                        </Box>
                                                    )}
                                                    <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.7rem', whiteSpace: 'pre-wrap', display: 'block', maxHeight: 200, overflowY: 'auto', color: '#c9d1d9' }}>
                                                        {stream?.content || ''}
                                                    </Typography>
                                                </Box>
                                            )}

                                            {/* PARSED STAGE 1 RESULT */}
                                            {stage1Item && (
                                                <Box>
                                                    <Typography variant="caption" sx={{ fontWeight: 800, opacity: 0.5, display: 'block', mb: 1 }}>STAGE 1 STRUCTURED OUTPUT</Typography>
                                                    <Box sx={{ p: 1, bgcolor: 'rgba(16,185,129,0.05)', borderRadius: 1, border: '1px solid rgba(16,185,129,0.15)', mb: 0.5 }}>
                                                        <Typography variant="caption" sx={{ fontWeight: 800, color: 'success.main', display: 'block' }}>{stage1Item.title}</Typography>
                                                    </Box>
                                                    {stage1Item.explanation && (
                                                        <Typography variant="caption" sx={{ display: 'block', mb: 0.5, opacity: 0.85, whiteSpace: 'pre-wrap', pl: 1, borderLeft: '2px solid rgba(255,255,255,0.1)' }}>
                                                            {stage1Item.explanation}
                                                        </Typography>
                                                    )}
                                                    <Typography variant="caption" sx={{ display: 'block', mb: 0.5, color: 'info.main' }}>Impact: {stage1Item.impact}</Typography>
                                                    {stage1Item.parseWarnings?.length > 0 && (
                                                        <Typography variant="caption" sx={{ display: 'block', color: 'warning.main', fontSize: '0.6rem' }}>
                                                            ⚠ {stage1Item.parseWarnings.join(' ')}
                                                        </Typography>
                                                    )}
                                                </Box>
                                            )}
                                        </Stack>
                                    </AccordionDetails>
                                </Accordion>
                            );
                        })}
                    </Stack>
                </Box>
            </Collapse>
        </Box>
    );
};

export default StageDailyRefinement;
