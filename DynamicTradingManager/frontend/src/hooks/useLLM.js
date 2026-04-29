import { useCallback } from 'react';
import { useLLMInternal } from '../context/LLMContext';
import { llmChat } from '../services/api';

/**
 * useLLM hook – provider-aware chat interface.
 */
export const useLLM = () => {
  const { config, setConfig } = useLLMInternal();

  const activeProvider = config.providers[config.activeProvider] || config.providers.puter;
  const isThinkingSupported = activeProvider.supports_thinking === true;

  /**
   * Send a chat completion with auto-routing.
   *
   * @param {string|Array} prompt – user prompt or array of messages [{role, content}]
   * @param {object} [opts] – { thinking, temperature, max_tokens, systemPrompt }
   * @returns {Promise<object|string>} – The assistant response (string for Puter, object for backend)
   */
  const sendChat = useCallback(async (prompt, opts = {}) => {
    const provider = config.providers[config.activeProvider] || config.providers.puter;

    // Puter AI: browser-side call
    if (provider.is_browser_only) {
      if (!window.puter) {
        throw new Error('Puter.js not found. Switch to a different LLM provider in Settings.');
      }
      // Puter AI chat usually expects a string
      const strPrompt = Array.isArray(prompt) ? prompt.map(m => m.content).join('\n') : prompt;
      const response = await window.puter.ai.chat(strPrompt);
      return response?.message?.content?.trim() || response?.toString() || '';
    }

    // Backend proxy call
    let messages = [];
    if (Array.isArray(prompt)) {
      messages = prompt;
    } else {
      if (opts.systemPrompt) {
        messages.push({ role: 'system', content: opts.systemPrompt });
      }
      messages.push({ role: 'user', content: prompt });
    }

    const payload = {
      base_url: provider.base_url,
      api_key: provider.api_key,
      model: provider.model,
      messages: messages.map(({ role, content }) => ({ role, content })),
      thinking: opts.thinking ?? config.thinking, // Use provided opt or global config
      temperature: opts.temperature ?? undefined,
      max_tokens: opts.max_tokens ?? undefined,
      reasoning_effort: opts.reasoningEffort ?? config.reasoningEffort,
    };

    const response = await llmChat(payload);
    return response.data;
  }, [config]);

  /**
   * Send a streaming chat completion.
   *
   * @param {string|Array} prompt – user prompt or array of messages
   * @param {object} [opts] – { onChunk, thinking, temperature, max_tokens }
   * @returns {Promise<object>} – The final accumulated response object
   */
  const streamChat = useCallback(async (prompt, opts = {}) => {
    const provider = config.providers[config.activeProvider] || config.providers.puter;

    // Puter AI: No native streaming support in easy-to-use API, so we simulate or use regular call
    if (provider.is_browser_only) {
      const result = await sendChat(prompt, opts);
      if (opts.onChunk) {
          // If it returned an object, use content, else result is string
          opts.onChunk({ content: typeof result === 'object' ? result.content : result });
      }
      return typeof result === 'object' ? result : { content: result };
    }

    // Backend proxy streaming
    let messages = [];
    if (Array.isArray(prompt)) {
      messages = prompt;
    } else {
      messages.push({ role: 'user', content: prompt });
    }

    const payload = {
      base_url: provider.base_url,
      api_key: provider.api_key,
      model: provider.model,
      messages: messages.map(({ role, content }) => ({ role, content })),
      thinking: opts.thinking ?? config.thinking,
      temperature: opts.temperature ?? undefined,
      max_tokens: opts.max_tokens ?? undefined,
      reasoning_effort: opts.reasoningEffort ?? config.reasoningEffort,
    };

    const stream = await import('../services/api').then(m => m.llmChatStream(payload));
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    
    let accumulated = { content: '', thinking: '', model: '' };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const part = JSON.parse(line);
          if (part.error) throw new Error(part.error);
          
          if (part.content) accumulated.content += part.content;
          if (part.thinking) accumulated.thinking += part.thinking;
          if (part.model) accumulated.model = part.model;

          if (opts.onChunk) {
            opts.onChunk({ 
              content: part.content || '', 
              thinking: part.thinking || '',
              model: part.model || accumulated.model
            });
          }
        } catch (e) {
          console.warn('Failed to parse stream chunk:', line, e);
        }
      }
    }

    return accumulated;
  }, [config, sendChat]);

  return {
    config,
    setConfig,
    activeProvider,
    isThinkingSupported,
    sendChat,
    streamChat,
  };
};
