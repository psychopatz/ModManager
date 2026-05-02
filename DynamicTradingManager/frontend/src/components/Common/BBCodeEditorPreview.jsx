import React, { useMemo, useState } from 'react';
import { Box, Paper, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { renderBBCodeToReact } from '../../utils/bbcodePreview.jsx';

const BBCodeEditorPreview = ({
  label = 'BBCode',
  value,
  onChange,
  editable = true,
  minRows = 6,
  maxRows = 28,
  editorHelperText,
  previewTitle = 'Preview',
  compact = false,
  defaultMode = 'editor',
}) => {
  const [mode, setMode] = useState(defaultMode);
  const text = String(value || '');
  const dynamicRows = Math.max(minRows, Math.min(maxRows, text.split('\n').length + 1));
  const preview = useMemo(() => renderBBCodeToReact(text), [text]);

  return (
    <Stack spacing={1}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="caption" sx={{ opacity: 0.6, fontWeight: 600 }}>{label}</Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={mode}
          onChange={(_, v) => v && setMode(v)}
        >
          {editable && <ToggleButton value="editor" sx={{ px: 1.5, py: 0.25, fontSize: '0.7rem' }}>Editor</ToggleButton>}
          <ToggleButton value="preview" sx={{ px: 1.5, py: 0.25, fontSize: '0.7rem' }}>Preview</ToggleButton>
        </ToggleButtonGroup>
      </Stack>

      {mode === 'editor' && editable && (
        <TextField
          fullWidth
          multiline
          value={text}
          rows={dynamicRows}
          onChange={(event) => onChange?.(event.target.value)}
          helperText={editorHelperText}
          sx={{ '& .MuiInputBase-input': { fontFamily: 'monospace', fontSize: compact ? '0.8rem' : '0.9rem' } }}
        />
      )}

      {mode === 'editor' && !editable && (
        <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'rgba(0,0,0,0.2)' }}>
          <Typography variant="caption" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', color: '#c9d1d9' }}>
            {text || 'No content.'}
          </Typography>
        </Paper>
      )}

      {mode === 'preview' && (
        <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'rgba(0,0,0,0.2)' }}>
          <Box sx={{ maxHeight: compact ? 260 : 360, overflowY: 'auto', pr: 0.5 }}>
            {text ? preview : <Typography variant="caption" sx={{ opacity: 0.5 }}>No content to preview.</Typography>}
          </Box>
        </Paper>
      )}
    </Stack>
  );
};

export default BBCodeEditorPreview;
