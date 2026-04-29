import React, { useState } from 'react';
import {
  Box,
  Chip,
  Paper,
  Stack,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';

/**
 * ManualPreview - Renders a live preview of a manual page or its raw Lua
 */
export const ManualPreview = ({ manual, selectedPage, backendOrigin }) => {
  const [viewMode, setViewMode] = useState('preview');

  const resolveImageUrl = (path) => {
    if (!path) return '';
    const normalized = String(path);
    if (normalized.startsWith('media/ui/Manuals/')) {
      const manualAssetBaseUrl = manual?.asset_base_url || '/static/manuals';
      return `${backendOrigin}${manualAssetBaseUrl}/${normalized.replace('media/ui/Manuals/', '').split('/').slice(1).join('/')}`;
    }
    return `${backendOrigin}/static/workshop/Contents/mods/DynamicTradingCommon/42.13/${normalized}`;
  };

  return (
    <Paper sx={{ p: 2, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">
          Live Preview
        </Typography>
        {manual?.raw_lua && (
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(e, newMode) => newMode && setViewMode(newMode)}
            size="small"
          >
            <ToggleButton value="preview">HTML Preview</ToggleButton>
            <ToggleButton value="lua">Raw Lua</ToggleButton>
          </ToggleButtonGroup>
        )}
      </Stack>

      {viewMode === 'lua' ? (
        <Box sx={{ flexGrow: 1, position: 'relative' }}>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 2,
              bgcolor: 'background.paper',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'divider',
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.8125rem',
              color: 'text.secondary',
              height: '100%',
            }}
          >
            {manual.raw_lua}
          </Box>
        </Box>
      ) : !selectedPage ? (
        <Typography variant="body2" color="text.secondary">
          Select a page to preview it.
        </Typography>
      ) : (
        <Stack spacing={2}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {manual?.title || 'Manual'}
            </Typography>
            <Typography variant="h5">
              {selectedPage.title || 'Untitled Page'}
            </Typography>
            {!!selectedPage.keywords?.length && (
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
                {selectedPage.keywords.map((keyword) => (
                  <Chip key={keyword} size="small" label={keyword} />
                ))}
              </Stack>
            )}
          </Box>

          {(selectedPage.blocks || []).map((block, index) => {
            if (block.type === 'heading') {
              const variant = Number(block.level) <= 1 ? 'h6' : 'subtitle1';
              return (
                <Box key={`preview-${index}`}>
                  <Typography variant="caption" color="text.secondary">
                    {block.id ? `#${block.id}` : 'Heading'}
                  </Typography>
                  <Typography variant={variant}>{block.text || 'Untitled heading'}</Typography>
                </Box>
              );
            }

            if (block.type === 'paragraph') {
              return (
                <Typography key={`preview-${index}`} variant="body2">
                  {block.text || 'Paragraph text'}
                </Typography>
              );
            }

            if (block.type === 'bullet_list') {
              return (
                <Stack key={`preview-${index}`} spacing={0.5}>
                  {(block.items || []).map((item, bulletIndex) => (
                    <Typography key={`bullet-${bulletIndex}`} variant="body2">
                      • {item}
                    </Typography>
                  ))}
                </Stack>
              );
            }

            if (block.type === 'image') {
              const src = resolveImageUrl(block.path);
              return (
                <Box key={`preview-${index}`}>
                  {src ? (
                    <Box
                      component="img"
                      src={src}
                      alt={block.caption || `Manual image ${index + 1}`}
                      sx={{
                        width: Math.min(Number(block.width || 220), 340),
                        maxWidth: '100%',
                        borderRadius: 2,
                        border: '1px solid rgba(255,255,255,0.12)',
                        display: 'block',
                      }}
                    />
                  ) : (
                    <Box sx={{ p: 2, border: '1px dashed rgba(255,255,255,0.2)', borderRadius: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        No image selected
                      </Typography>
                    </Box>
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {block.caption || block.path || 'Image block'}
                  </Typography>
                </Box>
              );
            }

            return (
              <Paper
                key={`preview-${index}`}
                variant="outlined"
                sx={{
                  p: 1.5,
                  bgcolor: block.tone === 'warn' ? 'rgba(255,183,77,0.08)' : block.tone === 'success' ? 'rgba(102,187,106,0.08)' : 'rgba(144,202,249,0.08)',
                }}
              >
                <Typography variant="subtitle2">{block.title || 'Callout'}</Typography>
                <Typography variant="body2">{block.text || 'Callout body'}</Typography>
              </Paper>
            );
          })}
        </Stack>
      )}
    </Paper>
  );
};
