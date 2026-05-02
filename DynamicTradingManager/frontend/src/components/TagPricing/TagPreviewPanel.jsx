import React from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { formatCompactDelta, formatPreviewNumber, formatPrice } from './formatters';
import { getTagTone } from './treeUtils';

const PreviewItemCard = ({
  row,
  selectedTag,
  previewData,
  overridesByItem,
  overrideDraft,
  setOverrideDraft,
  saving,
  blacklistingItemId,
  handleBlacklistItem,
  openOverrideEditor,
  handleDeleteItemOverride,
  handleSaveItemOverride,
  closeOverrideEditor,
  tagOptions,
}) => {
  const tone = getTagTone(row.primary_tag);
  const existingOverride = overridesByItem[row.item_id];
  const isEditingOverride = overrideDraft?.itemId === row.item_id;

  return (
    <Box
      key={`${row.item_id}-${selectedTag}`}
      sx={{
        display: 'grid',
        gap: 1.5,
        p: 1.25,
        borderRadius: 2,
        bgcolor: tone.bg,
        border: `1px solid ${tone.border}`,
      }}
    >
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        justifyContent="space-between"
        spacing={1.5}
        alignItems={{ xs: 'flex-start', md: 'center' }}
      >
        <Box>
          <Typography variant="body1" sx={{ color: tone.text }}>{row.name}</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            <Chip
              label={row.primary_tag}
              size="small"
              variant="outlined"
              sx={{ bgcolor: tone.bgStrong, borderColor: tone.border, color: tone.text }}
            />
            {existingOverride?.basePrice !== undefined ? (
              <Chip label={`Price ${existingOverride.basePrice}`} size="small" color="warning" />
            ) : null}
            {existingOverride?.stockRange ? (
              <Chip
                label={`Stock ${existingOverride.stockRange.min ?? row.stock_min}-${existingOverride.stockRange.max ?? row.stock_max}`}
                size="small"
                color="warning"
              />
            ) : null}
            {Array.isArray(existingOverride?.tags) ? (
              <Chip label={`Tags ${existingOverride.tags.length}`} size="small" color="warning" />
            ) : null}
          </Stack>
          <Typography variant="caption" sx={{ color: tone.muted, display: 'block', mt: 0.75 }}>
            {row.item_id}
          </Typography>
        </Box>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ xs: 'flex-start', sm: 'center' }}>
          <Box>
            <Typography variant="body2" sx={{ color: tone.muted }}>
              Price {row.current_price} {'->'} {row.preview_price}
            </Typography>
            {(row.current_global_price_clamp === 'max' || row.preview_global_price_clamp === 'max') ? (
              <Typography variant="caption" sx={{ color: 'warning.light', display: 'block' }}>
                Uncapped {formatPreviewNumber(row.current_pre_clamp_price)} {'->'} {formatPreviewNumber(row.preview_pre_clamp_price)} (max {formatPreviewNumber(row.global_max_price)})
              </Typography>
            ) : null}
            <Typography variant="caption" sx={{ color: tone.muted }}>
              Stock {row.stock_min}-{row.stock_max}
            </Typography>
          </Box>
          <Typography
            variant="body2"
            sx={{
              color: row.delta > 0
                ? 'warning.light'
                : row.delta < 0
                  ? 'success.light'
                  : row.raw_delta !== 0
                    ? 'info.light'
                    : tone.muted,
            }}
          >
            {formatPrice(row.delta)}
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {row.raw_delta !== 0 && row.delta === 0 && (row.current_global_price_clamp === 'max' || row.preview_global_price_clamp === 'max') ? (
              <Chip
                size="small"
                color="warning"
                variant="outlined"
                label={`Cap hides ${formatCompactDelta(row.raw_delta)}`}
              />
            ) : null}
            {row.current_global_price_clamp === 'max' || row.preview_global_price_clamp === 'max' ? (
              <Chip
                size="small"
                color="warning"
                variant="outlined"
                label="Max capped"
              />
            ) : null}
            <Button
              variant="outlined"
              size="small"
              color="error"
              onClick={() => handleBlacklistItem(row.item_id)}
              disabled={blacklistingItemId === row.item_id}
            >
              {blacklistingItemId === row.item_id ? 'Blacklisting...' : 'Blacklist'}
            </Button>
            <Button
              variant="outlined"
              size="small"
              onClick={() => openOverrideEditor(row)}
            >
              {isEditingOverride ? 'Editing Override' : 'Edit Override'}
            </Button>
            {existingOverride ? (
              <Button
                variant="outlined"
                size="small"
                onClick={() => handleDeleteItemOverride(row.item_id)}
                disabled={saving}
              >
                Delete Override
              </Button>
            ) : null}
          </Stack>
        </Stack>
      </Stack>

      {isEditingOverride ? (
        <Stack spacing={1.25} sx={{ pt: 0.5 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
            <TextField
              label={`Forced price (current ${overrideDraft.currentPrice})`}
              type="number"
              value={overrideDraft.basePrice}
              onChange={(event) => setOverrideDraft((current) => ({ ...current, basePrice: event.target.value }))}
              sx={{ width: { xs: '100%', md: 220 } }}
            />
            <TextField
              label={`Stock min (current ${overrideDraft.currentStockMin})`}
              type="number"
              value={overrideDraft.stockMin}
              onChange={(event) => setOverrideDraft((current) => ({ ...current, stockMin: event.target.value }))}
              sx={{ width: { xs: '100%', md: 180 } }}
            />
            <TextField
              label={`Stock max (current ${overrideDraft.currentStockMax})`}
              type="number"
              value={overrideDraft.stockMax}
              onChange={(event) => setOverrideDraft((current) => ({ ...current, stockMax: event.target.value }))}
              sx={{ width: { xs: '100%', md: 180 } }}
            />
          </Stack>

          <Autocomplete
            multiple
            options={tagOptions}
            value={overrideDraft.tags}
            onChange={(_, value) => setOverrideDraft((current) => ({ ...current, tags: value }))}
            renderTags={(value, getTagProps) => value.map((option, index) => (
              <Chip
                {...getTagProps({ index })}
                key={`${overrideDraft.itemId}-${option}`}
                label={option}
                size="small"
                sx={{
                  bgcolor: getTagTone(option).bg,
                  borderColor: getTagTone(option).border,
                  color: getTagTone(option).text,
                }}
                variant="outlined"
              />
            ))}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Override tags"
                placeholder="Choose discovered tags"
                helperText={`Current tags: ${(overrideDraft.currentTags || []).join(', ') || 'None'}`}
              />
            )}
          />

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              variant="outlined"
              size="small"
              onClick={() => setOverrideDraft((current) => ({ ...current, tags: [...current.currentTags] }))}
            >
              Load Current Tags
            </Button>
            <Button
              variant="outlined"
              size="small"
              onClick={() => setOverrideDraft((current) => ({ ...current, tags: [] }))}
            >
              Clear Tag Override
            </Button>
            <Button
              variant="contained"
              size="small"
              onClick={handleSaveItemOverride}
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Override'}
            </Button>
            <Button
              variant="outlined"
              size="small"
              onClick={closeOverrideEditor}
              disabled={saving}
            >
              Cancel
            </Button>
          </Stack>
        </Stack>
      ) : null}
    </Box>
  );
};

const TagPreviewPanel = ({
  selectedTag,
  loadingPreview,
  previewData,
  previewStale,
  handleGeneratePreview,
  config,
  overridesByItem,
  overrideDraft,
  setOverrideDraft,
  saving,
  blacklistingItemId,
  handleBlacklistItem,
  openOverrideEditor,
  handleDeleteItemOverride,
  handleSaveItemOverride,
  closeOverrideEditor,
  tagOptions,
}) => (
  <Paper elevation={3} sx={{ p: 3, minHeight: 420 }}>
    <Stack
      direction={{ xs: 'column', lg: 'row' }}
      justifyContent="space-between"
      alignItems={{ xs: 'flex-start', lg: 'center' }}
      spacing={1.5}
      sx={{ mb: 2 }}
    >
      <Box>
        <Typography variant="h5">Preview</Typography>
        <Typography variant="body2" color="text.secondary">
          Generate on demand to compare the selected branch against the current slider value.
        </Typography>
      </Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1}
        alignItems={{ xs: 'stretch', sm: 'center' }}
        sx={{ width: { xs: '100%', lg: 'auto' } }}
      >
        <Chip
          label={
            loadingPreview
              ? 'Generating preview...'
              : previewData
                ? `Avg ${previewData?.stats?.avg_current_price || 0} -> ${previewData?.stats?.avg_preview_price || 0}`
                : 'No preview yet'
          }
          color={loadingPreview ? 'warning' : previewStale ? 'warning' : 'default'}
          variant="outlined"
          sx={{ alignSelf: { xs: 'flex-start', sm: 'center' } }}
        />
        <Button
          variant="contained"
          onClick={handleGeneratePreview}
          disabled={!selectedTag || !config || loadingPreview}
          sx={{ whiteSpace: 'nowrap', minWidth: 172, alignSelf: { xs: 'stretch', sm: 'center' } }}
        >
          {loadingPreview ? 'Generating...' : 'Generate Preview'}
        </Button>
      </Stack>
    </Stack>

    {previewData ? (
      <Stack spacing={1.25}>
        {previewStale ? (
          <Alert severity="warning">
            The preview is stale. Generate it again to reflect the latest tag value.
          </Alert>
        ) : null}
        {(previewData.items || []).map((row) => (
          <PreviewItemCard
            key={`${row.item_id}-${selectedTag}`}
            row={row}
            selectedTag={selectedTag}
            previewData={previewData}
            overridesByItem={overridesByItem}
            overrideDraft={overrideDraft}
            setOverrideDraft={setOverrideDraft}
            saving={saving}
            blacklistingItemId={blacklistingItemId}
            handleBlacklistItem={handleBlacklistItem}
            openOverrideEditor={openOverrideEditor}
            handleDeleteItemOverride={handleDeleteItemOverride}
            handleSaveItemOverride={handleSaveItemOverride}
            closeOverrideEditor={closeOverrideEditor}
            tagOptions={tagOptions}
          />
        ))}
      </Stack>
    ) : (
      <Stack spacing={1.25}>
        {previewStale ? (
          <Alert severity="info">
            Preview is manual now. Click `Generate Preview` when you want to inspect the current tag value.
          </Alert>
        ) : null}
        <Typography color="text.secondary">
          Preview data will appear here once you generate it for the selected tag.
        </Typography>
      </Stack>
    )}
  </Paper>
);

export default TagPreviewPanel;
