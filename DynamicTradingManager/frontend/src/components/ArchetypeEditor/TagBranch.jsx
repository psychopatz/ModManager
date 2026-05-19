import React from 'react';
import { Box, Button, Stack, Typography } from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';

function TagBranch({
  node,
  depth,
  expandedTags,
  onToggle,
  onAddTag,
  onDragStart,
  forceExpand = false,
}) {
  const hasChildren = Boolean(node.children?.length);
  const isExpanded = forceExpand || Boolean(expandedTags[node.tag] ?? depth === 0);
  const itemCount = node.meta?.item_count || 0;
  const coveredCount = node.meta?.covered_item_count || 0;

  return (
    <Box sx={{ pl: depth ? 2 : 0, borderLeft: depth ? '1px solid rgba(255,255,255,0.08)' : 'none', ml: depth ? 0.75 : 0 }}>
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{
          py: 0.75,
          px: 1,
          borderRadius: 2,
          bgcolor: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.06)',
          mb: 0.75,
        }}
      >
        <Box sx={{ width: 28, display: 'grid', placeItems: 'center' }}>
          {hasChildren ? (
            <Button size="small" onClick={() => onToggle(node.tag)} sx={{ minWidth: 28, p: 0.25 }}>
              {isExpanded ? <KeyboardArrowDownIcon fontSize="small" /> : <KeyboardArrowRightIcon fontSize="small" />}
            </Button>
          ) : null}
        </Box>

        <Box
          draggable={Boolean(node.meta)}
          onDragStart={(event) => {
            if (!node.meta) {
              return;
            }
            onDragStart(event, node.meta);
          }}
          sx={{ flexGrow: 1, minWidth: 0, cursor: node.meta ? 'grab' : 'default' }}
        >
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {node.tag}
          </Typography>
          {node.meta ? (
            <Typography variant="caption" color="text.secondary">
              {itemCount} matching items, {coveredCount} already covered
            </Typography>
          ) : null}
        </Box>

        {node.meta ? (
          <Button size="small" variant="outlined" startIcon={<AddCircleOutlineIcon />} onClick={() => onAddTag(node.meta)}>
            Add
          </Button>
        ) : null}
      </Stack>

      {hasChildren && isExpanded ? (
        <Box>
          {node.children.map((child) => (
            <TagBranch
              key={child.tag}
              node={child}
              depth={depth + 1}
              expandedTags={expandedTags}
              onToggle={onToggle}
              onAddTag={onAddTag}
              onDragStart={onDragStart}
              forceExpand={forceExpand}
            />
          ))}
        </Box>
      ) : null}
    </Box>
  );
}

export default TagBranch;
