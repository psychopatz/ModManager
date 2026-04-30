import { useCallback } from 'react';
import { getBatchedGitHistory } from '../../services/api';

/**
 * Provides processBatch — the top-level orchestrator that runs Stage 1 → Stage 2 → Stage 3.
 *
 * @param {object} deps
 * @param {React.MutableRefObject} deps.batchesRef - live ref to batches array
 * @param {Function} deps.addLog                   - (id, type, msg) => void
 * @param {Function} deps.updateBatch              - (id, updates) => void
 * @param {Function} deps.processDay               - Stage 1: per-day LLM expansion
 * @param {Function} deps.consolidateBatch         - Stage 2: thematic consolidation
 * @param {Function} deps.saveBatchVolume          - Stage 3: write to backend
 */
export const useBatchProcess = ({ batchesRef, addLog, updateBatch, processDay, consolidateBatch, saveBatchVolume }) => {

    const processBatch = useCallback(async (id, config) => {
        const { since, until, module, branch } = config;
        const log = (type, msg) => addLog(id, type, msg);
        const setStep = (step) => updateBatch(id, { currentStep: step });
        const setProg = (val) => updateBatch(id, { progress: val });

        try {
            log('system', `Starting background batch: ${since} -> ${until}`);

            // Restore Stage 1 from resume cache if available
            if (config._resolvedResumeCache?.stage1Items?.length > 0) {
                updateBatch(id, {
                    stage1Items: config._resolvedResumeCache.stage1Items,
                    pages: config._resolvedResumeCache.pages || [],
                    currentStep: 'Loaded Stage 1 cache',
                });
            }

            // Fetch git history payload, preferring routed_history when available.
            let history = config.history || config._resolvedResumeCache?.history;
            let routedHistory = config.routedHistory || config._resolvedResumeCache?.routedHistory;
            let routingWarnings = config.routingWarnings || config._resolvedResumeCache?.routingWarnings || [];

            if (!history || !routedHistory) {
                setStep('Fetching git history...');
                const historyRes = await getBatchedGitHistory(since, until, branch, module);
                if (historyRes.status !== 200 || !historyRes.data.history) {
                    throw new Error(historyRes.data?.error || `Git history fetch failed for branch '${branch}'`);
                }
                history = historyRes.data.history;
                routedHistory = historyRes.data.routed_history || {};
                routingWarnings = historyRes.data.routing_warnings || [];
            } else {
                setStep('Preparing Stage 1...');
            }

            if (routingWarnings.length > 0) {
                log('warning', `Routing skipped ${routingWarnings.length} commit(s) with unknown submod paths.`);
            }

            const hasRoutedData = !!routedHistory && Object.keys(routedHistory).length > 0;
            const stage1History = hasRoutedData ? routedHistory : history;

            updateBatch(id, { history, routedHistory, routingWarnings });

            // ─── Stage 1 ───────────────────────────────────────────────────────
            const skipStage1 = config.resumeFromStage === 2 && config._resolvedResumeCache?.stage1Items?.length > 0;
            const allDates = Object.keys(stage1History).sort();
            const rangeDates = allDates.filter((d) => d >= since && d <= until);

            const total = hasRoutedData
                ? rangeDates.reduce((acc, d) => acc + Object.keys(stage1History[d] || {}).length, 0)
                : rangeDates.length;

            if (total === 0) {
                log('system', 'No git history found for the selected module, branch, and date range.');
                updateBatch(id, { status: 'idle', progress: 100, currentStep: 'No changes found' });
                return;
            }

            if (!skipStage1) {
                let processed = 0;
                for (let i = 0; i < rangeDates.length; i++) {
                    const date = rangeDates[i];
                    const dayGroups = stage1History[date] || {};

                    const entries = hasRoutedData
                        ? Object.entries(dayGroups)
                        : [[module, dayGroups]];

                    for (const [targetModule, commitsOrRepos] of entries) {
                        // Pause support
                        while (true) {
                            const currentBatch = batchesRef.current.find((b) => b.id === id);
                            if (!currentBatch) return;
                            if (!currentBatch.paused) break;
                            await new Promise((r) => setTimeout(r, 500));
                        }

                        setStep(`Processing ${date}${hasRoutedData ? ` (${targetModule})` : ''}...`);
                        const dayRepos = hasRoutedData ? { [targetModule]: commitsOrRepos } : commitsOrRepos;
                        if (dayRepos && Object.keys(dayRepos).length > 0) {
                            log('system', `-> Building Page for ${date}${hasRoutedData ? ` [${targetModule}]` : ''}`);
                            await processDay(id, date, dayRepos, { ...config, module: targetModule || module }, { targetModule: targetModule || module });
                        }
                        processed += 1;
                        setProg(Math.round((processed / total) * 100));
                    }
                }
            } else {
                setProg(100);
                setStep('Stage 1 skipped via cache');
            }

            // ─── Stage 2 ───────────────────────────────────────────────────────
            updateBatch(id, { progress: 100 });
            let pages = [];
            if (config.resumeFromStage !== 3) {
                const result = await consolidateBatch(id, config.consolidationPrompt);
                pages = [...(result?.newPages || [])];
            } else {
                const finalBatch = batchesRef.current.find((b) => b.id === id);
                pages = [...(finalBatch?.finalPages || finalBatch?.consolidatedPages || [])];
            }

            if (pages.length === 0) {
                const finalBatch = batchesRef.current.find((b) => b.id === id);
                pages = [...(finalBatch?.finalPages || finalBatch?.consolidatedPages || [])];
            }

            if (pages.length === 0) {
                log('system', 'No updates found in selected range.');
                updateBatch(id, { status: 'idle', currentStep: 'No changes found' });
                return;
            }

            updateBatch(id, {
                finalPages: pages,
                status: 'refining_done',
                currentStep: config.autoSaveAfterConsolidation
                    ? 'Auto-saving assembled update...'
                    : 'Stage 3 ready (commit when ready)',
            });

            // ─── Stage 3 (auto-save) ───────────────────────────────────────────
            // Pass categorization directly from the consolidation result to avoid
            // a batchesRef timing issue (React useEffect may not have synced yet).
            if (config.autoSaveAfterConsolidation) {
                const consolidationResult = batchesRef.current.find((b) => b.id === id);
                await saveBatchVolume(id, {
                    pages,
                    categorization: result?.categorization || consolidationResult?.categorization,
                });
                return;
            }

            log('success', 'Batch daily refinement complete. Stage 3 is ready for manual commit.');

        } catch (error) {
            log('error', `Batch Failed: ${error.message}`);
            updateBatch(id, { status: 'error', error: error.message, currentStep: 'Failed' });
        }
    }, [addLog, updateBatch, processDay, consolidateBatch, saveBatchVolume]);

    return { processBatch };
};
