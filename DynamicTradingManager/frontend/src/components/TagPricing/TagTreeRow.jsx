import React, { memo } from 'react';
import {
  Box,
  Button,
  Chip,
  ListItemButton,
  Stack,
  Typography,
} from '@mui/material';
import { formatPrice } from './formatters';
import { getTagTone } from './treeUtils';

const TagTreeRow = memo(({ index, style, visibleRows, selectedTag, onSelectTag, onToggleExpanded }) => {
  const { node, depth } = visibleRows[index];
  const hasChildren = (node.children || []).length > 0;
  const isRoot = depth === 0;
  const currentRoot = (node.tag || '').split('.')[0];
  const previousRoot = index > 0 ? (visibleRows[index - 1]?.node?.tag || '').split('.')[0] : '';
  const startsNewCategory = index === 0 || currentRoot !== previousRoot;
  const tone = getTagTone(node.tag);

  return (
    <Box
      style={style}
      sx={{
        px: 0.75,
        pt: startsNewCategory ? 0.45 : 0,
        pb: 0,
      }}
    >
      <ListItemButton
        selected={node.tag === selectedTag}
        onClick={() => onSelectTag(node.tag)}
        sx={{
          minHeight: isRoot ? 56 : 46,
          py: isRoot ? 0.45 : 0.2,
          pl: 1.5 + (depth * 2),
          borderLeft: depth > 0 ? `1px solid ${tone.border}` : `3px solid ${tone.border}`,
          borderRadius: 2,
          bgcolor: node.tag === selectedTag ? tone.bgStrong : tone.bg,
          boxShadow: isRoot ? `inset 0 0 0 1px ${tone.border}` : 'none',
          '&:hover': {
            bgcolor: tone.bgStrong,
          },
        }}
      >
        <Stack direction="row" spacing={1.25} alignItems="flex-start" sx={{ width: '100%' }}>
          {hasChildren ? (
            <Button
              size="small"
              variant="text"
              onClick={(event) => {
                event.stopPropagation();
                onToggleExpanded(node.tag);
              }}
              sx={{ minWidth: 28, px: 0.5, color: tone.text }}
            >
              {node.isExpanded ? '-' : '+'}
            </Button>
          ) : (
            <Box sx={{ width: 28, pt: 0.6, textAlign: 'center', color: tone.muted }}>
              .
            </Box>
          )}

          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={1}>
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  noWrap
                  sx={{
                    color: tone.text,
                    fontSize: isRoot ? '1.08rem' : '0.95rem',
                    fontWeight: isRoot ? 800 : 500,
                    letterSpacing: isRoot ? '0.01em' : 'normal',
                    lineHeight: 1.05,
                  }}
                >
                  {node.label}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    color: tone.muted,
                    fontSize: isRoot ? '0.69rem' : '0.68rem',
                    fontWeight: isRoot ? 700 : 400,
                    letterSpacing: isRoot ? '0.08em' : 'normal',
                    textTransform: isRoot ? 'uppercase' : 'none',
                    lineHeight: 1.05,
                  }}
                >
                  {isRoot ? `General Category • ${node.tag}` : node.tag}
                </Typography>
              </Box>
              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap justifyContent="flex-end">
                <Chip
                  label={`${node.item_count || 0} items`}
                  size="small"
                  variant="outlined"
                  sx={{ bgcolor: tone.bg, borderColor: tone.border, color: tone.text }}
                />
                {!!node.current_addition && (
                  <Chip
                    label={`Saved ${formatPrice(node.current_addition)}`}
                    size="small"
                    sx={{ bgcolor: tone.bgStrong, borderColor: tone.border, color: tone.text }}
                  />
                )}
              </Stack>
            </Stack>
          </Box>
        </Stack>
      </ListItemButton>
    </Box>
  );
});

export default TagTreeRow;
