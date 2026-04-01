/**
 * ManualEditorPage - Re-exports the refactored modular component
 * 
 * This file maintains backward compatibility by re-exporting from the new modular structure.
 * The actual implementation is now in ./ManualEditor/ManualEditorPage.jsx with all the logic
 * split into focused, reusable components:
 * 
 * - ManualEditor/ManualEditorPage.jsx - Main coordinator component
 * - ManualEditor/ManualDetailsForm.jsx - Manual metadata editor
 * - ManualEditor/ChaptersEditor.jsx - Chapters management
 * - ManualEditor/PagesEditor.jsx - Pages management
 * - ManualEditor/BlockEditor.jsx - Individual block editing
 * - ManualEditor/ManualPreview.jsx - Live preview
 * - ManualEditor/SaveStatusIndicator.jsx - Save status feedback
 * - hooks/useDraftManagement.js - Draft persistence hook with scoped localStorage
 */

export { default } from './ManualEditor/ManualEditorPage';
