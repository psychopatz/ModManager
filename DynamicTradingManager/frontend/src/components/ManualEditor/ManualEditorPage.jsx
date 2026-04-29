import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Fab,
  FormControl,
  InputLabel,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import RefreshIconMUI from '@mui/icons-material/Refresh';
import DeleteOutlineIconMUI from '@mui/icons-material/DeleteOutline';
import AddCircleOutlineIconMUI from '@mui/icons-material/AddCircleOutline';
import SaveOutlinedIconMUI from '@mui/icons-material/SaveOutlined';

import { createManualDefinition, deleteManualDefinition, getManualEditorData, saveManualDefinition, uploadManualImage, getGitBranches, getWorkshopTargets } from '../../services/api';
import { useDraftManagement } from '../../hooks/useDraftManagement';
import { ManualPreview } from './ManualPreview';
import { ManualDetailsForm } from './ManualDetailsForm';
import { ChaptersEditor } from './ChaptersEditor';
import { PagesEditor } from './PagesEditor';
import BatchUpdateGenerator from './BatchUpdateGenerator';

const NEW_MANUAL_KEY = '__new_manual__';

// ========== Helper Functions ==========

const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');

const cloneManual = (manual) => JSON.parse(JSON.stringify(manual));

const getDefaultSourceFolder = (module, editorScope = 'manuals') => {
  if (editorScope === 'updates') {
    return 'WhatsNew';
  }
  return 'Universal';
};

const getTodayUpdateId = () => {
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '_');
  return `dt_update_${today}`;
};

const createEmptyManual = (editorScope = 'manuals', suggestedId, module = 'DynamicTradingCommon') => {
  const isUpdateEditor = editorScope === 'updates';
  const resolvedModule = module;
  const defaultId = isUpdateEditor
    ? getTodayUpdateId()
    : `${resolvedModule}_manual_new`;
  return {
    manual_id: suggestedId || defaultId,
    title: '',
    description: '',
    start_page_id: '',
    audiences: [resolvedModule],
    sort_order: isUpdateEditor ? 10 : 300000,
    release_version: '',
    popup_version: isUpdateEditor ? suggestedId || defaultId : '',
    auto_open_on_update: isUpdateEditor,
    is_whats_new: isUpdateEditor,
    manual_type: isUpdateEditor ? 'whats_new' : 'manual',
    show_in_library: !isUpdateEditor,
    support_url: '',
    banner_title: '',
    banner_text: '',
    banner_action_label: '',
    source_folder: getDefaultSourceFolder(resolvedModule, editorScope),
    chapters: [],
    pages: [],
  };
};

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
      return {
        type: 'image',
        path: '',
        caption: '',
        width: 220,
        height: 140,
        keep_aspect_ratio: true,
        aspect_ratio: 220 / 140,
      };
    case 'callout':
      return { type: 'callout', tone: 'info', title: '', text: '' };
    default:
      return { type: 'paragraph', text: '' };
  }
};

const getPrimaryAudience = (manual) => manual?.audiences?.[0] || 'DynamicTradingCommon';

const audienceOptions = [
  { value: 'DynamicTradingCommon', label: 'Common Library' },
  { value: 'DynamicTrading', label: 'Dynamic Trading V1' },
  { value: 'DynamicTradingV2', label: 'Dynamic Trading V2' },
  { value: 'DynamicColonies', label: 'Dynamic Colonies' },
  { value: 'CurrencyExpanded', label: 'Currency Expanded' },
];

const getAudienceLabel = (manual) => audienceOptions.find((option) => option.value === getPrimaryAudience(manual))?.label || 'Common';

// ========== Main Component ==========

const ManualEditorPage = ({ editorScope = 'manuals' }) => {
  const isUpdateEditor = editorScope === 'updates';
  const [data, setData] = useState({ manuals: [], assets_base_url: '/static/manuals' });
  const [selectedModule, setSelectedModule] = useState(() => localStorage.getItem('mod_manager_last_module') || '');
  const [selectedManualKey, setSelectedManualKey] = useState('');
  const [selectedPageId, setSelectedPageId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [branches, setBranches] = useState(['develop', 'main']);
  const fileInputRef = useRef(null);
  const uploadTargetRef = useRef(null);
  const [batchGeneratorOpen, setBatchGeneratorOpen] = useState(false);

  // Per-module branch memory
  const [selectedBranch, setSelectedBranch] = useState(() => {
    const saved = localStorage.getItem('mod_manager_branches');
    if (saved && selectedModule) {
      const map = JSON.parse(saved);
      return map[selectedModule] || 'main';
    }
    return 'main';
  });

  const [modules, setModules] = useState([]);
  const [targets, setTargets] = useState([]);

  // Sync selection to localStorage
  useEffect(() => {
    if (selectedModule) {
      localStorage.setItem('mod_manager_last_module', selectedModule);

      // Restore branch for this specific module
      const saved = localStorage.getItem('mod_manager_branches');
      const map = saved ? JSON.parse(saved) : {};
      if (map[selectedModule]) {
        setSelectedBranch(map[selectedModule]);
      } else {
        setSelectedBranch('develop');
      }
    }
  }, [selectedModule]);

  const handleBranchChange = (newBranch) => {
    setSelectedBranch(newBranch);
    if (selectedModule) {
      const saved = localStorage.getItem('mod_manager_branches');
      const map = saved ? JSON.parse(saved) : {};
      map[selectedModule] = newBranch;
      localStorage.setItem('mod_manager_branches', JSON.stringify(map));
    }
  };

  const moduleOptions = useMemo(() => {
    return modules.map(m => ({ value: m.id, label: m.name, repo: m.project_key }));
  }, [modules]);

  useEffect(() => {
    getWorkshopTargets().then(res => {
      setTargets(res.data?.targets || []);
      setModules(res.data?.modules || []);
      if (res.data?.default_module) {
        setSelectedModule(res.data.default_module);
      }
    }).catch(() => { });
  }, []);

  useEffect(() => {
    if (moduleOptions.length > 0 && !moduleOptions.some(o => o.value === selectedModule)) {
      setSelectedModule(moduleOptions[0].value);
    }
  }, [moduleOptions, selectedModule]);

  const getAudienceLabel = (manual) => moduleOptions.find((option) => option.value === getPrimaryAudience(manual))?.label || 'Common';

  // Initialize with empty manual
  const [baseManual, setBaseManual] = useState(createEmptyManual(editorScope, undefined, 'DynamicTradingCommon'));

  // Use draft management hook with scoped localStorage
  const { draft, setDraft, discardDraft, clearDraft, isDrafty } = useDraftManagement(editorScope, baseManual);

  const backendOrigin = useMemo(() => {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }, []);

  const selectedPageIndex = useMemo(
    () => draft.pages.findIndex((page) => page.id === selectedPageId),
    [draft.pages, selectedPageId],
  );

  const selectedPage = selectedPageIndex >= 0 ? draft.pages[selectedPageIndex] : null;
  const isNewManual = selectedManualKey === NEW_MANUAL_KEY;
  const changedDraftPageId = useMemo(() => {
    if (!isDrafty || !draft?.pages?.length) return '';
    const baseById = new Map((baseManual?.pages || []).map((page) => [page.id, page]));
    for (const page of draft.pages) {
      const basePage = baseById.get(page.id);
      if (!basePage || JSON.stringify(basePage) !== JSON.stringify(page)) {
        return page.id;
      }
    }
    return draft.pages[0]?.id || '';
  }, [isDrafty, baseManual?.pages, draft.pages]);
  const changedDraftPageTitle = useMemo(() => {
    if (!changedDraftPageId) return '';
    return draft.pages.find((page) => page.id === changedDraftPageId)?.title || changedDraftPageId;
  }, [changedDraftPageId, draft.pages]);

  // ========== Load Data from Backend ==========

  const loadEditor = async (preferredKey = '', module = selectedModule, preferredPageId = '') => {
    if (!module) return;
    setLoading(true);
    try {
      const response = await getManualEditorData(editorScope, module);
      const filteredManuals = response.data?.manuals || [];
      const manuals = isUpdateEditor
        ? [...filteredManuals].sort((a, b) => b.manual_id.localeCompare(a.manual_id))
        : filteredManuals;

      setData({ ...response.data, manuals });
      const nextManual = manuals.find((manual) => manual.manual_id === preferredKey) || manuals[0] || null;

      if (nextManual) {
        setSelectedManualKey(nextManual.manual_id);
        setBaseManual(cloneManual(nextManual));
        const restoredPageId = preferredPageId && nextManual.pages?.some((page) => page.id === preferredPageId)
          ? preferredPageId
          : (nextManual.pages?.[0]?.id || '');
        setSelectedPageId(restoredPageId);
      } else {
        setSelectedManualKey('');
        const emptyManual = createEmptyManual(editorScope, undefined, module);
        setBaseManual(emptyManual);
        setSelectedPageId('');
      }
      setStatus({ type: '', message: '' });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error.response?.data?.detail || `Failed to load the ${isUpdateEditor ? 'update version' : 'manual'} editor data.`,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedModule) {
      loadEditor('', selectedModule);
      if (isUpdateEditor) {
        const repo = moduleOptions.find(o => o.value === selectedModule)?.repo || 'dynamictrading';
        getGitBranches(repo).then(res => setBranches(res.data)).catch(() => { });
      }
    }
  }, [editorScope, selectedModule]); // eslint-disable-line react-hooks/exhaustive-deps

  // ========== Manual Management Actions ==========

  const selectManual = (manual) => {
    setSelectedManualKey(manual.manual_id);
    setBaseManual(cloneManual(manual));
    setSelectedPageId(manual.pages?.[0]?.id || '');
    setStatus({ type: '', message: '' });
  };

  const createManual = () => {
    const suggestedId = isUpdateEditor
      ? getTodayUpdateId()
      : `${selectedModule}_manual_${(data.manuals?.length || 0) + 1}`;
    const next = createEmptyManual(editorScope, suggestedId, selectedModule);
    next.sort_order = isUpdateEditor ? Math.max(10, (data.manuals?.length || 0) + 10) : 300000 + (data.manuals?.length || 0);
    setSelectedManualKey(NEW_MANUAL_KEY);
    setBaseManual(next);
    setSelectedPageId('');
    setStatus({
      type: 'info',
      message: `New ${isUpdateEditor ? 'update version' : 'manual'} draft created. Fill in the fields and save when ready.`,
    });
  };

  const saveCurrentManual = async () => {
    if (!draft.manual_id.trim()) {
      setStatus({ type: 'error', message: 'Manual id is required.' });
      return;
    }

    setSaving(true);
    setStatus({ type: '', message: '' });

    try {
      const payload = {
        ...draft,
        manual_id: slugify(draft.manual_id),
        start_page_id: draft.start_page_id || '',
        audiences: [getPrimaryAudience(draft)],
        sort_order: Number(draft.sort_order || 0),
        release_version: String(draft.release_version || ''),
        popup_version: String(draft.popup_version || ''),
        auto_open_on_update: isUpdateEditor ? draft.auto_open_on_update !== false : draft.auto_open_on_update === true,
        is_whats_new: isUpdateEditor ? true : draft.is_whats_new === true,
        manual_type: String(draft.manual_type || ''),
        show_in_library: isUpdateEditor ? false : draft.show_in_library !== false,
        support_url: String(draft.support_url || ''),
        banner_title: String(draft.banner_title || ''),
        banner_text: String(draft.banner_text || ''),
        banner_action_label: String(draft.banner_action_label || ''),
        source_folder: isUpdateEditor ? 'WhatsNew' : draft.source_folder || getDefaultSourceFolder(getPrimaryAudience(draft), editorScope),
        module: getPrimaryAudience(draft),
      };
      const payloadModule = getPrimaryAudience(payload);

      if (isNewManual) {
        await createManualDefinition(payload, editorScope, payloadModule);
      } else {
        await saveManualDefinition(selectedManualKey, payload, editorScope, payloadModule);
      }

      if (payloadModule !== selectedModule) {
        setSelectedModule(payloadModule);
      }

      await loadEditor(payload.manual_id, payloadModule, selectedPageId);
      setStatus({
        type: 'success',
        message: `Saved ${isUpdateEditor ? 'update version' : 'manual'} "${payload.manual_id}".`,
      });
      clearDraft();
    } catch (error) {
      console.error('Manual save failed:', error);
      let message = error?.response?.data?.detail || error?.message || `Failed to save the ${isUpdateEditor ? 'update version' : 'manual'}.`;
      if (error?.response?.data) {
        try {
          message += ' | ' + JSON.stringify(error.response.data);
        } catch { }
      }
      setStatus({ type: 'error', message });
    } finally {
      setSaving(false);
    }
  };

  const deleteCurrentManual = async () => {
    if (isNewManual) {
      setSelectedManualKey('');
      const emptyManual = createEmptyManual(editorScope, undefined, selectedModule);
      setBaseManual(emptyManual);
      setSelectedPageId('');
      setStatus({
        type: 'info',
        message: `Discarded the unsaved ${isUpdateEditor ? 'update version' : 'manual'} draft.`,
      });
      return;
    }

    try {
      await deleteManualDefinition(selectedManualKey, editorScope, selectedModule);
      await loadEditor('', selectedModule);
      setStatus({
        type: 'success',
        message: `Deleted ${isUpdateEditor ? 'update version' : 'manual'} "${selectedManualKey}".`,
      });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error.response?.data?.detail || `Failed to delete the ${isUpdateEditor ? 'update version' : 'manual'}.`,
      });
    }
  };

  // ========== Draft Updates ==========

  const updateDraft = (updater) => {
    setDraft((current) => {
      const next = cloneManual(current);
      updater(next);
      return next;
    });
  };

  // ========== Chapter Updates ==========

  const handleAddChapter = () => {
    updateDraft((next) => {
      next.chapters.push(createEmptyChapter());
    });
  };

  const handleUpdateChapter = (index, field, value) => {
    updateDraft((next) => {
      next.chapters[index][field] = value;
    });
  };

  const handleMoveChapter = (index, direction) => {
    updateDraft((next) => {
      const target = index + direction;
      if (target < 0 || target >= next.chapters.length) return;
      [next.chapters[index], next.chapters[target]] = [next.chapters[target], next.chapters[index]];
    });
  };

  const handleDeleteChapter = (index) => {
    updateDraft((next) => {
      next.chapters.splice(index, 1);
    });
  };

  // ========== Page Updates ==========

  const handleAddPage = (newPage) => {
    updateDraft((next) => {
      next.pages.push(newPage);
      setSelectedPageId(newPage.id);
    });
  };

  const handleUpdatePage = (index, field, value) => {
    updateDraft((next) => {
      next.pages[index][field] = value;
      if (field === 'id' && selectedPageId === draft.pages[index]?.id) {
        setSelectedPageId(value);
      }
    });
  };

  const handleMovePage = (index, direction) => {
    updateDraft((next) => {
      const target = index + direction;
      if (target < 0 || target >= next.pages.length) return;
      [next.pages[index], next.pages[target]] = [next.pages[target], next.pages[index]];
    });
  };

  const handleDeletePage = (index) => {
    updateDraft((next) => {
      next.pages.splice(index, 1);
      setSelectedPageId(next.pages[Math.max(0, index - 1)]?.id || '');
    });
  };

  // ========== Block Updates ==========

  const handleUpdateBlock = (blockIndex, field, value) => {
    updateDraft((next) => {
      const block = next.pages[selectedPageIndex].blocks[blockIndex];
      block[field] = value;
    });
  };

  const handleChangeBlockType = (blockIndex, nextType) => {
    updateDraft((next) => {
      next.pages[selectedPageIndex].blocks[blockIndex] = createBlock(nextType);
    });
  };

  const handleMoveBlock = (blockIndex, direction) => {
    updateDraft((next) => {
      const blocks = next.pages[selectedPageIndex].blocks;
      const target = blockIndex + direction;
      if (target < 0 || target >= blocks.length) return;
      [blocks[blockIndex], blocks[target]] = [blocks[target], blocks[blockIndex]];
    });
  };

  const handleReorderBlock = (fromIndex, toIndex) => {
    updateDraft((next) => {
      const blocks = next.pages[selectedPageIndex].blocks;
      if (fromIndex === toIndex) return;
      if (fromIndex < 0 || toIndex < 0 || fromIndex >= blocks.length || toIndex >= blocks.length) return;
      const [moved] = blocks.splice(fromIndex, 1);
      blocks.splice(toIndex, 0, moved);
    });
  };

  const handleDeleteBlock = (blockIndex) => {
    updateDraft((next) => {
      next.pages[selectedPageIndex].blocks.splice(blockIndex, 1);
    });
  };

  const handleAddBlock = (pageIndex, newBlock) => {
    updateDraft((next) => {
      next.pages[pageIndex].blocks.push(newBlock);
    });
  };

  // ========== Image Upload ==========

  const promptImageUpload = (blockIndex) => {
    uploadTargetRef.current = blockIndex;
    fileInputRef.current?.click();
  };

  const uploadImageForBlock = async (file, blockIndex) => {
    if (!file || blockIndex == null || selectedPageIndex < 0) return;

    const manualId = slugify(draft.manual_id);
    if (!manualId) {
      setStatus({ type: 'error', message: 'Set the manual id before uploading images.' });
      return;
    }

    const formData = new FormData();
    formData.append('manual_id', manualId);
    formData.append('module', getPrimaryAudience(draft));
    formData.append('file', file);

    try {
      const response = await uploadManualImage(formData);
      updateDraft((next) => {
        const page = next.pages[selectedPageIndex];
        if (!page?.blocks?.[blockIndex]) return;
        page.blocks[blockIndex].path = response.data.path;
      });
      setStatus({ type: 'success', message: 'Image uploaded and linked to the selected block.' });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Image upload failed.' });
    }
  };

  const onImagePicked = async (event) => {
    const file = event.target.files?.[0];
    const blockIndex = uploadTargetRef.current;
    if (!file || blockIndex == null) return;

    await uploadImageForBlock(file, blockIndex);
    uploadTargetRef.current = null;
    event.target.value = '';
  };

  const handleImagePaste = async (blockIndex, file) => {
    await uploadImageForBlock(file, blockIndex);
  };

  // ========== Render ==========

  return (
    <Stack spacing={2} sx={{ minHeight: 0 }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h4">
            {isUpdateEditor ? 'Update Version Editor' : 'Manual Editor'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {isUpdateEditor
              ? 'Manage release notes across all modules.'
              : 'Edit manuals across all modules, including chapters, pages, images, and deep links.'}
          </Typography>
        </Box>

        {/* Action Buttons */}
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id="manual-module-view-label">Module View</InputLabel>
            <Select
              labelId="manual-module-view-label"
              label="Module View"
              value={moduleOptions.some(o => o.value === selectedModule) ? selectedModule : ""}
              onChange={(e) => setSelectedModule(e.target.value)}
              disabled={moduleOptions.length === 0}
            >
              {moduleOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {isUpdateEditor && (
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel id="manual-branch-label">Branch</InputLabel>
              <Select
                labelId="manual-branch-label"
                label="Branch"
                value={branches.includes(selectedBranch) ? selectedBranch : ""}
                onChange={(e) => handleBranchChange(e.target.value)}
                disabled={branches.length === 0}
              >
                {branches.map((b) => (
                  <MenuItem key={b} value={b}>
                    {b}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <Button
            startIcon={<RefreshIconMUI />}
            variant="outlined"
            onClick={() => loadEditor(selectedManualKey)}
            disabled={loading || saving}
          >
            Refresh
          </Button>

          <Button
            startIcon={<AddCircleOutlineIconMUI />}
            variant="outlined"
            onClick={createManual}
            disabled={loading || saving}
          >
            {isUpdateEditor ? 'New Update Version' : 'New Manual'}
          </Button>

          <Button
            startIcon={<DeleteOutlineIconMUI />}
            color="error"
            variant="outlined"
            onClick={deleteCurrentManual}
            disabled={loading || saving || (!selectedManualKey && !isNewManual)}
          >
            {isNewManual ? 'Discard Draft' : isUpdateEditor ? 'Delete Update' : 'Delete Manual'}
          </Button>

          {isUpdateEditor && (
            <Button
              variant="contained"
              color="secondary"
              onClick={() => setBatchGeneratorOpen(true)}
              disabled={loading || saving}
            >
              Batch Generate Updates
            </Button>
          )}

        </Stack>
      </Stack>

      {/* Status Alert */}
      {status.message && <Alert severity={status.type || 'info'}>{status.message}</Alert>}

      {/* Draft Indicator */}
      {isDrafty && (
        <Alert severity="warning">
          You have unsaved changes in {draft.title || draft.manual_id || 'this manual'}
          {changedDraftPageTitle ? ` / ${changedDraftPageTitle}` : ' / manual details'}.{' '}
          <Button size="small" variant="text" onClick={discardDraft}>
            Discard Draft
          </Button>
        </Alert>
      )}

      {/* File Input for Image Upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={onImagePicked}
      />

      {/* Main Editor Layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr) 360px', gap: 2, minHeight: 0 }}>
        {/* Manuals List */}
        <Paper sx={{ p: 2, overflow: 'auto' }}>
          <Typography variant="h6" gutterBottom>
            {isUpdateEditor ? 'Update Versions' : 'Manuals'}
          </Typography>
          <List dense>
            {(data.manuals || []).map((manual) => (
              <ListItemButton
                key={manual.manual_id}
                selected={selectedManualKey === manual.manual_id}
                onClick={() => selectManual(manual)}
              >
                <ListItemText
                  primary={(
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <span>{manual.title || manual.manual_id}</span>
                      {isDrafty && selectedManualKey === manual.manual_id && (
                        <Chip size="small" color="warning" label="Draft" />
                      )}
                    </Box>
                  )}
                  secondary={`${manual.manual_id} • ${getAudienceLabel(manual)}${manual.release_version ? ` • ${manual.release_version}` : ''
                    }${manual.pages?.length ? ` • ${manual.pages.length} pages` : ''}${manual.sort_order != null ? ` • #${manual.sort_order}` : ''
                    }`}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        {/* Editor Panels */}
        <Stack spacing={2} sx={{ minWidth: 0 }}>
          <ManualDetailsForm
            draft={draft}
            isNewManual={isNewManual}
            isUpdateEditor={isUpdateEditor}
            editorScope={editorScope}
            onUpdateDraft={updateDraft}
          />

          <ChaptersEditor
            chapters={draft.chapters}
            onAddChapter={handleAddChapter}
            onUpdateChapter={handleUpdateChapter}
            onMoveChapter={handleMoveChapter}
            onDeleteChapter={handleDeleteChapter}
          />

          <PagesEditor
            pages={draft.pages}
            chapters={draft.chapters}
            selectedPageId={selectedPageId}
            draftPageId={changedDraftPageId}
            isDrafty={isDrafty}
            onSelectPage={setSelectedPageId}
            onAddPage={handleAddPage}
            onUpdatePage={handleUpdatePage}
            onMovePage={handleMovePage}
            onDeletePage={handleDeletePage}
            onUpdateBlock={handleUpdateBlock}
            onChangeBlockType={handleChangeBlockType}
            onMoveBlock={handleMoveBlock}
            onReorderBlock={handleReorderBlock}
            onDeleteBlock={handleDeleteBlock}
            onImageUpload={promptImageUpload}
            onImagePaste={handleImagePaste}
            onAddBlock={handleAddBlock}
          />
        </Stack>

        {/* Preview */}
        <ManualPreview manual={draft} selectedPage={selectedPage} backendOrigin={backendOrigin} />
      </Box>

      {isUpdateEditor && (
        <BatchUpdateGenerator
          open={batchGeneratorOpen}
          onClose={() => setBatchGeneratorOpen(false)}
          onComplete={() => loadEditor(selectedManualKey)}
          branch={selectedBranch}
          module={selectedModule}
          targets={targets}
          modules={modules}
        />
      )}

      <Fab
        color={isDrafty ? 'warning' : 'primary'}
        variant="extended"
        onClick={saveCurrentManual}
        disabled={loading || saving || (!isDrafty && !isNewManual)}
        sx={{
          position: 'fixed',
          right: { xs: 16, md: 28 },
          bottom: { xs: 16, md: 28 },
          zIndex: 1400,
        }}
      >
        <SaveOutlinedIconMUI sx={{ mr: 1 }} />
        {saving ? 'Saving...' : isUpdateEditor ? 'Save Update' : 'Save Manual'}
      </Fab>
    </Stack>
  );
};

export default ManualEditorPage;
