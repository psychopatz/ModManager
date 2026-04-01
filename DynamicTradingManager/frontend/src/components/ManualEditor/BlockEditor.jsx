import React from 'react';
import {
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Paper,
  Button,
  Box,
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
        <Stack spacing={1}>
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
              onChange={(e) => handleFieldChange('width', e.target.value)}
              sx={{ width: 120 }}
            />
            <TextField
              label="Height"
              size="small"
              type="number"
              value={block.height || 140}
              onChange={(e) => handleFieldChange('height', e.target.value)}
              sx={{ width: 120 }}
            />
          </Stack>
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
