import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getBatchedGitHistory, getDonatorsDefinition, createManualDefinition, llmChat, llmChatStream } from '../services/api';
import { loadLLMConfig } from '../utils/llmUtils';

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
    const slugify = (v) => String(v || '').trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '');
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
        chapter_id: "release_notes",
        title: date,
        keywords: ["update", "release", date],
        blocks: [{ type: "heading", id: `heading_${pageId}`, level: 1, text: `Updates for ${date}` }]
    };
            
    let refinedText = '';
    let aiAttempted = false;

    if (improveWithAI) {
        aiAttempted = true;
        const prompt = `${systemPrompt}\n\nCommits for ${date}:\n${JSON.stringify(filteredDayData, null, 2)}`;
        const llmConfig = loadLLMConfig();
        const provider = llmConfig.providers[llmConfig.activeProvider] || {};
        const ctrl = new AbortController();
        abortRefs.current[batchId] = ctrl;

        try {
            if (provider.is_browser_only) {
                if (!window.puter) throw new Error('Puter.js not available.');
                const response = await window.puter.ai.chat(prompt);
                refinedText = response?.toString() || '';
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
        let curBlocks = [];
        const flush = () => { if (curBlocks.length > 0) { page.blocks.push({ type: "bullet_list", items: curBlocks }); curBlocks = []; } };
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            const hMatch = trimmed.match(/^###\s*(.*)/);
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
    
    // Update pages in batch
    setBatches(prev => prev.map(b => {
        if (b.id === batchId) {
            const otherPages = b.pages.filter(p => p.title !== date);
            return { ...b, pages: [...otherPages, page].sort((a,b) => b.title.localeCompare(a.title)) };
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
        const historyRes = await getBatchedGitHistory(since, branch);
        const history = historyRes.data.history || {};
        
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

        setStep('Saving manual...');
        const capitals = module.replace(/[^A-Z]/g, '') || 'Upd';
        const volId = `${capitals}_Upd_${until.replace(/-/g, '_')}`;
        const payload = {
            manual_id: volId,
            module: module,
            title: `Update: ${since.slice(5).replace(/-/g, '/')} - ${until.slice(5).replace(/-/g, '/')}`,
            description: `Consolidated updates from ${since} to ${until}`,
            start_page_id: pages[0].id,
            audiences: [module],
            is_whats_new: true,
            manual_type: "whats_new",
            source_folder: "WhatsNew", 
            chapters: [{ id: "release_notes", title: "Release Notes" }],
            pages
        };

        await createManualDefinition(payload, 'updates', module);
        log('success', `VOLUME SAVED: ${volId} (${pages.length} pages)`);
        updateBatch(id, { status: 'success', currentStep: 'Completed' });

    } catch (error) {
        log('error', `Batch Failed: ${error.message}`);
        updateBatch(id, { status: 'error', error: error.message, currentStep: 'Failed' });
    }
  };

  return (
    <BatchContext.Provider value={{ batches, spawnBatch, removeBatch, skipBatchItem, pauseBatch, resumeBatch, restartBatch, retryDay, openBatchId, openFullView, closeFullView }}>
      {children}
    </BatchContext.Provider>
  );
};
