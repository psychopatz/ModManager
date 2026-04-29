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

            // Fetch git history only when it was not already previewed in the generator.
            let history = config.history || config._resolvedResumeCache?.history;
            if (!history) {
                setStep('Fetching git history...');
                const historyRes = await getBatchedGitHistory(since, until, branch, module);
                if (historyRes.status !== 200 || !historyRes.data.history) {
                    throw new Error(historyRes.data?.error || `Git history fetch failed for branch '${branch}'`);
                }
                history = historyRes.data.history;
            } else {
                setStep('Preparing Stage 1...');
            }
            updateBatch(id, { history });

            // ─── Stage 1 ───────────────────────────────────────────────────────
            const skipStage1 = config.resumeFromStage === 2 && config._resolvedResumeCache?.stage1Items?.length > 0;
            const allDates = Object.keys(history).sort();
            const rangeDates = allDates.filter((d) => d >= since && d <= until);
            const total = rangeDates.length;

            if (total === 0) {
                log('system', 'No git history found for the selected module, branch, and date range.');
                updateBatch(id, { status: 'idle', progress: 100, currentStep: 'No changes found' });
                return;
            }

            if (!skipStage1) {
                for (let i = 0; i < total; i++) {
                    // Pause support
                    while (true) {
                        const currentBatch = batchesRef.current.find((b) => b.id === id);
                        if (!currentBatch) return;
                        if (!currentBatch.paused) break;
                        await new Promise((r) => setTimeout(r, 500));
                    }
                    const date = rangeDates[i];
                    setStep(`Processing ${date}...`);
                    const dayRepos = history[date];
                    if (dayRepos) {
                        log('system', `-> Building Page for ${date}`);
                        await processDay(id, date, dayRepos, config);
                    }
                    setProg(Math.round(((i + 1) / total) * 100));
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
            if (config.autoSaveAfterConsolidation) {
                await saveBatchVolume(id, { pages });
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
