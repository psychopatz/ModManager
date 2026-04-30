import { useCallback } from 'react';
import { createManualDefinition, saveManualDefinition, getManualEditorData } from '../../services/api';
import { STAGE2_CATEGORIES, assembleCategoryPages } from './batchUtils';

/**
 * Provides saveBatchVolume — persists assembled pages to the backend as a manual.
 *
 * @param {object} deps
 * @param {React.MutableRefObject} deps.batchesRef - live ref to batches array
 * @param {Function} deps.addLog                   - (id, type, msg) => void
 * @param {Function} deps.updateBatch              - (id, updates) => void
 * @param {Function} deps.saveBatchCache           - (id, partial) => void
 */
export const useBatchVolume = ({ batchesRef, addLog, updateBatch, saveBatchCache }) => {

    const saveBatchVolume = useCallback(async (batchId, overrides = {}) => {
        const batch = batchesRef.current.find((b) => b.id === batchId);
        if (!batch) return;

        try {
            const forceRecreate = overrides.forceRecreate || false;
            updateBatch(batchId, {
                currentStep: forceRecreate ? 'Force-recreating Lua files...' : 'Finalizing Save...',
                status: 'saving',
            });

            const { since, until, module } = batch.config;
            const fallbackPages = overrides.pages || batch.finalPages || batch.consolidatedPages || batch.pages;
            const stage1Items = batch.stage1Items || [];
            const cat = overrides.categorization || batch.categorization || {};

            // Group items by resolved target module. This enables split-save for multi-submod batches.
            const itemsByModule = new Map();
            for (const item of stage1Items) {
                const target = String(item?.target_module || module || '').trim();
                if (!target) continue;
                if (!itemsByModule.has(target)) itemsByModule.set(target, []);
                itemsByModule.get(target).push(item);
            }
            if (itemsByModule.size === 0) itemsByModule.set(module, []);

            const buildPagesForModule = (targetModule, moduleItems) => {
                if (moduleItems.length > 0 && cat?.map) {
                    const scopedMap = {};
                    for (const item of moduleItems) {
                        const mapped = cat.map[item.id] || 'Misc';
                        scopedMap[item.id] = mapped;
                    }
                    const scopedCategorization = {
                        ...cat,
                        map: scopedMap,
                        summaries: { ...(cat.summaries || {}) },
                    };
                    const rebuilt = assembleCategoryPages(moduleItems, scopedCategorization);
                    if (rebuilt.length > 0) return rebuilt;
                }

                const taggedFallback = (fallbackPages || []).filter((p) => String(p?.target_module || '').trim() === targetModule);
                if (taggedFallback.length > 0) return taggedFallback;
                return itemsByModule.size === 1 ? (fallbackPages || []) : [];
            };

            let savedCount = 0;
            for (const [targetModule, moduleItems] of itemsByModule.entries()) {
                const pages = buildPagesForModule(targetModule, moduleItems);
                if (!pages || pages.length === 0) {
                    addLog(batchId, 'warning', `Skipping ${targetModule}: no routable pages (likely unmatched paths).`);
                    continue;
                }

                const capitals = targetModule.replace(/[^A-Z]/g, '') || 'Upd';
                const volId = `${capitals}_Upd_${until.replace(/-/g, '_')}`;

                const itemIdSet = new Set(moduleItems.map((item) => item.id));
                const activeCats = STAGE2_CATEGORIES.filter(
                    (c) => (cat?.summaries?.[c] && String(cat.summaries[c] || '').trim())
                        && moduleItems.some((item) => (cat?.map?.[item.id] || 'Misc') === c)
                );

                // Build a concise, player-facing description instead of long pipe-separated lists.
                let rawDescription = '';
                if (cat?.overallTitle) {
                    const highlights = activeCats.slice(0, 2).map((c) => String(cat.summaries[c] || '').trim()).filter(Boolean);
                    rawDescription = highlights.length > 0 ? `${cat.overallTitle}. ${highlights.join(' — ')}` : `${cat.overallTitle}.`;
                } else if (activeCats.length > 0) {
                    const highlights = activeCats.slice(0, 3).map((c) => String(cat.summaries[c] || '').trim()).filter(Boolean);
                    rawDescription = highlights.join(' — ');
                } else {
                    rawDescription = `Consolidated updates from ${since} to ${until}`;
                }

                const richDescription = rawDescription.length > 499 ? `${rawDescription.slice(0, 496)}...` : rawDescription;
                const chapterDesc = (cat?.summaries?.Features || cat?.summaries?.Fixes || '');

                // Determine a sensible sort_order so newer updates appear after existing ones per target module.
                let assignedSortOrder = null;
                try {
                    const existingRes = await getManualEditorData('updates', targetModule);
                    const existingManuals = existingRes?.data?.manuals || [];
                    if (existingManuals.length > 0) {
                        const maxSort = existingManuals.reduce((acc, m) => Math.max(acc, Number(m.sort_order || 0)), Number.MIN_SAFE_INTEGER);
                        if (Number.isFinite(maxSort) && maxSort > Number.MIN_SAFE_INTEGER) assignedSortOrder = maxSort + 1;
                    }
                } catch (err) {
                    addLog(batchId, 'warning', `Failed to query sort order for ${targetModule}: ${err.message}`);
                }

                // Fallback base for updates mirrors backend default behavior (updates default to 0)
                if (assignedSortOrder === null) assignedSortOrder = 1;

                const payload = {
                    manual_id: volId,
                    module: targetModule,
                    title: overrides.title || batch.generatedUpdateTitle || `Update: ${since.slice(5).replace(/-/g, '/')} - ${until.slice(5).replace(/-/g, '/')}`,
                    description: richDescription,
                    start_page_id: pages[0]?.id || 'index',
                    audiences: [targetModule],
                    sort_order: assignedSortOrder,
                    is_whats_new: true,
                    manual_type: 'whats_new',
                    source_folder: 'WhatsNew',
                    chapters: [{ id: 'release_notes', title: 'Release Notes', description: chapterDesc }],
                    pages,
                };

                addLog(batchId, 'system', `Writing manual: ${volId} → module: ${targetModule} (${pages.length} pages, ${itemIdSet.size} items)`);

                if (forceRecreate) {
                    addLog(batchId, 'system', `Force-recreate: overwriting existing Lua for ${volId}`);
                    await saveManualDefinition(volId, payload, 'updates', targetModule);
                } else {
                    try {
                        await createManualDefinition(payload, 'updates', targetModule);
                        addLog(batchId, 'system', `Created new manual: ${volId}`);
                    } catch (createErr) {
                        const detail = String(createErr?.response?.data?.detail || createErr?.message || '');
                        if (/already exists|duplicate|manual/i.test(detail)) {
                            addLog(batchId, 'system', `Manual exists, updating: ${volId}`);
                            await saveManualDefinition(volId, payload, 'updates', targetModule);
                        } else {
                            throw createErr;
                        }
                    }
                }
                savedCount += 1;
            }

            if (savedCount === 0) {
                throw new Error('No routed pages could be saved. All groups were skipped due to unmatched paths.');
            }

            addLog(batchId, 'success', `VOLUME SAVED: ${savedCount} routed manual(s)`);
            updateBatch(batchId, { status: 'success', currentStep: 'Completed' });

            if (batch.config?.cacheOutputs) {
                saveBatchCache(batchId, { module, branch: batch.config.branch, since, until, finalPages: fallbackPages, generatedUpdateTitle: batch.generatedUpdateTitle });
            }
        } catch (error) {
            addLog(batchId, 'error', `Final Save Failed: ${error.message}`);
            updateBatch(batchId, { status: 'error', error: error.message, currentStep: 'Save ERROR' });
        }
    }, [addLog, updateBatch, saveBatchCache]);

    return { saveBatchVolume };
};
