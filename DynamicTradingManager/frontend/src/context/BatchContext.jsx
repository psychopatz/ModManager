import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getBatchedGitHistory, getDonatorsDefinition, createManualDefinition, llmChat, llmChatStream } from '../services/api';
import { loadLLMConfig } from '../utils/llmUtils';

const slugify = (str) => str.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');

const BatchContext = createContext();

export const useBatchSystem = () => {
  const context = useContext(BatchContext);
  if (!context) throw new Error('useBatchSystem must be used within a BatchProvider');
  return context;
};

export const BatchProvider = ({ children }) => {
  const [batches, setBatches] = useState(() => {
    const saved = localStorage.getItem('global_active_batches');
    return saved ? JSON.parse(saved) : [];
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
    const newBatch = {
      id,
      modName: config.moduleLabel || config.module,
      module: config.module,
      status: 'processing',
      progress: 0,
      currentStep: 'Starting...',
      logs: [],
      pages: [],
      streamingData: {},
      paused: false,
      config,
      startTime: Date.now()
    };
    setBatches(prev => [...prev, newBatch]);
    
    // Start the process in the background
    processBatch(id, config);
    return id;
  }, []);

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

    if (improveWithAI) {
        aiAttempted = true;
        const prompt = `${systemPrompt}\n\nIMPORTANT: Start your response with [TITLE: Your Thematic Title] on the very first line.\n\nCommits for ${date}:\n${JSON.stringify(filteredDayData, null, 2)}`;
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

                const response = await window.puter.ai.chat(prompt);
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
                        { role: 'system', content: systemPrompt },
                        { role: 'user', content: `Commits for ${date}:\n${JSON.stringify(filteredDayData, null, 2)}` },
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
            return { ...b, pages: [...otherPages, page].sort((a,b) => b.date.localeCompare(a.date)) };
        }
        return b;
    }));
  };

  const retryDay = useCallback(async (id, date) => {
      const b = batchesRef.current.find(x => x.id === id);
      if (!b) return;

      // Abort active if any
      if (abortRefs.current[id]) {
          abortRefs.current[id].abort();
          addLog(id, 'warning', `Active process aborted for ${date} to force restart.`);
      }
      
      const { config } = b;
      const historyRes = await getBatchedGitHistory(config.since, config.branch);
      const history = historyRes.data.history || {};
      const dayRepos = history[date];
      if (!dayRepos) return;

      addLog(id, 'system', `Force restarting day refinement for ${date}...`);
      await processDay(id, date, dayRepos, config);
  }, [addLog]);

  const consolidateBatch = async (batchId, customPrompt = null) => {
    const b = batchesRef.current.find(x => x.id === batchId);
    if (!b || b.pages.length === 0) return;

    const log = (type, msg) => addLog(batchId, type, msg);
    log('system', 'Starting agentic consolidation pass...');
    updateBatch(batchId, { currentStep: 'Consolidating pages...' });

    const pageSummaries = b.pages.map(p => ({
        id: p.id,
        title: p.title,
        summary: p.blocks.map(bl => bl.text || bl.items?.join(', ') || '').join(' ').slice(0, 500)
    }));

    const defaultConsolidationPrompt = `You are a professional release notes editor. Below is a list of update pages generated from git history.
Some pages might overlap in theme (e.g., several days of "UI Improvements"). 
Your goal: Group these into 3-5 high-level thematic pages.
Output your decision as a JSON object: 
{
  "pages": [
    { "title": "New Thematic Title", "source_page_ids": ["page_id_1", "page_id_2"] }
  ],
  "workshop_bbcode": "[B]Steam Workshop BBCode Summary Here[/B]"
}

Input:
${JSON.stringify(pageSummaries, null, 2)}`;

    const finalPrompt = customPrompt || defaultConsolidationPrompt;

    updateStreamingData(batchId, "_consolidation", { status: 'streaming', thinking: '', content: '' });

    try {
        const stream = await llmChatStream({
            messages: [{ role: 'system', content: 'You are a JSON-only response agent.' }, { role: 'user', content: finalPrompt }]
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

        let decision;
        try {
            const jsonText = streamContent.replace(/```json|```/g, '').trim();
            decision = JSON.parse(jsonText);
        } catch (e) {
            log('error', `Consolidation response was not valid JSON: ${e.message}`);
            updateBatch(batchId, { 
                status: 'error', 
                error: `Consolidation failed: AI response was not valid JSON. You can retry.`, 
                currentStep: 'Consolidation ERROR' 
            });
            return;
        }

        updateStreamingData(batchId, "_consolidation", { status: 'completed' });

        const newPages = decision.pages.map((group, idx) => {
            const sourcePages = b.pages.filter(p => group.source_page_ids.includes(p.id));
            const blocks = [];
            sourcePages.forEach(p => {
                blocks.push({ type: 'heading', level: 2, text: p.title });
                blocks.push(...p.blocks.filter(bl => bl.level !== 1)); // Skip redundant H1s
            });

            return {
                id: `consolidated_${idx}`,
                chapter_id: "release_notes",
                title: group.title,
                blocks
            };
        });

        updateBatch(batchId, { 
            consolidatedPages: newPages, 
            workshopMetadata: decision.workshop_bbcode,
            currentStep: 'Consolidation complete',
            consolidationError: null
        });
        updateStreamingData(batchId, "_consolidation", { status: 'completed' }); // Ensure it marks as done
        log('success', 'Batch consolidated into thematic pages!');

    } catch (e) {
        log('error', `Consolidation failed: ${e.message}`);
        updateBatch(batchId, { consolidationError: e.message });
        updateStreamingData(batchId, "_consolidation", { status: 'error', error: e.message });
    }
  };

  const processBatch = async (id, config) => {
    const { since, until, module, branch } = config;
    const log = (type, msg) => addLog(id, type, msg);
    const setStep = (step) => updateBatch(id, { currentStep: step });
    const setProg = (val) => updateBatch(id, { progress: val });

    try {
        log('system', `Starting background batch: ${since} -> ${until}`);
        
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
        
        const allDates = Object.keys(history).sort();
        const rangeDates = allDates.filter(d => d >= since && d <= until);
        const total = rangeDates.length;

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

        updateBatch(id, { progress: 100 });
        await consolidateBatch(id);

        const finalBatch = batchesRef.current.find(b => b.id === id);
        const pages = [...(finalBatch?.pages || [])];

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

        log('success', 'Batch daily refinement complete. You can now run thematic consolidation.');
        updateBatch(id, { status: 'refining_done', currentStep: 'Daily Refinement Complete' });

    } catch (error) {
        log('error', `Batch Failed: ${error.message}`);
        updateBatch(id, { status: 'error', error: error.message, currentStep: 'Failed' });
    }
  };

  const saveBatchVolume = async (batchId) => {
      const batch = batchesRef.current.find(b => b.id === batchId);
      if (!batch) return;

      try {
          updateBatch(batchId, { currentStep: 'Finalizing Save...', status: 'saving' });
          
          const { since, until, module } = batch.config;
          const pages = batch.consolidatedPages || batch.pages; // Use consolidated if available
          
          const capitals = module.replace(/[^A-Z]/g, '') || 'Upd';
          const volId = `${capitals}_Upd_${until.replace(/-/g, '_')}`;
          
          const payload = {
              manual_id: volId,
              module: module,
              title: `Update: ${since.slice(5).replace(/-/g, '/')} - ${until.slice(5).replace(/-/g, '/')}`,
              description: `Consolidated updates from ${since} to ${until}`,
              start_page_id: pages[0]?.id || "index",
              audiences: [module],
              is_whats_new: true,
              manual_type: "whats_new",
              source_folder: "WhatsNew", 
              chapters: [{ id: "release_notes", title: "Release Notes" }],
              pages
          };

          await createManualDefinition(payload, 'updates', module);
          addLog(batchId, 'success', `VOLUME SAVED: ${volId} (${pages.length} pages)`);
          updateBatch(batchId, { status: 'success', currentStep: 'Completed' });
      } catch (error) {
          addLog(batchId, 'error', `Final Save Failed: ${error.message}`);
          updateBatch(batchId, { status: 'error', error: error.message, currentStep: 'Save ERROR' });
      }
  };

  const dismissBatch = useCallback((id) => updateBatch(id, { dismissed: true }), [updateBatch]);

  return (
    <BatchContext.Provider value={{ batches, spawnBatch, removeBatch, skipBatchItem, pauseBatch, resumeBatch, restartBatch, retryDay, openBatchId, openFullView, closeFullView, dismissBatch, consolidateBatch, saveBatchVolume }}>
      {children}
    </BatchContext.Provider>
  );
};
