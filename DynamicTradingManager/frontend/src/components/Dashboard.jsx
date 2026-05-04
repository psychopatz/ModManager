import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Divider,
  Chip,
  ThemeProvider,
  createTheme,
  CssBaseline
} from '@mui/material';
import Actions from './Actions';
import TaskConsole from './TaskConsole';
import { getStats } from '../services/api';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#007acc' },
    secondary: { main: '#6a1b9a' },
    background: { default: '#0a0a0a', paper: '#121212' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 800, letterSpacing: '-0.02em' },
  }
});

const Dashboard = () => {
  const [stats, setStats] = useState({
    total_runtime: 0,
    total_vanilla: 0,
    total_modded: 0,
    registered_vanilla: 0,
    unregistered_vanilla: 0,
    mod_breakdown: {},
    source: 'dt_items',
    total_scripts: 0,
    blacklisted: 0,
    whitelisted: 0,
    overrides: 0,
    notifications: []
  });
  const [activeTaskId, setActiveTaskId] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await getStats();
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', py: 4, px: 2 }}>
        <Container maxWidth="xl">
          <Typography variant="h4" gutterBottom sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ width: 40, height: 40, bgcolor: 'primary.main', borderRadius: 1 }} />
            Dynamic Trading Manager
          </Typography>

          <Grid container spacing={3}>
            {/* Stats Cards */}
            <Grid size={{ xs: 12, sm: 10, md: 8, lg: 6 }} sx={{ mx: 'auto' }}>
              <Paper sx={{ p: 4, textAlign: 'center', borderTop: '4px solid #007acc' }}>
                <Typography color="textSecondary" variant="overline" sx={{ letterSpacing: 1.5 }}>Local Items Database</Typography>
                <Typography variant="h2" sx={{ my: 2 }}>{(stats.total_runtime ?? 0).toLocaleString()}</Typography>
                <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.9rem', display: 'block', mb: 1 }}>
                  {stats.registered_vanilla} Registered | {stats.unregistered_vanilla} Unregistered | {stats.total_modded} Modded
                </Typography>
                <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.75rem', display: 'block', opacity: 0.7, fontStyle: 'italic' }}>
                  {stats.total_scripts} Vanilla Script Items found in Game Files
                </Typography>

                {Object.keys(stats.mod_breakdown).length > 0 && (
                  <Box sx={{ mt: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="textSecondary" sx={{ letterSpacing: 1, display: 'block', mb: 1 }}>
                      DETECTED MODS
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'center' }}>
                      {Object.entries(stats.mod_breakdown).map(([modName, count]) => (
                        <Chip 
                          key={modName} 
                          label={`${modName}: ${count}`} 
                          size="small" 
                          variant="outlined" 
                          sx={{ fontSize: '0.65rem', borderColor: 'rgba(255,255,255,0.1)' }} 
                        />
                      ))}
                    </Box>
                  </Box>
                )}
                
                {/* Embed Blacklist, Whitelist, Overrides cleanly beneath */}
                <Divider sx={{ my: 2, opacity: 0.1 }} />
                <Grid container spacing={2} justifyContent="center">
                  <Grid size={4}>
                    <Typography variant="h6" sx={{ color: '#f44336' }}>{stats.blacklisted}</Typography>
                    <Typography variant="caption" color="textSecondary">Blacklisted</Typography>
                  </Grid>
                  <Grid size={4}>
                    <Typography variant="h6" sx={{ color: '#4caf50' }}>{stats.whitelisted}</Typography>
                    <Typography variant="caption" color="textSecondary">Whitelisted</Typography>
                  </Grid>
                  <Grid size={4}>
                    <Typography variant="h6" sx={{ color: '#ff9800' }}>{stats.overrides}</Typography>
                    <Typography variant="caption" color="textSecondary">Overrides</Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
            {/* Actions & Tools */}
            <Grid size={12}>
              <Paper sx={{ p: 0, overflow: 'hidden' }}>
                <Actions onTaskStarted={setActiveTaskId} />
              </Paper>
            </Grid>

          </Grid>
        </Container>

        {/* Real-time Task Console */}
        <TaskConsole 
            taskId={activeTaskId} 
            onClose={() => {
                setActiveTaskId(null);
                fetchStats(); // Update stats when console closes (task likely finished)
            }} 
        />
      </Box>
    </ThemeProvider>
  );
};

export default Dashboard;
