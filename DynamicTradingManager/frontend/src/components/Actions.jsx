import React, { useState } from 'react';
import { 
  Button, 
  Stack, 
  TextField, 
  Alert, 
  Snackbar, 
  Box, 
  Typography, 
  Divider, 
  Grid,
  Paper,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { 
  Refresh as RefreshIcon, 
  Add as AddIcon, 
  DeleteForever as DeleteIcon,
  Search as SearchIcon,
  List as ListIcon,
  BarChart as StatsIcon,
  Description as DocsIcon,
  LocalShipping as SpawnIcon
} from '@mui/icons-material';
import * as api from '../services/api';

const Actions = ({ onTaskStarted }) => {
    const [batchSize, setBatchSize] = useState(50);
    const [propName, setPropName] = useState('');
    const [valueFilter, setValueFilter] = useState('');
    const [minUsage, setMinUsage] = useState(1);
    const [resetDialogOpen, setResetDialogOpen] = useState(false);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

    const handleAction = async (actionFn, ...args) => {
        try {
            const res = await actionFn(...args);
            if (res.data.task_id) {
                onTaskStarted(res.data.task_id);
                setSnackbar({ open: true, message: 'Task started successfully', severity: 'success' });
            }
        } catch (err) {
            setSnackbar({ open: true, message: 'Failed to trigger action', severity: 'error' });
        }
    };

    return (
        <Box sx={{ p: 2 }}>
            <Grid container spacing={3}>
                {/* Core Registry Management */}
                <Grid size={12}>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        Registry Management
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'rgba(0,0,0,0.02)' }}>
                        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
                            <Button 
                                variant="contained" 
                                startIcon={<RefreshIcon />}
                                onClick={() => handleAction(api.triggerUpdate)}
                            >
                                Update Prices/Stock
                            </Button>
                            
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <TextField 
                                    label="Batch Size" 
                                    type="number" 
                                    value={batchSize} 
                                    onChange={(e) => setBatchSize(parseInt(e.target.value) || 50)}
                                    size="small"
                                    sx={{ width: 100 }}
                                />
                                <Button 
                                    variant="contained" 
                                    color="secondary" 
                                    startIcon={<AddIcon />}
                                    onClick={() => handleAction(api.triggerAdd, batchSize)}
                                >
                                    Add Items Batch
                                </Button>
                            </Box>

                            <Button 
                                variant="contained" 
                                color="secondary" 
                                onClick={() => handleAction(api.triggerAdd, 'all')}
                            >
                                Generate All Items
                            </Button>

                            <Button 
                                variant="outlined" 
                                color="error" 
                                startIcon={<DeleteIcon />}
                                onClick={() => setResetDialogOpen(true)}
                            >
                                Delete All Items
                            </Button>
                        </Stack>
                    </Paper>
                </Grid>

                {/* Analysis Tools */}
                <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="h6" gutterBottom>Property Analysis</Typography>
                    <Paper variant="outlined" sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                             <TextField 
                                label="Property Name" 
                                value={propName} 
                                onChange={(e) => setPropName(e.target.value)}
                                size="small"
                                placeholder="e.g. Tags"
                            />
                            <TextField 
                                label="Value Filter (Optional)" 
                                value={valueFilter} 
                                onChange={(e) => setValueFilter(e.target.value)}
                                size="small"
                            />
                            <Button 
                                variant="contained" 
                                onClick={() => handleAction(api.triggerFindProperty, propName, valueFilter)}
                                disabled={!propName}
                            >
                                <SearchIcon />
                            </Button>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <TextField 
                                label="Min Usage" 
                                type="number"
                                value={minUsage} 
                                onChange={(e) => setMinUsage(parseInt(e.target.value) || 1)}
                                size="small"
                                sx={{ width: 100 }}
                            />
                            <Button 
                                variant="outlined" 
                                startIcon={<ListIcon />}
                                onClick={() => handleAction(api.triggerListProperties, minUsage)}
                            >
                                List All Properties
                            </Button>
                        </Box>
                        <Button 
                            variant="outlined" 
                            startIcon={<DocsIcon />}
                            onClick={() => handleAction(api.triggerGenerateDocs)}
                        >
                            Generate Parameters Doc
                        </Button>
                    </Paper>
                </Grid>

                {/* Growth & Economy */}
                <Grid size={{ xs: 12, md: 6 }}>
                    <Typography variant="h6" gutterBottom>Economy & Spawns</Typography>
                    <Paper variant="outlined" sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <Button 
                            variant="contained" 
                            color="success"
                            startIcon={<SpawnIcon />}
                            onClick={() => handleAction(api.triggerAnalyzeSpawns)}
                            fullWidth
                        >
                            Analyze Global Spawn Rates
                        </Button>
                        <Button 
                            variant="outlined" 
                            startIcon={<StatsIcon />}
                            onClick={() => handleAction(api.triggerRarityStats)}
                            fullWidth
                        >
                            View Rarity Distribution
                        </Button>
                    </Paper>
                </Grid>
            </Grid>

            {/* Delete All Confirmation Dialog */}
            <Dialog open={resetDialogOpen} onClose={() => setResetDialogOpen(false)}>
                <DialogTitle sx={{ color: 'error.main' }}>Confirm Delete All Items?</DialogTitle>
                <DialogContent>
                    <Typography>
                        This will permanently delete the entire Items folder and all registered item files. 
                        This action cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
                    <Button 
                        color="error" 
                        variant="contained" 
                        onClick={() => {
                            setResetDialogOpen(false);
                            handleAction(api.triggerReset);
                        }}
                    >
                        DELETE ALL
                    </Button>
                </DialogActions>
            </Dialog>

            <Snackbar 
                open={snackbar.open} 
                autoHideDuration={4000} 
                onClose={() => setSnackbar({ ...snackbar, open: false })}
            >
                <Alert severity={snackbar.severity} sx={{ width: '100%' }}>
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    );
};

export default Actions;
