import React, { useRef } from 'react';
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import { getClipboardImageFromPasteEvent, readClipboardImageFile } from './clipboardImage';
import { formatDonation, resolveDonatorImageUrl } from './donatorsUtils';

export default function DonatorRow({
  supporter,
  index,
  backendOrigin,
  assetBaseUrl,
  currencySymbol,
  onChange,
  onDelete,
  onUpload,
  onPasteImage,
  onPasteError,
  uploading = false,
}) {
  const fileInputRef = useRef(null);
  const previewUrl = resolveDonatorImageUrl(backendOrigin, assetBaseUrl, supporter.image_path);

  const handlePasteEvent = (event) => {
    const file = getClipboardImageFromPasteEvent(event);
    if (!file) return;
    event.preventDefault();
    if (onPasteImage) {
      onPasteImage(file);
      return;
    }
    onUpload(file);
  };

  const handlePasteButton = async () => {
    try {
      const file = await readClipboardImageFile();
      if (onPasteImage) {
        await onPasteImage(file);
        return;
      }
      await onUpload(file);
    } catch (error) {
      if (onPasteError) {
        onPasteError(error);
      }
    }
  };

  return (
    <Paper
      variant="outlined"
      tabIndex={0}
      onPaste={handlePasteEvent}
      sx={{
        p: 2,
        outline: 'none',
        '&:focus-visible': {
          borderColor: 'secondary.main',
          boxShadow: '0 0 0 1px rgba(244,143,177,0.55)',
        },
      }}
    >
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="subtitle1">Donator #{index + 1}</Typography>
          <Button color="error" onClick={onDelete}>
            Remove
          </Button>
        </Stack>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
          <TextField
            fullWidth
            label="Name"
            value={supporter.name || ''}
            onChange={(event) => onChange('name', event.target.value)}
          />
          <TextField
            fullWidth
            label="Generated ID"
            value={supporter.id || ''}
            InputProps={{ readOnly: true }}
            helperText="Auto-generated from the donor name"
          />
          <TextField
            fullWidth
            type="number"
            label="Total Donation"
            value={supporter.total_donation ?? 0}
            onChange={(event) => onChange('total_donation', event.target.value)}
            helperText={`Displayed as ${formatDonation(supporter.total_donation, currencySymbol)}`}
          />
        </Stack>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }}>
          <TextField
            fullWidth
            label="Image Path"
            value={supporter.image_path || ''}
            onChange={(event) => onChange('image_path', event.target.value)}
          />
          <Button variant="outlined" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload Image'}
          </Button>
          <Button variant="outlined" onClick={handlePasteButton} disabled={uploading}>
            Paste Image
          </Button>
          <FormControlLabel
            control={<Checkbox checked={supporter.active !== false} onChange={(event) => onChange('active', event.target.checked)} />}
            label="Active"
          />
        </Stack>

        <TextField
          fullWidth
          multiline
          minRows={2}
          maxRows={5}
          label="Support Message"
          value={supporter.support_message || ''}
          onChange={(event) => onChange('support_message', event.target.value)}
          helperText="Shown in the Hall of Fame card as the supporter message."
        />

        <Typography variant="caption" color="text.secondary">
          Click this donor card and press Ctrl+V to paste an image from the clipboard, or use the Paste Image button.
        </Typography>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onUpload(file);
            event.target.value = '';
          }}
        />

        <Box
          sx={{
            height: 120,
            borderRadius: 2,
            border: '1px solid rgba(255,255,255,0.12)',
            bgcolor: 'rgba(255,255,255,0.03)',
            display: 'grid',
            placeItems: 'center',
            overflow: 'hidden',
          }}
        >
          {previewUrl ? (
            <Box
              component="img"
              src={previewUrl}
              alt={supporter.name || `Donator ${index + 1}`}
              sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <Typography variant="body2" color="text.secondary">
              No donor image selected
            </Typography>
          )}
        </Box>
      </Stack>
    </Paper>
  );
}
