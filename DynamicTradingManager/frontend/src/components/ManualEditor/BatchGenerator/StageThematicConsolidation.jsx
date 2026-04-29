import React from 'react';
import { 
    Box, Typography, Stack, Collapse, TextField, Button
} from '@mui/material';
import {
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    AutoFixHigh as ConsolidationIcon,
    AutoAwesome as AiStatusIcon,
    RestartAlt as ResetIcon
} from '@mui/icons-material';

const StageThematicConsolidation = ({
    attachedBatch,
    sectionsExpanded,
    setSectionsExpanded,
    showConsolidationSettings,
    setShowConsolidationSettings,
    consolidationPrompt,
    setConsolidationPrompt,
    resetConsolidationPrompt,
    consolidateBatch,
}) => {
    const isLocked = attachedBatch.status !== 'success' && attachedBatch.progress < 100;

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
                </Stack>
                {isLocked && <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.disabled', fontSize: '0.6rem' }}>LOCKED</Typography>}
            </Box>

            <Collapse in={sectionsExpanded.consolidation}>
                <Box sx={{ pl: 2, pb: 2, pr: 1 }}>
                    <Stack spacing={2}>
                        {(attachedBatch.consolidatedPages || []).map((page, idx) => (
                            <Box key={idx} sx={{ p: 1.5, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 1.5, border: '1px solid rgba(255,255,255,0.05)' }}>
                                <Typography variant="caption" sx={{ fontWeight: 800, color: 'info.main', display: 'block', mb: 0.5 }}>{page.title.toUpperCase()}</Typography>
                                <Typography variant="caption" sx={{ opacity: 0.6, fontSize: '0.7rem' }}>
                                    Merged {page.blocks.filter(b => b.type === 'heading').length} sections into this theme.
                                </Typography>
                            </Box>
                        ))}

                        <Button 
                            size="small" 
                            variant="text" 
                            onClick={() => setShowConsolidationSettings(!showConsolidationSettings)}
                            startIcon={showConsolidationSettings ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            sx={{ alignSelf: 'flex-start', fontSize: '0.65rem' }}
                        >
                            Refine Consolidation Prompt
                        </Button>
                        
                        <Collapse in={showConsolidationSettings}>
                            <Stack spacing={1} sx={{ mt: 1, p: 2, bgcolor: 'rgba(33, 150, 243, 0.05)', borderRadius: 2, border: '1px solid rgba(21, 101, 192, 0.2)' }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" fontWeight={800} color="primary.main">ADJUST CONSOLIDATION AGENT</Typography>
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
                                <Button 
                                    size="small" 
                                    variant="contained" 
                                    onClick={() => consolidateBatch(attachedBatch.id, consolidationPrompt)}
                                    startIcon={<AiStatusIcon />}
                                    sx={{ alignSelf: 'flex-end', mt: 1 }}
                                >
                                    Re-run Agent
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
