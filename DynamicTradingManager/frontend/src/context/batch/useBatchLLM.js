import { useCallback } from 'react';
import { llmChatStream } from '../../services/api';
import { loadLLMConfig } from '../../utils/llmUtils';
import {
    slugify,
    STAGE2_CATEGORIES,
    parseStage1StructuredItem,
    parseStage2Categorization,
    normalizeOverallTitle,
    assembleCategoryPages,
    generateSteamBBCode,
} from './batchUtils';

/**
 * Provides Stage 1 (daily LLM expansion) and Stage 2 (thematic consolidation) operations.
 *
 * @param {object} deps
 * @param {React.MutableRefObject} deps.batchesRef    - live ref to batches array
 * @param {Function} deps.setBatches                  - React state setter for batches
 * @param {Function} deps.addLog                      - (id, type, msg) => void
 * @param {Function} deps.updateBatch                 - (id, updates) => void
 * @param {Function} deps.updateStreamingData         - (id, key, data) => void
 * @param {Function} deps.saveBatchCache              - (id, partial) => void
 * @param {React.MutableRefObject} deps.abortRefs     - { [batchId]: AbortController }
 */
export const useBatchLLM = ({ batchesRef, setBatches, addLog, updateBatch, updateStreamingData, saveBatchCache, abortRefs }) => {

    // ─── Stage 1: per-day LLM expansion ────────────────────────────────────────
    const processDay = useCallback(async (batchId, date, dayRepos, config) => {
        const { improveWithAI, typeFilters, systemPrompt } = config;
        const log = (type, msg) => addLog(batchId, type, msg);
        const parseCommitType = (s) =>
            s && typeof s === 'string' ? (s.match(/^(\w+)(\(.*\))?:/)?.[1].toLowerCase() || 'other') : 'other';

        // Filter commits by type
        const filteredDayData = {};
        let totalCommits = 0;
        for (const [repo, commits] of Object.entries(dayRepos)) {
            const filtered = commits.filter((c) => {
                const type = parseCommitType(c.subject || c.message);
                return (
                    typeFilters.includes(type) ||
                    (typeFilters.includes('other') &&
                        !['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test'].includes(type))
                );
            });
            if (filtered.length > 0) {
                filteredDayData[repo] = filtered;
                totalCommits += filtered.length;
            }
        }
        if (totalCommits === 0) return;

        const pageId = date.replace(/-/g, '_');
        const page = {
            id: pageId,
            date,
            chapter_id: 'release_notes',
            title: date,
            keywords: ['update', 'release', date],
            blocks: [{ type: 'heading', id: `heading_${pageId}`, level: 1, text: `Updates for ${date}` }],
        };

        // Build fallback structured item from raw commits
        const commitRefs = [];
        const fallbackTags = new Set();
        Object.entries(filteredDayData).forEach(([repo, commits]) => {
            commits.forEach((c) => {
                commitRefs.push(`${repo}: ${c.subject || c.message || 'Untitled commit'}`);
                const t = parseCommitType(c.subject || c.message || '');
                if (t && t !== 'other') fallbackTags.add(t);
            });
        });
        const fallbackStructuredItem = {
            id: `item_${pageId}`,
            date,
            sourceRepos: Object.keys(filteredDayData),
            title: `Updates for ${date}`,
            explanation: 'Summary generated from commit activity for this day.',
            impact: 'Incremental improvements and fixes.',
            tags: Array.from(fallbackTags),
            commitRefs,
        };

        let refinedText = '';
        let aiAttempted = false;

        if (improveWithAI) {
            aiAttempted = true;
            const stage1SystemMsg = systemPrompt ||
                `You are a professional release notes writer for a Project Zomboid mod. You write concise, player-facing descriptions of changes. You NEVER reference git internals, commit hashes, or developer jargon. Your tone is clear, informative, and engaging.`;

            const expansionPrompt = `Analyze the following git commits for ${date} and produce a structured release note entry.

You MUST output EXACTLY this format with each section marker on its own line. DO NOT include section markers inside the section text:

[TITLE]
Write a descriptive, player-facing title for today's changes. Examples: "Radio Scanner UI & LotteryAgent Expansion" or "Companion Combat Improvements". NOT a date.

[IMPACT]
One sentence describing the most important player-facing benefit of these changes.

[TAGS]
feat, fix, refactor

[EXPLANATION]
Write 3-6 bullet points or short paragraphs. Use **Bold Topic**: description format. Focus on what PLAYERS experience, not technical details. Do NOT include the [EXPLANATION] tag in the text.

[COMMIT_REFS]
- RepoName: commit subject line

CRITICAL: Section markers ([TITLE], [IMPACT], etc.) must appear ALONE on their own line. NEVER put a section marker inside the content of another section.

Commits for ${date}:
${Object.entries(filteredDayData)
    .map(([repo, commits]) => `${repo}:\n${commits.map((c) => `  - ${c.subject || c.message}`).join('\n')}`)
    .join('\n\n')}`;

            const llmConfig = loadLLMConfig();
            const provider = llmConfig.providers[llmConfig.activeProvider] || {};
            const ctrl = new AbortController();
            abortRefs.current[batchId] = ctrl;

            try {
                if (provider.is_browser_only) {
                    if (!window.puter) throw new Error('Puter.js not available.');
                    updateStreamingData(batchId, date, { content: '', thinking: 'AI is analyzing commits via Puter...', status: 'streaming' });
                    const response = await window.puter.ai.chat(`${stage1SystemMsg}\n\n${expansionPrompt}`);
                    refinedText = response?.toString() || '';
                    updateStreamingData(batchId, date, { content: refinedText, thinking: '', status: 'completed' });
                } else {
                    const streamResponse = await llmChatStream({
                        base_url: provider.base_url,
                        api_key: provider.api_key,
                        model: provider.model,
                        messages: [
                            { role: 'system', content: stage1SystemMsg },
                            { role: 'user', content: expansionPrompt },
                        ],
                        thinking: true,
                    }, ctrl.signal);

                    const reader = streamResponse.getReader();
                    const decoder = new TextDecoder();
                    let streamContent = '';
                    let streamThinking = '';
                    let buffer = '';
                    let lastUpdate = Date.now();

                    const throttleUpdate = (force = false) => {
                        const now = Date.now();
                        if (force || now - lastUpdate > 100) {
                            updateStreamingData(batchId, date, {
                                content: streamContent,
                                thinking: streamThinking,
                                status: force ? 'completed' : 'streaming',
                            });
                            lastUpdate = now;
                        }
                    };

                    while (true) {
                        if (ctrl.signal.aborted) throw { name: 'AbortError' };
                        const { done, value } = await reader.read();
                        if (done) break;
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';
                        for (const line of lines) {
                            const trimmed = line.trim();
                            if (!trimmed) continue;
                            try {
                                const part = JSON.parse(trimmed);
                                if (part.content) streamContent += part.content;
                                if (part.thinking) streamThinking += part.thinking;
                                throttleUpdate();
                            } catch (e) { /* malformed chunk */ }
                        }
                    }
                    if (buffer.trim()) {
                        try {
                            const part = JSON.parse(buffer);
                            if (part.content) streamContent += part.content;
                            if (part.thinking) streamThinking += part.thinking;
                        } catch (e) { /* ignore */ }
                    }
                    throttleUpdate(true);
                    refinedText = streamContent;
                }
            } catch (e) {
                if (e.name === 'AbortError') log('warning', `   AI cancelled for ${date}.`);
                else log('error', `   AI Error for ${date}: ${e.message}`);
                refinedText = '';
            } finally {
                delete abortRefs.current[batchId];
            }
        }

        let structuredItem = { ...fallbackStructuredItem };

        if (!refinedText || refinedText.trim() === '%ContextNotFound%') {
            if (aiAttempted && refinedText.trim() === '%ContextNotFound%') {
                log('system', `   (Skipped ${date}: Trivial changes)`);
            } else {
                for (const [repo, commits] of Object.entries(filteredDayData)) {
                    page.blocks.push({ type: 'heading', id: `repo_${repo.toLowerCase()}_${pageId}`, level: 2, text: repo.trim() });
                    page.blocks.push({ type: 'bullet_list', items: commits.map((c) => c.subject) });
                }
            }
        } else {
            structuredItem = parseStage1StructuredItem(refinedText, fallbackStructuredItem);
            if (structuredItem.parseWarnings.length > 0) {
                log('warning', `   Stage 1 parse warnings for ${date}: ${structuredItem.parseWarnings.join(' ')}`);
            }

            const lines = refinedText.split('\n');
            let foundTitle = '';
            for (let i = 0; i < Math.min(lines.length, 5); i++) {
                const line = lines[i].trim();
                const tagMatch = line.match(/^\[TITLE:\s*(.*?)\]/i);
                const h1Match = line.match(/^#\s*(.*)/);
                if (tagMatch) { foundTitle = tagMatch[1].trim(); lines.splice(i, 1); break; }
                else if (h1Match) { foundTitle = h1Match[1].trim(); lines.splice(i, 1); break; }
            }
            if (foundTitle) {
                page.title = foundTitle;
                const hBlock = page.blocks.find((b) => b.type === 'heading' && b.level === 1);
                if (hBlock) hBlock.text = foundTitle;
            }

            let curBlocks = [];
            const flush = () => {
                if (curBlocks.length > 0) { page.blocks.push({ type: 'bullet_list', items: curBlocks }); curBlocks = []; }
            };
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                const hMatch = trimmed.match(/^###\s*(.*)/) || trimmed.match(/^##\s*(.*)/);
                if (hMatch) { flush(); page.blocks.push({ type: 'heading', id: `ai_h_${pageId}_${slugify(hMatch[1])}`, level: 2, text: hMatch[1].trim() }); continue; }
                const cMatch = trimmed.match(/^>\s*\[!(info|success|warning|danger)\]\s*(.*?)\s*\|\s*(.*)/i);
                if (cMatch) { flush(); page.blocks.push({ type: 'callout', tone: cMatch[1].toLowerCase(), title: cMatch[2].trim(), text: cMatch[3] }); continue; }
                const iMatch = trimmed.match(/^!\[(.*?)\]\((.*?)\)/);
                if (iMatch) { flush(); page.blocks.push({ type: 'image', caption: iMatch[1], path: iMatch[2] }); continue; }
                const bMatch = trimmed.match(/^[*-]\s*(.*)/);
                if (bMatch) { curBlocks.push(bMatch[1]); continue; }
                if (curBlocks.length > 0) curBlocks.push(trimmed);
                else page.blocks.push({ type: 'paragraph', text: trimmed });
            }
            flush();
        }

        // Merge page + structuredItem into batch state
        setBatches((prev) =>
            prev.map((b) => {
                if (b.id !== batchId) return b;
                const otherPages = b.pages.filter((p) => p.date !== date);
                const otherItems = (b.stage1Items || []).filter((item) => item.date !== date);
                return {
                    ...b,
                    pages: [...otherPages, page].sort((a, z) => z.date.localeCompare(a.date)),
                    stage1Items: [...otherItems, structuredItem].sort((a, z) => z.date.localeCompare(a.date)),
                };
            })
        );

        const batchState = batchesRef.current.find((b) => b.id === batchId);
        if (batchState?.config?.cacheOutputs) {
            saveBatchCache(batchId, {
                module: batchState.module,
                branch: batchState.config.branch,
                since: batchState.config.since,
                until: batchState.config.until,
                pages: (batchState.pages || []).filter((p) => p.date !== date).concat([page]),
                stage1Items: (batchState.stage1Items || []).filter((item) => item.date !== date).concat([structuredItem]),
            });
        }
    }, [addLog, updateBatch, updateStreamingData, saveBatchCache, setBatches]);

    // ─── Stage 2: thematic consolidation ───────────────────────────────────────
    const consolidateBatch = useCallback(async (batchId, customPrompt = null) => {
        const b = batchesRef.current.find((x) => x.id === batchId);
        if (!b || (b.stage1Items || []).length === 0) return null;

        const log = (type, msg) => addLog(batchId, type, msg);
        log('system', 'Starting agentic consolidation pass...');
        updateBatch(batchId, { currentStep: 'Consolidating pages...' });

        const stage1TitlePayload = b.stage1Items.map((item) => ({ id: item.id, date: item.date, title: item.title }));

        const defaultConsolidationPrompt = `You are a professional release notes curator for a Project Zomboid mod called Dynamic Trading. Your job is to categorize structured update items into thematic pages and write an engaging overall update title.

IMPORTANT RULES:
- Do NOT use date ranges in the OVERALL_TITLE. Use a creative, player-facing title that captures the spirit of the changes.
- OVERALL_TITLE must be 3-8 words. Examples: "The April Sprint: New Tools & Refinements", "Companion Overhaul and Balance Pass"
- Every item_id must appear in CATEGORY_MAP exactly once.
- Category summaries should be 1-2 sentences each describing what changed, written for players, not developers.
- Use only these exact categories: Features, Fixes, QoL, Performance, Balance, Misc

Output ONLY in this exact format (no extra text, no JSON, no markdown code blocks):
OVERALL_TITLE: your creative player-facing title here
CATEGORY_MAP:
- item_id => Category
CATEGORY_SUMMARIES:
Features: what new features were added this cycle
Fixes: what bugs or issues were resolved
QoL: what quality-of-life improvements were made
Performance: what performance improvements were made
Balance: what balance changes were made
Misc: any other changes

Input items (id | date | title):
${stage1TitlePayload.map((item) => `- ${item.id} | ${item.date} | ${item.title}`).join('\n')}`;

        const finalPrompt = customPrompt || defaultConsolidationPrompt;
        updateStreamingData(batchId, '_consolidation', { status: 'streaming', thinking: '', content: '' });

        try {
            const llmConfig = loadLLMConfig();
            const provider = llmConfig.providers[llmConfig.activeProvider] || {};

            if (provider.is_browser_only) {
                if (!window.puter) throw new Error('Puter.js not available.');
                const response = await window.puter.ai.chat(finalPrompt);
                const streamContent = response?.toString() || '';
                updateStreamingData(batchId, '_consolidation', { content: streamContent, thinking: '', status: 'completed' });

                const categorization = parseStage2Categorization(streamContent, b.stage1Items || []);
                categorization.overallTitle = normalizeOverallTitle(categorization.overallTitle, categorization, b.stage1Items || []);
                const newPages = assembleCategoryPages(b.stage1Items || [], categorization);
                const workshopMetadata = generateSteamBBCode(categorization.overallTitle || 'Update Summary', categorization, newPages);

                updateBatch(batchId, {
                    consolidatedPages: newPages, categorization,
                    generatedUpdateTitle: categorization.overallTitle,
                    finalPages: newPages, workshopMetadata,
                    currentStep: 'Consolidation complete', consolidationError: null,
                });

                if (b.config?.cacheOutputs) {
                    saveBatchCache(batchId, {
                        module: b.module, since: b.config.since, until: b.config.until,
                        branch: b.config.branch,
                        stage1Items: b.stage1Items, categorization,
                        generatedUpdateTitle: categorization.overallTitle,
                        finalPages: newPages, workshopMetadata, pages: b.pages,
                    });
                }

                log('success', `Stage 2 complete. ${newPages.length} category pages assembled.`);
                return { newPages, workshopMetadata, categorization };
            }

            if (!provider.base_url || !provider.model) {
                throw new Error('Active LLM provider is missing base_url or model. Configure it in LLM Settings.');
            }

            const stream = await llmChatStream({
                base_url: provider.base_url,
                api_key: provider.api_key,
                model: provider.model,
                messages: [
                    { role: 'system', content: 'You are a strict categorization assistant. Follow the requested markdown format exactly.' },
                    { role: 'user', content: finalPrompt },
                ],
                thinking: !!llmConfig.thinking,
            });

            const reader = stream.getReader();
            const decoder = new TextDecoder();
            let streamContent = '';
            let streamThinking = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;
                    try {
                        const part = JSON.parse(trimmed);
                        if (part.content) streamContent += part.content;
                        if (part.thinking) streamThinking += part.thinking;
                        updateStreamingData(batchId, '_consolidation', { content: streamContent, thinking: streamThinking, status: 'streaming' });
                    } catch (e) { /* malformed chunk */ }
                }
            }

            const categorization = parseStage2Categorization(streamContent, b.stage1Items || []);
            categorization.overallTitle = normalizeOverallTitle(categorization.overallTitle, categorization, b.stage1Items || []);
            const newPages = assembleCategoryPages(b.stage1Items || [], categorization);
            const workshopMetadata = generateSteamBBCode(categorization.overallTitle || 'Update Summary', categorization, newPages);

            updateStreamingData(batchId, '_consolidation', { status: 'completed' });
            log('success', `Stage 2 complete. ${newPages.length} category pages assembled.`);

            updateBatch(batchId, {
                consolidatedPages: newPages, categorization,
                generatedUpdateTitle: categorization.overallTitle,
                finalPages: newPages, workshopMetadata,
                currentStep: 'Consolidation complete', consolidationError: null,
            });

            if (b.config?.cacheOutputs) {
                saveBatchCache(batchId, {
                    module: b.module, since: b.config.since, until: b.config.until,
                    branch: b.config.branch,
                    stage1Items: b.stage1Items, categorization,
                    generatedUpdateTitle: categorization.overallTitle,
                    finalPages: newPages, workshopMetadata, pages: b.pages,
                });
            }
            return { newPages, workshopMetadata, categorization };

        } catch (e) {
            log('error', `Consolidation failed: ${e.message}`);
            updateBatch(batchId, { consolidationError: e.message });
            updateStreamingData(batchId, '_consolidation', { status: 'error', error: e.message });
            return null;
        }
    }, [addLog, updateBatch, updateStreamingData, saveBatchCache]);

    return { processDay, consolidateBatch };
};
