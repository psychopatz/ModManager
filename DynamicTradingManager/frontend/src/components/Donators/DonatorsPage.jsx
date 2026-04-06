import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import { getDonatorsDefinition, saveDonatorsDefinition, uploadDonatorImage } from '../../services/api';
import DonatorRow from './DonatorRow';
import DonatorsPreview from './DonatorsPreview';
import { createEmptySupporter, createSupporterUiKey, slugifyDonator, sortSupporters } from './donatorsUtils';

function normalizeSupporter(entry, fallbackIndex) {
  const generatedId = slugifyDonator(entry?.id || entry?.name || `supporter_${fallbackIndex + 1}`) || `supporter_${fallbackIndex + 1}`;
  return {
    ui_key: String(entry?.ui_key || createSupporterUiKey(generatedId || `supporter_${fallbackIndex + 1}`)),
    id: generatedId,
    name: String(entry?.name || ''),
    total_donation: Number(entry?.total_donation || 0),
    image_path: String(entry?.image_path || ''),
    support_message: String(entry?.support_message || entry?.supportMessage || entry?.message || ''),
    active: entry?.active !== false,
  };
}

export default function DonatorsPage() {
  const [state, setState] = useState({
    supporters: [],
    title: 'Hall of Fame Donators',
    page_title: 'Hall of Fame',
    block_title: 'Hall of Fame Donators',
    autoplay_ms: 4000,
    currency_symbol: '$',
    thank_you_text: 'Thank you to everyone helping keep Dynamic Trading moving.',
    asset_base_url: '/static/manuals/dt_support_hall_of_fame',
  });
  const [status, setStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingIndex, setUploadingIndex] = useState(-1);

  const backendOrigin = useMemo(() => {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }, []);

  const loadDonators = async () => {
    setLoading(true);
    setStatus({ type: '', message: '' });
    try {
      const response = await getDonatorsDefinition();
      const payload = response.data || {};
      const supporters = sortSupporters((payload.supporters || []).map(normalizeSupporter));
      setState({
        supporters,
        title: String(payload.title || 'Hall of Fame Donators'),
        page_title: String(payload.page_title || 'Hall of Fame'),
        block_title: String(payload.block_title || 'Hall of Fame Donators'),
        autoplay_ms: Number(payload.autoplay_ms || 4000),
        currency_symbol: String(payload.currency_symbol || '$'),
        thank_you_text: String(payload.thank_you_text || 'Thank you to everyone helping keep Dynamic Trading moving.'),
        asset_base_url: String(payload.asset_base_url || '/static/manuals/dt_support_hall_of_fame'),
      });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Failed to load donators definition.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDonators();
  }, []);

  const updateSupporters = (updater) => {
    setState((current) => {
      const nextSupporters = updater(current.supporters.map((entry, index) => normalizeSupporter(entry, index)));
      return {
        ...current,
        supporters: nextSupporters.map((entry, index) => normalizeSupporter(entry, index)),
      };
    });
  };

  const handleSupporterFieldChange = (index, field, value) => {
    updateSupporters((entries) => {
      const next = [...entries];
      const row = { ...next[index] };

      if (field === 'total_donation') {
        row.total_donation = Number(value || 0);
      } else if (field === 'active') {
        row.active = value === true;
      } else if (field === 'name') {
        row.name = value;
        row.id = slugifyDonator(value) || `supporter_${index + 1}`;
      } else {
        row[field] = value;
      }

      next[index] = row;
      return next;
    });
  };

  const handleAddSupporter = () => {
    updateSupporters((entries) => [...entries, createEmptySupporter(entries.length + 1)]);
  };

  const handleDeleteSupporter = (index) => {
    updateSupporters((entries) => entries.filter((_, entryIndex) => entryIndex !== index));
  };

  const handleUpload = async (index, file, source = 'upload') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('module', 'common');

    try {
      setUploadingIndex(index);
      const response = await uploadDonatorImage(formData);
      handleSupporterFieldChange(index, 'image_path', response.data.path);
      setStatus({ type: 'success', message: source === 'clipboard' ? 'Donator image pasted from clipboard.' : 'Donator image uploaded.' });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error.response?.data?.detail || error.message || 'Donator image upload failed.',
      });
    } finally {
      setUploadingIndex(-1);
    }
  };

  const handlePasteError = (error) => {
    setStatus({
      type: 'error',
      message: error?.message || 'Clipboard image paste failed.',
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setStatus({ type: '', message: '' });
    try {
      const payload = {
        title: state.title,
        page_title: state.page_title,
        block_title: state.block_title,
        autoplay_ms: state.autoplay_ms,
        currency_symbol: state.currency_symbol,
        thank_you_text: state.thank_you_text,
        supporters: sortSupporters(state.supporters).map((entry, index) => normalizeSupporter(entry, index)),
      };
      const response = await saveDonatorsDefinition(payload);
      const manual = response.data?.manual || {};
      setState((current) => ({
        ...current,
        supporters: sortSupporters((manual.supporters || []).map(normalizeSupporter)),
        thank_you_text: String(manual.thank_you_text || current.thank_you_text || ''),
        asset_base_url: String(manual.asset_base_url || current.asset_base_url),
      }));
      setStatus({ type: 'success', message: 'Hall of Fame manual updated.' });
    } catch (error) {
      setStatus({ type: 'error', message: error.response?.data?.detail || 'Failed to save donators definition.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1.2fr 0.8fr' }, gap: 3 }}>
      <Paper elevation={3} sx={{ p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
          <Box>
            <Typography variant="h4" gutterBottom>
              Donators
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Dedicated editor for the Hall of Fame donor manual and support-banner donor carousel.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={loadDonators} disabled={loading || saving}>
              Reload
            </Button>
            <Button variant="contained" onClick={handleSave} disabled={loading || saving}>
              {saving ? 'Saving...' : 'Save Donators'}
            </Button>
          </Stack>
        </Stack>

        {status.message ? (
          <Alert severity={status.type || 'info'} sx={{ mb: 2 }}>
            {status.message}
          </Alert>
        ) : null}

        <Stack spacing={1.5} sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary">
            Manual ID: `dt_support_hall_of_fame`
          </Typography>
          <Typography variant="subtitle2" color="text.secondary">
            Manual Type: `donators`
          </Typography>
          <Typography variant="subtitle2" color="text.secondary">
            Sort Mode: highest donation first
          </Typography>
        </Stack>

        <TextField
          fullWidth
          multiline
          minRows={2}
          maxRows={4}
          label="Thank You Text"
          value={state.thank_you_text}
          onChange={(event) => setState((current) => ({ ...current, thank_you_text: event.target.value }))}
          helperText="Shown at the bottom of the Hall of Fame page."
          sx={{ mb: 3 }}
        />

        <Stack spacing={2}>
          {state.supporters.map((supporter, index) => (
            <DonatorRow
              key={supporter.ui_key || `supporter-${index}`}
              supporter={supporter}
              index={index}
              backendOrigin={backendOrigin}
              assetBaseUrl={state.asset_base_url}
              currencySymbol={state.currency_symbol}
              onChange={(field, value) => handleSupporterFieldChange(index, field, value)}
              onDelete={() => handleDeleteSupporter(index)}
              onUpload={(file) => handleUpload(index, file, 'upload')}
              onPasteImage={(file) => handleUpload(index, file, 'clipboard')}
              onPasteError={handlePasteError}
              uploading={uploadingIndex === index}
            />
          ))}

          <Button variant="outlined" onClick={handleAddSupporter}>
            Add Donator
          </Button>
        </Stack>
      </Paper>

      <DonatorsPreview
        supporters={state.supporters}
        backendOrigin={backendOrigin}
        assetBaseUrl={state.asset_base_url}
        currencySymbol={state.currency_symbol}
        autoplayMs={state.autoplay_ms}
        thankYouText={state.thank_you_text}
      />
    </Box>
  );
}
