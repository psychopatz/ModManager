import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
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
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import RefreshIcon from '@mui/icons-material/Refresh';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { createManualDefinition, deleteManualDefinition, getManualEditorData, saveManualDefinition, uploadManualImage } from '../services/api';

const NEW_MANUAL_KEY = '__new_manual__';

const createEmptyManual = (suggestedId = 'manual_new') => ({
  manual_id: suggestedId,
  title: '',
  description: '',
  start_page_id: '',
  chapters: [],
  pages: [],
});

const createEmptyChapter = () => ({
  id: '',
  title: '',
  description: '',
});

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

const cloneManual = (manual) => JSON.parse(JSON.stringify(manual));

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

const toneOptions = ['info', 'warn', 'success'];

function ManualPreview({ manual, selectedPage, backendOrigin }) {
  const resolveImageUrl = (path) => {
    if (!path) return '';
    const normalized = String(path);
    if (normalized.startsWith('media/ui/Manuals/')) {
      return `${backendOrigin}/static/manuals/${normalized.replace('media/ui/Manuals/', '')}`;
    }
    return `${backendOrigin}/static/workshop/Contents/mods/DynamicTradingCommon/42.13/${normalized}`;
  };

  return (
    <Paper sx={{ p: 2, height: '100%', overflow: 'auto' }}>
      <Typography variant="h6" gutterBottom>
        Live Preview
      </Typography>
      {!selectedPage ? (
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
}

const ManualEditorPage = () => {
  const [data, setData] = useState({ manuals: [], assets_base_url: '/static/manuals' });
  const [draft, setDraft] = useState(createEmptyManual());
  const [selectedManualKey, setSelectedManualKey] = useState('');
  const [selectedPageId, setSelectedPageId] = useState('');
  const [newBlockType, setNewBlockType] = useState('paragraph');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const fileInputRef = useRef(null);
  const uploadTargetRef = useRef(null);

  const backendOrigin = useMemo(() => {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }, []);

  const selectedPageIndex = useMemo(
    () => draft.pages.findIndex((page) => page.id === selectedPageId),
    [draft.pages, selectedPageId],
  );

  const selectedPage = selectedPageIndex >= 0 ? draft.pages[selectedPageIndex] : null;
  const chapterIds = draft.chapters.map((chapter) => chapter.id).filter(Boolean);
  const isNewManual = selectedManualKey === NEW_MANUAL_KEY;

  const applyPayload = (payload, preferredKey = '') => {
    setData(payload);
    const manuals = payload?.manuals || [];
    const nextManual = manuals.find((manual) => manual.manual_id === preferredKey) || manuals[0] || null;
    if (nextManual) {
      setSelectedManualKey(nextManual.manual_id);
      setDraft(cloneManual(nextManual));
      setSelectedPageId(nextManual.pages?.[0]?.id || '');
    } else {
      setSelectedManualKey('');
      setDraft(createEmptyManual());
      setSelectedPageId('');
    }
  };

  const loadEditor = async (preferredKey = '') => {
    setLoading(true);
    try {
      const response = await getManualEditorData();
      applyPayload(response.data, preferredKey);
      setStatus({ type: '', message: '' });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Failed to load manual editor data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEditor();
  }, []);

  const selectManual = (manual) => {
    setSelectedManualKey(manual.manual_id);
    setDraft(cloneManual(manual));
    setSelectedPageId(manual.pages?.[0]?.id || '');
    setStatus({ type: '', message: '' });
  };

  const updateDraft = (updater) => {
    setDraft((current) => {
      const next = cloneManual(current);
      updater(next);
      return next;
    });
  };

  const createManual = () => {
    const suggestedId = `manual_${(data.manuals?.length || 0) + 1}`;
    const next = createEmptyManual(suggestedId);
    setSelectedManualKey(NEW_MANUAL_KEY);
    setDraft(next);
    setSelectedPageId('');
    setStatus({ type: 'info', message: 'New manual draft created. Fill in the fields and save when ready.' });
  };

  const saveCurrentManual = async () => {
    if (!draft.manual_id.trim()) {
      setStatus({ type: 'error', message: 'Manual id is required.' });
      return;
    }

    setSaving(true);
    try {
      const payload = {
        ...draft,
        manual_id: slugify(draft.manual_id),
        start_page_id: draft.start_page_id || '',
      };

      if (isNewManual) {
        await createManualDefinition(payload);
      } else {
        await saveManualDefinition(selectedManualKey, payload);
      }

      await loadEditor(payload.manual_id);
      setStatus({ type: 'success', message: `Saved manual "${payload.manual_id}".` });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Failed to save manual.' });
    } finally {
      setSaving(false);
    }
  };

  const deleteCurrentManual = async () => {
    if (isNewManual) {
      setSelectedManualKey('');
      setDraft(createEmptyManual());
      setSelectedPageId('');
      setStatus({ type: 'info', message: 'Discarded the unsaved manual draft.' });
      return;
    }

    try {
      await deleteManualDefinition(selectedManualKey);
      await loadEditor();
      setStatus({ type: 'success', message: `Deleted manual "${selectedManualKey}".` });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Failed to delete manual.' });
    }
  };

  const updateChapter = (index, field, value) => {
    updateDraft((next) => {
      next.chapters[index][field] = field === 'id' ? slugify(value) : value;
    });
  };

  const moveChapter = (index, direction) => {
    updateDraft((next) => {
      const target = index + direction;
      if (target < 0 || target >= next.chapters.length) return;
      [next.chapters[index], next.chapters[target]] = [next.chapters[target], next.chapters[index]];
    });
  };

  const updatePage = (index, field, value) => {
    updateDraft((next) => {
      if (field === 'keywords') {
        next.pages[index].keywords = String(value)
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean);
        return;
      }
      next.pages[index][field] = field === 'id' || field === 'chapter_id' ? slugify(value) : value;
      if (field === 'id' && selectedPageId === draft.pages[index]?.id) {
        setSelectedPageId(slugify(value));
      }
    });
  };

  const movePage = (index, direction) => {
    updateDraft((next) => {
      const target = index + direction;
      if (target < 0 || target >= next.pages.length) return;
      [next.pages[index], next.pages[target]] = [next.pages[target], next.pages[index]];
    });
  };

  const updateBlock = (blockIndex, field, value) => {
    updateDraft((next) => {
      const block = next.pages[selectedPageIndex].blocks[blockIndex];
      if (field === 'items') {
        block.items = String(value)
          .split('\n')
          .map((part) => part.trim())
          .filter(Boolean);
        return;
      }
      if (field === 'level' || field === 'width' || field === 'height') {
        block[field] = Number(value || 0);
        return;
      }
      block[field] = field === 'id' ? slugify(value) : value;
    });
  };

  const changeBlockType = (blockIndex, nextType) => {
    updateDraft((next) => {
      next.pages[selectedPageIndex].blocks[blockIndex] = createBlock(nextType);
    });
  };

  const moveBlock = (blockIndex, direction) => {
    updateDraft((next) => {
      const blocks = next.pages[selectedPageIndex].blocks;
      const target = blockIndex + direction;
      if (target < 0 || target >= blocks.length) return;
      [blocks[blockIndex], blocks[target]] = [blocks[target], blocks[blockIndex]];
    });
  };

  const promptImageUpload = (blockIndex) => {
    uploadTargetRef.current = blockIndex;
    fileInputRef.current?.click();
  };

  const onImagePicked = async (event) => {
    const file = event.target.files?.[0];
    if (!file || uploadTargetRef.current == null) return;

    const manualId = slugify(draft.manual_id);
    if (!manualId) {
      setStatus({ type: 'error', message: 'Set the manual id before uploading images.' });
      return;
    }

    const formData = new FormData();
    formData.append('manual_id', manualId);
    formData.append('file', file);

    try {
      const response = await uploadManualImage(formData);
      const blockIndex = uploadTargetRef.current;
      updateDraft((next) => {
        next.pages[selectedPageIndex].blocks[blockIndex].path = response.data.path;
      });
      setStatus({ type: 'success', message: 'Image uploaded and linked to the selected block.' });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Image upload failed.' });
    } finally {
      uploadTargetRef.current = null;
      event.target.value = '';
    }
  };

  return (
    <Stack spacing={2} sx={{ minHeight: 0 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h4">Manual Editor</Typography>
          <Typography variant="body2" color="text.secondary">
            Edit DT Commons manuals, chapters, pages, image blocks, and deep-link section ids.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<RefreshIcon />} variant="outlined" onClick={() => loadEditor(selectedManualKey)} disabled={loading || saving}>
            Refresh
          </Button>
          <Button startIcon={<AddCircleOutlineIcon />} variant="outlined" onClick={createManual} disabled={loading || saving}>
            New Manual
          </Button>
          <Button startIcon={<DeleteOutlineIcon />} color="error" variant="outlined" onClick={deleteCurrentManual} disabled={loading || saving || (!selectedManualKey && !isNewManual)}>
            {isNewManual ? 'Discard Draft' : 'Delete Manual'}
          </Button>
          <Button startIcon={<SaveOutlinedIcon />} variant="contained" onClick={saveCurrentManual} disabled={loading || saving}>
            {saving ? 'Saving...' : 'Save Manual'}
          </Button>
        </Stack>
      </Stack>

      {status.message ? <Alert severity={status.type || 'info'}>{status.message}</Alert> : null}

      <input ref={fileInputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={onImagePicked} />

      <Box sx={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr) 360px', gap: 2, minHeight: 0 }}>
        <Paper sx={{ p: 2, overflow: 'auto' }}>
          <Typography variant="h6" gutterBottom>
            Manuals
          </Typography>
          <List dense>
            {(data.manuals || []).map((manual) => (
              <ListItemButton key={manual.manual_id} selected={selectedManualKey === manual.manual_id} onClick={() => selectManual(manual)}>
                <ListItemText
                  primary={manual.title || manual.manual_id}
                  secondary={`${manual.manual_id}${manual.pages?.length ? ` • ${manual.pages.length} pages` : ''}`}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        <Stack spacing={2} sx={{ minWidth: 0 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Manual Details
            </Typography>
            <Stack spacing={2}>
              <TextField
                label="Manual ID"
                value={draft.manual_id}
                onChange={(event) => updateDraft((next) => { next.manual_id = slugify(event.target.value); })}
                disabled={!isNewManual}
                helperText={isNewManual ? 'Used for file name, deep links, and image folders.' : 'Manual ids are locked for existing manuals in this v1 editor.'}
              />
              <TextField
                label="Title"
                value={draft.title}
                onChange={(event) => updateDraft((next) => { next.title = event.target.value; })}
              />
              <TextField
                label="Description"
                value={draft.description}
                onChange={(event) => updateDraft((next) => { next.description = event.target.value; })}
                multiline
                minRows={2}
              />
              <TextField
                label="Start Page ID"
                value={draft.start_page_id}
                onChange={(event) => updateDraft((next) => { next.start_page_id = slugify(event.target.value); })}
              />
            </Stack>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="h6">Chapters</Typography>
              <Button startIcon={<AddCircleOutlineIcon />} size="small" onClick={() => updateDraft((next) => { next.chapters.push(createEmptyChapter()); })}>
                Add Chapter
              </Button>
            </Stack>
            <Stack spacing={1.5}>
              {draft.chapters.map((chapter, index) => (
                <Paper key={`chapter-${index}`} variant="outlined" sx={{ p: 1.5 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <TextField label="ID" size="small" value={chapter.id} onChange={(event) => updateChapter(index, 'id', event.target.value)} sx={{ minWidth: 140 }} />
                    <TextField label="Title" size="small" value={chapter.title} onChange={(event) => updateChapter(index, 'title', event.target.value)} sx={{ flexGrow: 1 }} />
                    <IconButton size="small" onClick={() => moveChapter(index, -1)}><ArrowUpwardIcon fontSize="inherit" /></IconButton>
                    <IconButton size="small" onClick={() => moveChapter(index, 1)}><ArrowDownwardIcon fontSize="inherit" /></IconButton>
                    <IconButton size="small" color="error" onClick={() => updateDraft((next) => { next.chapters.splice(index, 1); })}><DeleteOutlineIcon fontSize="inherit" /></IconButton>
                  </Stack>
                  <TextField label="Description" size="small" value={chapter.description} onChange={(event) => updateChapter(index, 'description', event.target.value)} fullWidth />
                </Paper>
              ))}
            </Stack>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="h6">Pages</Typography>
              <Button
                startIcon={<AddCircleOutlineIcon />}
                size="small"
                onClick={() => updateDraft((next) => {
                  const nextPage = createEmptyPage(next.chapters[0]?.id || '');
                  nextPage.id = slugify(`page_${next.pages.length + 1}`);
                  nextPage.title = `Page ${next.pages.length + 1}`;
                  next.pages.push(nextPage);
                  setSelectedPageId(nextPage.id);
                })}
              >
                Add Page
              </Button>
            </Stack>

            <Box sx={{ display: 'grid', gridTemplateColumns: '220px minmax(0, 1fr)', gap: 2 }}>
              <List dense sx={{ border: '1px solid rgba(255,255,255,0.12)', borderRadius: 1, minHeight: 160 }}>
                {draft.pages.map((page, index) => (
                  <ListItemButton key={page.id || `page-${index}`} selected={selectedPageId === page.id} onClick={() => setSelectedPageId(page.id)}>
                    <ListItemText
                      primary={page.title || page.id || `Page ${index + 1}`}
                      secondary={page.chapter_id || 'No chapter'}
                    />
                  </ListItemButton>
                ))}
              </List>

              {!selectedPage ? (
                <Typography variant="body2" color="text.secondary">
                  Select or create a page to edit it.
                </Typography>
              ) : (
                <Stack spacing={1.5}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TextField
                      label="Page ID"
                      size="small"
                      value={selectedPage.id}
                      onChange={(event) => updatePage(selectedPageIndex, 'id', event.target.value)}
                      sx={{ minWidth: 160 }}
                    />
                    <TextField
                      label="Title"
                      size="small"
                      value={selectedPage.title}
                      onChange={(event) => updatePage(selectedPageIndex, 'title', event.target.value)}
                      sx={{ flexGrow: 1 }}
                    />
                    <IconButton size="small" onClick={() => movePage(selectedPageIndex, -1)}><ArrowUpwardIcon fontSize="inherit" /></IconButton>
                    <IconButton size="small" onClick={() => movePage(selectedPageIndex, 1)}><ArrowDownwardIcon fontSize="inherit" /></IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => updateDraft((next) => {
                        next.pages.splice(selectedPageIndex, 1);
                        setSelectedPageId(next.pages[Math.max(0, selectedPageIndex - 1)]?.id || '');
                      })}
                    >
                      <DeleteOutlineIcon fontSize="inherit" />
                    </IconButton>
                  </Stack>

                  <FormControl size="small">
                    <InputLabel id="manual-page-chapter-label">Chapter</InputLabel>
                    <Select
                      labelId="manual-page-chapter-label"
                      label="Chapter"
                      value={selectedPage.chapter_id || ''}
                      onChange={(event) => updatePage(selectedPageIndex, 'chapter_id', event.target.value)}
                    >
                      {chapterIds.map((chapterId) => (
                        <MenuItem key={chapterId} value={chapterId}>{chapterId}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <TextField
                    label="Keywords"
                    size="small"
                    value={(selectedPage.keywords || []).join(', ')}
                    onChange={(event) => updatePage(selectedPageIndex, 'keywords', event.target.value)}
                    helperText="Comma-separated search keywords."
                  />

                  <Divider />

                  <Stack direction="row" spacing={1} alignItems="center">
                    <FormControl size="small" sx={{ minWidth: 180 }}>
                      <InputLabel id="new-block-type-label">New Block Type</InputLabel>
                      <Select
                        labelId="new-block-type-label"
                        label="New Block Type"
                        value={newBlockType}
                        onChange={(event) => setNewBlockType(event.target.value)}
                      >
                        {blockTypeOptions.map((option) => (
                          <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Button
                      startIcon={<AddCircleOutlineIcon />}
                      onClick={() => updateDraft((next) => {
                        next.pages[selectedPageIndex].blocks.push(createBlock(newBlockType));
                      })}
                    >
                      Add Block
                    </Button>
                  </Stack>

                  <Stack spacing={1.5}>
                    {selectedPage.blocks.map((block, blockIndex) => (
                      <Paper key={`block-${blockIndex}`} variant="outlined" sx={{ p: 1.5 }}>
                        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                          <FormControl size="small" sx={{ minWidth: 170 }}>
                            <InputLabel id={`block-type-${blockIndex}`}>Type</InputLabel>
                            <Select
                              labelId={`block-type-${blockIndex}`}
                              label="Type"
                              value={block.type}
                              onChange={(event) => changeBlockType(blockIndex, event.target.value)}
                            >
                              {blockTypeOptions.map((option) => (
                                <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                          <IconButton size="small" onClick={() => moveBlock(blockIndex, -1)}><ArrowUpwardIcon fontSize="inherit" /></IconButton>
                          <IconButton size="small" onClick={() => moveBlock(blockIndex, 1)}><ArrowDownwardIcon fontSize="inherit" /></IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => updateDraft((next) => {
                              next.pages[selectedPageIndex].blocks.splice(blockIndex, 1);
                            })}
                          >
                            <DeleteOutlineIcon fontSize="inherit" />
                          </IconButton>
                        </Stack>

                        {block.type === 'heading' && (
                          <Stack spacing={1}>
                            <Stack direction="row" spacing={1}>
                              <TextField label="Section ID" size="small" value={block.id || ''} onChange={(event) => updateBlock(blockIndex, 'id', event.target.value)} sx={{ minWidth: 180 }} />
                              <TextField label="Level" size="small" type="number" value={block.level || 1} onChange={(event) => updateBlock(blockIndex, 'level', event.target.value)} sx={{ width: 100 }} />
                            </Stack>
                            <TextField label="Heading Text" size="small" value={block.text || ''} onChange={(event) => updateBlock(blockIndex, 'text', event.target.value)} fullWidth />
                          </Stack>
                        )}

                        {block.type === 'paragraph' && (
                          <TextField label="Paragraph Text" size="small" value={block.text || ''} onChange={(event) => updateBlock(blockIndex, 'text', event.target.value)} multiline minRows={3} fullWidth />
                        )}

                        {block.type === 'bullet_list' && (
                          <TextField
                            label="Bullet Items"
                            size="small"
                            value={(block.items || []).join('\n')}
                            onChange={(event) => updateBlock(blockIndex, 'items', event.target.value)}
                            multiline
                            minRows={4}
                            helperText="One bullet item per line."
                            fullWidth
                          />
                        )}

                        {block.type === 'image' && (
                          <Stack spacing={1}>
                            <Stack direction="row" spacing={1}>
                              <TextField label="Path" size="small" value={block.path || ''} onChange={(event) => updateBlock(blockIndex, 'path', event.target.value)} sx={{ flexGrow: 1 }} />
                              <Button startIcon={<UploadFileIcon />} onClick={() => promptImageUpload(blockIndex)}>
                                Upload
                              </Button>
                            </Stack>
                            <TextField label="Caption" size="small" value={block.caption || ''} onChange={(event) => updateBlock(blockIndex, 'caption', event.target.value)} fullWidth />
                            <Stack direction="row" spacing={1}>
                              <TextField label="Width" size="small" type="number" value={block.width || 220} onChange={(event) => updateBlock(blockIndex, 'width', event.target.value)} sx={{ width: 120 }} />
                              <TextField label="Height" size="small" type="number" value={block.height || 140} onChange={(event) => updateBlock(blockIndex, 'height', event.target.value)} sx={{ width: 120 }} />
                            </Stack>
                          </Stack>
                        )}

                        {block.type === 'callout' && (
                          <Stack spacing={1}>
                            <FormControl size="small" sx={{ minWidth: 160 }}>
                              <InputLabel id={`tone-${blockIndex}`}>Tone</InputLabel>
                              <Select labelId={`tone-${blockIndex}`} label="Tone" value={block.tone || 'info'} onChange={(event) => updateBlock(blockIndex, 'tone', event.target.value)}>
                                {toneOptions.map((tone) => (
                                  <MenuItem key={tone} value={tone}>{tone}</MenuItem>
                                ))}
                              </Select>
                            </FormControl>
                            <TextField label="Title" size="small" value={block.title || ''} onChange={(event) => updateBlock(blockIndex, 'title', event.target.value)} fullWidth />
                            <TextField label="Body" size="small" value={block.text || ''} onChange={(event) => updateBlock(blockIndex, 'text', event.target.value)} multiline minRows={3} fullWidth />
                          </Stack>
                        )}
                      </Paper>
                    ))}
                  </Stack>
                </Stack>
              )}
            </Box>
          </Paper>
        </Stack>

        <ManualPreview manual={draft} selectedPage={selectedPage} backendOrigin={backendOrigin} />
      </Box>
    </Stack>
  );
};

export default ManualEditorPage;
