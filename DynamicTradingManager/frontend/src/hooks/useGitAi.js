import { useState, useEffect, useCallback } from 'react';
import { useLLM } from './useLLM';

/**
 * useGitAi hook
 * Encapsulates git fetching, prompt management, and AI generation logic.
 * Now routes through the LLM provider system instead of calling Puter directly.
 */
export const useGitAi = ({
  storageKey = 'git_ai_assistant',
  defaultPrompt = 'Identify recent changes and summarize them in professional bullet points. Do NOT use emojis; prefer plain bullet markers (-) and concise phrasing. Avoid pipe separators.',
}) => {
  const [systemPrompt, setSystemPrompt] = useState(() => {
    return localStorage.getItem(storageKey) || defaultPrompt;
  });

  const { sendChat } = useLLM();

  const resetPrompt = useCallback(() => {
    setSystemPrompt(defaultPrompt);
    localStorage.setItem(storageKey, defaultPrompt);
  }, [defaultPrompt, storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, systemPrompt);
  }, [systemPrompt, storageKey]);

  const generateContent = async (context) => {
    const { targetName, branch, commits, customInstructions, subMods = [] } = context;
    
    let commitSummary = '';
    if (Array.isArray(commits)) {
        // Single project list
        commitSummary = commits.map(c => `- ${c.message}${c.body ? `\n  ${c.body.split('\n')[0]}` : ''}`).join('\n');
    } else {
        // Suite-wide object: { RepoName: [commits] }
        commitSummary = Object.entries(commits).map(([repo, list]) => {
            return `[${repo}]\n${list.map(c => `- ${c.message}`).join('\n')}`;
        }).join('\n\n');
    }

    let prompt = `Project Context: ${targetName || 'Manual'}\nBranch: ${branch}\n\n`;
    if (subMods?.length > 0) {
        prompt += `Detected Sub-mods: ${subMods.map(m => `"${m.id}" (${m.name})`).join(', ')}\n`;
        prompt += `Please include "module": "MOD_ID" in the root of your JSON output if you can identify which mod these changes belong to.\n\n`;
    }
    prompt += `Commits:\n${commitSummary}\n\nRules:\n${systemPrompt}\n\n${customInstructions || ''}`;
    
    const result = await sendChat(prompt, { systemPrompt });
    
    // sendChat returns { content, thinking, model } if backend, or string if puter.
    // We normalize it here.
    if (typeof result === 'string') {
        return { content: result, thinking: null };
    }
    return {
        content: result.content || '',
        thinking: result.thinking || null
    };
  };

  return {
    systemPrompt,
    setSystemPrompt,
    resetPrompt,
    generateContent,
  };
};
