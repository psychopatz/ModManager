import { useCallback } from 'react';
import { CACHE_PREFIX, safeJsonParse } from './batchUtils';

const INDEX_KEY = `${CACHE_PREFIX}index`;
const MAX_INDEX_ENTRIES = 20;
const MAX_STAGE1_ITEMS = 180;
const MAX_COMMIT_REFS_PER_ITEM = 10;
const MAX_TEXT_LEN = 600;

const truncateText = (value, max = MAX_TEXT_LEN) => {
    const text = String(value || '');
    return text.length > max ? `${text.slice(0, max - 3)}...` : text;
};

const compactStage1Item = (item) => ({
    ...item,
    title: truncateText(item?.title, 180),
    explanation: truncateText(item?.explanation, 320),
    impact: truncateText(item?.impact, 180),
    commitRefs: Array.isArray(item?.commitRefs) ? item.commitRefs.slice(0, MAX_COMMIT_REFS_PER_ITEM) : [],
});

const compactCachePayload = (payload) => {
    if (!payload || typeof payload !== 'object') return payload;
    const next = { ...payload };

    if (Array.isArray(next.stage1Items)) {
        next.stage1Items = next.stage1Items
            .slice(-MAX_STAGE1_ITEMS)
            .map(compactStage1Item);
    }

    if (Array.isArray(next.pages)) {
        // Pages can be large due to full block contents; keep recent set.
        next.pages = next.pages.slice(-MAX_STAGE1_ITEMS);
    }

    if (Array.isArray(next.finalPages)) {
        next.finalPages = next.finalPages.slice(-MAX_STAGE1_ITEMS);
    }

    if (next.generatedUpdateTitle) {
        next.generatedUpdateTitle = truncateText(next.generatedUpdateTitle, 180);
    }

    return next;
};

const isQuotaError = (error) => {
    if (!error) return false;
    const message = String(error?.message || error || '').toLowerCase();
    return message.includes('quota') || message.includes('exceeded the quota');
};

export const useBatchCache = () => {
    const pruneOldestCaches = useCallback(() => {
        const index = safeJsonParse(localStorage.getItem(INDEX_KEY), []);
        if (!Array.isArray(index) || index.length === 0) return [];

        const ranked = index
            .map((batchId) => {
                const cache = safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}${batchId}`), null);
                return {
                    batchId,
                    updatedAt: Number(cache?.updatedAt || 0),
                };
            })
            .sort((a, b) => a.updatedAt - b.updatedAt);

        const toRemove = ranked.slice(0, Math.max(1, Math.ceil(ranked.length / 3))).map((row) => row.batchId);
        const keepSet = new Set(ranked.map((row) => row.batchId));

        toRemove.forEach((batchId) => {
            localStorage.removeItem(`${CACHE_PREFIX}${batchId}`);
            keepSet.delete(batchId);
        });

        const nextIndex = index.filter((id) => keepSet.has(id));
        localStorage.setItem(INDEX_KEY, JSON.stringify(nextIndex));
        return nextIndex;
    }, []);

    const saveBatchCache = useCallback((batchId, partial) => {
        const cacheKey = `${CACHE_PREFIX}${batchId}`;
        const current = safeJsonParse(localStorage.getItem(cacheKey), {});
        const compactPartial = compactCachePayload(partial);
        const next = compactCachePayload({ ...current, ...compactPartial, updatedAt: Date.now() });

        try {
            localStorage.setItem(cacheKey, JSON.stringify(next));
        } catch (error) {
            if (isQuotaError(error)) {
                try {
                    pruneOldestCaches();
                    localStorage.setItem(cacheKey, JSON.stringify(next));
                } catch (retryError) {
                    // Final fallback: disable this write without throwing in UI runtime.
                    console.warn('Batch cache write skipped due to storage quota.', retryError);
                    return false;
                }
            } else {
                console.warn('Batch cache write failed.', error);
                return false;
            }
        }

        const index = safeJsonParse(localStorage.getItem(INDEX_KEY), []);
        let nextIndex = index.includes(batchId) ? index : [...index, batchId];
        if (nextIndex.length > MAX_INDEX_ENTRIES) {
            const overflow = nextIndex.length - MAX_INDEX_ENTRIES;
            const evicted = nextIndex.slice(0, overflow);
            evicted.forEach((id) => localStorage.removeItem(`${CACHE_PREFIX}${id}`));
            nextIndex = nextIndex.slice(overflow);
        }
        try {
            localStorage.setItem(INDEX_KEY, JSON.stringify(nextIndex));
        } catch (error) {
            console.warn('Batch cache index write skipped due to storage constraints.', error);
            return false;
        }
        return true;
    }, [pruneOldestCaches]);

    const loadBatchCache = useCallback((batchId) => {
        return safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}${batchId}`), null);
    }, []);

    const listBatchCaches = useCallback(() => {
        const index = safeJsonParse(localStorage.getItem(INDEX_KEY), []);
        return index
            .map((batchId) => {
                const cache = safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}${batchId}`), null);
                if (!cache) return null;
                return {
                    batchId,
                    module: cache.module,
                    branch: cache.branch,
                    since: cache.since,
                    until: cache.until,
                    updatedAt: cache.updatedAt,
                    stage1Count: (cache.stage1Items || []).length,
                    hasStage2: !!cache.categorization,
                    hasFinalPayload: !!cache.finalPages,
                    generatedUpdateTitle: cache.generatedUpdateTitle || '',
                };
            })
            .filter(Boolean)
            .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    }, []);

    const clearBatchCache = useCallback((batchId) => {
        localStorage.removeItem(`${CACHE_PREFIX}${batchId}`);
        const index = safeJsonParse(localStorage.getItem(INDEX_KEY), []);
        try {
            localStorage.setItem(INDEX_KEY, JSON.stringify(index.filter((id) => id !== batchId)));
        } catch (error) {
            console.warn('Batch cache index cleanup failed.', error);
        }
    }, []);

    return { saveBatchCache, loadBatchCache, listBatchCaches, clearBatchCache };
};
