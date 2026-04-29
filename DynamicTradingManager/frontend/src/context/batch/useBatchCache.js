import { useCallback } from 'react';
import { CACHE_PREFIX, safeJsonParse } from './batchUtils';

export const useBatchCache = () => {
    const saveBatchCache = useCallback((batchId, partial) => {
        const cacheKey = `${CACHE_PREFIX}${batchId}`;
        const current = safeJsonParse(localStorage.getItem(cacheKey), {});
        const next = { ...current, ...partial, updatedAt: Date.now() };
        localStorage.setItem(cacheKey, JSON.stringify(next));

        const index = safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}index`), []);
        if (!index.includes(batchId)) {
            localStorage.setItem(`${CACHE_PREFIX}index`, JSON.stringify([...index, batchId]));
        }
    }, []);

    const loadBatchCache = useCallback((batchId) => {
        return safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}${batchId}`), null);
    }, []);

    const listBatchCaches = useCallback(() => {
        const index = safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}index`), []);
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
        const index = safeJsonParse(localStorage.getItem(`${CACHE_PREFIX}index`), []);
        localStorage.setItem(`${CACHE_PREFIX}index`, JSON.stringify(index.filter((id) => id !== batchId)));
    }, []);

    return { saveBatchCache, loadBatchCache, listBatchCaches, clearBatchCache };
};
