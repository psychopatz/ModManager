import React, { useState } from 'react';
import { 
    Box, Typography, Stack, Collapse, TextField, Button
} from '@mui/material';
import {
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    AutoFixHigh as ConsolidationIcon,
    AutoAwesome as AiStatusIcon,
    RestartAlt as ResetIcon,
    Psychology as ThinkingIcon
} from '@mui/icons-material';

const StageThematicConsolidation = ({
    attachedBatch,
    sectionsExpanded,
    setSectionsExpanded,
    consolidationPrompt,
    setConsolidationPrompt,
    resetConsolidationPrompt,
    consolidateBatch,
}) => {
    const [showPromptEditor, setShowPromptEditor] = useState(false);
    const isLocked = attachedBatch.status !== 'success' && attachedBatch.progress < 100;
    const stream = attachedBatch.streamingData?._consolidation;
    const isStreaming = stream?.status === 'streaming';

    return (
        <Box sx={{ 
            bgcolor: 'rgba(255,255,255,0.03)', 
            borderRadius: 1.5, mb: 1, 
            border: '1px solid rgba(255,255,255,0.05)',
            opacity: isLocked ? 0.4 : 1,
            pointerEvents: isLocked ? 'none' : 'auto',
            position: 'relative'
        }}>
            <Box 
                sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: isLocked ? 'default' : 'pointer', p: 1 }}
                onClick={() => !isLocked && setSectionsExpanded(prev => ({ ...prev, consolidation: !prev.consolidation }))}
            >
                <Stack direction="row" spacing={1} alignItems="center">
                    {sectionsExpanded.consolidation ? <ExpandLessIcon sx={{ fontSize: 18 }} /> : <ExpandMoreIcon sx={{ fontSize: 18 }} />}
                    <ConsolidationIcon sx={{ fontSize: 18, color: 'info.main' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 800, letterSpacing: '0.05em' }}>STAGE 2: THEMATIC CONSOLIDATION</Typography>
                    {isStreaming && (
                        <Typography variant="caption" sx={{ color: 'info.main', fontSize: '0.6rem', fontStyle: 'italic' }}>streaming...</Typography>
                    )}
                </Stack>
                {isLocked && <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.disabled', fontSize: '0.6rem' }}>LOCKED</Typography>}
            </Box>

            <Collapse in={sectionsExpanded.consolidation}>
                <Box sx={{ pl: 2, pb: 2, pr: 1 }}>
                    <Stack spacing={2}>
                        {/* LIVE LLM OUTPUT */}
                        {(isStreaming || stream?.content) && (
                            <Box sx={{ p: 1.5, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 1.5, border: '1px solid rgba(33,150,243,0.25)' }}>
                                <Typography variant="caption" sx={{ fontWeight: 800, color: 'info.main', display: 'block', mb: 1 }}>
                                    {isStreaming ? '⟳ CONSOLIDATION AGENT (streaming...)' : 'CONSOLIDATION AGENT OUTPUT'}
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

                        {/* OVERALL TITLE */}
                        {attachedBatch.generatedUpdateTitle && (
                            <Box sx={{ p: 1.5, bgcolor: 'rgba(33, 150, 243, 0.08)', borderRadius: 1.5, border: '1px solid rgba(33, 150, 243, 0.2)' }}>
                                <Typography variant="caption" sx={{ fontWeight: 800, color: 'info.main', display: 'block', mb: 0.5 }}>OVERALL UPDATE TITLE</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 700 }}>{attachedBatch.generatedUpdateTitle}</Typography>
                            </Box>
                        )}

                        {/* CATEGORY PAGES SUMMARY */}
                        {(attachedBatch.consolidatedPages || []).map((page, idx) => (
                            <Box key={idx} sx={{ p: 1.5, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1.5, border: '1px solid rgba(255,255,255,0.05)' }}>
                                <Typography variant="caption" sx={{ fontWeight: 800, color: 'info.main', display: 'block', mb: 0.5 }}>{page.title.toUpperCase()}</Typography>
                                {attachedBatch.categorization?.summaries?.[page.title] && (
                                    <Typography variant="caption" sx={{ display: 'block', opacity: 0.8, mb: 0.5 }}>
                                        {attachedBatch.categorization.summaries[page.title]}
                                    </Typography>
                                )}
                                <Typography variant="caption" sx={{ opacity: 0.5, fontSize: '0.7rem' }}>
                                    {page.blocks.filter(b => b.type === 'heading').length} entries in this category
                                </Typography>
                            </Box>
                        ))}

                        {/* CATEGORY MAP PREVIEW */}
                        {attachedBatch.categorization?.map && (
                            <Box sx={{ p: 1.5, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 1.5, border: '1px solid rgba(255,255,255,0.05)' }}>
                                <Typography variant="caption" sx={{ fontWeight: 800, opacity: 0.7, display: 'block', mb: 1 }}>CATEGORY MAP PREVIEW</Typography>
                                {Object.entries(attachedBatch.categorization.map).slice(0, 10).map(([itemId, category]) => (
                                    <Typography key={itemId} variant="caption" sx={{ display: 'block', fontFamily: 'monospace', opacity: 0.8 }}>
                                        {itemId} ⟹ {category}
                                    </Typography>
                                ))}
                            </Box>
                        )}

                        {/* PROMPT EDITOR TOGGLE */}
                        <Button 
                            size="small" 
                            variant="text" 
                            onClick={(e) => { e.stopPropagation(); setShowPromptEditor(p => !p); }}
                            startIcon={showPromptEditor ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            sx={{ alignSelf: 'flex-start', fontSize: '0.65rem' }}
                        >
                            REFINE CONSOLIDATION PROMPT
                        </Button>
                        
                        <Collapse in={showPromptEditor}>
                            <Stack spacing={1} sx={{ p: 2, bgcolor: 'rgba(33, 150, 243, 0.05)', borderRadius: 2, border: '1px solid rgba(21, 101, 192, 0.2)' }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" fontWeight={800} color="info.main">ADJUST CONSOLIDATION AGENT</Typography>
                                    <Button size="small" startIcon={<ResetIcon />} onClick={(e) => { e.stopPropagation(); resetConsolidationPrompt(); }} sx={{ fontSize: '0.65rem' }}>Reset</Button>
                                </Box>
                                <TextField
                                    fullWidth
                                    multiline
                                    rows={8}
                                    variant="filled"
                                    value={consolidationPrompt}
                                    onChange={(e) => setConsolidationPrompt(e.target.value)}
                                    placeholder="Leave empty to use the default consolidation prompt..."
                                    sx={{ '& .MuiInputBase-input': { fontSize: '0.8rem', fontFamily: 'monospace' } }}
                                />
                                <Button 
                                    size="small" 
                                    variant="contained" 
                                    color="info"
                                    onClick={(e) => { e.stopPropagation(); consolidateBatch(attachedBatch.id, consolidationPrompt || null); }}
                                    startIcon={<AiStatusIcon />}
                                    sx={{ alignSelf: 'flex-end', mt: 1 }}
                                >
                                    RE-RUN AGENT
                                </Button>
                            </Stack>
                        </Collapse>
                    </Stack>
                </Box>
            </Collapse>
        </Box>
    );
};

export default StageThematicConsolidation;
