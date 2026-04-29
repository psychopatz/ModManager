import React, { Suspense, lazy, useState } from 'react';
import { ThemeProvider, createTheme, CssBaseline, Container, Typography, Box, AppBar, Toolbar, Button, CircularProgress, IconButton, Tooltip } from '@mui/material';
import { BrowserRouter, Routes, Route, Link as RouterLink } from 'react-router-dom';
import SmartToyIcon from '@mui/icons-material/SmartToy';

const Dashboard = lazy(() => import('./components/Dashboard'));
const ItemsPage = lazy(() => import('./components/ItemsPage'));
const PricingPage = lazy(() => import('./components/PricingPage'));
const TagPricingPage = lazy(() => import('./components/TagPricingPage'));
const ArchetypeEditorPage = lazy(() => import('./components/ArchetypeEditorPage'));
const DonatorsPage = lazy(() => import('./components/DonatorsPage'));
const ManualEditorPage = lazy(() => import('./components/ManualEditorPage'));
const UpdateVersionEditorPage = lazy(() => import('./components/UpdateVersionEditorPage'));
const SimulationDashboard = lazy(() => import('./components/Simulation/SimulationDashboard'));
const ConsolePage = lazy(() => import('./components/ConsolePage'));
const WorkshopPage = lazy(() => import('./components/WorkshopPage'));
const LLMSettingsPanel = lazy(() => import('./components/LLM/LLMSettingsPanel'));
const LLMChatFloating = lazy(() => import('./components/LLM/LLMChatFloating'));

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
  },
});

import { BatchProvider } from './context/BatchContext';
import { LLMProvider } from './context/LLMContext';
import BatchFloatingOverlay from './components/ManualEditor/BatchFloatingOverlay';
import BatchUpdateGenerator from './components/ManualEditor/BatchUpdateGenerator';

function App() {
  const [llmOpen, setLlmOpen] = useState(false);

  return (
    <ThemeProvider theme={darkTheme}>
      <LLMProvider>
        <BatchProvider>
          <CssBaseline />
          <BrowserRouter>
            <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
              <AppBar position="static">
                {/* ... existing header ... */}
                <Toolbar>
                  <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                  Dynamic Trading Manager
                  </Typography>
                  <Button color="inherit" component={RouterLink} to="/">Dashboard</Button>
                  <Button color="inherit" component={RouterLink} to="/items">Vanilla Items</Button>
                  <Button color="inherit" component={RouterLink} to="/pricing">Pricing Model</Button>
                  <Button color="inherit" component={RouterLink} to="/pricing/tags">Tag Pricing</Button>
                  <Button color="inherit" component={RouterLink} to="/archetypes">Archetype Editor</Button>
                  <Button color="inherit" component={RouterLink} to="/donators">Donators</Button>
                  <Button color="inherit" component={RouterLink} to="/manuals">Manual Editor</Button>
                  <Button color="inherit" component={RouterLink} to="/updates">Update Version Editor</Button>
                  <Button color="inherit" component={RouterLink} to="/simulation">Economy Simulation</Button>
                  <Button color="inherit" component={RouterLink} to="/workshop">Workshop</Button>
                  <Button color="inherit" component={RouterLink} to="/console">Console</Button>
                  <Tooltip title="LLM Provider Settings">
                    <IconButton color="inherit" onClick={() => setLlmOpen(true)} sx={{ ml: 1 }}>
                      <SmartToyIcon />
                    </IconButton>
                  </Tooltip>
                </Toolbar>
              </AppBar>
              <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Suspense fallback={(
                  <Box sx={{ minHeight: 320, display: 'grid', placeItems: 'center' }}>
                    <CircularProgress />
                  </Box>
                )}
                >
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/items" element={<ItemsPage />} />
                    <Route path="/pricing" element={<PricingPage />} />
                    <Route path="/pricing/tags" element={<TagPricingPage />} />
                    <Route path="/archetypes" element={<ArchetypeEditorPage />} />
                    <Route path="/donators" element={<DonatorsPage />} />
                    <Route path="/manuals" element={<ManualEditorPage />} />
                    <Route path="/updates" element={<UpdateVersionEditorPage />} />
                    <Route path="/simulation" element={<SimulationDashboard />} />
                    <Route path="/workshop" element={<WorkshopPage />} />
                    <Route path="/console" element={<ConsolePage />} />
                  </Routes>
                </Suspense>
              </Container>
              <BatchFloatingOverlay />
              <BatchUpdateGenerator />
              <Suspense fallback={null}>
                <LLMSettingsPanel open={llmOpen} onClose={() => setLlmOpen(false)} />
                <Box sx={{ position: 'fixed', bottom: 100, right: 24, zIndex: 5000, pointerEvents: 'none' }}>
                    <LLMChatFloating />
                </Box>
              </Suspense>
            </Box>
        </BrowserRouter>
        </BatchProvider>
      </LLMProvider>
    </ThemeProvider>
  );
}

export default App;

