import React, { useState } from 'react';
import { 
  Button, 
  Stack, 
  TextField, 
  Alert, 
  Snackbar, 
  Box, 
  Typography, 
  Grid,
  Paper
} from '@mui/material';
import { 
  Search as SearchIcon,
  List as ListIcon,
  BarChart as StatsIcon,
  Description as DocsIcon,
  LocalShipping as SpawnIcon
} from '@mui/icons-material';
import * as api from '../services/api';

const Actions = ({ onTaskStarted }) => {
    const [propName, setPropName] = useState('');
    const [valueFilter, setValueFilter] = useState('');
    const [minUsage, setMinUsage] = useState(1);
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
                        <Button 
                            variant="contained" 
                            color="primary"
                            startIcon={<SearchIcon />}
                            onClick={async () => {
                                try {
                                    const res = await api.syncSandboxOptions();
                                    setSnackbar({ 
                                        open: true, 
                                        message: `Successfully synced ${res.data.options_count} sandbox options!`, 
                                        severity: 'success' 
                                    });
                                } catch (err) {
                                    setSnackbar({ 
                                        open: true, 
                                        message: 'Failed to sync sandbox options', 
                                        severity: 'error' 
                                    });
                                }
                            }}
                            fullWidth
                            sx={{ mt: 1 }}
                        >
                            Sync MarketSense Sandbox
                        </Button>
                    </Paper>
                </Grid>
            </Grid>

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
