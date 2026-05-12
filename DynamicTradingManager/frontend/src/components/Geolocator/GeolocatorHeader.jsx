import React from 'react';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
import MapIcon from '@mui/icons-material/Map';

const GeolocatorHeader = () => (
  <Paper
    elevation={4}
    sx={{
      p: 3,
      border: '1px solid',
      borderColor: 'divider',
      background: 'linear-gradient(135deg, rgba(25,118,210,0.18), rgba(10,10,10,0.95))',
    }}
  >
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }}>
      <Box>
        <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.04em' }}>
          Geolocator Forge
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 860, mt: 1 }}>
          Build geolocator definitions into `DynamicTradingCommon/common`, with separate flows for modded generation and vanilla discovery.
        </Typography>
      </Box>
      <Chip icon={<MapIcon />} label="Registry Tools" color="primary" variant="outlined" />
    </Stack>
  </Paper>
);

export default GeolocatorHeader;
