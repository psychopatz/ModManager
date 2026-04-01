import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Container, 
  Grid, 
  Paper, 
  Typography, 
  Divider,
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
    total_vanilla: 0,
    registered: 0,
    unregistered: 0,
    coverage: 0,
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
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper sx={{ p: 3, textAlign: 'center', borderTop: '4px solid #007acc' }}>
                <Typography color="textSecondary" variant="overline">Total Vanilla</Typography>
                <Typography variant="h3">{stats.total_vanilla.toLocaleString()}</Typography>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper sx={{ p: 3, textAlign: 'center', borderTop: '4px solid #4caf50' }}>
                <Typography color="textSecondary" variant="overline">Registered</Typography>
                <Typography variant="h3" sx={{ color: '#4caf50' }}>{stats.registered.toLocaleString()}</Typography>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper sx={{ p: 3, textAlign: 'center', borderTop: '4px solid #ff9800' }}>
                <Typography color="textSecondary" variant="overline">Unregistered</Typography>
                <Typography variant="h3" sx={{ color: '#ff9800' }}>{stats.unregistered.toLocaleString()}</Typography>
              </Paper>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Paper sx={{ p: 3, textAlign: 'center', borderTop: '4px solid #9c27b0' }}>
                <Typography color="textSecondary" variant="overline">Coverage</Typography>
                <Typography variant="h3" sx={{ color: '#9c27b0' }}>{stats.coverage}%</Typography>
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
