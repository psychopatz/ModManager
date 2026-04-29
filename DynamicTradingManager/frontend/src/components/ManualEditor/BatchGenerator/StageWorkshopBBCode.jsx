import React from 'react';
import { 
    Box, Typography, Stack, Collapse, IconButton, Button
} from '@mui/material';
import {
    ExpandMore as ExpandMoreIcon,
    ExpandLess as ExpandLessIcon,
    ContentCopy as CopyIcon,
    AutoFixHigh as AutoFixIcon,
    Terminal as WorkshopIcon
} from '@mui/icons-material';

const StageWorkshopBBCode = ({
    attachedBatch,
    sectionsExpanded,
    setSectionsExpanded,
    consolidateBatch,
    consolidationPrompt,
    saveBatchVolume,
    setStatus,
}) => {
    const isLocked = !attachedBatch.workshopMetadata && attachedBatch.progress < 100;

    return (
        <Box sx={{ 
            bgcolor: 'rgba(255,255,255,0.03)', 
            borderRadius: 1.5, 
            border: '1px solid rgba(255,255,255,0.05)',
            opacity: isLocked ? 0.4 : 1,
            pointerEvents: isLocked ? 'none' : 'auto'
        }}>
            <Box 
                sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: isLocked ? 'default' : 'pointer', p: 1 }}
                onClick={() => !isLocked && setSectionsExpanded(prev => ({ ...prev, workshop: !prev.workshop }))}
            >
                <Stack direction="row" spacing={1} alignItems="center">
                    {sectionsExpanded.workshop ? <ExpandLessIcon sx={{ fontSize: 18 }} /> : <ExpandMoreIcon sx={{ fontSize: 18 }} />}
                    <WorkshopIcon sx={{ fontSize: 18, color: 'success.main' }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 800, letterSpacing: '0.05em' }}>STAGE 3: WORKSHOP BBCODE</Typography>
                </Stack>
                {isLocked && <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.disabled', fontSize: '0.6rem' }}>LOCKED</Typography>}
            </Box>

            <Collapse in={sectionsExpanded.workshop}>
                <Box sx={{ pl: 2, pb: 2, pr: 1 }}>
                    {attachedBatch.workshopMetadata ? (
                        <Box sx={{ p: 1.5, bgcolor: 'rgba(0,0,0,0.2)', borderRadius: 1.5, border: '1px solid rgba(255,255,255,0.05)', position: 'relative' }}>
                            <IconButton 
                                size="small" 
                                sx={{ position: 'absolute', top: 5, right: 5, opacity: 0.5, '&:hover': { opacity: 1 } }}
                                onClick={() => {
                                    navigator.clipboard.writeText(attachedBatch.workshopMetadata);
                                    setStatus({ type: 'success', message: 'BBCode copied!' });
                                }}
                            >
                                <CopyIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap', color: '#c9d1d9', fontSize: '0.7rem' }}>
                                {attachedBatch.workshopMetadata}
                            </Typography>
                        </Box>
                    ) : (
                        <Button 
                            size="small" 
                            variant="outlined" 
                            startIcon={<AutoFixIcon />}
                            onClick={() => consolidateBatch(attachedBatch.id, consolidationPrompt)}
                        >
                            Generate Workshop Metadata
                        </Button>
                    )}

                    {attachedBatch.workshopMetadata && (
                        <Button
                            fullWidth
                            variant="contained"
                            color="success"
                            startIcon={<AutoFixIcon />}
                            onClick={() => saveBatchVolume(attachedBatch.id)}
                            disabled={attachedBatch.status === 'saving'}
                            sx={{ mt: 2, fontWeight: 800 }}
                        >
                            {attachedBatch.status === 'saving' ? 'Saving Volume...' : 'COMMIT BATCH TO MANUALS'}
                        </Button>
                    )}
                </Box>
            </Collapse>
        </Box>
    );
};

export default StageWorkshopBBCode;
