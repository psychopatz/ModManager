import React, { useEffect, useState } from 'react';
import {
  Box,
  CircularProgress,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';

import * as api from '../services/api';
import { useLLMInternal } from '../context/LLMContext';
import GeolocatorHeader from './Geolocator/GeolocatorHeader';
import GeolocatorModdedTab from './Geolocator/GeolocatorModdedTab';
import GeolocatorVanillaTab from './Geolocator/GeolocatorVanillaTab';
import { buildActiveLLMConfig } from './Geolocator/geolocatorUtils';

const targetStorageKey = 'dt_geolocator_target';
const moduleStorageKey = 'dt_geolocator_module';
const modeStorageKey = 'dt_geolocator_mode';

const GeolocatorPage = () => {
  const [targets, setTargets] = useState([]);
  const [modules, setModules] = useState([]);
  const [selectedTarget, setSelectedTarget] = useState(() => localStorage.getItem(targetStorageKey) || '');
  const [selectedModule, setSelectedModule] = useState(() => localStorage.getItem(moduleStorageKey) || 'DynamicTradingCommon');
  const [activeMode, setActiveMode] = useState(() => localStorage.getItem(modeStorageKey) || 'modded');
  const [loadingContext, setLoadingContext] = useState(true);
  const { config: llmStateConfig } = useLLMInternal();
  const activeLLMConfig = buildActiveLLMConfig(llmStateConfig);

  useEffect(() => {
    loadTargets();
  }, []);

  useEffect(() => {
    localStorage.setItem(targetStorageKey, selectedTarget);
  }, [selectedTarget]);

  useEffect(() => {
    localStorage.setItem(moduleStorageKey, selectedModule);
  }, [selectedModule]);

  useEffect(() => {
    localStorage.setItem(modeStorageKey, activeMode);
  }, [activeMode]);

  const loadTargets = async () => {
    setLoadingContext(true);
    try {
      const res = await api.getGeolocatorTargets();
      const availableTargets = res.data?.targets || [];
      const availableModules = res.data?.modules || [];
      const fallbackTarget = res.data?.default_target || availableTargets[0]?.key || '';
      const fallbackModule = res.data?.default_module || 'DynamicTradingCommon';
      const nextTarget = availableTargets.some((item) => item.key === selectedTarget) ? selectedTarget : fallbackTarget;
      const nextModule = availableModules.some((item) => item.id === selectedModule) ? selectedModule : fallbackModule;
      setTargets(availableTargets);
      setModules(availableModules);
      setSelectedTarget(nextTarget);
      setSelectedModule(nextModule);
    } finally {
      setLoadingContext(false);
    }
  };

  return (
    <Box sx={{ width: '100%', minHeight: '100vh', py: 4 }}>
      <Stack spacing={3}>
        <GeolocatorHeader />

        <Paper elevation={3} sx={{ p: 3 }}>
          <Stack spacing={2.5}>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Context
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Shared output settings stay here so modded generation and vanilla discovery can use the same project context without sharing component logic.
            </Typography>

            {loadingContext ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth>
                    <InputLabel id="geolocator-target-label">Project Target</InputLabel>
                    <Select
                      labelId="geolocator-target-label"
                      label="Project Target"
                      value={targets.some(t => t.key === selectedTarget) ? selectedTarget : ''}
                      onChange={(event) => setSelectedTarget(event.target.value)}
                    >
                      {targets.map((target) => (
                        <MenuItem key={target.key} value={target.key}>
                          {target.title || target.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControl fullWidth>
                    <InputLabel id="geolocator-module-label">Output Module</InputLabel>
                    <Select
                      labelId="geolocator-module-label"
                      label="Output Module"
                      value={modules.some(m => m.id === selectedModule) ? selectedModule : ''}
                      onChange={(event) => setSelectedModule(event.target.value)}
                    >
                      {modules.map((module) => (
                        <MenuItem key={module.id} value={module.id}>
                          {module.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            )}
          </Stack>
        </Paper>

        <Paper elevation={3} sx={{ px: 2, pt: 1 }}>
          <Tabs
            value={activeMode}
            onChange={(_, value) => setActiveMode(value)}
            variant="scrollable"
            allowScrollButtonsMobile
          >
            <Tab value="modded" label="Modded Forge" />
            <Tab value="vanilla" label="Vanilla Discovery" />
          </Tabs>
        </Paper>

        {activeMode === 'modded' ? (
          <GeolocatorModdedTab
            selectedTarget={selectedTarget}
            selectedModule={selectedModule}
            loadingContext={loadingContext}
            activeLLMConfig={activeLLMConfig}
          />
        ) : (
          <GeolocatorVanillaTab
            selectedTarget={selectedTarget}
            selectedModule={selectedModule}
          />
        )}
      </Stack>
    </Box>
  );
};

export default GeolocatorPage;
