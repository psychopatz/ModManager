import React, { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Box, Stack } from '@mui/material';
import {
  addBlacklistItem,
  deleteItemOverride,
  getOverrides,
  getPricingConfig,
  getPricingTags,
  previewPricingTag,
  saveItemOverride,
  savePricingConfig,
} from '../../services/api';
import { formatPrice } from './formatters';
import {
  buildTagTree,
  filterTree,
  flattenVisibleNodes,
  lineageForTag,
  makeOverrideDraft,
} from './treeUtils';
import TagTreePanel from './TagTreePanel';
import TagDetailsPanel from './TagDetailsPanel';
import TagPreviewPanel from './TagPreviewPanel';

const TagPricingPage = () => {
  const [config, setConfig] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [overridesByItem, setOverridesByItem] = useState({});
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [pendingAddition, setPendingAddition] = useState(0);
  const [previewData, setPreviewData] = useState(null);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewStale, setPreviewStale] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expandedTags, setExpandedTags] = useState({});
  const [blacklistingItemId, setBlacklistingItemId] = useState('');
  const [overrideDraft, setOverrideDraft] = useState(null);
  const [catalogSource, setCatalogSource] = useState('');
  const [catalogItemCount, setCatalogItemCount] = useState(0);

  const loadPage = async (keepSelection = true) => {
    setLoadingCatalog(true);
    setStatus({ type: '', message: '' });
    try {
      const [configRes, tagRes, overridesRes] = await Promise.all([
        getPricingConfig(),
        getPricingTags(),
        getOverrides(),
      ]);
      const nextConfig = configRes.data;
      const nextCatalog = tagRes.data?.tags || [];
      const nextOverridesByItem = overridesRes.data?.by_item || {};

      setConfig(nextConfig);
      setCatalog(nextCatalog);
      setOverridesByItem(nextOverridesByItem);
      setCatalogSource(tagRes.data?.source || '');
      setCatalogItemCount(Number(tagRes.data?.item_count || 0));

      const fallbackTag = nextCatalog[0]?.tag || '';
      const nextSelectedTag = keepSelection && selectedTag && nextCatalog.some((row) => row.tag === selectedTag)
        ? selectedTag
        : fallbackTag;

      setSelectedTag(nextSelectedTag);
      if (nextSelectedTag) {
        setPendingAddition(Number(nextConfig?.tag_price_additions?.[nextSelectedTag] || 0));
      }
    } catch (err) {
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to load tag pricing data.' });
    } finally {
      setLoadingCatalog(false);
    }
  };

  useEffect(() => {
    loadPage(false);
  }, []);

  useEffect(() => {
    if (!selectedTag || !config) {
      return;
    }
    setPendingAddition(Number(config?.tag_price_additions?.[selectedTag] || 0));
    setExpandedTags((current) => {
      const next = { ...current };
      lineageForTag(selectedTag).forEach((tag) => {
        next[tag] = true;
      });
      return next;
    });
  }, [selectedTag, config]);

  useEffect(() => {
    setPreviewStale(Boolean(selectedTag));
  }, [selectedTag, pendingAddition, config]);

  useEffect(() => {
    setPreviewData((current) => (current?.tag === selectedTag ? current : null));
  }, [selectedTag]);

  const tree = useMemo(() => buildTagTree(catalog), [catalog]);
  const deferredSearch = useDeferredValue(search.trim());
  const filteredTree = useMemo(() => filterTree(tree, deferredSearch), [tree, deferredSearch]);
  const catalogByTag = useMemo(() => {
    const map = new Map();
    catalog.forEach((row) => {
      map.set(row.tag, row);
    });
    return map;
  }, [catalog]);
  const selectedCatalogRow = catalogByTag.get(selectedTag) || null;
  const tagOptions = useMemo(() => catalog.map((row) => row.tag), [catalog]);
  const visibleRows = useMemo(() => flattenVisibleNodes(
    filteredTree,
    expandedTags,
    Boolean(deferredSearch),
  ).map((row) => ({
    ...row,
    node: {
      ...row.node,
      isExpanded: Boolean(deferredSearch) || Boolean(expandedTags[row.node.tag] ?? row.depth === 0),
    },
  })), [deferredSearch, expandedTags, filteredTree]);
  const visibleNodeCount = visibleRows.length;

  const lineage = useMemo(() => lineageForTag(selectedTag), [selectedTag]);
  const compoundRows = useMemo(() => lineage.map((tag) => {
    const savedValue = Number(config?.tag_price_additions?.[tag] || 0);
    const pendingValue = tag === selectedTag ? Number(pendingAddition || 0) : savedValue;
    return {
      tag,
      savedValue,
      pendingValue,
    };
  }), [config, lineage, pendingAddition, selectedTag]);
  const savedCompoundTotal = compoundRows.reduce((total, row) => total + row.savedValue, 0);
  const pendingCompoundTotal = compoundRows.reduce((total, row) => total + row.pendingValue, 0);
  const hasUnsavedChange = Number(pendingAddition || 0) !== Number(config?.tag_price_additions?.[selectedTag] || 0);

  const toggleExpanded = useCallback((tag) => {
    setExpandedTags((current) => ({
      ...current,
      [tag]: !current[tag],
    }));
  }, []);

  const handleSelectTag = useCallback((tag) => {
    setSelectedTag(tag);
  }, []);

  const handleSave = async () => {
    if (!config || !selectedTag) {
      return;
    }

    setSaving(true);
    setStatus({ type: '', message: '' });
    try {
      const nextConfig = {
        ...config,
        tag_price_additions: {
          ...(config.tag_price_additions || {}),
        },
      };

      const nextValue = Number(pendingAddition || 0);
      if (Math.abs(nextValue) < 1e-9) {
        delete nextConfig.tag_price_additions[selectedTag];
      } else {
        nextConfig.tag_price_additions[selectedTag] = nextValue;
      }

      const res = await savePricingConfig(nextConfig);
      setConfig(res.data);
      setCatalog((current) => current.map((row) => (
        row.tag === selectedTag
          ? { ...row, current_addition: nextValue }
          : row
      )));
      const luaSync = res?.data?.__lua_sync;
      const luaNote = luaSync?.path
        ? ` Lua synced: ${luaSync.path} (${luaSync.count || 0} tag entries).`
        : '';
      setStatus({ type: 'success', message: `Saved ${selectedTag} to the backend config.${luaNote} Parent values still compound into child tags.` });
    } catch (err) {
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to save tag pricing.' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (!selectedTag || !config) {
      return;
    }
    setPendingAddition(Number(config?.tag_price_additions?.[selectedTag] || 0));
  };

  const handleExpandAll = () => {
    const next = {};
    catalog.forEach((row) => {
      next[row.tag] = true;
    });
    setExpandedTags(next);
  };

  const handleCollapseAll = () => {
    setExpandedTags({});
  };

  const handleGeneratePreview = async () => {
    if (!selectedTag || !config) {
      return;
    }

    const saved = Number(config?.tag_price_additions?.[selectedTag] || 0);
    const nextAddition = Number.isFinite(pendingAddition) ? pendingAddition : saved;

    setLoadingPreview(true);
    setStatus({ type: '', message: '' });
    try {
      const res = await previewPricingTag({
        tag: selectedTag,
        addition: nextAddition,
        limit: 40,
      });
      setPreviewData(res.data);
      setPreviewStale(false);
    } catch (err) {
      setPreviewData(null);
      setStatus((current) => ({
        ...current,
        type: 'error',
        message: err?.response?.data?.detail || 'Failed to preview tag pricing.',
      }));
    } finally {
      setLoadingPreview(false);
    }
  };

  const openOverrideEditor = (row) => {
    setOverrideDraft(makeOverrideDraft(row, overridesByItem[row.item_id]));
  };

  const closeOverrideEditor = () => {
    setOverrideDraft(null);
  };

  const handleSaveItemOverride = async () => {
    if (!overrideDraft) {
      return;
    }

    const payload = {
      item_id: overrideDraft.itemId,
    };

    if (overrideDraft.basePrice !== '') {
      const value = Number(overrideDraft.basePrice);
      if (!Number.isFinite(value) || value < 0) {
        setStatus({ type: 'error', message: 'Override price must be a non-negative number.' });
        return;
      }
      payload.base_price = value;
    }

    if (overrideDraft.stockMin !== '') {
      const value = Number(overrideDraft.stockMin);
      if (!Number.isInteger(value) || value < 0) {
        setStatus({ type: 'error', message: 'Override stock min must be a non-negative whole number.' });
        return;
      }
      payload.stock_min = value;
    }

    if (overrideDraft.stockMax !== '') {
      const value = Number(overrideDraft.stockMax);
      if (!Number.isInteger(value) || value < 0) {
        setStatus({ type: 'error', message: 'Override stock max must be a non-negative whole number.' });
        return;
      }
      payload.stock_max = value;
    }

    if (
      payload.stock_min !== undefined
      && payload.stock_max !== undefined
      && payload.stock_min > payload.stock_max
    ) {
      setStatus({ type: 'error', message: 'Override stock min cannot be greater than stock max.' });
      return;
    }

    if ((overrideDraft.tags || []).length) {
      payload.tags = overrideDraft.tags;
    }

    if (
      payload.base_price === undefined
      && payload.stock_min === undefined
      && payload.stock_max === undefined
      && !payload.tags
    ) {
      setStatus({ type: 'error', message: 'Add at least one override field before saving.' });
      return;
    }

    setSaving(true);
    setStatus({ type: '', message: '' });
    try {
      const res = await saveItemOverride(payload);
      setOverridesByItem(res.data?.overrides?.reduce?.((acc, entry) => {
        if (entry?.item) {
          acc[entry.item] = entry;
        }
        return acc;
      }, {}) || overridesByItem);
      setStatus({ type: 'success', message: `Saved override for ${overrideDraft.itemId}.` });
      closeOverrideEditor();
      await loadPage(true);
    } catch (err) {
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to save item override.' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteItemOverride = async (itemId) => {
    if (!itemId) {
      return;
    }

    setSaving(true);
    setStatus({ type: '', message: '' });
    try {
      const res = await deleteItemOverride(itemId);
      setOverridesByItem(res.data?.overrides?.reduce?.((acc, entry) => {
        if (entry?.item) {
          acc[entry.item] = entry;
        }
        return acc;
      }, {}) || {});
      setStatus({ type: 'success', message: `Deleted override for ${itemId}.` });
      if (overrideDraft?.itemId === itemId) {
        closeOverrideEditor();
      }
      await loadPage(true);
    } catch (err) {
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to delete item override.' });
    } finally {
      setSaving(false);
    }
  };

  const handleBlacklistItem = async (itemId) => {
    if (!itemId) {
      return;
    }

    setBlacklistingItemId(itemId);
    setStatus({ type: '', message: '' });
    try {
      await addBlacklistItem(itemId);
      setStatus({ type: 'success', message: `${itemId} was added to the blacklist.` });
      if (overrideDraft?.itemId === itemId) {
        closeOverrideEditor();
      }
      await loadPage(true);
    } catch (err) {
      setStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to add item to blacklist.' });
    } finally {
      setBlacklistingItemId('');
    }
  };

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '0.95fr 1.25fr' }, gap: 3 }}>
      <TagTreePanel
        status={status}
        search={search}
        setSearch={setSearch}
        loadingCatalog={loadingCatalog}
        visibleNodeCount={visibleNodeCount}
        handleExpandAll={handleExpandAll}
        handleCollapseAll={handleCollapseAll}
        loadPage={loadPage}
        saving={saving}
        visibleRows={visibleRows}
        selectedTag={selectedTag}
        handleSelectTag={handleSelectTag}
        toggleExpanded={toggleExpanded}
      />

      <Stack spacing={3}>
        <TagDetailsPanel
          selectedTag={selectedTag}
          pendingAddition={pendingAddition}
          setPendingAddition={setPendingAddition}
          hasUnsavedChange={hasUnsavedChange}
          saving={saving}
          handleReset={handleReset}
          handleSave={handleSave}
          config={config}
          selectedCatalogRow={selectedCatalogRow}
          catalogSource={catalogSource}
          catalogItemCount={catalogItemCount}
          compoundRows={compoundRows}
          savedCompoundTotal={savedCompoundTotal}
          pendingCompoundTotal={pendingCompoundTotal}
          previewData={previewData}
        />

        <TagPreviewPanel
          selectedTag={selectedTag}
          loadingPreview={loadingPreview}
          previewData={previewData}
          previewStale={previewStale}
          handleGeneratePreview={handleGeneratePreview}
          config={config}
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
      </Stack>
    </Box>
  );
};

export default TagPricingPage;
