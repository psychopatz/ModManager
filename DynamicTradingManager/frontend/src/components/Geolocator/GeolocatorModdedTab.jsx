import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import TravelExploreIcon from '@mui/icons-material/TravelExplore';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import RefreshIcon from '@mui/icons-material/Refresh';

import * as api from '../../services/api';
import TaskConsole from '../TaskConsole';
import {
  countByState,
  formatDate,
  formatPoiSecondary,
  getRegistryChipColor,
  renderRegistryLabel,
} from './geolocatorUtils';

const pathStorageKey = 'dt_geolocator_source_path';
const workshopRootStorageKey = 'dt_geolocator_workshop_root';
const workshopSourceStorageKey = 'dt_geolocator_workshop_source';

const GeolocatorModdedTab = ({
  selectedTarget,
  selectedModule,
  loadingContext,
  activeLLMConfig,
}) => {
  const [sourcePath, setSourcePath] = useState(() => localStorage.getItem(pathStorageKey) || '');
  const [workshopRoot, setWorkshopRoot] = useState(() => localStorage.getItem(workshopRootStorageKey) || '');
  const [workshopSources, setWorkshopSources] = useState([]);
  const [selectedWorkshopSource, setSelectedWorkshopSource] = useState(() => localStorage.getItem(workshopSourceStorageKey) || '');
  const [loadingWorkshopSources, setLoadingWorkshopSources] = useState(true);
  const [inspecting, setInspecting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState(null);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, severity: 'info', message: '' });
  const llmConfigKey = JSON.stringify(activeLLMConfig || {});

  useEffect(() => {
    localStorage.setItem(pathStorageKey, sourcePath);
  }, [sourcePath]);

  useEffect(() => {
    localStorage.setItem(workshopRootStorageKey, workshopRoot);
  }, [workshopRoot]);

  useEffect(() => {
    localStorage.setItem(workshopSourceStorageKey, selectedWorkshopSource);
  }, [selectedWorkshopSource]);

  useEffect(() => {
    if (!loadingContext && selectedTarget && selectedModule) {
      loadWorkshopSources(workshopRoot);
    }
  }, [selectedTarget, selectedModule, loadingContext, llmConfigKey]);

  const loadWorkshopSources = async (overrideRoot = '') => {
    setLoadingWorkshopSources(true);
    try {
      const res = await api.getGeolocatorWorkshopSources(
        overrideRoot || workshopRoot || undefined,
        selectedTarget || undefined,
        selectedModule || 'DynamicTradingCommon',
        activeLLMConfig,
      );
      const nextRoot = res.data?.root_path || overrideRoot || workshopRoot;
      const sources = res.data?.sources || [];
      setWorkshopRoot(nextRoot);
      setWorkshopSources(sources);

      if (sources.length === 0) {
        setSelectedWorkshopSource('');
        return;
      }

      const hasStored = sources.some((item) => item.id === selectedWorkshopSource);
      const nextSourceId = hasStored ? selectedWorkshopSource : sources[0].id;
      setSelectedWorkshopSource(nextSourceId);

      const selectedSource = sources.find((item) => item.id === nextSourceId);
      if (selectedSource && !sourcePath.trim()) {
        setSourcePath(selectedSource.source_path);
      }
    } catch (error) {
      setWorkshopSources([]);
      setSelectedWorkshopSource('');
      setSnackbar({
        open: true,
        severity: 'error',
        message: error.response?.data?.detail || 'Failed to load workshop map mods.',
      });
    } finally {
      setLoadingWorkshopSources(false);
    }
  };

  const handleWorkshopSourceSelect = (value) => {
    setSelectedWorkshopSource(value);
    const selectedSource = workshopSources.find((item) => item.id === value);
    if (selectedSource) {
      setSourcePath(selectedSource.source_path);
    }
  };

  const handleInspect = async () => {
    if (!sourcePath.trim()) {
      setSnackbar({ open: true, severity: 'warning', message: 'Enter a workshop map path first.' });
      return;
    }
    setInspecting(true);
    try {
      const res = await api.inspectGeolocatorSource({
        source_path: sourcePath.trim(),
        target: selectedTarget || undefined,
        module: selectedModule || 'DynamicTradingCommon',
        llm_config: activeLLMConfig,
      });
      setPreview(res.data);
      setSnackbar({ open: true, severity: 'success', message: 'Map source inspected.' });
    } catch (error) {
      setPreview(null);
      setSnackbar({
        open: true,
        severity: 'error',
        message: error.response?.data?.detail || 'Failed to inspect the map source.',
      });
    } finally {
      setInspecting(false);
    }
  };

  const handleGenerate = async () => {
    if (!sourcePath.trim()) {
      setSnackbar({ open: true, severity: 'warning', message: 'Enter a workshop map path first.' });
      return;
    }
    setGenerating(true);
    try {
      const res = await api.generateGeolocatorRegistry({
        source_path: sourcePath.trim(),
        target: selectedTarget || undefined,
        module: selectedModule || 'DynamicTradingCommon',
        llm_config: activeLLMConfig,
      });
      setActiveTaskId(res.data.task_id || null);
      setSnackbar({ open: true, severity: 'info', message: 'Generation task started.' });
    } catch (error) {
      setSnackbar({
        open: true,
        severity: 'error',
        message: error.response?.data?.detail || 'Failed to start generation.',
      });
    } finally {
      setGenerating(false);
    }
  };

  const previewMods = preview?.mods || [];

  return (
    <>
      <Grid container spacing={3}>
        <Grid item xs={12} lg={5}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Stack spacing={2.5}>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                Modded Source
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Point this at a Steam workshop item, a mod folder, a `common` folder, or a direct `media/maps/&lt;MapFolder&gt;` path.
              </Typography>

              {loadingContext ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
                  <CircularProgress />
                </Box>
              ) : (
                <>
                  <TextField
                    fullWidth
                    label="Workshop Content Root"
                    value={workshopRoot}
                    onChange={(event) => setWorkshopRoot(event.target.value)}
                    placeholder="/home/.../steamapps/workshop/content/108600"
                  />

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
                    <Button
                      variant="outlined"
                      startIcon={<RefreshIcon />}
                      onClick={() => loadWorkshopSources(workshopRoot)}
                      disabled={loadingWorkshopSources}
                    >
                      {loadingWorkshopSources ? 'Loading Workshop Mods...' : 'Refresh Workshop Mods'}
                    </Button>
                    <Chip label={`Valid Map Mods: ${workshopSources.length}`} variant="outlined" />
                  </Stack>

                  {workshopSources.length > 0 && (
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      <Chip size="small" label={`Added: ${countByState(workshopSources, 'added')}`} color="success" variant="outlined" />
                      <Chip size="small" label={`Outdated: ${countByState(workshopSources, 'outdated')}`} color="warning" variant="outlined" />
                      <Chip size="small" label={`Partial: ${countByState(workshopSources, 'partial')}`} color="secondary" variant="outlined" />
                      <Chip size="small" label={`Not Added: ${countByState(workshopSources, 'not_added')}`} variant="outlined" />
                    </Stack>
                  )}

                  <FormControl fullWidth>
                    <InputLabel id="geolocator-workshop-source-label">Workshop Map Mod</InputLabel>
                    <Select
                      labelId="geolocator-workshop-source-label"
                      label="Workshop Map Mod"
                      value={selectedWorkshopSource}
                      onChange={(event) => handleWorkshopSourceSelect(event.target.value)}
                    >
                      {workshopSources.map((source) => (
                        <MenuItem key={source.id} value={source.id}>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1.5, width: '100%' }}>
                            <Typography variant="body2">
                              {source.mod_name} ({source.map_count})
                            </Typography>
                            <Chip
                              size="small"
                              label={renderRegistryLabel(source.registry_status)}
                              color={getRegistryChipColor(source.registry_status)}
                              variant="outlined"
                              sx={{ minWidth: 108, justifyContent: 'center' }}
                            />
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  {selectedWorkshopSource && (
                    <Alert severity="info" variant="outlined">
                      {(() => {
                        const selectedSource = workshopSources.find((item) => item.id === selectedWorkshopSource);
                        if (!selectedSource) {
                          return 'Select a workshop map mod.';
                        }
                        const itemId = selectedSource.workshop_item_id ? `Workshop ${selectedSource.workshop_item_id}` : 'Workshop item';
                        const status = selectedSource.registry_status || {};
                        const addedAt = status.added_at ? ` | Added: ${formatDate(status.added_at)}` : '';
                        const version = status.generated_version || status.source_version ? ` | Version: ${status.generated_version || status.source_version}` : '';
                        return `${itemId} | Maps: ${selectedSource.map_names.join(', ')} | ${renderRegistryLabel(status)}${addedAt}${version}`;
                      })()}
                    </Alert>
                  )}

                  <TextField
                    fullWidth
                    multiline
                    minRows={4}
                    label="Selected Source Path"
                    value={sourcePath}
                    onChange={(event) => setSourcePath(event.target.value)}
                    placeholder="/home/.../steamapps/workshop/content/108600/<workshop-id>/mods/<ModName>/common"
                  />

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                    <Button
                      variant="outlined"
                      startIcon={<TravelExploreIcon />}
                      onClick={handleInspect}
                      disabled={inspecting || generating || loadingContext}
                      fullWidth
                    >
                      {inspecting ? 'Inspecting...' : 'Inspect'}
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<AutoFixHighIcon />}
                      onClick={handleGenerate}
                      disabled={generating || inspecting || loadingContext}
                      fullWidth
                    >
                      {generating ? 'Starting...' : 'Generate Files'}
                    </Button>
                  </Stack>

                  <Alert severity="info" variant="outlined">
                    Only workshop mods with real map assets are listed here. Generated files are written into the selected project module under `common/media/lua/shared/DT/Common/GeolocatorDefinitions`.
                  </Alert>

                  {!activeLLMConfig && (
                    <Alert severity="warning" variant="outlined">
                      No backend LLM is active. Generic clustered POIs will use deterministic fallback labels.
                    </Alert>
                  )}
                </>
              )}
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
            <Stack spacing={2}>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                Modded Preview
              </Typography>

              {!preview ? (
                <Alert severity="warning" variant="outlined">
                  Run an inspect first to preview detected mods, maps, bounds, POIs by source bucket, and output files.
                </Alert>
              ) : (
                <>
                  <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} flexWrap="wrap">
                    <Chip label={`Mods: ${preview.total_mods || 0}`} color="primary" variant="outlined" />
                    <Chip label={`Maps: ${preview.total_maps || 0}`} color="primary" variant="outlined" />
                    <Chip label={preview.project_name || 'Unknown Project'} variant="outlined" />
                    <Chip label={preview.module || 'DynamicTradingCommon'} variant="outlined" />
                  </Stack>

                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle2" color="text.secondary">Resolved Source</Typography>
                      <Typography variant="body2" sx={{ wordBreak: 'break-all', mb: 2 }}>
                        {preview.resolved_source_path}
                      </Typography>
                      <Typography variant="subtitle2" color="text.secondary">Output Root</Typography>
                      <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                        {preview.output_root}
                      </Typography>
                    </CardContent>
                  </Card>

                  <Stack spacing={2}>
                    {previewMods.map((mod) => (
                      <Card key={`${mod.mod_id}-${mod.mod_root}`} variant="outlined">
                        <CardContent>
                          <Stack spacing={1.5}>
                            <Box>
                              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                                {mod.mod_name}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Mod ID: {mod.mod_id} | Output Folder: {mod.output_folder}
                              </Typography>
                              <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                                <Chip
                                  size="small"
                                  label={renderRegistryLabel(mod.registry_status)}
                                  color={getRegistryChipColor(mod.registry_status)}
                                  variant="outlined"
                                />
                                {mod.registry_status?.added_at && (
                                  <Chip size="small" label={`Added ${formatDate(mod.registry_status.added_at)}`} variant="outlined" />
                                )}
                                {(mod.registry_status?.generated_version || mod.registry_status?.source_version) && (
                                  <Chip
                                    size="small"
                                    label={`Version ${mod.registry_status.generated_version || mod.registry_status.source_version}`}
                                    variant="outlined"
                                  />
                                )}
                              </Stack>
                            </Box>

                            {mod.warnings?.length > 0 && (
                              <Alert severity="warning" variant="outlined">
                                {mod.warnings.join(' ')}
                              </Alert>
                            )}

                            <Divider />

                            <Stack spacing={2}>
                              {mod.maps.map((mapItem) => (
                                <Paper key={mapItem.output_file} variant="outlined" sx={{ p: 2 }}>
                                  <Stack spacing={1.5}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                                      <Box>
                                        <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                                          {mapItem.display_name}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                          {mapItem.long_name}
                                        </Typography>
                                      </Box>
                                      <Stack direction="row" spacing={1} flexWrap="wrap">
                                        <Chip
                                          size="small"
                                          label={renderRegistryLabel(mapItem.registry_status)}
                                          color={getRegistryChipColor(mapItem.registry_status)}
                                          variant="outlined"
                                        />
                                        <Chip size="small" label={`POIs: ${mapItem.poi_count}`} />
                                        <Chip size="small" label={`Annotations: ${mapItem.poi_buckets?.annotation?.length || 0}`} color="info" variant="outlined" />
                                        <Chip size="small" label={`Objects: ${mapItem.poi_buckets?.objects?.length || 0}`} color="success" variant="outlined" />
                                        <Chip size="small" label={`Generic: ${mapItem.poi_buckets?.generic?.length || 0}`} color="warning" variant="outlined" />
                                        <Chip size="small" label={`Spawn Points: ${mapItem.spawnpoint_count}`} />
                                      </Stack>
                                    </Box>

                                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                      Bounds: X {mapItem.bounds.minX}..{mapItem.bounds.maxX} | Y {mapItem.bounds.minY}..{mapItem.bounds.maxY}
                                    </Typography>
                                    <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                                      Output: {mapItem.output_file}
                                    </Typography>

                                    {mapItem.warnings?.length > 0 && (
                                      <Alert severity="warning" variant="outlined">
                                        {mapItem.warnings.join(' ')}
                                      </Alert>
                                    )}

                                    <Box>
                                      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                                        POI Preview
                                      </Typography>
                                      {mapItem.pois?.length ? (
                                        <Stack spacing={1.5}>
                                          {renderPoiBucket('Annotation Labels', mapItem.poi_buckets?.annotation, 'info')}
                                          {renderPoiBucket('Named Objects', mapItem.poi_buckets?.objects, 'success')}
                                          {renderPoiBucket('Generic Clusters', mapItem.poi_buckets?.generic, 'warning')}
                                        </Stack>
                                      ) : (
                                        <Typography variant="body2" color="text.secondary">
                                          No POIs were generated for this map.
                                        </Typography>
                                      )}
                                    </Box>
                                  </Stack>
                                </Paper>
                              ))}
                            </Stack>
                          </Stack>
                        </CardContent>
                      </Card>
                    ))}
                  </Stack>
                </>
              )}
            </Stack>
          </Paper>
        </Grid>
      </Grid>

      <TaskConsole taskId={activeTaskId} onClose={() => setActiveTaskId(null)} onSuccess={handleInspect} />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
      >
        <Alert onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))} severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

function renderPoiBucket(title, pois, color) {
  if (!pois?.length) {
    return null;
  }

  return (
    <Box key={title}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          {title}
        </Typography>
        <Chip size="small" label={pois.length} color={color} variant="outlined" />
      </Stack>
      <List dense sx={{ py: 0 }}>
        {pois.slice(0, 6).map((poi) => (
          <ListItem key={`${poi.id}-${poi.x}-${poi.y}`} sx={{ px: 0 }}>
            <ListItemText
              primary={poi.name}
              secondary={formatPoiSecondary(poi)}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}

export default GeolocatorModdedTab;
