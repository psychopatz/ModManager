import React from 'react';
import {
  Button,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';

const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');

const createEmptyChapter = () => ({
  id: '',
  title: '',
  description: '',
});

/**
 * ChaptersEditor - Component for editing chapters in a manual
 */
export const ChaptersEditor = ({
  chapters,
  onAddChapter,
  onUpdateChapter,
  onMoveChapter,
  onDeleteChapter,
}) => {
  const handleFieldChange = (index, field, value) => {
    onUpdateChapter(index, field, field === 'id' ? slugify(value) : value);
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h6">Chapters</Typography>
        <Button startIcon={<AddCircleOutlineIcon />} size="small" onClick={onAddChapter}>
          Add Chapter
        </Button>
      </Stack>
      <Stack spacing={1.5}>
        {chapters.map((chapter, index) => (
          <Paper key={`chapter-${index}`} variant="outlined" sx={{ p: 1.5 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <TextField
                label="ID"
                size="small"
                value={chapter.id || ''}
                onChange={(e) => handleFieldChange(index, 'id', e.target.value)}
                sx={{ minWidth: 140 }}
              />
              <TextField
                label="Title"
                size="small"
                value={chapter.title || ''}
                onChange={(e) => handleFieldChange(index, 'title', e.target.value)}
                sx={{ flexGrow: 1 }}
              />
              <IconButton size="small" onClick={() => onMoveChapter(index, -1)}>
                <ArrowUpwardIcon fontSize="inherit" />
              </IconButton>
              <IconButton size="small" onClick={() => onMoveChapter(index, 1)}>
                <ArrowDownwardIcon fontSize="inherit" />
              </IconButton>
              <IconButton size="small" color="error" onClick={() => onDeleteChapter(index)}>
                <DeleteOutlineIcon fontSize="inherit" />
              </IconButton>
            </Stack>
            <TextField
              label="Description"
              size="small"
              value={chapter.description || ''}
              onChange={(e) => handleFieldChange(index, 'description', e.target.value)}
              fullWidth
            />
          </Paper>
        ))}
      </Stack>
    </Paper>
  );
};
