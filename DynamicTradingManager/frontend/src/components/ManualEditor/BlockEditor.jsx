import React from 'react';
import {
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Paper,
  Button,
  Box,
  Checkbox,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import UploadFileIcon from '@mui/icons-material/UploadFile';

const blockTypeOptions = [
  { value: 'heading', label: 'Heading' },
  { value: 'paragraph', label: 'Paragraph' },
  { value: 'bullet_list', label: 'Bullet List' },
  { value: 'image', label: 'Image' },
  { value: 'callout', label: 'Callout' },
  { value: 'supporter_carousel', label: 'Supporters' },
];

const toneOptions = ['info', 'warn', 'success'];

const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');

/**
 * BlockEditor - Component for editing individual blocks within a page
 */
export const BlockEditor = ({
  block,
  blockIndex,
  onUpdateBlock,
  onChangeBlockType,
  onMoveBlock,
  onDeleteBlock,
  onImageUpload,
  onImagePaste,
}) => {
  const handleFieldChange = (field, value) => {
    if (field === 'items') {
      const items = String(value)
        .split('\n')
        .map((part) => part.trim())
        .filter(Boolean);
      onUpdateBlock(blockIndex, field, items);
    } else if (field === 'level' || field === 'width' || field === 'height') {
      onUpdateBlock(blockIndex, field, Number(value || 0));
    } else if (field === 'id') {
      onUpdateBlock(blockIndex, field, slugify(value));
    } else {
      onUpdateBlock(blockIndex, field, value);
    }
  };

  const handleImagePaste = (event) => {
    if (block.type !== 'image') return;
    const items = Array.from(event.clipboardData?.items || []);
    const imageItem = items.find((item) => item.type?.startsWith('image/'));
    if (!imageItem || !onImagePaste) return;

    const file = imageItem.getAsFile();
    if (!file) return;

    event.preventDefault();
    onImagePaste(blockIndex, file);
  };

  const handleImageScaleChange = (field, rawValue) => {
    const nextValue = Number(rawValue || 0);
    const isLocked = block.keep_aspect_ratio !== false;

    if (!isLocked) {
      onUpdateBlock(blockIndex, field, nextValue);
      return;
    }

    const width = Number(block.width || 220);
    const height = Number(block.height || 140);
    const ratio = Number(block.aspect_ratio) > 0
      ? Number(block.aspect_ratio)
      : (width > 0 && height > 0 ? width / height : 1);

    onUpdateBlock(blockIndex, field, nextValue);

    if (nextValue <= 0 || ratio <= 0) return;

    if (field === 'width') {
      onUpdateBlock(blockIndex, 'height', Math.max(1, Math.round(nextValue / ratio)));
    } else {
      onUpdateBlock(blockIndex, 'width', Math.max(1, Math.round(nextValue * ratio)));
    }
  };

  const handleAspectRatioToggle = (checked) => {
    onUpdateBlock(blockIndex, 'keep_aspect_ratio', checked);
    if (!checked) return;

    const width = Number(block.width || 220);
    const height = Number(block.height || 140);
    const ratio = width > 0 && height > 0 ? width / height : 1;
    onUpdateBlock(blockIndex, 'aspect_ratio', ratio);
  };

  return (
    <Paper variant="outlined" sx={{ p: 1.5 }}>
      {/* Block type selector and action buttons */}
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <FormControl size="small" sx={{ minWidth: 170 }}>
          <InputLabel id={`block-type-${blockIndex}`}>Type</InputLabel>
          <Select
            labelId={`block-type-${blockIndex}`}
            label="Type"
            value={block.type || 'paragraph'}
            onChange={(e) => onChangeBlockType(blockIndex, e.target.value)}
          >
            {blockTypeOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <IconButton size="small" onClick={() => onMoveBlock(blockIndex, -1)}>
          <ArrowUpwardIcon fontSize="inherit" />
        </IconButton>
        <IconButton size="small" onClick={() => onMoveBlock(blockIndex, 1)}>
          <ArrowDownwardIcon fontSize="inherit" />
        </IconButton>
        <IconButton size="small" color="error" onClick={() => onDeleteBlock(blockIndex)}>
          <DeleteOutlineIcon fontSize="inherit" />
        </IconButton>
      </Stack>

      {/* Heading block */}
      {block.type === 'heading' && (
        <Stack spacing={1}>
          <Stack direction="row" spacing={1}>
            <TextField
              label="Section ID"
              size="small"
              value={block.id || ''}
              onChange={(e) => handleFieldChange('id', e.target.value)}
              sx={{ minWidth: 180 }}
            />
            <TextField
              label="Level"
              size="small"
              type="number"
              value={block.level || 1}
              onChange={(e) => handleFieldChange('level', e.target.value)}
              sx={{ width: 100 }}
            />
          </Stack>
          <TextField
            label="Heading Text"
            size="small"
            value={block.text || ''}
            onChange={(e) => handleFieldChange('text', e.target.value)}
            fullWidth
          />
        </Stack>
      )}

      {/* Paragraph block */}
      {block.type === 'paragraph' && (
        <TextField
          label="Paragraph Text"
          size="small"
          value={block.text || ''}
          onChange={(e) => handleFieldChange('text', e.target.value)}
          multiline
          minRows={3}
          fullWidth
        />
      )}

      {/* Bullet list block */}
      {block.type === 'bullet_list' && (
        <TextField
          label="Bullet Items"
          size="small"
          value={(block.items || []).join('\n')}
          onChange={(e) => handleFieldChange('items', e.target.value)}
          multiline
          minRows={4}
          helperText="One bullet item per line."
          fullWidth
        />
      )}

      {/* Image block */}
      {block.type === 'image' && (
        <Stack spacing={1} onPaste={handleImagePaste}>
          <Stack direction="row" spacing={1}>
            <TextField
              label="Path"
              size="small"
              value={block.path || ''}
              onChange={(e) => handleFieldChange('path', e.target.value)}
              sx={{ flexGrow: 1 }}
            />
            <Button
              startIcon={<UploadFileIcon />}
              onClick={() => onImageUpload(blockIndex)}
              size="small"
            >
              Upload
            </Button>
          </Stack>
          <Box sx={{ fontSize: 12, color: 'text.secondary' }}>
            Paste a screenshot with Ctrl+V while this image block is focused.
          </Box>
          <TextField
            label="Caption"
            size="small"
            value={block.caption || ''}
            onChange={(e) => handleFieldChange('caption', e.target.value)}
            fullWidth
          />
          <Stack direction="row" spacing={1}>
            <TextField
              label="Width"
              size="small"
              type="number"
              value={block.width || 220}
              onChange={(e) => handleImageScaleChange('width', e.target.value)}
              sx={{ width: 120 }}
            />
            <TextField
              label="Height"
              size="small"
              type="number"
              value={block.height || 140}
              onChange={(e) => handleImageScaleChange('height', e.target.value)}
              sx={{ width: 120 }}
            />
          </Stack>
          <FormControlLabel
            control={(
              <Checkbox
                size="small"
                checked={block.keep_aspect_ratio !== false}
                onChange={(e) => handleAspectRatioToggle(e.target.checked)}
              />
            )}
            label="Keep aspect ratio while scaling"
          />
        </Stack>
      )}

      {/* Callout block - with special attention to ensure all fields save */}
      {block.type === 'callout' && (
        <Stack spacing={1}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id={`tone-${blockIndex}`}>Tone</InputLabel>
            <Select
              labelId={`tone-${blockIndex}`}
              label="Tone"
              value={block.tone || 'info'}
              onChange={(e) => handleFieldChange('tone', e.target.value)}
            >
              {toneOptions.map((tone) => (
                <MenuItem key={tone} value={tone}>{tone}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Title"
            size="small"
            value={block.title || ''}
            onChange={(e) => {
              console.log('Callout title changed:', e.target.value);
              handleFieldChange('title', e.target.value);
            }}
            fullWidth
          />
          <TextField
            label="Body"
            size="small"
            value={block.text || ''}
            onChange={(e) => {
              console.log('Callout text changed:', e.target.value);
              handleFieldChange('text', e.target.value);
            }}
            multiline
            minRows={3}
            fullWidth
          />
        </Stack>
      )}
    </Paper>
  );
};
