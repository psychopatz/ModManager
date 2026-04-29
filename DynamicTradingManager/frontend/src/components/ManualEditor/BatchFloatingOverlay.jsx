import React, { useState } from 'react';
import { Box, Paper, Typography, LinearProgress, IconButton, Stack, Collapse, Chip } from '@mui/material';
import { 
  Close as CloseIcon, 
  KeyboardArrowUp as ExpandIcon, 
  KeyboardArrowDown as CollapseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  OpenInFull as MaximizeIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon
} from '@mui/icons-material';
import { useBatchSystem } from '../../context/BatchContext';
import LLMChatFloating from '../LLM/LLMChatFloating';

const BatchWidget = ({ batch }) => {
  const [expanded, setExpanded] = useState(false);
  const { dismissBatch, openFullView } = useBatchSystem();

  const isError = batch.status === 'error';
  const isSuccess = batch.status === 'success';
  const isProcessing = batch.status === 'processing';

  return (
    <Paper
      elevation={6}
      sx={{
        width: expanded ? 450 : 280,
        mb: 2,
        overflow: 'hidden',
        background: 'rgba(30, 30, 30, 0.9)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        borderRadius: 2,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        boxShadow: expanded ? '0 12px 40px rgba(0,0,0,0.5)' : '0 4px 20px rgba(0,0,0,0.3)',
        pointerEvents: 'auto'
      }}
    >
      <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" noWrap sx={{ fontWeight: 'bold' }}>
            {batch.modName}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap display="block">
            {batch.currentStep}
          </Typography>
        </Box>
        
        {isSuccess && <SuccessIcon color="success" fontSize="small" />}
        {isError && <ErrorIcon color="error" fontSize="small" />}
        
        <IconButton size="small" onClick={() => setExpanded(!expanded)}>
          {expanded ? <CollapseIcon fontSize="inherit" /> : <ExpandIcon fontSize="inherit" />}
        </IconButton>
        <IconButton size="small" onClick={() => openFullView(batch.id)}>
          <MaximizeIcon fontSize="inherit" />
        </IconButton>
        <IconButton size="small" onClick={() => dismissBatch(batch.id)}>
          <CloseIcon fontSize="inherit" />
        </IconButton>
      </Box>

      <LinearProgress 
        variant="determinate" 
        value={batch.progress} 
        color={isError ? "error" : isSuccess ? "success" : "primary"}
        sx={{ height: 4 }}
      />

      <Collapse in={expanded}>
        <Box sx={{ p: 1.5, pt: 1, maxHeight: 200, overflowY: 'auto', bgcolor: 'rgba(0,0,0,0.2)' }}>
          <Stack spacing={0.5}>
            {(batch.logs || []).slice(-5).map((log, i) => {
              const type = log[1];
              let color = '#bdbdbd'; // Default grey
              
              // Mapping semantic types to colors
              const typeMap = {
                'success': '#4caf50',
                'error': '#f44336',
                'warning': '#ff9800',
                'system': '#2196f3',
                'feat': '#3b82f6',
                'fix': '#ef4444',
                'refactor': '#f59e0b',
                'perf': '#8b5cf6',
                'docs': '#10b981',
                'chore': '#6b7280',
                'style': '#ec4899',
                'test': '#6366f1'
              };
              
              if (typeMap[type]) color = typeMap[type];

              return (
                <Typography key={i} variant="caption" sx={{ 
                  fontFamily: '"Fira Code", "Roboto Mono", monospace',
                  color: color,
                  display: 'block',
                  fontSize: '0.7rem',
                  lineHeight: 1.2,
                  mb: 0.2
                }}>
                  <span style={{ opacity: 0.4, marginRight: 4 }}>{log[0]}</span>
                  {log[2]}
                </Typography>
              );
            })}
          </Stack>
          {isError && (
             <Typography variant="caption" color="error" sx={{ mt: 1, display: 'block', fontWeight: 'bold' }}>
                Error: {batch.error}
             </Typography>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

const BatchFloatingOverlay = () => {
  const { batches, openBatchId } = useBatchSystem();

  if (!batches || batches.length === 0) return null;

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 24,
        left: 24,
        zIndex: 5000, 
        display: 'flex',
        flexDirection: 'column-reverse',
        alignItems: 'flex-start',
        pointerEvents: 'none'
      }}
    >
      <Box sx={{ pointerEvents: 'auto' }}> 
        {batches.map(batch => (
          // Hide from floating overlay if full monitor is open for this batch, or if it is manually dismissed
          (openBatchId !== batch.id && !batch.dismissed) && <BatchWidget key={batch.id} batch={batch} />
        ))}
      </Box>
    </Box>
  );
};

export default BatchFloatingOverlay;
