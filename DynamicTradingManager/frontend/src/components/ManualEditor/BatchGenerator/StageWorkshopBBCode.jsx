import React, { useEffect, useState } from 'react';
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
import BBCodeEditorPreview from '../../Common/BBCodeEditorPreview';

const LOG_COLORS = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', system: '#60a5fa', info: '#9ca3af' };

const StageWorkshopBBCode = ({
    attachedBatch,
    sectionsExpanded,
    setSectionsExpanded,
    consolidateBatch,
    consolidationPrompt,
    setBatchWorkshopMetadata,
    setStatus,
}) => {
    const isLocked = !attachedBatch.workshopMetadata && attachedBatch.progress < 100;
    const logs = attachedBatch.logs || [];
    const [draftMetadata, setDraftMetadata] = useState(attachedBatch.workshopMetadata || '');

    useEffect(() => {
        setDraftMetadata(attachedBatch.workshopMetadata || '');
    }, [attachedBatch.id, attachedBatch.workshopMetadata]);

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
                    {attachedBatch.generatedUpdateTitle && (
                        <Typography variant="caption" sx={{ display: 'block', mb: 1.5, fontWeight: 700, color: 'success.main' }}>
                            📌 {attachedBatch.generatedUpdateTitle}
                        </Typography>
                    )}

                    {/* LOGS */}
                    {logs.length > 0 && (
                        <Box sx={{ mb: 2, p: 1, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 1.5, border: '1px solid rgba(255,255,255,0.05)', maxHeight: 160, overflowY: 'auto' }}>
                            <Typography variant="caption" sx={{ fontWeight: 800, opacity: 0.5, display: 'block', mb: 0.5, fontSize: '0.6rem' }}>BATCH LOGS</Typography>
                            {logs.map(([ts, type, msg], i) => (
                                <Typography key={i} variant="caption" sx={{ display: 'block', fontFamily: 'monospace', fontSize: '0.65rem', color: LOG_COLORS[type] || '#9ca3af' }}>
                                    <span style={{ opacity: 0.5 }}>{ts}</span> {msg}
                                </Typography>
                            ))}
                        </Box>
                    )}

                    {attachedBatch.workshopMetadata ? (
                        <Box sx={{ position: 'relative' }}>
                            <IconButton 
                                size="small" 
                                sx={{ position: 'absolute', top: 5, right: 5, opacity: 0.5, '&:hover': { opacity: 1 }, zIndex: 2 }}
                                onClick={() => {
                                    navigator.clipboard.writeText(draftMetadata || attachedBatch.workshopMetadata);
                                    setStatus({ type: 'success', message: 'BBCode copied!' });
                                }}
                            >
                                <CopyIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                            <BBCodeEditorPreview
                                label="Workshop BBCode"
                                value={draftMetadata}
                                onChange={(next) => {
                                    setDraftMetadata(next);
                                    setBatchWorkshopMetadata?.(attachedBatch.id, next);
                                }}
                                editable
                                minRows={6}
                                maxRows={22}
                                editorHelperText="Stage 3 output is editable here and updates live."
                                previewTitle="Rendered Workshop Preview"
                                compact
                            />
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
                            color="info"
                            startIcon={<CopyIcon />}
                            onClick={() => {
                                navigator.clipboard.writeText(draftMetadata || attachedBatch.workshopMetadata);
                                setStatus({ type: 'success', message: 'Workshop update BBCode copied!' });
                            }}
                            sx={{ mt: 2, fontWeight: 800 }}
                        >
                            COPY WORKSHOP UPDATE
                        </Button>
                    )}
                </Box>
            </Collapse>
        </Box>
    );
};

export default StageWorkshopBBCode;
