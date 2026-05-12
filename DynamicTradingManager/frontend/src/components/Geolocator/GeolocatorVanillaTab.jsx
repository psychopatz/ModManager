import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  Grid,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import Button from '@mui/material/Button';
import TaskConsole from '../TaskConsole';
import { formatDate, formatErrorMessage, getRegistryChipColor, renderRegistryLabel } from './geolocatorUtils';

import * as api from '../../services/api';

const GeolocatorVanillaTab = ({ selectedTarget, selectedModule }) => {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [maps, setMaps] = useState([]);
  const [selectedMapIds, setSelectedMapIds] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (selectedTarget && selectedModule) {
      loadMaps();
    }
  }, [selectedTarget, selectedModule]);

  const loadMaps = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.getGeolocatorVanillaMaps(selectedTarget, selectedModule);
      const newMaps = Array.isArray(res.data) ? res.data : [];
      setMaps(newMaps);
      
      // Select all by default, except things that look like challenge maps
      const defaultSelected = newMaps
        .filter(m => !String(m.folder || '').toLowerCase().includes('challenge'))
        .map(m => m.id);
      setSelectedMapIds(defaultSelected);
    } catch (loadError) {
      setMaps([]);
      setSelectedMapIds([]);
      setError(loadError.response?.data?.detail || 'Failed to load vanilla map discovery data.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.generateGeolocatorVanillaRegistry({
        target: selectedTarget,
        module: selectedModule,
        map_ids: selectedMapIds,
      });
      setActiveTaskId(res.data.task_id || null);
    } catch (genError) {
      setError(genError.response?.data?.detail || 'Failed to start vanilla generation.');
    } finally {
      setGenerating(false);
    }
  };

  const toggleMapSelection = (id) => {
    setSelectedMapIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    setSelectedMapIds(maps.map((m) => m.id));
  };

  const handleSelectNone = () => {
    setSelectedMapIds([]);
  };

  const selectedCount = selectedMapIds.length;

  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, lg: 4 }}>
        <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
          <Stack spacing={2.5}>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Vanilla Discovery
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Preview the backend’s vanilla map discovery results. This stays separate from the modded forge so each workflow can evolve independently.
            </Typography>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ xs: 'stretch', sm: 'center' }}>
              <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadMaps} disabled={loading}>
                {loading ? 'Refreshing...' : 'Refresh Vanilla Maps'}
              </Button>
              <Chip label={`Discovered Maps: ${maps.length}`} variant="outlined" />
            </Stack>

            <Alert severity="info" variant="outlined">
              This panel dynamically discovers base game map assets. You can generate registry files for the selected vanilla locations into the current project context.
            </Alert>

            <Stack direction="row" spacing={1}>
              <Button size="small" onClick={handleSelectAll}>All</Button>
              <Button size="small" onClick={handleSelectNone}>None</Button>
            </Stack>

            <Button
              variant="contained"
              onClick={handleGenerate}
              disabled={loading || generating || maps.length === 0 || selectedCount === 0}
              fullWidth
            >
              {generating ? 'Starting...' : `Generate Registry for ${selectedCount} Maps`}
            </Button>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {formatErrorMessage(error)}
              </Alert>
            )}
          </Stack>
        </Paper>
      </Grid>

      <Grid size={{ xs: 12, lg: 8 }}>
        <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
          <Stack spacing={2}>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>
              Vanilla Preview
            </Typography>

            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                <CircularProgress />
              </Box>
            ) : error ? (
              <Alert severity="error" variant="outlined">
                Unable to load vanilla discovery.
              </Alert>
            ) : maps.length === 0 ? (
              <Alert severity="warning" variant="outlined">
                No vanilla maps were discovered by the backend.
              </Alert>
            ) : (
              <>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} flexWrap="wrap">
                  <Chip label={`Maps: ${maps.length}`} color="primary" variant="outlined" />
                  <Chip label={`Annotated: ${maps.filter((item) => item.annotationCount > 0).length}`} color="info" variant="outlined" />
                  <Chip label={`With Spawn Points: ${maps.filter((item) => item.spawnPointCount > 0).length}`} color="success" variant="outlined" />
                </Stack>

                <Stack spacing={2}>
                  {maps.map((mapItem) => (
                    <Card key={mapItem.id} variant="outlined">
                      <CardContent>
                        <Stack spacing={1.5}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}>
                            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                              <Checkbox
                                size="small"
                                checked={selectedMapIds.includes(mapItem.id)}
                                onChange={() => toggleMapSelection(mapItem.id)}
                                sx={{ p: 0.5, mt: -0.25 }}
                              />
                              <Box>
                                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                                  {mapItem.name}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Folder: {mapItem.folder} | Definition ID: {mapItem.id}
                                </Typography>
                              </Box>
                            </Box>
                            <Stack direction="row" spacing={1} flexWrap="wrap">
                              <Chip size="small" label={`Cells: ${mapItem.cellCount}`} />
                              <Chip size="small" label={`Spawn Points: ${mapItem.spawnPointCount}`} color="success" variant="outlined" />
                              <Chip size="small" label={`Annotations: ${mapItem.annotationCount}`} color="info" variant="outlined" />
                              <Chip size="small" label={`World Features: ${mapItem.featureCount}`} color="warning" variant="outlined" />
                            </Stack>
                          </Box>

                          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                            <Chip
                              size="small"
                              label={renderRegistryLabel(mapItem.registry_status)}
                              color={getRegistryChipColor(mapItem.registry_status)}
                              variant="outlined"
                            />
                            {mapItem.registry_status?.added_at && (
                              <Chip size="small" label={`Added ${formatDate(mapItem.registry_status.added_at)}`} variant="outlined" />
                            )}
                          </Stack>

                          <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary', mt: 1 }}>
                            {mapItem.poiCount} POIs discovered: {mapItem.poiBuckets?.annotation?.length || 0} annotations, {mapItem.poiBuckets?.objects?.length || 0} objects
                          </Typography>

                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            Bounds: X {mapItem.bounds.minX}..{mapItem.bounds.maxX} | Y {mapItem.bounds.minY}..{mapItem.bounds.maxY}
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary', wordBreak: 'break-all' }}>
                            Output: {mapItem.output_file}
                          </Typography>
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
      <TaskConsole taskId={activeTaskId} onClose={() => setActiveTaskId(null)} onSuccess={loadMaps} />
    </Grid>
  );
};

export default GeolocatorVanillaTab;
