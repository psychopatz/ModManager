import React from 'react';
import {
  Alert,
  Box,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { List as VirtualList } from 'react-window';
import { TREE_ROW_HEIGHT } from './constants';
import AutoSizer from './AutoSizer';
import TagTreeRow from './TagTreeRow';

const TagTreePanel = ({
  status,
  search,
  setSearch,
  loadingCatalog,
  visibleNodeCount,
  handleExpandAll,
  handleCollapseAll,
  loadPage,
  saving,
  visibleRows,
  selectedTag,
  handleSelectTag,
  toggleExpanded,
}) => (
  <Paper elevation={3} sx={{ p: 3, minHeight: 760, display: 'flex', flexDirection: 'column' }}>
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4" gutterBottom>
          Tag Pricing
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Browse dynamic pricing tags as a collapsible hierarchy. Root tags like `Food` compound into `Food.NonPerishable` and `Food.NonPerishable.Canned`.
        </Typography>
      </Box>

      {status.message ? (
        <Alert severity={status.type || 'info'}>
          {status.message}
        </Alert>
      ) : null}

      <TextField
        label="Search categories, domains, or samples"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Food.NonPerishable"
      />

      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="body2" color="text.secondary">
          {loadingCatalog ? 'Loading tags...' : `${visibleNodeCount} visible nodes`}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={handleExpandAll} disabled={loadingCatalog}>
            Expand All
          </Button>
          <Button variant="outlined" onClick={handleCollapseAll} disabled={loadingCatalog}>
            Collapse All
          </Button>
          <Button variant="outlined" onClick={() => loadPage(true)} disabled={loadingCatalog || saving}>
            Reload
          </Button>
        </Stack>
      </Stack>
    </Stack>

    <Box sx={{ mt: 2, flexGrow: 1, minHeight: 520, borderRadius: 2, overflow: 'hidden', bgcolor: 'rgba(255,255,255,0.03)' }}>
      <AutoSizer>
        {({ height, width }) => (
          height > 0 && width > 0 ? (
            <VirtualList
              style={{ height, width }}
              rowCount={visibleRows.length}
              rowHeight={TREE_ROW_HEIGHT}
              rowComponent={TagTreeRow}
              rowProps={{
                visibleRows,
                selectedTag,
                onSelectTag: handleSelectTag,
                onToggleExpanded: toggleExpanded,
              }}
            />
          ) : null
        )}
      </AutoSizer>
    </Box>
  </Paper>
);

export default TagTreePanel;
