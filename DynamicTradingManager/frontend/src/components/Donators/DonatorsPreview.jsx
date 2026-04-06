import React, { useEffect, useState } from 'react';
import {
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
} from '@mui/material';

import { formatDonation, resolveDonatorImageUrl, sortSupporters } from './donatorsUtils';

function useCarouselIndex(length, autoplayMs) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [length]);

  useEffect(() => {
    if (!length || length <= 1) return undefined;
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % length);
    }, Math.max(1000, Number(autoplayMs || 4000)));
    return () => window.clearInterval(timer);
  }, [length, autoplayMs]);

  return index;
}

function PreviewCard({ supporter, rank, backendOrigin, assetBaseUrl, currencySymbol, compact = false }) {
  const imageUrl = resolveDonatorImageUrl(backendOrigin, assetBaseUrl, supporter?.image_path);
  const imageHeight = compact ? 112 : 220;

  return (
    <Stack direction={compact ? 'row' : 'column'} spacing={compact ? 1.5 : 2}>
      <Box
        sx={{
          width: compact ? 112 : '100%',
          minWidth: compact ? 112 : '100%',
          height: imageHeight,
          borderRadius: 3,
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.12)',
          bgcolor: 'rgba(255,255,255,0.05)',
          display: 'grid',
          placeItems: 'center',
        }}
      >
        {imageUrl ? (
          <Box
            component="img"
            src={imageUrl}
            alt={supporter?.name || 'Supporter'}
            sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <Typography variant="body2" color="text.secondary">
            No image
          </Typography>
        )}
      </Box>

      <Stack spacing={compact ? 0.75 : 1} sx={{ minWidth: 0 }}>
        <Chip size="small" label={`Rank #${rank}`} sx={{ alignSelf: 'flex-start' }} />
        <Typography variant={compact ? 'h6' : 'h5'} noWrap={compact}>
          {supporter?.name || 'Unnamed Supporter'}
        </Typography>
        <Typography variant={compact ? 'body1' : 'h6'} color="secondary.main">
          {formatDonation(supporter?.total_donation, currencySymbol)}
        </Typography>
      </Stack>
    </Stack>
  );
}

function EmptyState({ compact = false }) {
  return (
    <Stack spacing={1}>
      <Typography variant={compact ? 'subtitle1' : 'h6'}>No supporters yet</Typography>
      <Typography variant="body2" color="text.secondary">
        Add donors in the manager to populate the in-game Hall of Fame carousel.
      </Typography>
    </Stack>
  );
}

export default function DonatorsPreview({
  supporters,
  backendOrigin,
  assetBaseUrl,
  currencySymbol,
  autoplayMs,
  thankYouText,
}) {
  const activeSupporters = sortSupporters((supporters || []).filter((entry) => entry.active !== false));
  const currentIndex = useCarouselIndex(activeSupporters.length, autoplayMs);
  const current = activeSupporters[currentIndex] || null;

  return (
    <Stack spacing={2}>
      <Paper
        elevation={3}
        sx={{
          p: 2.5,
          background: 'linear-gradient(135deg, rgba(191,138,58,0.18) 0%, rgba(14,18,26,0.96) 100%)',
        }}
      >
        <Stack spacing={2}>
          <Typography variant="h6">Manual Carousel Preview</Typography>
          {current ? (
            <PreviewCard
              supporter={current}
              rank={currentIndex + 1}
              backendOrigin={backendOrigin}
              assetBaseUrl={assetBaseUrl}
              currencySymbol={currencySymbol}
            />
          ) : (
            <EmptyState />
          )}
          {activeSupporters.length > 1 && (
            <Stack direction="row" spacing={1}>
              {activeSupporters.map((entry, index) => (
                <Box
                  key={entry.id || index}
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    bgcolor: index === currentIndex ? 'secondary.main' : 'rgba(255,255,255,0.18)',
                  }}
                />
              ))}
            </Stack>
          )}
          {thankYouText ? (
            <Typography variant="body2" color="text.secondary">
              {thankYouText}
            </Typography>
          ) : null}
        </Stack>
      </Paper>

      <Paper
        elevation={3}
        sx={{
          p: 2,
          background: 'linear-gradient(135deg, rgba(120,74,22,0.22) 0%, rgba(25,18,10,0.95) 100%)',
        }}
      >
        <Stack spacing={1.5}>
          <Typography variant="subtitle1">Support Banner Preview</Typography>
          {current ? (
            <PreviewCard
              supporter={current}
              rank={currentIndex + 1}
              backendOrigin={backendOrigin}
              assetBaseUrl={assetBaseUrl}
              currencySymbol={currencySymbol}
              compact
            />
          ) : (
            <EmptyState compact />
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
