import React from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    List,
    ListItem,
    ListItemText,
    IconButton,
    Typography,
    Chip,
    Stack,
    Box,
    Tooltip
} from '@mui/material';
import {
    Delete as DeleteIcon,
    OpenInNew as OpenIcon,
    Refresh as RefreshIcon,
    Close as CloseIcon
} from '@mui/icons-material';
import { useBatchSystem } from '../../context/BatchContext';

const BatchHistoryModal = ({ open, onClose, onOpenBatch }) => {
    const { batches, removeBatch, restartBatch } = useBatchSystem();

    // Sort batches by start time (newest first)
    const sortedBatches = [...batches].sort((a, b) => (b.startTime || 0) - (a.startTime || 0));

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                Batch Generation History
                <IconButton onClick={onClose} size="small">
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent dividers sx={{ p: 0 }}>
                {sortedBatches.length === 0 ? (
                    <Box sx={{ p: 4, textAlign: 'center', opacity: 0.5 }}>
                        <Typography variant="body1">No batch history found.</Typography>
                        <Typography variant="caption">Start a new batch generation to see it here.</Typography>
                    </Box>
                ) : (
                    <List disablePadding>
                        {sortedBatches.map((batch, index) => {
                            const isCompleted = batch.status === 'success';
                            const isError = batch.status === 'error';
                            const isProcessing = batch.status === 'processing';
                            
                            const dateRange = (batch.config?.since && batch.config?.until) 
                                ? `${batch.config.since} → ${batch.config.until}`
                                : 'Unknown Date Range';

                            return (
                                <ListItem 
                                    key={batch.id} 
                                    divider={index !== sortedBatches.length - 1}
                                    sx={{ 
                                        flexDirection: 'column', 
                                        alignItems: 'flex-start',
                                        bgcolor: isProcessing ? 'rgba(59, 130, 246, 0.05)' : 'transparent',
                                        py: 2
                                    }}
                                >
                                    <Stack direction="row" spacing={2} width="100%" alignItems="flex-start" justifyContent="space-between">
                                        <Box>
                                            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
                                                {batch.modName || batch.module}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary" display="block">
                                                {dateRange} • {batch.pages?.length || 0} pages cached
                                            </Typography>
                                            <Typography variant="caption" sx={{ opacity: 0.6 }}>
                                                Last Step: {batch.currentStep}
                                            </Typography>
                                        </Box>
                                        
                                        <Stack alignItems="flex-end" spacing={1}>
                                            <Chip 
                                                label={batch.status.toUpperCase()} 
                                                size="small" 
                                                color={isCompleted ? 'success' : isError ? 'error' : 'primary'}
                                                variant={isProcessing ? 'filled' : 'outlined'}
                                                sx={{ height: 20, fontSize: '0.65rem', fontWeight: 800 }}
                                            />
                                            {isProcessing && (
                                                <Typography variant="caption" color="primary.main" fontWeight={800}>
                                                    {batch.progress}%
                                                </Typography>
                                            )}
                                        </Stack>
                                    </Stack>

                                    <Stack direction="row" spacing={1} sx={{ mt: 2, width: '100%', justifyContent: 'flex-end' }}>
                                        <Tooltip title="Delete History">
                                            <IconButton 
                                                size="small" 
                                                color="error"
                                                onClick={() => removeBatch(batch.id)}
                                            >
                                                <DeleteIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>

                                        {!isProcessing && (
                                            <Tooltip title="Force Restart">
                                                <IconButton 
                                                    size="small" 
                                                    color="warning"
                                                    onClick={() => restartBatch(batch.id)}
                                                >
                                                    <RefreshIcon fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                        )}

                                        <Button 
                                            size="small" 
                                            variant="contained" 
                                            color="primary"
                                            startIcon={<OpenIcon />}
                                            onClick={() => {
                                                onOpenBatch(batch.id);
                                                onClose();
                                            }}
                                            sx={{ ml: 2 }}
                                        >
                                            Open View
                                        </Button>
                                    </Stack>
                                </ListItem>
                            );
                        })}
                    </List>
                )}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
};

export default BatchHistoryModal;
