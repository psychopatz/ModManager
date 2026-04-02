import React from 'react';
import {
  Alert,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  Paper,
} from '@mui/material';

const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');

const audienceOptions = [
  { value: 'common', label: 'Common' },
  { value: 'v1', label: 'Dynamic Trading V1' },
  { value: 'v2', label: 'Dynamic Trading V2' },
  { value: 'colony', label: 'Dynamic Colonies' },
  { value: 'currency', label: 'Currency Expanded' },
];

const getDefaultSourceFolder = (module, editorScope = 'manuals') => {
  if (editorScope === 'updates') {
    return 'WhatsNew';
  }
  if (module === 'v1') return 'V1';
  if (module === 'v2') return 'V2';
  if (module === 'colony') return 'Colony';
  return 'Universal';
};

const getSourceFolderOptions = (module, editorScope = 'manuals') => {
  if (editorScope === 'updates') {
    return [{ value: 'WhatsNew', label: "What's New" }];
  }
  if (module === 'v1') {
    return [{ value: 'V1', label: 'V1' }];
  }
  if (module === 'v2') {
    return [{ value: 'V2', label: 'V2' }];
  }
  if (module === 'colony') {
    return [{ value: 'Colony', label: 'Colonies' }];
  }
  if (module === 'currency') {
    return [{ value: 'Universal', label: 'Currency Expanded' }];
  }
  return [
    { value: 'Universal', label: 'Universal' },
    { value: 'Support', label: 'Support Banner Manual' },
  ];
};

const getPrimaryAudience = (manual) => manual?.audiences?.[0] || 'common';
const TITLE_MAX_LENGTH = 22;
const DESCRIPTION_MAX_LENGTH = 69;

const incrementVersion = (value) => {
  const match = String(value || '').trim().match(/^(\d+)(?:\.(\d+))?(?:\.(\d+))?$/);
  if (!match) return '0.0.1';
  const major = Number(match[1] || 0);
  const minor = Number(match[2] || 0);
  const patch = Number(match[3] || 0) + 1;
  return `${major}.${minor}.${patch}`;
};

/**
 * ManualDetailsForm - Editable form for manual metadata
 */
export const ManualDetailsForm = ({
  draft,
  isNewManual,
  isUpdateEditor,
  editorScope,
  onUpdateDraft,
}) => {
  const titleLength = String(draft.title || '').length;
  const isTitleAtLimit = titleLength >= TITLE_MAX_LENGTH;
  const descriptionLength = String(draft.description || '').length;
  const isDescriptionAtLimit = descriptionLength >= DESCRIPTION_MAX_LENGTH;

  const handleFieldChange = (field, value) => {
    onUpdateDraft((next) => {
      if (field === 'manual_id') {
        next.manual_id = slugify(value);
      } else if (field === 'start_page_id') {
        next.start_page_id = slugify(value);
      } else if (field === 'title') {
        next.title = String(value || '').slice(0, TITLE_MAX_LENGTH);
      } else if (field === 'description') {
        next.description = String(value || '').slice(0, DESCRIPTION_MAX_LENGTH);
      } else {
        next[field] = value;
      }
    });
  };

  const handleAudienceChange = (value) => {
    onUpdateDraft((next) => {
      next.audiences = [value];
      next.source_folder = getDefaultSourceFolder(value, editorScope || 'manuals');
      if ((editorScope || 'manuals') === 'updates') {
        next.manual_type = 'whats_new';
      } else if (value === 'currency' && !next.manual_id.startsWith('ce_')) {
        next.manual_id = slugify(next.manual_id || 'ce_manual_new');
      }
    });
  };

  const handleSourceFolderChange = (value) => {
    onUpdateDraft((next) => {
      next.source_folder = value;
      if (value === 'Support') {
        next.manual_type = 'support';
        next.show_in_library = false;
        next.popup_version = next.popup_version || next.manual_id || 'support';
      } else if ((editorScope || 'manuals') === 'updates' || value === 'WhatsNew') {
        next.manual_type = 'whats_new';
        next.is_whats_new = true;
        next.show_in_library = false;
      } else if (!next.manual_type || next.manual_type === 'support' || next.manual_type === 'whats_new') {
        next.manual_type = 'manual';
      }
    });
  };

  const isSupportManual = draft.source_folder === 'Support' || draft.manual_type === 'support';
  const sourceFolderOptions = getSourceFolderOptions(getPrimaryAudience(draft), editorScope);

  const handleIncrementVersion = () => {
    onUpdateDraft((next) => {
      const current = next.release_version || next.popup_version || '';
      const bumped = incrementVersion(current);
      next.release_version = bumped;
      if (isUpdateEditor || !next.popup_version) {
        next.popup_version = bumped;
      }
    });
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        {isUpdateEditor ? 'Update Details' : 'Manual Details'}
      </Typography>
      <Stack spacing={2}>
        <TextField
          label={isUpdateEditor ? 'Update ID' : 'Manual ID'}
          value={draft.manual_id || ''}
          onChange={(e) => handleFieldChange('manual_id', e.target.value)}
          disabled={!isNewManual}
          helperText={isNewManual
            ? 'Used for file name, deep links, and image folders.'
            : `${isUpdateEditor ? 'Update' : 'Manual'} ids are locked for existing entries in this editor.`}
        />
        <TextField
          label="Title"
          value={draft.title || ''}
          onChange={(e) => handleFieldChange('title', e.target.value)}
          inputProps={{ maxLength: TITLE_MAX_LENGTH }}
          helperText={isTitleAtLimit
            ? `${titleLength}/${TITLE_MAX_LENGTH} (max reached)`
            : `${titleLength}/${TITLE_MAX_LENGTH}`}
          error={isTitleAtLimit}
        />
        <TextField
          label="Description"
          value={draft.description || ''}
          onChange={(e) => handleFieldChange('description', e.target.value)}
          inputProps={{ maxLength: DESCRIPTION_MAX_LENGTH }}
          helperText={isDescriptionAtLimit
            ? `${descriptionLength}/${DESCRIPTION_MAX_LENGTH} (max reached)`
            : `${descriptionLength}/${DESCRIPTION_MAX_LENGTH}`}
          error={isDescriptionAtLimit}
          multiline
          minRows={2}
        />
        {isUpdateEditor && (
          <Alert severity="info">
            Turning off auto-open here disables that one release version only. A newer release version will auto-open again until the player opts out of that newer version too.
          </Alert>
        )}
        <TextField
          label="Start Page ID"
          value={draft.start_page_id || ''}
          onChange={(e) => handleFieldChange('start_page_id', e.target.value)}
        />
        <Stack direction="row" spacing={2}>
          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel id="manual-audience-label">Module</InputLabel>
            <Select
              labelId="manual-audience-label"
              label="Module"
              value={getPrimaryAudience(draft)}
              onChange={(e) => handleAudienceChange(e.target.value)}
            >
              {audienceOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Sort Order"
            type="number"
            value={draft.sort_order ?? 0}
            onChange={(e) => handleFieldChange('sort_order', Number(e.target.value || 0))}
            sx={{ width: 140 }}
          />
          <TextField
            label={isUpdateEditor ? 'Update Version' : 'Release Version'}
            value={draft.release_version || ''}
            onChange={(e) => handleFieldChange('release_version', e.target.value)}
            sx={{ minWidth: 180 }}
          />
          <Button variant="outlined" onClick={handleIncrementVersion}>
            Increment Version
          </Button>
        </Stack>
        <Stack direction="row" spacing={2}>
          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel id="manual-source-folder-label">Definition Folder</InputLabel>
            <Select
              labelId="manual-source-folder-label"
              label="Definition Folder"
              value={draft.source_folder || getDefaultSourceFolder(getPrimaryAudience(draft), editorScope)}
              onChange={(e) => handleSourceFolderChange(e.target.value)}
            >
              {sourceFolderOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Popup Version"
            value={draft.popup_version || ''}
            onChange={(e) => handleFieldChange('popup_version', e.target.value)}
            helperText={isSupportManual ? 'Used by the support banner to decide visibility.' : 'Optional override for update/support version tracking.'}
            sx={{ minWidth: 220 }}
          />
        </Stack>
        <Stack direction="row" spacing={2}>
          <FormControlLabel
            control={(
              <Checkbox
                checked={draft.auto_open_on_update === true}
                onChange={(e) => handleFieldChange('auto_open_on_update', e.target.checked)}
              />
            )}
            label={isUpdateEditor ? 'Auto-open this update' : 'Auto-open after update'}
          />
          {!isUpdateEditor && (
            <FormControlLabel
              control={(
                <Checkbox
                  checked={draft.is_whats_new === true}
                  onChange={(e) => handleFieldChange('is_whats_new', e.target.checked)}
                />
              )}
              label="Mark as What's New"
            />
          )}
          {!isUpdateEditor && (
            <FormControlLabel
              control={(
                <Checkbox
                  checked={draft.show_in_library !== false}
                  onChange={(e) => handleFieldChange('show_in_library', e.target.checked)}
                />
              )}
              label="Show in library"
            />
          )}
        </Stack>
        {isSupportManual && (
          <>
            <Alert severity="info">
              Support manuals drive the banner shown above normal manual pages. Keep "Show in library" off if this should stay banner-only.
            </Alert>
            <TextField
              label="Support URL"
              value={draft.support_url || ''}
              onChange={(e) => handleFieldChange('support_url', e.target.value)}
              helperText="Optional external link opened by the support button if your game-side handler uses it."
            />
            <TextField
              label="Banner Title"
              value={draft.banner_title || ''}
              onChange={(e) => handleFieldChange('banner_title', e.target.value)}
            />
            <TextField
              label="Banner Text"
              value={draft.banner_text || ''}
              onChange={(e) => handleFieldChange('banner_text', e.target.value)}
              multiline
              minRows={2}
            />
            <TextField
              label="Banner Button Label"
              value={draft.banner_action_label || ''}
              onChange={(e) => handleFieldChange('banner_action_label', e.target.value)}
            />
          </>
        )}
      </Stack>
    </Paper>
  );
};
