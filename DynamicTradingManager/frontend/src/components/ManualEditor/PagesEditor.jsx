import React from 'react';
import {
  Box,
  Button,
  Chip,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  Paper,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import { BlockEditor } from './BlockEditor';

const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');

const blockTypeOptions = [
  { value: 'heading', label: 'Heading' },
  { value: 'paragraph', label: 'Paragraph' },
  { value: 'bullet_list', label: 'Bullet List' },
  { value: 'image', label: 'Image' },
  { value: 'callout', label: 'Callout' },
];

const createEmptyPage = (chapterId = '') => ({
  id: '',
  chapter_id: chapterId,
  title: '',
  keywords: [],
  blocks: [],
});

const createBlock = (type) => {
  switch (type) {
    case 'heading':
      return { type: 'heading', id: '', level: 1, text: '' };
    case 'bullet_list':
      return { type: 'bullet_list', items: [] };
    case 'image':
      return { type: 'image', path: '', caption: '', width: 220, height: 140 };
    case 'callout':
      return { type: 'callout', tone: 'info', title: '', text: '' };
    default:
      return { type: 'paragraph', text: '' };
  }
};

/**
 * PagesEditor - Component for editing pages, chapters and blocks in a manual
 */
export const PagesEditor = ({
  pages,
  chapters,
  selectedPageId,
  draftPageId,
  isDrafty,
  onSelectPage,
  onAddPage,
  onUpdatePage,
  onMovePage,
  onDeletePage,
  onUpdateBlock,
  onChangeBlockType,
  onMoveBlock,
  onDeleteBlock,
  onImageUpload,
  onAddBlock,
}) => {
  const selectedPageIndex = pages.findIndex((page) => page.id === selectedPageId);
  const selectedPage = selectedPageIndex >= 0 ? pages[selectedPageIndex] : null;
  const chapterIds = chapters.map((chapter) => chapter.id).filter(Boolean);

  const [newBlockType, setNewBlockType] = React.useState('paragraph');

  const handlePageFieldChange = (field, value) => {
    if (field === 'keywords') {
      const keywords = String(value)
        .split(',')
        .map((part) => part.trim())
        .filter(Boolean);
      onUpdatePage(selectedPageIndex, field, keywords);
    } else if (field === 'id' || field === 'chapter_id') {
      onUpdatePage(selectedPageIndex, field, slugify(value));
    } else {
      onUpdatePage(selectedPageIndex, field, value);
    }
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h6">Pages</Typography>
        <Button
          startIcon={<AddCircleOutlineIcon />}
          size="small"
          onClick={() => {
            const nextPage = createEmptyPage(chapters[0]?.id || '');
            nextPage.id = slugify(`page_${pages.length + 1}`);
            nextPage.title = `Page ${pages.length + 1}`;
            onAddPage(nextPage);
          }}
        >
          Add Page
        </Button>
      </Stack>

      <Box sx={{ display: 'grid', gridTemplateColumns: '220px minmax(0, 1fr)', gap: 2 }}>
        {/* Pages list */}
        <List dense sx={{ border: '1px solid rgba(255,255,255,0.12)', borderRadius: 1, minHeight: 160 }}>
          {pages.map((page, index) => (
            <ListItemButton
              key={page.id || `page-${index}`}
              selected={selectedPageId === page.id}
              onClick={() => onSelectPage(page.id)}
            >
              <ListItemText
                primary={(
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span>{page.title || page.id || `Page ${index + 1}`}</span>
                    {isDrafty && draftPageId && draftPageId === page.id && (
                      <Chip size="small" color="warning" label="Draft" />
                    )}
                  </Box>
                )}
                secondary={page.chapter_id || 'No chapter'}
              />
            </ListItemButton>
          ))}
        </List>

        {/* Page editor or empty state */}
        {!selectedPage ? (
          <Typography variant="body2" color="text.secondary">
            Select or create a page to edit it.
          </Typography>
        ) : (
          <Stack spacing={1.5}>
            {/* Page metadata */}
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField
                label="Page ID"
                size="small"
                value={selectedPage.id || ''}
                onChange={(e) => handlePageFieldChange('id', e.target.value)}
                sx={{ minWidth: 160 }}
              />
              <TextField
                label="Title"
                size="small"
                value={selectedPage.title || ''}
                onChange={(e) => handlePageFieldChange('title', e.target.value)}
                sx={{ flexGrow: 1 }}
              />
              <IconButton size="small" onClick={() => onMovePage(selectedPageIndex, -1)}>
                <ArrowUpwardIcon fontSize="inherit" />
              </IconButton>
              <IconButton size="small" onClick={() => onMovePage(selectedPageIndex, 1)}>
                <ArrowDownwardIcon fontSize="inherit" />
              </IconButton>
              <IconButton
                size="small"
                color="error"
                onClick={() => onDeletePage(selectedPageIndex)}
              >
                <DeleteOutlineIcon fontSize="inherit" />
              </IconButton>
            </Stack>

            {/* Chapter assignment */}
            <FormControl size="small">
              <InputLabel id="manual-page-chapter-label">Chapter</InputLabel>
              <Select
                labelId="manual-page-chapter-label"
                label="Chapter"
                value={selectedPage.chapter_id || ''}
                onChange={(e) => handlePageFieldChange('chapter_id', e.target.value)}
              >
                {chapterIds.map((chapterId) => (
                  <MenuItem key={chapterId} value={chapterId}>{chapterId}</MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Keywords */}
            <TextField
              label="Keywords"
              size="small"
              value={(selectedPage.keywords || []).join(', ')}
              onChange={(e) => handlePageFieldChange('keywords', e.target.value)}
              helperText="Comma-separated search keywords."
            />

            <Divider />

            {/* Block addition controls */}
            <Stack direction="row" spacing={1} alignItems="center">
              <FormControl size="small" sx={{ minWidth: 180 }}>
                <InputLabel id="new-block-type-label">New Block Type</InputLabel>
                <Select
                  labelId="new-block-type-label"
                  label="New Block Type"
                  value={newBlockType}
                  onChange={(e) => setNewBlockType(e.target.value)}
                >
                  {blockTypeOptions.map((option) => (
                    <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                startIcon={<AddCircleOutlineIcon />}
                onClick={() => {
                  const newBlock = createBlock(newBlockType);
                  onAddBlock(selectedPageIndex, newBlock);
                }}
              >
                Add Block
              </Button>
            </Stack>

            {/* Blocks list */}
            <Stack spacing={1.5}>
              {selectedPage.blocks.map((block, blockIndex) => (
                <BlockEditor
                  key={`block-${blockIndex}`}
                  block={block}
                  blockIndex={blockIndex}
                  onUpdateBlock={onUpdateBlock}
                  onChangeBlockType={onChangeBlockType}
                  onMoveBlock={onMoveBlock}
                  onDeleteBlock={onDeleteBlock}
                  onImageUpload={onImageUpload}
                />
              ))}
            </Stack>
          </Stack>
        )}
      </Box>
    </Paper>
  );
};
