import { useCallback } from 'react';
import { createManualDefinition, saveManualDefinition, getManualEditorData } from '../../services/api';
import { STAGE2_CATEGORIES } from './batchUtils';

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
            const pages = overrides.pages || batch.finalPages || batch.consolidatedPages || batch.pages;

            const capitals = module.replace(/[^A-Z]/g, '') || 'Upd';
            const volId = `${capitals}_Upd_${until.replace(/-/g, '_')}`;

            const cat = batch.categorization || {};
            const activeCats = STAGE2_CATEGORIES.filter((c) => cat?.summaries?.[c] && String(cat.summaries[c] || '').trim());

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

            const richDescription = rawDescription.length > 499 ? rawDescription.slice(0, 496) + '...' : rawDescription;
            const chapterDesc = (cat?.summaries?.Features || cat?.summaries?.Fixes || '');

            // Determine a sensible sort_order so newer updates appear after existing ones
            let assignedSortOrder = null;
            try {
                const existingRes = await getManualEditorData('updates', module);
                const existingManuals = existingRes?.data?.manuals || [];
                if (existingManuals.length > 0) {
                    const maxSort = existingManuals.reduce((acc, m) => Math.max(acc, Number(m.sort_order || 0)), Number.MIN_SAFE_INTEGER);
                    if (Number.isFinite(maxSort) && maxSort > Number.MIN_SAFE_INTEGER) assignedSortOrder = maxSort + 1;
                }
            } catch (err) {
                addLog(batchId, 'warning', `Failed to query existing manuals for sort order: ${err.message}`);
            }

            // Fallback base for updates mirrors backend default behavior (updates default to 0)
            if (assignedSortOrder === null) assignedSortOrder = 0 + 1;

            const payload = {
                manual_id: volId,
                module,
                title: overrides.title || batch.generatedUpdateTitle || `Update: ${since.slice(5).replace(/-/g, '/')} - ${until.slice(5).replace(/-/g, '/')}`,
                description: richDescription,
                start_page_id: pages[0]?.id || 'index',
                audiences: [module],
                sort_order: assignedSortOrder,
                is_whats_new: true,
                manual_type: 'whats_new',
                source_folder: 'WhatsNew',
                chapters: [{ id: 'release_notes', title: 'Release Notes', description: chapterDesc }],
                pages,
            };

            addLog(batchId, 'system', `Writing manual: ${volId} → module: ${module} (${pages.length} pages)`);

            if (forceRecreate) {
                addLog(batchId, 'system', `Force-recreate: overwriting existing Lua for ${volId}`);
                await saveManualDefinition(volId, payload, 'updates', module);
            } else {
                try {
                    await createManualDefinition(payload, 'updates', module);
                    addLog(batchId, 'system', `Created new manual: ${volId}`);
                } catch (createErr) {
                    const detail = String(createErr?.response?.data?.detail || createErr?.message || '');
                    if (/already exists|duplicate|manual/i.test(detail)) {
                        addLog(batchId, 'system', `Manual exists, updating: ${volId}`);
                        await saveManualDefinition(volId, payload, 'updates', module);
                    } else {
                        throw createErr;
                    }
                }
            }

            addLog(batchId, 'success', `VOLUME SAVED: ${volId} (${pages.length} pages)`);
            updateBatch(batchId, { status: 'success', currentStep: 'Completed' });

            if (batch.config?.cacheOutputs) {
                saveBatchCache(batchId, { module, branch: batch.config.branch, since, until, finalPages: pages, generatedUpdateTitle: payload.title });
            }
        } catch (error) {
            addLog(batchId, 'error', `Final Save Failed: ${error.message}`);
            updateBatch(batchId, { status: 'error', error: error.message, currentStep: 'Save ERROR' });
        }
    }, [addLog, updateBatch, saveBatchCache]);

    return { saveBatchVolume };
};
