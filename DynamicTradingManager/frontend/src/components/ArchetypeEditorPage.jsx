import React, { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import RefreshIcon from '@mui/icons-material/Refresh';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import ArrowBackIosNewIcon from '@mui/icons-material/ArrowBackIosNew';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import { getArchetypeEditorData, saveArchetypeDefinition, getWorkshopTargets } from '../services/api';

const DRAG_MIME = 'application/x-dt-archetype-entry';

const allocationKey = (entry) => {
  if (entry.kind === 'item') {
    return `item:${entry.item_id}`;
  }
  return `tag:${(entry.tags || []).join('|')}`;
};

const cloneAllocations = (allocations = []) => allocations.map((entry) => ({
  kind: entry.kind,
  count: Number(entry.count || 1),
  tags: Array.isArray(entry.tags) ? [...entry.tags] : undefined,
  item_id: entry.item_id,
  item_name: entry.item_name,
  label: entry.label,
  matched_item_count: Number(entry.matched_item_count || 0),
  sample_items: Array.isArray(entry.sample_items) ? [...entry.sample_items] : [],
}));

const cloneTags = (values = []) => values.map((value) => String(value));
const cloneWants = (values = []) => values.map((row) => ({
  tag: row.tag || '',
  multiplier: String(row.multiplier ?? ''),
}));

const createDraftFromArchetype = (archetype) => ({
  name: archetype?.name || '',
  allocations: cloneAllocations(archetype?.allocations || []),
  expertTags: cloneTags(archetype?.expert_tags || []),
  forbid: cloneTags(archetype?.forbid || []),
  wants: cloneWants(archetype?.wants || []),
});

const normalizeAllocationsForSave = (allocations = []) => allocations.map((entry) => {
  if (entry.kind === 'item') {
    return {
      kind: 'item',
      item_id: entry.item_id,
      count: Math.max(1, Number(entry.count || 1)),
    };
  }

  return {
    kind: 'tag',
    tags: Array.isArray(entry.tags) ? entry.tags.filter(Boolean) : [],
    count: Math.max(1, Number(entry.count || 1)),
  };
});

const buildSavePayload = (draft, archetypeId = '') => ({
  name: String(draft.name || '').trim() || archetypeId,
  allocations: normalizeAllocationsForSave(draft.allocations || []),
  expert_tags: (draft.expertTags || []).map((value) => String(value).trim()).filter(Boolean),
  forbid: (draft.forbid || []).map((value) => String(value).trim()).filter(Boolean),
  wants: (draft.wants || [])
    .map((row) => ({
      tag: String(row.tag || '').trim(),
      multiplier: Number(row.multiplier),
    }))
    .filter((row) => row.tag),
});

const issueKey = (issue) => JSON.stringify({
  code: issue.code,
  field: issue.field,
  value: issue.value,
  path: issue.path,
});

const buildTagTree = (rows) => {
  const nodeMap = new Map();

  const ensureNode = (tag) => {
    if (!nodeMap.has(tag)) {
      const parts = tag.split('.');
      nodeMap.set(tag, {
        tag,
        label: parts[parts.length - 1],
        children: [],
        meta: null,
      });
    }
    return nodeMap.get(tag);
  };

  rows.forEach((row) => {
    const parts = row.tag.split('.');
    const node = ensureNode(row.tag);
    node.meta = row;

    for (let index = 1; index < parts.length; index += 1) {
      const parentTag = parts.slice(0, index).join('.');
      const childTag = parts.slice(0, index + 1).join('.');
      const parent = ensureNode(parentTag);
      const child = ensureNode(childTag);
      if (!parent.children.some((candidate) => candidate.tag === child.tag)) {
        parent.children.push(child);
      }
    }
  });

  const sortNode = (node) => {
    node.children.sort((left, right) => left.label.localeCompare(right.label));
    node.children.forEach(sortNode);
  };

  const roots = Array.from(nodeMap.values()).filter((node) => !node.tag.includes('.'));
  roots.sort((left, right) => left.label.localeCompare(right.label));
  roots.forEach(sortNode);
  return roots;
};

const filterTree = (nodes, query) => {
  if (!query) {
    return nodes;
  }

  const lowered = query.toLowerCase();

  return nodes.reduce((acc, node) => {
    const filteredChildren = filterTree(node.children || [], query);
    const sampleHit = (node.meta?.sample_items || []).some((sample) => (
      sample.item_id.toLowerCase().includes(lowered)
      || sample.name.toLowerCase().includes(lowered)
    ));
    const matchesSelf = node.tag.toLowerCase().includes(lowered) || sampleHit;

    if (!matchesSelf && !filteredChildren.length) {
      return acc;
    }

    acc.push({
      ...node,
      children: filteredChildren,
    });
    return acc;
  }, []);
};

function TagBranch({
  node,
  depth,
  expandedTags,
  onToggle,
  onAddTag,
  onDragStart,
  forceExpand = false,
}) {
  const hasChildren = Boolean(node.children?.length);
  const isExpanded = forceExpand || Boolean(expandedTags[node.tag] ?? depth === 0);
  const itemCount = node.meta?.item_count || 0;
  const coveredCount = node.meta?.covered_item_count || 0;

  return (
    <Box sx={{ pl: depth ? 2 : 0, borderLeft: depth ? '1px solid rgba(255,255,255,0.08)' : 'none', ml: depth ? 0.75 : 0 }}>
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{
          py: 0.75,
          px: 1,
          borderRadius: 2,
          bgcolor: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.06)',
          mb: 0.75,
        }}
      >
        <Box sx={{ width: 28, display: 'grid', placeItems: 'center' }}>
          {hasChildren ? (
            <Button size="small" onClick={() => onToggle(node.tag)} sx={{ minWidth: 28, p: 0.25 }}>
              {isExpanded ? <KeyboardArrowDownIcon fontSize="small" /> : <KeyboardArrowRightIcon fontSize="small" />}
            </Button>
          ) : null}
        </Box>

        <Box
          draggable={Boolean(node.meta)}
          onDragStart={(event) => {
            if (!node.meta) {
              return;
            }
            onDragStart(event, node.meta);
          }}
          sx={{ flexGrow: 1, minWidth: 0, cursor: node.meta ? 'grab' : 'default' }}
        >
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {node.tag}
          </Typography>
          {node.meta ? (
            <Typography variant="caption" color="text.secondary">
              {itemCount} matching items, {coveredCount} already covered
            </Typography>
          ) : null}
        </Box>

        {node.meta ? (
          <Button size="small" variant="outlined" startIcon={<AddCircleOutlineIcon />} onClick={() => onAddTag(node.meta)}>
            Add
          </Button>
        ) : null}
      </Stack>

      {hasChildren && isExpanded ? (
        <Box>
          {node.children.map((child) => (
            <TagBranch
              key={child.tag}
              node={child}
              depth={depth + 1}
              expandedTags={expandedTags}
              onToggle={onToggle}
              onAddTag={onAddTag}
              onDragStart={onDragStart}
              forceExpand={forceExpand}
            />
          ))}
        </Box>
      ) : null}
    </Box>
  );
}

function TagCollectionEditor({
  label,
  helperText,
  values,
  options,
  onChange,
}) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        {label}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
        {helperText}
      </Typography>
      <Autocomplete
        multiple
        freeSolo
        options={options}
        value={values}
        onChange={(_, nextValue) => onChange(nextValue)}
        renderTags={(tagValue, getTagProps) => tagValue.map((option, index) => (
          <Chip {...getTagProps({ index })} key={`${label}-${option}-${index}`} size="small" label={option} />
        ))}
        renderInput={(params) => <TextField {...params} label={label} placeholder="Type a tag or choose from autocomplete" />}
      />
    </Box>
  );
}

const ArchetypeEditorPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [selectedArchetypeId, setSelectedArchetypeId] = useState('');
  const [draftName, setDraftName] = useState('');
  const [draftAllocations, setDraftAllocations] = useState([]);
  const [draftExpertTags, setDraftExpertTags] = useState([]);
  const [draftForbid, setDraftForbid] = useState([]);
  const [draftWants, setDraftWants] = useState([]);
  const [expandedTags, setExpandedTags] = useState({});
  const [tagSearch, setTagSearch] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [issueReplacement, setIssueReplacement] = useState(null);
  const [portraitIndexes, setPortraitIndexes] = useState({});
  const [targets, setTargets] = useState([]);
  const [modules, setModules] = useState([]);
  const [selectedModule, setSelectedModule] = useState('');
  const [pendingIssueKeysByArchetype, setPendingIssueKeysByArchetype] = useState({});

  const deferredTagSearch = useDeferredValue(tagSearch);
  const backendOrigin = useMemo(() => {
    if (typeof window === 'undefined') {
      return 'http://localhost:8000';
    }
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }, []);

  const applyPayload = useCallback((payload, preferredArchetypeId = '') => {
    setData(payload);
    const archetypes = payload?.archetypes || [];
    const selected = archetypes.find((row) => row.archetype_id === preferredArchetypeId) || archetypes[0] || null;
    const draft = createDraftFromArchetype(selected);
    setSelectedArchetypeId(selected?.archetype_id || '');
    setDraftName(draft.name);
    setDraftAllocations(draft.allocations);
    setDraftExpertTags(draft.expertTags);
    setDraftForbid(draft.forbid);
    setDraftWants(draft.wants);
    setIssueReplacement(null);
    setPortraitIndexes({});
  }, []);

  const loadTargets = useCallback(async () => {
    try {
      const res = await getWorkshopTargets();
      setTargets(res.data?.targets || []);
      const foundModules = res.data?.modules || [];
      setModules(foundModules);
      const defaultMod = res.data?.default_module || (foundModules.length > 0 ? foundModules[0].id : 'DynamicTradingCommon');
      setSelectedModule(defaultMod);
    } catch (error) {
      console.error('Failed to load targets', error);
    }
  }, []);

  useEffect(() => {
    loadTargets();
  }, [loadTargets]);

  const mergeSavedArchetype = useCallback((savedArchetype) => {
    setData((current) => {
      if (!current) {
        return current;
      }

      const nextArchetypes = (current.archetypes || []).map((row) => (
        row.archetype_id === savedArchetype.archetype_id ? savedArchetype : row
      ));

      return {
        ...current,
        archetypes: nextArchetypes,
        meta: {
          ...current.meta,
          invalid_archetype_count: nextArchetypes.filter((row) => row.validation?.issue_count > 0).length,
        },
      };
    });
  }, []);

  const loadData = useCallback(async (preferredArchetypeId = '', moduleOverride) => {
    const targetModule = moduleOverride || selectedModule;
    setLoading(true);
    setStatus({ type: '', message: '' });
    try {
      const response = await getArchetypeEditorData(targetModule);
      applyPayload(response.data, preferredArchetypeId);
    } catch (error) {
      setStatus({
        type: 'error',
        message: error?.response?.data?.detail || 'Failed to load archetype editor data.',
      });
    } finally {
      setLoading(false);
    }
  }, [applyPayload, selectedModule]);

  useEffect(() => {
    if (selectedModule) {
      loadData('', selectedModule);
    }
  }, [selectedModule, loadData]);

  const selectedArchetype = useMemo(
    () => data?.archetypes?.find((row) => row.archetype_id === selectedArchetypeId) || null,
    [data, selectedArchetypeId],
  );

  const currentDraft = useMemo(() => ({
    name: draftName,
    allocations: draftAllocations,
    expertTags: draftExpertTags,
    forbid: draftForbid,
    wants: draftWants,
  }), [draftAllocations, draftExpertTags, draftForbid, draftName, draftWants]);

  const validation = selectedArchetype?.validation || { issue_count: 0, error_count: 0, warning_count: 0, issues: [] };
  const validationTone = validation.error_count ? 'error' : (validation.warning_count ? 'warning' : 'success');
  const pendingIssueKeys = pendingIssueKeysByArchetype[selectedArchetypeId] || [];

  const savedSnapshot = useMemo(
    () => JSON.stringify(buildSavePayload({
      name: selectedArchetype?.name || '',
      allocations: selectedArchetype?.allocations || [],
      expertTags: selectedArchetype?.expert_tags || [],
      forbid: selectedArchetype?.forbid || [],
      wants: selectedArchetype?.wants || [],
    }, selectedArchetypeId)),
    [selectedArchetype, selectedArchetypeId],
  );
  const draftSnapshot = useMemo(
    () => JSON.stringify(buildSavePayload(currentDraft, selectedArchetypeId)),
    [currentDraft, selectedArchetypeId],
  );
  const isDirty = savedSnapshot !== draftSnapshot;

  const availableTagMap = useMemo(() => {
    const map = new Map();
    (data?.available_tags || []).forEach((row) => {
      map.set(row.tag, row);
    });
    return map;
  }, [data]);

  const tagOptions = useMemo(
    () => (data?.available_tags || []).map((row) => row.tag),
    [data],
  );

  const tagTree = useMemo(
    () => buildTagTree(data?.available_tags || []),
    [data],
  );
  const filteredTagTree = useMemo(
    () => filterTree(tagTree, deferredTagSearch.trim()),
    [tagTree, deferredTagSearch],
  );

  const addOrIncrementAllocation = useCallback((entry) => {
    setDraftAllocations((current) => {
      const key = allocationKey(entry);
      const existingIndex = current.findIndex((row) => allocationKey(row) === key);
      if (existingIndex >= 0) {
        return current.map((row, index) => (
          index === existingIndex
            ? { ...row, count: Math.max(1, Number(row.count || 1) + Number(entry.count || 1)) }
            : row
        ));
      }
      return [...current, { ...entry, count: Math.max(1, Number(entry.count || 1)) }];
    });
  }, []);

  const addTagAllocation = useCallback((tagRow) => {
    addOrIncrementAllocation({
      kind: 'tag',
      tags: [tagRow.tag],
      label: tagRow.tag,
      count: 1,
      matched_item_count: Number(tagRow.item_count || 0),
      sample_items: tagRow.sample_items || [],
    });
  }, [addOrIncrementAllocation]);

  const addItemAllocation = useCallback((item) => {
    if (!item) {
      return;
    }

    addOrIncrementAllocation({
      kind: 'item',
      item_id: item.item_id,
      item_name: item.name,
      label: item.item_id,
      count: 1,
      matched_item_count: 1,
      sample_items: [{ item_id: item.item_id, name: item.name }],
    });
  }, [addOrIncrementAllocation]);

  const handleDragStart = useCallback((event, payload) => {
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData(DRAG_MIME, JSON.stringify({ kind: 'tag', tag: payload.tag }));
  }, []);

  const handleDrop = useCallback((event) => {
    event.preventDefault();
    const raw = event.dataTransfer.getData(DRAG_MIME);
    if (!raw) {
      return;
    }

    try {
      const payload = JSON.parse(raw);
      if (payload.kind === 'tag' && payload.tag && availableTagMap.has(payload.tag)) {
        addTagAllocation(availableTagMap.get(payload.tag));
      }
    } catch (error) {
      setStatus({ type: 'error', message: 'Unable to read dragged tag payload.' });
    }
  }, [addTagAllocation, availableTagMap]);

  const handleSelectArchetype = (nextId) => {
    if (nextId === selectedArchetypeId) {
      return;
    }
    if (isDirty && !window.confirm('Switch archetypes and discard unsaved changes?')) {
      return;
    }

    const nextArchetype = data?.archetypes?.find((row) => row.archetype_id === nextId);
    const draft = createDraftFromArchetype(nextArchetype);
    setSelectedArchetypeId(nextId);
    setDraftName(draft.name);
    setDraftAllocations(draft.allocations);
    setDraftExpertTags(draft.expertTags);
    setDraftForbid(draft.forbid);
    setDraftWants(draft.wants);
    setIssueReplacement(null);
    setPortraitIndexes({});
    setStatus({ type: '', message: '' });
  };

  const handleSave = async () => {
    if (!selectedArchetypeId) {
      return;
    }

    setSaving(true);
    setStatus({ type: '', message: '' });
    try {
      const response = await saveArchetypeDefinition(
        selectedArchetypeId,
        buildSavePayload(currentDraft, selectedArchetypeId),
        selectedModule
      );
      mergeSavedArchetype(response.data.archetype);
      const draft = createDraftFromArchetype(response.data.archetype);
      setDraftName(draft.name);
      setDraftAllocations(draft.allocations);
      setDraftExpertTags(draft.expertTags);
      setDraftForbid(draft.forbid);
      setDraftWants(draft.wants);
      setPendingIssueKeysByArchetype((current) => ({
        ...current,
        [selectedArchetypeId]: [],
      }));
      setIssueReplacement(null);
      setStatus({ type: 'success', message: `Saved archetype fields for ${selectedArchetype?.name || selectedArchetypeId}.` });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error?.response?.data?.detail || 'Failed to save archetype definition.',
      });
    } finally {
      setSaving(false);
    }
  };

  const updateAllocationCount = (index, value) => {
    setDraftAllocations((current) => current.map((entry, entryIndex) => (
      entryIndex === index
        ? { ...entry, count: value === '' ? '' : Math.max(1, Number(value)) }
        : entry
    )));
  };

  const removeAllocation = (index) => {
    setDraftAllocations((current) => current.filter((_, entryIndex) => entryIndex !== index));
  };

  const addWantRow = () => {
    setDraftWants((current) => [...current, { tag: '', multiplier: '1.0' }]);
  };

  const updateWantRow = (index, nextRow) => {
    setDraftWants((current) => current.map((row, rowIndex) => (
      rowIndex === index ? { ...row, ...nextRow } : row
    )));
  };

  const removeWantRow = (index) => {
    setDraftWants((current) => current.filter((_, rowIndex) => rowIndex !== index));
  };

  const startIssueReplacement = (issue) => {
    setIssueReplacement({
      issue,
      value: issue.value || '',
    });
  };

  const applyIssueReplacement = () => {
    const nextValue = String(issueReplacement?.value || '').trim();
    const path = issueReplacement?.issue?.path;
    if (!nextValue || !path) {
      return;
    }

    if (path.section === 'allocations') {
      setDraftAllocations((current) => current.map((entry, index) => {
        if (index !== path.entry_index) {
          return entry;
        }
        const nextTags = [...(entry.tags || [])];
        nextTags[path.tag_index] = nextValue;
        return { ...entry, tags: nextTags };
      }));
    }

    if (path.section === 'expert_tags') {
      setDraftExpertTags((current) => current.map((value, index) => (index === path.index ? nextValue : value)));
    }

    if (path.section === 'forbid') {
      setDraftForbid((current) => current.map((value, index) => (index === path.index ? nextValue : value)));
    }

    if (path.section === 'wants') {
      setDraftWants((current) => current.map((row, index) => (
        index === path.index ? { ...row, tag: nextValue } : row
      )));
    }

    const fixedIssueKey = issueKey(issueReplacement.issue);
    setPendingIssueKeysByArchetype((current) => {
      const existing = current[selectedArchetypeId] || [];
      if (existing.includes(fixedIssueKey)) {
        return current;
      }
      return {
        ...current,
        [selectedArchetypeId]: [...existing, fixedIssueKey],
      };
    });
    setIssueReplacement(null);
    setStatus({ type: 'info', message: `Updated "${issueReplacement.issue.value}" in the draft. Save changes to write it back to Lua.` });
  };

  const stepPortrait = (label, direction, total) => {
    setPortraitIndexes((current) => {
      const currentIndex = current[label] || 0;
      return {
        ...current,
        [label]: (currentIndex + direction + total) % total,
      };
    });
  };

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '320px 1fr' }, gap: 3 }}>
      <Paper elevation={3} sx={{ p: 2.5, minHeight: 720 }}>
        <Typography variant="h5" gutterBottom>
          Archetypes
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Pick a trader archetype, then edit every Lua field from one place.
        </Typography>

        {data?.meta ? (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Chip size="small" label={`${data.meta.archetype_count} archetypes`} />
            <Chip size="small" label={`${data.meta.tag_count} tags`} />
            <Chip size="small" label={`${data.meta.uncovered_tag_count} uncovered`} color="warning" variant="outlined" />
            <Chip size="small" label={`${data.meta.invalid_archetype_count} with findings`} color="warning" variant="outlined" />
          </Stack>
        ) : null}

        <Stack spacing={1}>
          {(data?.archetypes || []).map((archetype) => {
            const issueTone = archetype.validation?.error_count ? 'error' : (archetype.validation?.warning_count ? 'warning' : 'default');
            return (
              <Button
                key={archetype.archetype_id}
                variant={archetype.archetype_id === selectedArchetypeId ? 'contained' : 'outlined'}
                color={archetype.archetype_id === selectedArchetypeId ? 'primary' : 'inherit'}
                onClick={() => handleSelectArchetype(archetype.archetype_id)}
                sx={{ justifyContent: 'space-between', px: 1.5, py: 1.2 }}
              >
                <Box sx={{ textAlign: 'left' }}>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {archetype.name}
                  </Typography>
                  <Typography variant="caption" sx={{ opacity: 0.8 }}>
                    {archetype.archetype_id}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={0.75} alignItems="center">
                  <Chip size="small" label={`${archetype.allocation_count} rows`} color={archetype.archetype_id === selectedArchetypeId ? 'secondary' : 'default'} />
                  {archetype.validation?.issue_count ? (
                    <Chip
                      size="small"
                      label={`${archetype.validation.issue_count} issue${archetype.validation.issue_count === 1 ? '' : 's'}`}
                      color={issueTone}
                      variant={archetype.archetype_id === selectedArchetypeId ? 'filled' : 'outlined'}
                    />
                  ) : null}
                </Stack>
              </Button>
            );
          })}
        </Stack>
      </Paper>

      <Stack spacing={3}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'flex-start' }} spacing={2} sx={{ mb: 2.5 }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h4">Archetype Lua Editor</Typography>
              <Typography variant="body2" color="text.secondary">
                Edit `name`, `allocations`, `expertTags`, `wants`, and `forbid`, then save the whole archetype definition back to Lua.
              </Typography>
            </Box>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ flexShrink: 0 }}>
              <Stack direction="row" spacing={0.5} sx={{ overflowX: 'auto', pb: 1, px: 1 }}>
                {modules.map(m => (
                  <Chip
                    key={m.id}
                    label={m.name}
                    clickable
                    color={selectedModule === m.id ? 'primary' : 'default'}
                    onClick={() => {
                        if (isDirty && !window.confirm('Switch modules and discard unsaved changes?')) return;
                        setSelectedModule(m.id);
                    }}
                  />
                ))}
              </Stack>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => loadData(selectedArchetypeId)}
                disabled={loading || saving}
                sx={{ whiteSpace: 'nowrap', minWidth: 138 }}
              >
                Reload
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveOutlinedIcon />}
                onClick={handleSave}
                disabled={!selectedArchetypeId || saving || loading}
                sx={{ whiteSpace: 'nowrap', minWidth: 176, px: 2.5 }}
              >
                {saving ? 'Saving Changes...' : 'Save Changes'}
              </Button>
            </Stack>
          </Stack>

          {status.message ? (
            <Alert severity={status.type || 'info'} sx={{ mb: 2 }}>
              {status.message}
            </Alert>
          ) : null}

          <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3} alignItems={{ xs: 'stretch', lg: 'flex-start' }}>
            <Box sx={{ flex: 1.02, minWidth: 0 }}>
              <TextField
                fullWidth
                label="Search tags or sample items"
                value={tagSearch}
                onChange={(event) => setTagSearch(event.target.value)}
                sx={{ mb: 2 }}
              />

              <Paper
                variant="outlined"
                sx={{ p: 1.25, height: 560, overflow: 'auto', bgcolor: 'rgba(255,255,255,0.02)' }}
              >
                {loading ? (
                  <Typography color="text.secondary">Loading available tags...</Typography>
                ) : filteredTagTree.length ? (
                  filteredTagTree.map((node) => (
                    <TagBranch
                      key={node.tag}
                      node={node}
                      depth={0}
                      expandedTags={expandedTags}
                      onToggle={(tag) => setExpandedTags((current) => ({ ...current, [tag]: !current[tag] }))}
                      onAddTag={addTagAllocation}
                      onDragStart={handleDragStart}
                      forceExpand={Boolean(deferredTagSearch.trim())}
                    />
                  ))
                ) : (
                  <Typography color="text.secondary">No tags matched this search.</Typography>
                )}
              </Paper>
            </Box>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Stack spacing={2.5}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="h5" gutterBottom>
                    {selectedArchetype?.archetype_id || 'Select an archetype'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                    {selectedArchetype?.source_file || 'No source file selected'}
                  </Typography>
                  <TextField
                    fullWidth
                    label="Display Name"
                    value={draftName}
                    onChange={(event) => setDraftName(event.target.value)}
                    placeholder="Trader name shown in game"
                  />

                  {selectedArchetype?.portraits?.length ? (
                    <Stack spacing={1.5} sx={{ mt: 2 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                        Portraits
                      </Typography>
                      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
                        {selectedArchetype.portraits.map((group) => {
                          const currentIndex = portraitIndexes[group.label] || 0;
                          const imageUrl = group.images[currentIndex];
                          return (
                            <Paper key={group.label} variant="outlined" sx={{ p: 1.25, flex: 1, bgcolor: 'rgba(255,255,255,0.02)' }}>
                              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                  {group.label}
                                </Typography>
                                <Chip size="small" label={`${currentIndex + 1}/${group.images.length}`} />
                              </Stack>
                              <Box
                                component="img"
                                src={`${backendOrigin}${imageUrl}`}
                                alt={`${selectedArchetype.archetype_id} ${group.label} portrait ${currentIndex + 1}`}
                                sx={{
                                  width: '100%',
                                  aspectRatio: '1 / 1.15',
                                  objectFit: 'cover',
                                  borderRadius: 2,
                                  border: '1px solid rgba(255,255,255,0.08)',
                                  bgcolor: 'rgba(0,0,0,0.22)',
                                }}
                              />
                              <Stack direction="row" spacing={1} sx={{ mt: 1.25 }}>
                                <Button
                                  fullWidth
                                  variant="outlined"
                                  size="small"
                                  startIcon={<ArrowBackIosNewIcon />}
                                  onClick={() => stepPortrait(group.label, -1, group.images.length)}
                                >
                                  Prev
                                </Button>
                                <Button
                                  fullWidth
                                  variant="outlined"
                                  size="small"
                                  endIcon={<ArrowForwardIosIcon />}
                                  onClick={() => stepPortrait(group.label, 1, group.images.length)}
                                >
                                  Next
                                </Button>
                              </Stack>
                            </Paper>
                          );
                        })}
                      </Stack>
                    </Stack>
                  ) : null}
                </Paper>

                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    borderColor: validationTone === 'error' ? 'error.main' : (validationTone === 'warning' ? 'warning.main' : 'success.main'),
                    bgcolor: validationTone === 'error'
                      ? 'rgba(244,67,54,0.08)'
                      : (validationTone === 'warning' ? 'rgba(255,152,0,0.08)' : 'rgba(76,175,80,0.08)'),
                  }}
                >
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.25 }}>
                    <Chip size="small" label={validation.issue_count ? `${validation.issue_count} issue${validation.issue_count === 1 ? '' : 's'}` : 'No invalid Lua entries'} color={validationTone} />
                    <Chip size="small" label={`${validation.error_count || 0} errors`} color="error" variant="outlined" />
                    <Chip size="small" label={`${validation.warning_count || 0} warnings`} color="warning" variant="outlined" />
                  </Stack>

                  <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
                    Invalid Archetype Detector
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
                    Click Replace on a tag issue to prefill the current broken value and correct it with autocomplete.
                  </Typography>

                  {validation.issue_count ? (
                    <Stack spacing={1}>
                      {validation.issues.map((issue, index) => (
                        <Box key={`${issue.code}-${issue.field || 'field'}-${issue.value || index}`}>
                          <Alert
                            severity={pendingIssueKeys.includes(issueKey(issue)) ? 'info' : (issue.level === 'error' ? 'error' : 'warning')}
                            variant="outlined"
                            action={issue.replaceable ? (
                              pendingIssueKeys.includes(issueKey(issue)) ? (
                                <Chip size="small" color="info" label="Pending Save" />
                              ) : (
                                <Button
                                  color="inherit"
                                  size="small"
                                  startIcon={<AutoFixHighIcon />}
                                  onClick={() => startIssueReplacement(issue)}
                                >
                                  Replace
                                </Button>
                              )
                            ) : null}
                          >
                            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                              <Typography variant="body2">{issue.message}</Typography>
                              {pendingIssueKeys.includes(issueKey(issue)) ? (
                                <Chip size="small" color="info" variant="outlined" label="Pending" />
                              ) : null}
                            </Stack>
                          </Alert>
                        </Box>
                      ))}
                    </Stack>
                  ) : (
                    <Alert severity="success" variant="outlined">
                      No invalid variables or unknown tags were detected in this archetype Lua block.
                    </Alert>
                  )}

                  {issueReplacement ? (
                    <Paper variant="outlined" sx={{ p: 1.5, mt: 1.5 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        Replace detected value
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
                        The current invalid value is already loaded below, so you can just erase the wrong part and pick a valid tag.
                      </Typography>
                      <Autocomplete
                        freeSolo
                        options={tagOptions}
                        value={null}
                        inputValue={issueReplacement.value}
                        onInputChange={(_, nextValue) => setIssueReplacement((current) => ({ ...current, value: nextValue }))}
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            label="Replacement tag"
                            placeholder="Start typing to autocorrect"
                          />
                        )}
                      />
                      <Stack direction="row" spacing={1} sx={{ mt: 1.25 }}>
                        <Button variant="contained" onClick={applyIssueReplacement}>
                          Apply Replacement
                        </Button>
                        <Button variant="outlined" onClick={() => setIssueReplacement(null)}>
                          Cancel
                        </Button>
                      </Stack>
                    </Paper>
                  ) : null}
                </Paper>

                <Paper
                  variant="outlined"
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={handleDrop}
                  sx={{ p: 2, borderStyle: 'dashed', bgcolor: 'rgba(144,202,249,0.08)' }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    Drop Tags Into Allocations
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Drag from the tree on the left and new allocation rows will be appended here.
                  </Typography>
                </Paper>

                <Stack spacing={1.25} sx={{ maxHeight: 420, overflow: 'auto', pr: 0.5 }}>
                  {(draftAllocations || []).length ? (
                    draftAllocations.map((entry, index) => (
                      <Paper key={`${allocationKey(entry)}-${index}`} variant="outlined" sx={{ p: 1.5 }}>
                        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} justifyContent="space-between">
                          <Box sx={{ minWidth: 0, flexGrow: 1 }}>
                            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mb: 0.75 }}>
                              <Chip size="small" label={entry.kind === 'item' ? 'Item ID' : 'Tag'} color={entry.kind === 'item' ? 'secondary' : 'primary'} variant="outlined" />
                              <Typography variant="body1" sx={{ fontWeight: 700, wordBreak: 'break-word' }}>
                                {entry.kind === 'item' ? entry.item_id : (entry.tags || []).join(' + ')}
                              </Typography>
                            </Stack>

                            {entry.kind === 'item' && entry.item_name ? (
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.75 }}>
                                {entry.item_name}
                              </Typography>
                            ) : null}

                            <Typography variant="caption" color="text.secondary">
                              Matches {entry.matched_item_count || 0} item{Number(entry.matched_item_count || 0) === 1 ? '' : 's'}
                            </Typography>

                            {entry.sample_items?.length ? (
                              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                                {entry.sample_items.map((sample) => (
                                  <Chip
                                    key={`${entry.kind}-${sample.item_id}`}
                                    size="small"
                                    variant="outlined"
                                    label={`${sample.name} (${sample.item_id})`}
                                  />
                                ))}
                              </Stack>
                            ) : null}
                          </Box>

                          <Stack direction="row" spacing={1} alignItems="center">
                            <TextField
                              label="Count"
                              size="small"
                              type="number"
                              value={entry.count}
                              onChange={(event) => updateAllocationCount(index, event.target.value)}
                              onBlur={() => updateAllocationCount(index, Math.max(1, Number(entry.count || 1)))}
                              sx={{ width: 110 }}
                              inputProps={{ min: 1 }}
                            />
                            <Button color="error" variant="outlined" startIcon={<DeleteOutlineIcon />} onClick={() => removeAllocation(index)}>
                              Remove
                            </Button>
                          </Stack>
                        </Stack>
                      </Paper>
                    ))
                  ) : (
                    <Typography color="text.secondary">No allocation rows yet. Drop tags here or add item IDs below.</Typography>
                  )}
                </Stack>

                <Divider />

                <TagCollectionEditor
                  label="Expert Tags"
                  helperText="These tags mark the trader as a specialist. Use autocomplete or type directly."
                  values={draftExpertTags}
                  options={tagOptions}
                  onChange={setDraftExpertTags}
                />

                <Divider />

                <Box>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                    <Box>
                      <Typography variant="h6">Wants</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Edit the wanted tag list and its multipliers.
                      </Typography>
                    </Box>
                    <Button variant="outlined" startIcon={<AddCircleOutlineIcon />} onClick={addWantRow}>
                      Add Want
                    </Button>
                  </Stack>

                  <Stack spacing={1}>
                    {draftWants.length ? draftWants.map((row, index) => (
                      <Paper key={`want-${index}`} variant="outlined" sx={{ p: 1.25 }}>
                        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25}>
                          <Autocomplete
                            freeSolo
                            options={tagOptions}
                            value={null}
                            inputValue={row.tag}
                            onInputChange={(_, value) => updateWantRow(index, { tag: value })}
                            renderInput={(params) => <TextField {...params} fullWidth label="Wanted tag" />}
                            sx={{ flex: 1 }}
                          />
                          <TextField
                            label="Multiplier"
                            type="number"
                            value={row.multiplier}
                            onChange={(event) => updateWantRow(index, { multiplier: event.target.value })}
                            sx={{ width: { xs: '100%', md: 140 } }}
                          />
                          <Button color="error" variant="outlined" startIcon={<DeleteOutlineIcon />} onClick={() => removeWantRow(index)}>
                            Remove
                          </Button>
                        </Stack>
                      </Paper>
                    )) : (
                      <Typography color="text.secondary">No wants configured yet.</Typography>
                    )}
                  </Stack>
                </Box>

                <Divider />

                <TagCollectionEditor
                  label="Forbid"
                  helperText="Tags in this list should never be traded by the archetype."
                  values={draftForbid}
                  options={tagOptions}
                  onChange={setDraftForbid}
                />

                <Divider />

                <Box>
                  <Typography variant="h6" gutterBottom>
                    Add Item ID
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    Explicit item rows are useful for one-off stock picks that should always be reachable.
                  </Typography>

                  <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
                    <Autocomplete
                      fullWidth
                      options={data?.item_catalog || []}
                      value={selectedItem}
                      onChange={(_, value) => setSelectedItem(value)}
                      getOptionLabel={(option) => `${option.item_id} - ${option.name}`}
                      renderInput={(params) => <TextField {...params} label="Item ID" placeholder="Base.Axe" />}
                      isOptionEqualToValue={(option, value) => option.item_id === value.item_id}
                    />
                    <Button
                      variant="outlined"
                      startIcon={<AddCircleOutlineIcon />}
                      onClick={() => {
                        addItemAllocation(selectedItem);
                        setSelectedItem(null);
                      }}
                    >
                      Add Item
                    </Button>
                  </Stack>
                </Box>
              </Stack>
            </Box>
          </Stack>
        </Paper>

        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Tags Not Currently Accessible
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            These tags exist on real items, but no current archetype allocation reaches them yet. Click or drag them into allocations to cover those gaps.
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {(data?.uncovered_tags || []).map((tagRow) => (
              <Chip
                key={tagRow.tag}
                label={`${tagRow.tag} (${tagRow.item_count})`}
                color="warning"
                variant="outlined"
                onClick={() => addTagAllocation(tagRow)}
                draggable
                onDragStart={(event) => handleDragStart(event, tagRow)}
                sx={{ cursor: 'grab' }}
              />
            ))}
          </Stack>

          {!data?.uncovered_tags?.length ? (
            <Typography color="text.secondary">Every available tag is currently reachable by at least one archetype allocation.</Typography>
          ) : null}
        </Paper>
      </Stack>
    </Box>
  );
};

export default ArchetypeEditorPage;
