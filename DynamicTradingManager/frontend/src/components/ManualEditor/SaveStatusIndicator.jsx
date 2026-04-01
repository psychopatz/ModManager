import React from 'react';
import {
  Button,
  CircularProgress,
  Tooltip,
  Badge,
  Box,
} from '@mui/material';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

/**
 * SaveStatusIndicator - Button with visual feedback for save state
 * Shows:
 * - Pending state (gray, disabled)
 * - Saving state (spinner, disabled)
 * - Success state (green checkmark, brief indication)
 * - Error state (red, clickable to retry)
 */
export const SaveStatusIndicator = ({
  saving,
  isDrafty,
  lastSaveStatus, // 'success' | 'error' | null
  onSave,
  disabled,
  isUpdateEditor,
}) => {
  const label = isUpdateEditor ? 'Save Update' : 'Save Manual';
  const savingLabel = isUpdateEditor ? 'Saving Update...' : 'Saving Manual...';

  if (saving) {
    return (
      <Tooltip title="Saving...">
        <span>
          <Button
            startIcon={<CircularProgress size={18} color="inherit" />}
            variant="contained"
            disabled
            sx={{ bgcolor: 'primary.light' }}
          >
            {savingLabel}
          </Button>
        </span>
      </Tooltip>
    );
  }

  if (lastSaveStatus === 'success') {
    return (
      <Tooltip title="All changes saved">
        <span>
          <Button
            startIcon={<CheckCircleOutlineIcon sx={{ color: 'success.main' }} />}
            variant="contained"
            disabled={disabled || !isDrafty}
            onClick={onSave}
          >
            {label}
          </Button>
        </span>
      </Tooltip>
    );
  }

  if (lastSaveStatus === 'error') {
    return (
      <Tooltip title="Save failed - Click to retry">
        <span>
          <Button
            startIcon={<ErrorOutlineIcon sx={{ color: 'error.main' }} />}
            variant="contained"
            color="error"
            disabled={disabled}
            onClick={onSave}
          >
            {label}
          </Button>
        </span>
      </Tooltip>
    );
  }

  // Default state - has changes to save
  if (isDrafty) {
    return (
      <Tooltip title={disabled ? 'Loading...' : 'Click to save your changes'}>
        <span>
          <Badge
            badgeContent="●"
            color="warning"
            sx={{
              '& .MuiBadge-badge': {
                right: 0,
                top: 13,
                border: `2px solid white`,
                padding: '0 4px',
              },
            }}
          >
            <Button
              startIcon={<SaveOutlinedIcon />}
              variant="contained"
              disabled={disabled}
              onClick={onSave}
            >
              {label}
            </Button>
          </Badge>
        </span>
      </Tooltip>
    );
  }

  // No draft changes
  return (
    <Tooltip title="No unsaved changes">
      <span>
        <Button
          startIcon={<SaveOutlinedIcon />}
          variant="contained"
          disabled={disabled || true}
        >
          {label}
        </Button>
      </span>
    </Tooltip>
  );
};
