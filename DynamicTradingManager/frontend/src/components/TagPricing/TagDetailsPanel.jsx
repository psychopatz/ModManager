import React from 'react';
import {
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  Slider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { SLIDER_MIN, SLIDER_MAX } from './constants';
import { formatPrice } from './formatters';
import { getTagTone } from './treeUtils';

const TagDetailsPanel = ({
  selectedTag,
  pendingAddition,
  setPendingAddition,
  hasUnsavedChange,
  saving,
  handleReset,
  handleSave,
  config,
  selectedCatalogRow,
  catalogSource,
  catalogItemCount,
  compoundRows,
  savedCompoundTotal,
  pendingCompoundTotal,
  previewData,
}) => {
  const selectedTone = getTagTone(selectedTag);

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      {selectedTag ? (
        <Stack spacing={2.5}>
          <Box>
            <Typography variant="overline" color="text.secondary">Selected Tag</Typography>
            <Typography variant="h4" sx={{ color: selectedTone.text }}>{selectedTag}</Typography>
            <Typography variant="body2" color="text.secondary">
              Editing a parent category raises or lowers the whole branch. Editing the selected node adds another layer on top of its inherited chain.
            </Typography>
          </Box>

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'stretch', md: 'center' }}>
            <Box sx={{ flexGrow: 1, px: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Flat price addition
              </Typography>
              <Slider
                value={Number(pendingAddition || 0)}
                min={SLIDER_MIN}
                max={SLIDER_MAX}
                step={1}
                valueLabelDisplay="auto"
                onChange={(_, value) => setPendingAddition(Array.isArray(value) ? value[0] : value)}
                sx={{ color: selectedTone.text }}
              />
            </Box>
            <TextField
              label="Exact amount"
              type="number"
              value={Number(pendingAddition || 0)}
              onChange={(event) => setPendingAddition(Number(event.target.value || 0))}
              sx={{ width: { xs: '100%', md: 160 } }}
            />
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={handleReset} disabled={!hasUnsavedChange || saving}>
                Reset
              </Button>
              <Button variant="contained" onClick={handleSave} disabled={saving || !selectedTag || !config || !hasUnsavedChange}>
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </Stack>
          </Stack>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`Pending ${formatPrice(pendingAddition)}`} color={hasUnsavedChange ? 'warning' : 'default'} />
            <Chip label={`Saved ${formatPrice(config?.tag_price_additions?.[selectedTag] || 0)}`} variant="outlined" />
            <Chip label={`${selectedCatalogRow?.item_count || 0} matching items`} variant="outlined" />
            {catalogSource ? <Chip label={`Source ${catalogSource}`} variant="outlined" /> : null}
            {catalogItemCount > 0 ? <Chip label={`Runtime items ${catalogItemCount}`} variant="outlined" /> : null}
          </Stack>

          <Divider />

          <Box>
            <Typography variant="subtitle1" gutterBottom>Compound Chain</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Every saved value in this path stacks into the selected branch and all of its children.
            </Typography>
            <Stack spacing={1}>
              {compoundRows.map((row) => {
                const tone = getTagTone(row.tag);
                return (
                  <Box
                    key={row.tag}
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 2,
                      p: 1.2,
                      borderRadius: 2,
                      bgcolor: tone.bg,
                      border: `1px solid ${tone.border}`,
                    }}
                  >
                    <Typography variant="body2" sx={{ color: tone.text }}>
                      {row.tag}
                    </Typography>
                    <Typography variant="body2" sx={{ color: tone.muted }}>
                      {formatPrice(row.pendingValue)}
                      {row.pendingValue !== row.savedValue ? ` (${formatPrice(row.savedValue)} saved)` : ''}
                    </Typography>
                  </Box>
                );
              })}
            </Stack>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }}>
              <Chip label={`Saved chain ${formatPrice(savedCompoundTotal)}`} variant="outlined" />
              <Chip label={`Preview chain ${formatPrice(pendingCompoundTotal)}`} color={hasUnsavedChange ? 'warning' : 'default'} />
            </Stack>
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle1" gutterBottom>Affected Domains</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {(previewData?.domains || selectedCatalogRow?.domains || []).map((domain) => {
                const tone = getTagTone(domain.tag);
                return (
                  <Chip
                    key={`${selectedTag}-${domain.tag}`}
                    label={`${domain.tag} (${domain.count})`}
                    variant="outlined"
                    sx={{ bgcolor: tone.bg, borderColor: tone.border, color: tone.text }}
                  />
                );
              })}
            </Stack>
          </Box>

          <Box>
            <Typography variant="subtitle1" gutterBottom>Sample Items</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {(selectedCatalogRow?.samples || []).map((sample) => (
                <Chip key={`${selectedTag}-${sample.item_id}`} label={`${sample.name} (${sample.item_id})`} variant="outlined" />
              ))}
            </Stack>
          </Box>
        </Stack>
      ) : (
        <Typography color="text.secondary">
          Select a category tag to start tuning additive pricing.
        </Typography>
      )}
    </Paper>
  );
};

export default TagDetailsPanel;
