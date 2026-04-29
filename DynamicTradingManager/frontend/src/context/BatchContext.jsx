import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getBatchedGitHistory, getDonatorsDefinition, createManualDefinition, saveManualDefinition, llmChat, llmChatStream } from '../services/api';
import { loadLLMConfig } from '../utils/llmUtils';

const slugify = (str) => str.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
const STAGE2_CATEGORIES = ['Features', 'Fixes', 'QoL', 'Performance', 'Balance', 'Misc'];
const CACHE_PREFIX = 'git_batch_cache_';

const safeJsonParse = (raw, fallback = null) => {
    if (!raw) return fallback;
    try {
        return JSON.parse(raw);
    } catch (e) {
        return fallback;
    }
};

const extractSection = (text, header) => {
    if (!text) return '';
    // Block format: [HEADER]\nContent...\n[NEXT_HEADER] or end-of-string
    const blockRe = new RegExp(`\\[${header}\\][^\\S\\n]*\\n([\\s\\S]*?)(?=\\n\\[[A-Z_]+\\]|$)`, 'i');
    const bm = text.match(blockRe);
    if (bm) return bm[1].trim();
    // Inline format: [HEADER]: value  or [HEADER] value on same line
    const inlineRe = new RegExp(`\\[${header}\\][:\\s]+(.+)`, 'i');
    const im = text.match(inlineRe);
    return im ? im[1].trim() : '';
};

// Strip all [SECTION] markers from text so they never appear in-game
const SECTION_TAG_RE = /\[(TITLE|IMPACT|TAGS|EXPLANATION|COMMIT_REFS)\][:\s]*/gi;
const sanitizePageText = (text) =>
    (text || '').replace(SECTION_TAG_RE, '').replace(/\n{3,}/g, '\n\n').trim();

const parseStage1StructuredItem = (text, fallback) => {
    const clean = (text || '').replace(/```[\\s\\S]*?```/g, (m) => m.replace(/```/g, '')).trim();
    const titleFromTag = extractSection(clean, 'TITLE').split('\n')[0]?.trim() || '';
    const impactFromTag = extractSection(clean, 'IMPACT').split('\n')[0]?.trim() || '';
    const tagsRaw = extractSection(clean, 'TAGS').split('\n')[0] || '';
    const explanationRaw = extractSection(clean, 'EXPLANATION');
    // If no [EXPLANATION] marker found, fall back to the whole text but strip all markers so they never show in-game
    const explanation = explanationRaw ? sanitizePageText(explanationRaw) : sanitizePageText(clean);
    const refsSection = extractSection(clean, 'COMMIT_REFS');

    const commitRefs = refsSection
        ? refsSection
                .split('\n')
                .map((line) => line.replace(/^[-*]\s*/, '').trim())
                .filter(Boolean)
        : (fallback.commitRefs || []);

    const tags = tagsRaw
        ? tagsRaw
                .split(',')
                .map((t) => t.trim())
                .filter(Boolean)
        : (fallback.tags || []);

    const item = {
        id: fallback.id,
        date: fallback.date,
        sourceRepos: fallback.sourceRepos,
        title: titleFromTag || fallback.title,
        explanation: explanation || fallback.explanation,
        impact: impactFromTag || fallback.impact,
        tags,
        commitRefs,
        parseWarnings: []
    };

    if (!titleFromTag) item.parseWarnings.push('Missing [TITLE], fallback used.');
    if (!impactFromTag) item.parseWarnings.push('Missing [IMPACT], fallback used.');
    if (!extractSection(clean, 'EXPLANATION')) item.parseWarnings.push('Missing [EXPLANATION], full response used.');
    if (!refsSection) item.parseWarnings.push('Missing [COMMIT_REFS], fallback used.');

    return item;
};

const categoryFromLabel = (label = '') => {
    const normalized = label.trim().toLowerCase();
    const hit = STAGE2_CATEGORIES.find((c) => c.toLowerCase() === normalized);
    return hit || 'Misc';
};

const parseStage2Categorization = (content, items) => {
    const lines = (content || '').split('\n').map((l) => l.trim()).filter(Boolean);
    const map = {};
    const summaries = {};
    STAGE2_CATEGORIES.forEach((c) => { summaries[c] = ''; });

    let overallTitle = 'Update Summary';
    let inMap = false;
    let inSummaries = false;

    for (const line of lines) {
        if (/^OVERALL_TITLE\s*:/i.test(line)) {
            overallTitle = line.replace(/^OVERALL_TITLE\s*:/i, '').trim() || overallTitle;
            continue;
        }
        if (/^CATEGORY_MAP\s*:/i.test(line)) {
            inMap = true;
            inSummaries = false;
            continue;
        }
        if (/^CATEGORY_SUMMARIES\s*:/i.test(line)) {
            inMap = false;
            inSummaries = true;
            continue;
        }

        if (inMap) {
            const mapMatch = line.match(/^[-*]\s*(.*?)\s*=>\s*(.+)$/);
            if (mapMatch) {
                map[mapMatch[1].trim()] = categoryFromLabel(mapMatch[2].trim());
            }
            continue;
        }

        if (inSummaries) {
            const summaryMatch = line.match(/^([A-Za-z]+)\s*:\s*(.*)$/);
            if (summaryMatch) {
                const category = categoryFromLabel(summaryMatch[1]);
                summaries[category] = summaryMatch[2].trim();
            }
        }
    }

    items.forEach((item) => {
        if (!map[item.id]) map[item.id] = 'Misc';
    });

    return { overallTitle, map, summaries };
};

const normalizeOverallTitle = (title, categorization, stage1Items) => {
    const clean = (title || '').trim();
    const looksDateOnly = /^(daily|weekly|monthly)?\s*(update|update log|changelog|release notes)?\s*\(?[a-z]*\s*\d{1,2}(?:\s*[-–]\s*\d{1,2})?,?\s*\d{4}\)?$/i.test(clean)
        || /^\d{4}-\d{2}-\d{2}(\s*[-–]\s*\d{4}-\d{2}-\d{2})?$/i.test(clean)
        || clean.length < 8;

    if (!looksDateOnly) return clean;

    const categoryCounts = STAGE2_CATEGORIES.map((category) => ({
        category,
        count: stage1Items.filter((item) => categorization.map[item.id] === category).length,
    }))
        .filter((row) => row.count > 0 && row.category !== 'Misc')
        .sort((a, b) => b.count - a.count);

    if (categoryCounts.length === 0) return 'Mod Update Roundup';
    if (categoryCounts.length === 1) return `${categoryCounts[0].category} Spotlight Update`;
    return `${categoryCounts[0].category} and ${categoryCounts[1].category} Update Roundup`;
};

// Build a richly-formatted Steam Workshop BBCode post
const generateSteamBBCode = (title, categorization, pages) => {
    const releaseDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const lines = [];
    lines.push(`[h1]${title}[/h1]`);
    lines.push(`[i]Released ${releaseDate}[/i]`);
    lines.push('[hr][/hr]');
    lines.push('');
    lines.push("Thank you for your continued support! Here's a full breakdown of what changed in this update:");
    lines.push('');

    STAGE2_CATEGORIES.forEach(cat => {
        const catPage = pages.find(p => p.title === cat);
        if (!catPage) return;
        const summary = categorization.summaries?.[cat];
        const headings = catPage.blocks.filter(b => b.type === 'heading' && b.level === 2);
        if (headings.length === 0) return;

        const icons = { Features: '🚀', Fixes: '🔧', QoL: '✨', Performance: '⚡', Balance: '⚖️', Misc: '📝' };
        lines.push(`[h2]${icons[cat] || '▸'} ${cat}[/h2]`);
        if (summary) lines.push(`[i]${summary}[/i]`);
        lines.push('');
        lines.push('[list]');
        headings.forEach((h) => {
            // Find the impact callout that follows this heading
            const hIdx = catPage.blocks.indexOf(h);
            const impact = catPage.blocks.slice(hIdx + 1, hIdx + 4).find(b => b.type === 'callout' && b.tone === 'success');
            if (impact) {
                lines.push(`[*][b]${h.text}[/b] — ${impact.text}`);
            } else {
                lines.push(`[*][b]${h.text}[/b]`);
            }
        });
        lines.push('[/list]');
        lines.push('');
    });

    lines.push('[hr][/hr]');
    lines.push('[i]If you enjoy this mod, please consider leaving a rating and sharing it with your friends![/i]');

    return lines.join('\n');
};

const assembleCategoryPages = (stage1Items, categorization) => {
    return STAGE2_CATEGORIES
        .map((category) => {
            const items = stage1Items.filter((item) => categorization.map[item.id] === category);
            if (items.length === 0) return null;

            const blocks = [];
            if (categorization.summaries?.[category]) {
                blocks.push({
                    type: 'callout',
                    tone: 'info',
                    title: `${category} Highlights`,
                    text: categorization.summaries[category]
                });
            }

            items.forEach((item) => {
                blocks.push({
                    type: 'heading',
                    id: `item_${slugify(item.id || item.title || 'entry')}`,
                    level: 2,
                    text: item.title
                });
                const cleanExplanation = sanitizePageText(item.explanation);
                if (cleanExplanation) {
                    blocks.push({ type: 'paragraph', text: cleanExplanation });
                }
                if (item.impact) {
                    blocks.push({ type: 'callout', tone: 'success', title: 'Impact', text: sanitizePageText(item.impact) });
                }
                // Tags and commit refs are intentionally excluded from viewer-facing pages
            });

            return {
                id: `cat_${slugify(category)}`,
                chapter_id: 'release_notes',
                title: category,
                blocks
            };
        })
        .filter(Boolean);
};

const BatchContext = createContext();

export const useBatchSystem = () => {
  const context = useContext(BatchContext);
  if (!context) throw new Error('useBatchSystem must be used within a BatchProvider');
  return context;
};

export const BatchProvider = ({ children }) => {
  const [batches, setBatches] = useState(() => {
        const saved = localStorage.getItem('global_active_batches');
        return safeJsonParse(saved, []);
  });
  const [openBatchId, setOpenBatchId] = useState(null);
  const batchesRef = useRef([]);

  // Sync ref for access inside loops
  useEffect(() => {
    batchesRef.current = batches;
  }, [batches]);

  const openFullView = useCallback((id) => setOpenBatchId(id), []);
  const closeFullView = useCallback(() => setOpenBatchId(null), []);

  // Sync to localStorage
  useEffect(() => {
    localStorage.setItem('global_active_batches', JSON.stringify(batches));
  }, [batches]);

  const updateBatch = useCallback((id, updates) => {
    setBatches(prev => prev.map(b => b.id === id ? { ...b, ...updates } : b));
  }, []);

    const saveBatchCache = useCallback((batchId, partial) => {
        const cacheKey = `${CACHE_PREFIX}${batchId}`;
        const current = safeJsonParse(localStorage.getItem(cacheKey), {});
        const next = {
            ...current,
            ...partial,
            updatedAt: Date.now(),
        };
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
                    since: cache.since,
                    until: cache.until,
                    updatedAt: cache.updatedAt,
                    stage1Count: (cache.stage1Items || []).length,
                    hasStage2: !!cache.categorization,
                    hasFinalPayload: !!cache.finalPages,
                    generatedUpdateTitle: cache.generatedUpdateTitle || ''
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

  const pauseBatch = useCallback((id) => updateBatch(id, { paused: true }), [updateBatch]);
  const resumeBatch = useCallback((id) => updateBatch(id, { paused: false }), [updateBatch]);

  const updateStreamingData = useCallback((batchId, key, data) => {
    setBatches(prev => prev.map(b => {
      if (b.id === batchId) {
        return {
          ...b,
          streamingData: {
            ...(b.streamingData || {}),
            [key]: { ...(b.streamingData?.[key] || {}), ...data }
          }
        };
      }
      return b;
    }));
  }, []);

  const restartBatch = useCallback((id) => {
     setBatches(prev => prev.map(b => {
        if (b.id === id) {
            return {
                ...b,
                status: 'processing',
                progress: 0,
                currentStep: 'Restarting...',
                pages: [],
                streamingData: {},
                paused: false
            };
        }
        return b;
     }));
     const b = batchesRef.current.find(x => x.id === id);
     if (b) processBatch(id, b.config);
  }, [updateBatch]);

  const addLog = useCallback((id, type, content) => {
    const timestamp = new Date().toLocaleTimeString();
    setBatches(prev => prev.map(b => {
      if (b.id === id) {
        const newLogs = [...(b.logs || []), [timestamp, type, content]].slice(-100);
        return { ...b, logs: newLogs };
      }
      return b;
    }));
  }, []);

  const abortRefs = useRef({});

  const skipBatchItem = useCallback((id) => {
    if (abortRefs.current[id]) {
       abortRefs.current[id].abort();
       addLog(id, 'warning', 'Manual skip triggered. AI generation cancelled for current item.');
    } else {
       addLog(id, 'info', 'Skip ignored: No active AI process found for this item.');
    }
  }, [addLog]);

  const spawnBatch = useCallback(async (config) => {
    const id = `batch_${Date.now()}`;
        const resumeCache = config.resumeCacheId ? loadBatchCache(config.resumeCacheId) : null;
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
      streamingData: {},
      paused: false,
      config,
      startTime: Date.now()
    };
    setBatches(prev => [...prev, newBatch]);
    
    // Start the process in the background
        processBatch(id, { ...config, _resolvedResumeCache: resumeCache });
    return id;
    }, [loadBatchCache]);

  const removeBatch = useCallback((id) => {
    if (abortRefs.current[id]) abortRefs.current[id].abort();
    setBatches(prev => prev.filter(b => b.id !== id));
  }, []);

  const processDay = async (batchId, date, dayRepos, config) => {
    const { improveWithAI, typeFilters, systemPrompt } = config;
    const log = (type, msg) => addLog(batchId, type, msg);
    const parseCommitType = (s) => (s && typeof s === 'string') ? (s.match(/^(\w+)(\(.*\))?:/)?.[1].toLowerCase() || 'other') : 'other';

    const filteredDayData = {};
    let totalCommits = 0;
            
    for (const [repo, commits] of Object.entries(dayRepos)) {
        const filtered = commits.filter(c => {
            const type = parseCommitType(c.subject || c.message);
            return typeFilters.includes(type) || (typeFilters.includes('other') && !['feat', 'fix', 'refactor', 'perf', 'docs', 'chore', 'style', 'test'].includes(type));
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
        date: date, // Stable date reference
        chapter_id: "release_notes",
        title: date, // Default title
        keywords: ["update", "release", date],
        blocks: []
    };
    
    // Add default header block (can be replaced by AI title later)
    page.blocks.push({ type: "heading", id: `heading_${pageId}`, level: 1, text: `Updates for ${date}` });
            
        let refinedText = '';
    let aiAttempted = false;
        const commitRefs = [];
        const fallbackTags = new Set();

        Object.entries(filteredDayData).forEach(([repo, commits]) => {
            commits.forEach((c) => {
                commitRefs.push(`${repo}: ${c.subject || c.message || 'Untitled commit'}`);
                const parsedType = parseCommitType(c.subject || c.message || '');
                if (parsedType && parsedType !== 'other') fallbackTags.add(parsedType);
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
            commitRefs
        };

    if (improveWithAI) {
        aiAttempted = true;
        const stage1SystemMsg = systemPrompt || `You are a professional release notes writer for a Project Zomboid mod. You write concise, player-facing descriptions of changes. You NEVER reference git internals, commit hashes, or developer jargon. Your tone is clear, informative, and engaging.`;
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
${Object.entries(filteredDayData).map(([repo, commits]) => `${repo}:\n${commits.map(c => `  - ${c.subject || c.message}`).join('\n')}`).join('\n\n')}`;
        const llmConfig = loadLLMConfig();
        const provider = llmConfig.providers[llmConfig.activeProvider] || {};
        const ctrl = new AbortController();
        abortRefs.current[batchId] = ctrl;

        try {
            if (provider.is_browser_only) {
                if (!window.puter) throw new Error('Puter.js not available.');
                
                // Show "Thinking" state for browser-only mode since it doesn't stream
                setBatches(prev => prev.map(b => {
                    if (b.id === batchId) {
                        return {
                            ...b,
                            streamingData: {
                                ...(b.streamingData || {}),
                                [date]: { content: '', thinking: 'AI is analyzing commits via Puter...', status: 'streaming' }
                            }
                        };
                    }
                    return b;
                }));

                const response = await window.puter.ai.chat(`${stage1SystemMsg}\n\n${expansionPrompt}`);
                refinedText = response?.toString() || '';
                
                // Final update
                setBatches(prev => prev.map(b => {
                    if (b.id === batchId) {
                        return {
                            ...b,
                            streamingData: {
                                ...(b.streamingData || {}),
                                [date]: { content: refinedText, thinking: '', status: 'completed' }
                            }
                        };
                    }
                    return b;
                }));
            } else {
                const streamResponse = await llmChatStream({
                    base_url: provider.base_url,
                    api_key: provider.api_key,
                    model: provider.model,
                    messages: [
                        { role: 'system', content: stage1SystemMsg },
                        { role: 'user', content: expansionPrompt },
                    ],
                    thinking: true
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
                        setBatches(prev => prev.map(b => {
                            if (b.id === batchId) {
                                return {
                                    ...b,
                                    streamingData: {
                                        ...(b.streamingData || {}),
                                        [date]: { content: streamContent, thinking: streamThinking, status: force ? 'completed' : 'streaming' }
                                    }
                                };
                            }
                            return b;
                        }));
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
                        } catch (e) { }
                    }
                }
                if (buffer.trim()) {
                    try {
                        const part = JSON.parse(buffer);
                        if (part.content) streamContent += part.content;
                        if (part.thinking) streamThinking += part.thinking;
                    } catch (e) {}
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
                page.blocks.push({ type: "heading", id: `repo_${repo.toLowerCase()}_${pageId}`, level: 2, text: repo.trim() });
                page.blocks.push({ type: "bullet_list", items: commits.map(c => c.subject) });
            }
        }
    } else {
                structuredItem = parseStage1StructuredItem(refinedText, fallbackStructuredItem);
                if (structuredItem.parseWarnings.length > 0) {
                    log('warning', `   Stage 1 parse warnings for ${date}: ${structuredItem.parseWarnings.join(' ')}`);
                }

        const lines = refinedText.split('\n');
        
        // Extract Title: Look for [TITLE: ...] or a leading # Header
        let foundTitle = '';
        for (let i = 0; i < Math.min(lines.length, 5); i++) {
            const line = lines[i].trim();
            const tagMatch = line.match(/^\[TITLE:\s*(.*?)\]/i);
            const h1Match = line.match(/^#\s*(.*)/);
            if (tagMatch) {
                foundTitle = tagMatch[1].trim();
                lines.splice(i, 1);
                break;
            } else if (h1Match) {
                foundTitle = h1Match[1].trim();
                lines.splice(i, 1);
                break;
            }
        }

        if (foundTitle) {
            page.title = foundTitle;
            // Update the automatic heading block to match the thematic title
            const hBlock = page.blocks.find(b => b.type === 'heading' && b.level === 1);
            if (hBlock) hBlock.text = foundTitle;
        }

        let curBlocks = [];
        const flush = () => { if (curBlocks.length > 0) { page.blocks.push({ type: "bullet_list", items: curBlocks }); curBlocks = []; } };
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            const hMatch = trimmed.match(/^###\s*(.*)/) || trimmed.match(/^##\s*(.*)/);
            if (hMatch) { flush(); page.blocks.push({ type: "heading", id: `ai_h_${pageId}_${slugify(hMatch[1])}`, level: 2, text: hMatch[1].trim() }); continue; }
            const cMatch = trimmed.match(/^>\s*\[!(info|success|warning|danger)\]\s*(.*?)\s*\|\s*(.*)/i);
            if (cMatch) { flush(); page.blocks.push({ type: "callout", tone: cMatch[1].toLowerCase(), title: cMatch[2].trim(), text: cMatch[3] }); continue; }
            const iMatch = trimmed.match(/^!\[(.*?)\]\((.*?)\)/);
            if (iMatch) { flush(); page.blocks.push({ type: "image", caption: iMatch[1], path: iMatch[2] }); continue; }
            const bMatch = trimmed.match(/^[*-]\s*(.*)/);
            if (bMatch) { curBlocks.push(bMatch[1]); continue; }
            if (curBlocks.length > 0) curBlocks.push(trimmed);
            else page.blocks.push({ type: "paragraph", text: trimmed });
        }
        flush();
    }
    
    // Update pages in batch (preserving date order)
    setBatches(prev => prev.map(b => {
        if (b.id === batchId) {
            const otherPages = b.pages.filter(p => p.date !== date);
                        const otherItems = (b.stage1Items || []).filter((item) => item.date !== date);
                        const stage1Items = [...otherItems, structuredItem].sort((a, b) => b.date.localeCompare(a.date));
                        const pages = [...otherPages, page].sort((a,b) => b.date.localeCompare(a.date));
                        return { ...b, pages, stage1Items };
        }
        return b;
    }));

        const batchState = batchesRef.current.find((b) => b.id === batchId);
        if (batchState?.config?.cacheOutputs) {
            saveBatchCache(batchId, {
                module: batchState.module,
                since: batchState.config.since,
                until: batchState.config.until,
                pages: (batchState.pages || []).filter((p) => p.date !== date).concat([page]),
                stage1Items: (batchState.stage1Items || []).filter((item) => item.date !== date).concat([structuredItem]),
            });
        }
  };

  const retryDay = useCallback(async (id, date) => {
      const b = batchesRef.current.find(x => x.id === id);
      if (!b) return;
      if (abortRefs.current[id]) {
          abortRefs.current[id].abort();
          addLog(id, 'warning', `Active process aborted for ${date} to force restart.`);
      }
      const { config } = b;
      const historyRes = await getBatchedGitHistory(config.since, config.until, config.branch, config.module);
      const history = historyRes.data.history || {};
      const dayRepos = history[date];
      if (!dayRepos) return;
      addLog(id, 'system', `Force restarting day refinement for ${date}...`);
      await processDay(id, date, dayRepos, config);
  }, [addLog]);

  const consolidateBatch = async (batchId, customPrompt = null) => {
    const b = batchesRef.current.find(x => x.id === batchId);
    if (!b || (b.stage1Items || []).length === 0) return null;

    const log = (type, msg) => addLog(batchId, type, msg);
    log('system', 'Starting agentic consolidation pass...');
    updateBatch(batchId, { currentStep: 'Consolidating pages...' });

    const stage1TitlePayload = b.stage1Items.map((item) => ({
        id: item.id,
        date: item.date,
        title: item.title,
    }));

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

    updateStreamingData(batchId, "_consolidation", { status: 'streaming', thinking: '', content: '' });

    try {
        const llmConfig = loadLLMConfig();
        const provider = llmConfig.providers[llmConfig.activeProvider] || {};

        if (provider.is_browser_only) {
            if (!window.puter) throw new Error('Puter.js not available.');
            const response = await window.puter.ai.chat(finalPrompt);
            const streamContent = response?.toString() || '';

            updateStreamingData(batchId, "_consolidation", {
                content: streamContent,
                thinking: '',
                status: 'completed'
            });

            const categorization = parseStage2Categorization(streamContent, b.stage1Items || []);
            categorization.overallTitle = normalizeOverallTitle(categorization.overallTitle, categorization, b.stage1Items || []);
            const newPages = assembleCategoryPages(b.stage1Items || [], categorization);
            const workshopMetadata = generateSteamBBCode(categorization.overallTitle || 'Update Summary', categorization, newPages);

            updateBatch(batchId, {
                consolidatedPages: newPages,
                categorization,
                generatedUpdateTitle: categorization.overallTitle,
                finalPages: newPages,
                workshopMetadata,
                currentStep: 'Consolidation complete',
                consolidationError: null
            });

            if (b.config?.cacheOutputs) {
                saveBatchCache(batchId, {
                    module: b.module,
                    since: b.config.since,
                    until: b.config.until,
                    stage1Items: b.stage1Items,
                    categorization,
                    generatedUpdateTitle: categorization.overallTitle,
                    finalPages: newPages,
                    workshopMetadata,
                    pages: b.pages,
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
                { role: 'user', content: finalPrompt }
            ],
            thinking: !!llmConfig.thinking
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
                    updateStreamingData(batchId, "_consolidation", {
                        content: streamContent,
                        thinking: streamThinking,
                        status: 'streaming'
                    });
                } catch (e) { }
            }
        }

        const categorization = parseStage2Categorization(streamContent, b.stage1Items || []);
        categorization.overallTitle = normalizeOverallTitle(categorization.overallTitle, categorization, b.stage1Items || []);
        const newPages = assembleCategoryPages(b.stage1Items || [], categorization);
        const workshopMetadata = generateSteamBBCode(categorization.overallTitle || 'Update Summary', categorization, newPages);

        updateStreamingData(batchId, "_consolidation", { status: 'completed' });
        log('success', `Stage 2 complete. ${newPages.length} category pages assembled.`);

        updateBatch(batchId, {
            consolidatedPages: newPages,
            categorization,
            generatedUpdateTitle: categorization.overallTitle,
            finalPages: newPages,
            workshopMetadata,
            currentStep: 'Consolidation complete',
            consolidationError: null
        });

        if (b.config?.cacheOutputs) {
            saveBatchCache(batchId, {
                module: b.module,
                since: b.config.since,
                until: b.config.until,
                stage1Items: b.stage1Items,
                categorization,
                generatedUpdateTitle: categorization.overallTitle,
                finalPages: newPages,
                workshopMetadata,
                pages: b.pages,
            });
        }
        return { newPages, workshopMetadata, categorization };

    } catch (e) {
        log('error', `Consolidation failed: ${e.message}`);
        updateBatch(batchId, { consolidationError: e.message });
        updateStreamingData(batchId, "_consolidation", { status: 'error', error: e.message });
        return null;
    }
  };

  const processBatch = async (id, config) => {
    const { since, until, module, branch } = config;
    const log = (type, msg) => addLog(id, type, msg);
    const setStep = (step) => updateBatch(id, { currentStep: step });
    const setProg = (val) => updateBatch(id, { progress: val });

    try {
        log('system', `Starting background batch: ${since} -> ${until}`);

            if (config._resolvedResumeCache?.stage1Items?.length > 0) {
                updateBatch(id, {
                    stage1Items: config._resolvedResumeCache.stage1Items,
                    pages: config._resolvedResumeCache.pages || [],
                    currentStep: 'Loaded Stage 1 cache'
                });
            }
        
        setStep('Fetching donators...');
        let currentDonators = null;
        try {
            const res = await getDonatorsDefinition();
            currentDonators = res.data;
        } catch (e) {
            log('warning', 'Could not fetch donator data. Hall of Fame will be skipped.');
        }

        setStep('Fetching git history...');
        let history = config.history;
        if (!history) {
            const historyRes = await getBatchedGitHistory(since, until, branch, module);
            if (historyRes.status !== 200 || !historyRes.data.history) {
                 throw new Error(historyRes.data?.error || `Git history fetch failed for branch '${branch}'`);
            }
            history = historyRes.data.history;
        }
        updateBatch(id, { history });
        
        const skipStage1 = config.resumeFromStage === 2 && config._resolvedResumeCache?.stage1Items?.length > 0;
        const allDates = Object.keys(history).sort();
        const rangeDates = allDates.filter(d => d >= since && d <= until);
        const total = rangeDates.length;

        if (!skipStage1) {
          for (let i = 0; i < total; i++) {
              while (true) {
                  const currentBatch = batchesRef.current.find(b => b.id === id);
                  if (!currentBatch) return; 
                  if (!currentBatch.paused) break;
                  await new Promise(r => setTimeout(r, 500));
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

        updateBatch(id, { progress: 100 });
                let pages = [];
                if (config.resumeFromStage !== 3) {
                    const consolidationResult = await consolidateBatch(id, config.consolidationPrompt);
                    pages = [...(consolidationResult?.newPages || [])];
                } else {
                    const finalBatch = batchesRef.current.find(b => b.id === id);
                    pages = [...(finalBatch?.finalPages || finalBatch?.consolidatedPages || [])];
                }

                if (pages.length === 0) {
                    const finalBatch = batchesRef.current.find(b => b.id === id);
                    pages = [...(finalBatch?.finalPages || finalBatch?.consolidatedPages || [])];
                }

        if (pages.length === 0) {
            log('system', 'No updates found in selected range.');
            updateBatch(id, { status: 'idle', currentStep: 'No changes found' });
            return;
        }

           if (currentDonators) {
               pages.push({
                id: "hall_of_fame",
                chapter_id: "release_notes",
                title: currentDonators.page_title || "Hall of Fame",
                blocks: [{
                    type: "supporter_carousel",
                    title: currentDonators.block_title || "Hall of Fame",
                    supporters: currentDonators.supporters || []
                }]
            });
        }

                updateBatch(id, {
                    finalPages: pages,
                    status: 'refining_done',
                    currentStep: config.autoSaveAfterConsolidation ? 'Auto-saving assembled update...' : 'Stage 3 ready (commit when ready)'
                });

                if (config.autoSaveAfterConsolidation) {
                    await saveBatchVolume(id, { pages });
                    return;
                }

                log('success', 'Batch daily refinement complete. Stage 3 is ready for manual commit.');

    } catch (error) {
        log('error', `Batch Failed: ${error.message}`);
        updateBatch(id, { status: 'error', error: error.message, currentStep: 'Failed' });
    }
  };

    const saveBatchVolume = async (batchId, overrides = {}) => {
      const batch = batchesRef.current.find(b => b.id === batchId);
      if (!batch) return;

      try {
          const forceRecreate = overrides.forceRecreate || false;
          updateBatch(batchId, { currentStep: forceRecreate ? 'Force-recreating Lua files...' : 'Finalizing Save...', status: 'saving' });
          
          const { since, until, module } = batch.config;
          const pages = overrides.pages || batch.finalPages || batch.consolidatedPages || batch.pages;
          
          const capitals = module.replace(/[^A-Z]/g, '') || 'Upd';
          const volId = `${capitals}_Upd_${until.replace(/-/g, '_')}`;

          const cat = batch.categorization;
          const activeCats = STAGE2_CATEGORIES.filter(c => cat?.summaries?.[c]);
          const richDescription = activeCats.length > 0
              ? activeCats.map(c => `${c}: ${cat.summaries[c]}`).join(' | ')
              : `Consolidated updates from ${since} to ${until}`;
          const chapterDesc = cat?.summaries?.Features || cat?.summaries?.Fixes || '';

          const payload = {
              manual_id: volId,
              module: module,
              title: overrides.title || batch.generatedUpdateTitle || `Update: ${since.slice(5).replace(/-/g, '/')} - ${until.slice(5).replace(/-/g, '/')}`,
              description: richDescription,
              start_page_id: pages[0]?.id || "index",
              audiences: [module],
              is_whats_new: true,
              manual_type: "whats_new",
              source_folder: "WhatsNew", 
              chapters: [{ id: "release_notes", title: "Release Notes", description: chapterDesc }],
              pages
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
              saveBatchCache(batchId, {
                  module,
                  since,
                  until,
                  finalPages: pages,
                  generatedUpdateTitle: payload.title,
              });
          }
      } catch (error) {
          addLog(batchId, 'error', `Final Save Failed: ${error.message}`);
          updateBatch(batchId, { status: 'error', error: error.message, currentStep: 'Save ERROR' });
      }
  };

  const dismissBatch = useCallback((id) => updateBatch(id, { dismissed: true }), [updateBatch]);

  return (
        <BatchContext.Provider value={{ batches, spawnBatch, removeBatch, skipBatchItem, pauseBatch, resumeBatch, restartBatch, retryDay, openBatchId, openFullView, closeFullView, dismissBatch, consolidateBatch, saveBatchVolume, listBatchCaches, clearBatchCache }}>
      {children}
    </BatchContext.Provider>
  );
};
