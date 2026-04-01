import { useEffect, useMemo, useRef, useState } from 'react';

/**
 * Custom hook for managing manual drafts with localStorage scoped per manual and editor scope
 */
export const useDraftManagement = (editorScope, initialDraft) => {
  const [draft, setDraftState] = useState(initialDraft);
  const [isDrafty, setIsDrafty] = useState(false);
  const skipPersistRef = useRef(true);

  const draftKey = useMemo(
    () => `manual_draft_${editorScope}_${initialDraft?.manual_id || 'new'}`,
    [editorScope, initialDraft?.manual_id],
  );

  // Rehydrate draft when selected manual/scope changes.
  useEffect(() => {
    skipPersistRef.current = true;

    // Load from localStorage if available
    try {
      const saved = localStorage.getItem(draftKey);
      if (saved) {
        setDraftState(JSON.parse(saved));
        setIsDrafty(true);
      } else {
        setDraftState(initialDraft);
        setIsDrafty(false);
      }
    } catch (e) {
      console.error('Failed to load draft from localStorage', e);
      setDraftState(initialDraft);
      setIsDrafty(false);
    }
  }, [draftKey, initialDraft]);

  // Save draft to localStorage whenever it changes
  useEffect(() => {
    if (!draftKey) return;
    if (skipPersistRef.current) {
      skipPersistRef.current = false;
      return;
    }

    try {
      localStorage.setItem(draftKey, JSON.stringify(draft));
      setIsDrafty(true);
    } catch (e) {
      console.error('Failed to save draft to localStorage', e);
    }
  }, [draft, draftKey]);

  const setDraft = (updater) => {
    setDraftState((current) => {
      if (typeof updater === 'function') {
        return updater(current);
      }
      return updater;
    });
  };

  const discardDraft = () => {
    if (draftKey) {
      localStorage.removeItem(draftKey);
    }
    setDraftState(initialDraft);
    setIsDrafty(false);
  };

  const clearDraft = () => {
    if (draftKey) {
      localStorage.removeItem(draftKey);
    }
    setIsDrafty(false);
  };

  return {
    draft,
    setDraft,
    discardDraft,
    clearDraft,
    isDrafty,
    draftKey,
  };
};
