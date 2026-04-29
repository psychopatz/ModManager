import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getBatchedGitHistory, getDonatorsDefinition, createManualDefinition } from '../services/api';

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

  const openFullView = useCallback((id) => setOpenBatchId(id), []);
  const closeFullView = useCallback(() => setOpenBatchId(null), []);

  // Sync to localStorage
  useEffect(() => {
    localStorage.setItem('global_active_batches', JSON.stringify(batches));
  }, [batches]);

  const updateBatch = useCallback((id, updates) => {
    setBatches(prev => prev.map(b => b.id === id ? { ...b, ...updates } : b));
  }, []);

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
      config,
      startTime: Date.now()
    };
    setBatches(prev => [...prev, newBatch]);
    
    // Start the process in the background
    processBatch(id, config);
    return id;
  }, []);

  const removeBatch = useCallback((id) => {
    setBatches(prev => prev.filter(b => b.id !== id));
  }, []);

  const processBatch = async (id, config) => {
    const { since, until, module, improveWithAI, typeFilters, branch, systemPrompt } = config;
    
    // Internal utils
    const log = (type, msg) => addLog(id, type, msg);
    const setStep = (step) => updateBatch(id, { currentStep: step });
    const setProg = (val) => updateBatch(id, { progress: val });
    const slugify = (v) => String(v || '').trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '');
    const parseCommitType = (s) => (s && typeof s === 'string') ? (s.match(/^(\w+)(\(.*\))?:/)?.[1].toLowerCase() || 'other') : 'other';

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
        const pages = [];

        for (let i = 0; i < total; i++) {
            const date = rangeDates[i];
            setStep(`Processing ${date}...`);
            
            const dayRepos = history[date];
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
            
            if (totalCommits === 0) {
                setProg(Math.round(((i + 1) / total) * 100));
                continue;
            }

            log('system', `-> Building Page for ${date} (${totalCommits} commits)`);
            const pageId = date.replace(/-/g, '_');
            const page = {
                id: pageId,
                chapter_id: "release_notes",
                title: date,
                keywords: ["update", "release", date],
                blocks: [{ type: "heading", id: `heading_${pageId}`, level: 1, text: `Updates for ${date}` }]
            };
            
            if (improveWithAI && window.puter) {
                const prompt = `${systemPrompt}\n\nCommits for ${date}:\n${JSON.stringify(filteredDayData, null, 2)}`;
                log('system', `   (Thinking... AI is refining ${totalCommits} commits)`);
                const response = await window.puter.ai.chat(prompt);
                const refinedText = response?.toString() || '';
                
                if (refinedText.trim() === '%ContextNotFound%') {
                    log('system', `   (Skipped ${date}: Trivial changes)`);
                    setProg(Math.round(((i + 1) / total) * 100));
                    continue;
                }

                // Log a snippet of the AI output
                const firstLine = refinedText.split('\n').find(l => l.trim().length > 0) || '';
                log('success', `   [AI] ${firstLine.slice(0, 50)}...`);

                const lines = refinedText.split('\n');
                let curBlocks = [];
                const flush = () => { if (curBlocks.length > 0) { page.blocks.push({ type: "bullet_list", items: curBlocks }); curBlocks = []; } };
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;
                    const hMatch = trimmed.match(/^###\s*(.*)/);
                    if (hMatch) { flush(); page.blocks.push({ type: "heading", id: `ai_h_${pageId}_${slugify(hMatch[1])}`, level: 2, text: hMatch[1].slice(0, 25) }); continue; }
                    const cMatch = trimmed.match(/^>\s*\[!(info|success|warning|danger)\]\s*(.*?)\s*\|\s*(.*)/i);
                    if (cMatch) { flush(); page.blocks.push({ type: "callout", tone: cMatch[1].toLowerCase(), title: cMatch[2].slice(0, 25), text: cMatch[3] }); continue; }
                    const iMatch = trimmed.match(/^!\[(.*?)\]\((.*?)\)/);
                    if (iMatch) { flush(); page.blocks.push({ type: "image", caption: iMatch[1], path: iMatch[2] }); continue; }
                    const bMatch = trimmed.match(/^[*-]\s*(.*)/);
                    if (bMatch) { curBlocks.push(bMatch[1]); continue; }
                    if (curBlocks.length > 0) curBlocks.push(trimmed);
                    else page.blocks.push({ type: "paragraph", text: trimmed });
                }
                flush();
            } else {
                for (const [repo, commits] of Object.entries(filteredDayData)) {
                    log('system', `   [${repo}]`);
                    commits.forEach(c => {
                        const type = parseCommitType(c.subject || c.message);
                        log(type, `    - ${c.subject}`);
                    });
                    page.blocks.push({ type: "heading", id: `repo_${repo.toLowerCase()}_${pageId}`, level: 2, text: repo.slice(0, 25) });
                    page.blocks.push({ type: "bullet_list", items: commits.map(c => c.subject) });
                }
            }
            
            pages.push(page);
            updateBatch(id, { pages: [...pages] });
            setProg(Math.round(((i + 1) / total) * 100));
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
            source_folder: "WhatsNew", // Ensure it's saved in WhatsNew for updates
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
    <BatchContext.Provider value={{ batches, spawnBatch, removeBatch, openBatchId, openFullView, closeFullView }}>
      {children}
    </BatchContext.Provider>
  );
};
