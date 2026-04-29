import React from 'react';
import { Stack, Box, Typography, Alert, LinearProgress, Button } from '@mui/material';
import { 
    CheckCircle as SuccessIcon, 
    Error as ErrorIcon,
    Refresh as RefreshIcon,
    ContentCopy as CopyIcon
} from '@mui/icons-material';
import AiMonitor from './AiMonitor';
import StageDailyRefinement from './StageDailyRefinement';
import StageThematicConsolidation from './StageThematicConsolidation';
import StageWorkshopBBCode from './StageWorkshopBBCode';

const BatchProcessMonitor = ({
    attachedBatch,
    sectionsExpanded, setSectionsExpanded,
    getDayList, history, loading, getTypeColor, retryDay,
    showConsolidationSettings, setShowConsolidationSettings,
    consolidationPrompt, setConsolidationPrompt, 
    resetConsolidationPrompt, consolidateBatch,
    saveBatchVolume,
    setStatus, handleClose
}) => {
    if (!attachedBatch) return null;

    const streamingDay = Object.keys(attachedBatch.streamingData || {}).find(k => attachedBatch.streamingData[k].status === 'streaming');
    const isConsolidating = attachedBatch.streamingData?._consolidation?.status === 'streaming';
    
    // Active streaming state for AiMonitor
    const activeStreamingData = isConsolidating ? attachedBatch.streamingData._consolidation : (streamingDay ? attachedBatch.streamingData[streamingDay] : null);
    const activeStreamingTitle = isConsolidating ? "Thematic Consolidation" : (streamingDay ? `Refining ${streamingDay}` : "AI Monitor");

    return (
        <Stack spacing={2} sx={{ mt: 1 }}>
            <Box sx={{ bgcolor: 'rgba(255,255,255,0.03)', p: 1.5, borderRadius: 2, border: '1px solid rgba(255,255,255,0.05)' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 800, color: 'primary.main', letterSpacing: '0.1em' }}>BATCH PROGRESSION</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 800, opacity: 0.5 }}>{attachedBatch.progress}%</Typography>
                </Stack>
                <LinearProgress 
                    variant="determinate" 
                    value={attachedBatch.progress} 
                    sx={{ height: 6, borderRadius: 3, bgcolor: 'rgba(255,255,255,0.05)', '& .MuiLinearProgress-bar': { borderRadius: 3 } }} 
                />
                <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7, fontStyle: 'italic', textAlign: 'center' }}>
                    {attachedBatch.currentStep}
                </Typography>
            </Box>

            {/* Centralized AI Reasoning & Output Monitor */}
            <AiMonitor 
                title={activeStreamingTitle}
                thinking={activeStreamingData?.thinking}
                content={activeStreamingData?.content}
                status={activeStreamingData?.status}
                isAnyStreaming={!!activeStreamingData}
            />

            <Box sx={{ maxHeight: 600, overflowY: 'auto', pr: 1, '&::-webkit-scrollbar': { width: 4 }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 2 } }}>
                <Stack spacing={1}>
                    <StageDailyRefinement 
                        attachedBatch={attachedBatch}
                        sectionsExpanded={sectionsExpanded}
                        setSectionsExpanded={setSectionsExpanded}
                        getDayList={getDayList}
                        history={history}
                        loading={loading}
                        getTypeColor={getTypeColor}
                        retryDay={retryDay}
                    />

                    <StageThematicConsolidation 
                        attachedBatch={attachedBatch}
                        sectionsExpanded={sectionsExpanded}
                        setSectionsExpanded={setSectionsExpanded}
                        consolidationPrompt={consolidationPrompt}
                        setConsolidationPrompt={setConsolidationPrompt}
                        resetConsolidationPrompt={resetConsolidationPrompt}
                        consolidateBatch={consolidateBatch}
                    />

                    <StageWorkshopBBCode 
                        attachedBatch={attachedBatch}
                        sectionsExpanded={sectionsExpanded}
                        setSectionsExpanded={setSectionsExpanded}
                        consolidateBatch={consolidateBatch}
                        consolidationPrompt={consolidationPrompt}
                        saveBatchVolume={saveBatchVolume}
                        setStatus={setStatus}
                    />
                </Stack>
            </Box>

            {attachedBatch.status === 'success' && (
                <Alert severity="success" icon={<SuccessIcon />}>
                    Update successfully generated and saved to the backend.
                </Alert>
            )}

            {attachedBatch.status === 'error' && (
                <Alert severity="error" icon={<ErrorIcon />}>
                    {attachedBatch.error}
                </Alert>
            )}
        </Stack>
    );
};

export default BatchProcessMonitor;
