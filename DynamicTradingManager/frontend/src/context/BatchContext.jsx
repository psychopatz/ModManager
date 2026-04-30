import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getBatchedGitHistory } from '../services/api';
import { safeJsonParse } from './batch/batchUtils';
import { useBatchCache } from './batch/useBatchCache';
import { useBatchLLM } from './batch/useBatchLLM';
import { useBatchVolume } from './batch/useBatchVolume';
import { useBatchProcess } from './batch/useBatchProcess';

const BatchContext = createContext();

export const useBatchSystem = () => {
    const context = useContext(BatchContext);
    if (!context) throw new Error('useBatchSystem must be used within a BatchProvider');
    return context;
};

export const BatchProvider = ({ children }) => {
    // Use a session-scoped instance id so multiple concurrently-opened windows
    // don't stomp each other's active batch list in localStorage.
    const INSTANCE_KEY = 'dtm_batch_instance_id';
    const instanceId = (() => {
        try {
            let id = sessionStorage.getItem(INSTANCE_KEY);
            if (!id) {
                id = `inst_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
                sessionStorage.setItem(INSTANCE_KEY, id);
            }
            return id;
        } catch (e) {
            return `inst_${Date.now()}`;
        }
    })();
    const GLOBAL_BATCH_KEY = `global_active_batches_${instanceId}`;

    const [batches, setBatches] = useState(() => safeJsonParse(localStorage.getItem(GLOBAL_BATCH_KEY), []));
    const [openBatchId, setOpenBatchId] = useState(null);
    const batchesRef = useRef([]);
    const abortRefs = useRef({});

    useEffect(() => { batchesRef.current = batches; }, [batches]);
    useEffect(() => { try { localStorage.setItem(GLOBAL_BATCH_KEY, JSON.stringify(batches)); } catch (e) {} }, [batches, GLOBAL_BATCH_KEY]);

    const openFullView = useCallback((id) => setOpenBatchId(id), []);
    const closeFullView = useCallback(() => setOpenBatchId(null), []);

    const updateBatch = useCallback((id, updates) => {
        setBatches((prev) => prev.map((b) => (b.id === id ? { ...b, ...updates } : b)));
    }, []);

    const addLog = useCallback((id, type, content) => {
        const timestamp = new Date().toLocaleTimeString();
        setBatches((prev) =>
            prev.map((b) => {
                if (b.id !== id) return b;
                return { ...b, logs: [...(b.logs || []), [timestamp, type, content]].slice(-100) };
            })
        );
    }, []);

    const updateStreamingData = useCallback((batchId, key, data) => {
        setBatches((prev) =>
            prev.map((b) => {
                if (b.id !== batchId) return b;
                return {
                    ...b,
                    streamingData: {
                        ...(b.streamingData || {}),
                        [key]: { ...(b.streamingData?.[key] || {}), ...data },
                    },
                };
            })
        );
    }, []);

    // ─── Sub-hooks ──────────────────────────────────────────────────────────────
    const { saveBatchCache, loadBatchCache, listBatchCaches, clearBatchCache } = useBatchCache();

    const { processDay, consolidateBatch } = useBatchLLM({
        batchesRef, setBatches, addLog, updateBatch, updateStreamingData, saveBatchCache, abortRefs,
    });

    const { saveBatchVolume } = useBatchVolume({ batchesRef, addLog, updateBatch, saveBatchCache });

    const { processBatch } = useBatchProcess({
        batchesRef, addLog, updateBatch, processDay, consolidateBatch, saveBatchVolume,
    });

    // ─── Batch lifecycle ────────────────────────────────────────────────────────
    const spawnBatch = useCallback(async (config) => {
        const id = `batch_${Date.now()}`;
        const rawResumeCache = config.resumeCacheId ? loadBatchCache(config.resumeCacheId) : null;
        const resumeCache = rawResumeCache
            && rawResumeCache.module === config.module
            && (!rawResumeCache.branch || rawResumeCache.branch === config.branch)
            ? rawResumeCache
            : null;
        const newBatch = {
            id,
            modName: config.moduleLabel || config.module,
            module: config.module,
            status: 'processing',
            progress: 0,
            currentStep: 'Starting...',
            logs: [],
            pages: resumeCache?.pages || [],
            stage1Items: resumeCache?.stage1Items || [],
            categorization: resumeCache?.categorization || null,
            generatedUpdateTitle: resumeCache?.generatedUpdateTitle || '',
            finalPages: resumeCache?.finalPages || null,
            history: config.history || resumeCache?.history || null,
            routedHistory: config.routedHistory || resumeCache?.routedHistory || null,
            routingWarnings: config.routingWarnings || resumeCache?.routingWarnings || [],
            streamingData: {},
            paused: false,
            config,
            startTime: Date.now(),
        };
        setOpenBatchId(id);
        const spawnNext = [...batchesRef.current, newBatch];
        batchesRef.current = spawnNext;
        setBatches(spawnNext);
        processBatch(id, { ...config, _resolvedResumeCache: resumeCache });
        return id;
    }, [loadBatchCache, processBatch]);

    const removeBatch = useCallback((id) => {
        if (abortRefs.current[id]) abortRefs.current[id].abort();
        setBatches((prev) => prev.filter((b) => b.id !== id));
    }, []);

    const skipBatchItem = useCallback((id) => {
        if (abortRefs.current[id]) {
            abortRefs.current[id].abort();
            addLog(id, 'warning', 'Manual skip triggered. AI generation cancelled for current item.');
        } else {
            addLog(id, 'info', 'Skip ignored: No active AI process found for this item.');
        }
    }, [addLog]);

    const restartBatch = useCallback((id) => {
        const restartNext = batchesRef.current.map((b) =>
            b.id === id
                ? { ...b, status: 'processing', progress: 0, currentStep: 'Restarting...', pages: [], streamingData: {}, paused: false }
                : b
        );
        batchesRef.current = restartNext;
        setBatches(restartNext);
        const b = batchesRef.current.find((x) => x.id === id);
        if (b) processBatch(id, b.config);
    }, [processBatch]);

    const retryDay = useCallback(async (id, date) => {
        const b = batchesRef.current.find((x) => x.id === id);
        if (!b) return;
        if (abortRefs.current[id]) {
            abortRefs.current[id].abort();
            addLog(id, 'warning', `Active process aborted for ${date} to force restart.`);
        }
        const historyRes = await getBatchedGitHistory(b.config.since, b.config.until, b.config.branch, b.config.module);
        const routed = historyRes.data.routed_history || {};
        const legacy = historyRes.data.history || {};
        const routedDay = routed[date];
        const entries = routedDay && Object.keys(routedDay).length > 0
            ? Object.entries(routedDay).map(([targetModule, commits]) => ({ targetModule, dayRepos: { [targetModule]: commits } }))
            : [{ targetModule: b.config.module, dayRepos: legacy[date] }];
        if (!entries.length || !entries[0].dayRepos) return;
        addLog(id, 'system', `Force restarting day refinement for ${date}...`);
        for (const entry of entries) {
            if (!entry.dayRepos) continue;
            await processDay(id, date, entry.dayRepos, { ...b.config, module: entry.targetModule || b.config.module }, { targetModule: entry.targetModule || b.config.module });
        }
    }, [addLog, processDay]);

    const pauseBatch = useCallback((id) => updateBatch(id, { paused: true }), [updateBatch]);
    const resumeBatch = useCallback((id) => updateBatch(id, { paused: false }), [updateBatch]);
    const dismissBatch = useCallback((id) => updateBatch(id, { dismissed: true }), [updateBatch]);

    return (
        <BatchContext.Provider value={{
            batches, openBatchId,
            spawnBatch, removeBatch, skipBatchItem,
            pauseBatch, resumeBatch, restartBatch, retryDay,
            openFullView, closeFullView, dismissBatch,
            consolidateBatch, saveBatchVolume,
            listBatchCaches, clearBatchCache,
        }}>
            {children}
        </BatchContext.Provider>
    );
};
