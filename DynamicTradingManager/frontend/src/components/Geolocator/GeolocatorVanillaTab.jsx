import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import Button from '@mui/material/Button';

import * as api from '../../services/api';

const GeolocatorVanillaTab = () => {
  const [loading, setLoading] = useState(true);
  const [maps, setMaps] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    loadMaps();
  }, []);

  const loadMaps = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.getGeolocatorVanillaMaps();
      setMaps(Array.isArray(res.data) ? res.data : []);
    } catch (loadError) {
      setMaps([]);
      setError(loadError.response?.data?.detail || 'Failed to load vanilla map discovery data.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} lg={4}>
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
              This panel is discovery-only for now. It reads the current vanilla map layout from the game media path exposed by the backend.
            </Alert>

            {error && (
              <Alert severity="error" variant="outlined">
                {error}
              </Alert>
            )}
          </Stack>
        </Paper>
      </Grid>

      <Grid item xs={12} lg={8}>
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
                            <Box>
                              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                                {mapItem.name}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                Folder: {mapItem.folder} | Definition ID: {mapItem.id}
                              </Typography>
                            </Box>
                            <Stack direction="row" spacing={1} flexWrap="wrap">
                              <Chip size="small" label={`Cells: ${mapItem.cellCount}`} />
                              <Chip size="small" label={`Spawn Points: ${mapItem.spawnPointCount}`} color="success" variant="outlined" />
                              <Chip size="small" label={`Annotations: ${mapItem.annotationCount}`} color="info" variant="outlined" />
                              <Chip size="small" label={`World Features: ${mapItem.featureCount}`} color="warning" variant="outlined" />
                            </Stack>
                          </Box>

                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            Bounds: X {mapItem.bounds.minX}..{mapItem.bounds.maxX} | Y {mapItem.bounds.minY}..{mapItem.bounds.maxY}
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
    </Grid>
  );
};

export default GeolocatorVanillaTab;
