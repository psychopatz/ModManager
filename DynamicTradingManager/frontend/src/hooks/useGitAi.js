import { useState, useEffect, useCallback } from 'react';

/**
 * useGitAi hook
 * Encapsulates git fetching, prompt management, and AI generation logic.
 */
export const useGitAi = ({
  storageKey = 'git_ai_assistant',
  defaultPrompt = 'Identify recent changes and summarize them in professional bullet points.',
}) => {
  const [systemPrompt, setSystemPrompt] = useState(() => {
    return localStorage.getItem(storageKey) || defaultPrompt;
  });

  const resetPrompt = useCallback(() => {
    setSystemPrompt(defaultPrompt);
    localStorage.setItem(storageKey, defaultPrompt);
  }, [defaultPrompt, storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, systemPrompt);
  }, [systemPrompt, storageKey]);

  const generateContent = async (context) => {
    if (!window.puter) {
      throw new Error('Puter.js not found. AI features unavailable.');
    }

    const { targetName, branch, commits, customInstructions } = context;
    
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

    const prompt = `Project Context: ${targetName || 'Manual'}\nBranch: ${branch}\n\nCommits:\n${commitSummary}\n\nRules:\n${systemPrompt}\n\n${customInstructions || ''}`;
    
    const response = await window.puter.ai.chat(prompt);
    return response?.message?.content?.trim() || '';
  };

  return {
    systemPrompt,
    setSystemPrompt,
    resetPrompt,
    generateContent,
  };
};
