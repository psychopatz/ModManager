# Manual Editor Refactoring - Developer Migration Guide

## What Changed

### Before (Monolithic)
- **Single File**: `components/ManualEditorPage.jsx` (1200+ lines)
- **Everything Mixed**: UI, state management, API calls, data processing all in one component
- **Hard to Test**: Can't test individual features in isolation
- **Difficult to Maintain**: Bug is somewhere in ~1200 lines
- **Poor Reusability**: Can't use components elsewhere without copying code
- **localStorage Issue**: Single key caused draft data to overwrite between manuals

### After (Modular)
- **Multiple Components**: Each with single responsibility
- **Organized Structure**: Clear separation of concerns
- **Easy to Test**: Test each component independently
- **Simple Debugging**: Bug is likely in one focused file
- **Reusable**: Components can be imported anywhere
- **Fixed Storage**: Each manual gets its own scoped localStorage key

## File Migration

### Import Changes

**Old Way** (still works via re-export):
```javascript
import ManualEditorPage from './components/ManualEditorPage';
```

**New Way** (direct imports):
```javascript
import ManualEditorPage from './components/ManualEditor/ManualEditorPage';
import { ManualDetailsForm } from './components/ManualEditor/ManualDetailsForm';
import { useDraftManagement } from './hooks/useDraftManagement';
```

Both work! The old import still works because `ManualEditorPage.jsx` re-exports the default.

## Directory Structure

**Before:**
```
frontend/src/
├── components/
│   └── ManualEditorPage.jsx (1200 lines)
└── hooks/
    └── (none)
```

**After:**
```
frontend/src/
├── components/
│   ├── ManualEditorPage.jsx (re-export, 20 lines)
│   └── ManualEditor/
│       ├── ManualEditorPage.jsx (600 lines - coordinator)
│       ├── ManualDetailsForm.jsx (120 lines)
│       ├── ChaptersEditor.jsx (100 lines)
│       ├── PagesEditor.jsx (220 lines)
│       ├── BlockEditor.jsx (180 lines)
│       ├── ManualPreview.jsx (150 lines)
│       └── SaveStatusIndicator.jsx (90 lines)
├── hooks/
│   └── useDraftManagement.js (70 lines)
└── services/
    └── api.js (unchanged)
```

## Component Responsibilities

### ManualEditorPage (Coordinator)
**What it does:**
- Manages overall editor state
- Handles manual loading from backend
- Orchestrates save/delete operations
- Coordinates between all sub-components
- Manages image uploads

**When to edit:**
- Adding new API endpoints
- Changing save/load flow
- Adding new editor scope types
- Changing overall layout

### ManualDetailsForm
**What it does:**
- Renders form for manual metadata
- Handles ID, Title, Description editing
- Manages Module/Audience selection
- Handles auto-open and version fields

**When to edit:**
- Changing manual metadata fields
- Adding new manual-level settings
- Modifying field validation or formatting

### ChaptersEditor
**What it does:**
- Lists all chapters
- Handles add/edit/delete of chapters
- Manages chapter reordering
- Ensures IDs are slugified

**When to edit:**
- Changing chapter fields
- Adding chapter-level features
- Modifying move/order logic

### PagesEditor
**What it does:**
- Lists and selects pages
- Provides page metadata editing (ID, Title)
- Manages chapter assignment
- Handles keyword entry
- Delegates block editing to BlockEditor

**When to edit:**
- Changing page fields
- Adding page-level features
- Changing block interaction

### BlockEditor
**What it does:**
- Renders editor for single block
- Handles all 5 block types
- Type-specific editing UI
- Special logging for callout debugging

**When to edit:**
- Fixing block type issues
- Adding new block types
- Changing block field behavior

### ManualPreview
**What it does:**
- Shows live preview of selected page
- Renders all block types with styling
- Handles image URL resolution
- Updates in real-time

**When to edit:**
- Changing preview styling
- Fixing image display issues
- Adding preview features
- Changing block rendering

### SaveStatusIndicator
**What it does:**
- Shows save state (pending/saving/success/error)
- Visual feedback with icons and colors
- Tooltips for each state
- Auto-clears success after 4 seconds

**When to edit:**
- Changing save feedback messages
- Modifying state colors/icons
- Changing timeout behavior
- Adding more save states

### useDraftManagement Hook
**What it does:**
- Manages draft state with localStorage
- Scopes storage per manual and editor scope
- Auto-saves on every change
- Tracks unsaved state with isDrafty flag
- Provides discard/clear methods

**When to edit:**
- Changing storage key format
- Modifying save frequency
- Handling storage errors
- Adding new draft operations

## Data Flow

### Creating a Manual
```
User clicks "New Manual"
         ↓
ManualEditorPage.createManual()
         ↓
Sets selectedManualKey = NEW_MANUAL_KEY
Sets baseManual = createEmptyManual()
         ↓
useDraftManagement sets draft from baseManual
Saves to localStorage with key: manual_draft_{scope}_new
         ↓
UI updates showing empty forms
```

### Editing Content
```
User types in field → componentReceivesChange
         ↓
updateDraft() called
         ↓
useDraftManagement detects change
         ↓
Saves to localStorage automatically
         ↓
isDrafty flag becomes true
         ↓
SaveStatusIndicator shows yellow indicator
```

### Saving to Backend
```
User clicks Save
         ↓
ManualEditorPage.saveCurrentManual()
         ↓
Validates manual_id
         ↓
Formats payload with all data
         ↓
API call: createManualDefinition() or saveManualDefinition()
         ↓
SaveStatusIndicator shows spinner
         ↓
On success:
  - Green checkmark shows
  - Success closes after 4s
  - localStorage draft cleared with clearDraft()
  - Page reloaded to sync data
         ↓
On error:
  - Red error icon shows
  - Error persists until retry
  - localStorage draft saved for recovery
```

## Debugging Guide

### Save Button Not Showing Yellow Indicator
**Check:**
1. Is `isDrafty` flag true? (React DevTools)
2. Is localStorage working? (DevTools > Application > localStorage)
3. Did `useDraftManagement` initialize? (Browser console)

### Callout Not Saving
**Check:**
1. Open console (F12) and look for "Callout title changed" logs
2. Check localStorage has the callout data
3. Check callout block has all three fields filled
4. Network request shows all data in payload

### Draft Lost After Refresh
**Check:**
1. Is localStorage enabled in browser?
2. Check storage quota: `navigator.storage.estimate()`
3. Check key format in localStorage
4. Any errors in browser console?

### Changes Not Persisting Between Manuals
**Check:**
1. Each manual should have its own key
2. Old code used single key - new code uses per-manual key
3. Verify keys like: `manual_draft_manuals_manual_1`
4. Different manuals should have different keys

## Performance Tips

### For Large Manuals
- Use `React.memo()` on BlockEditor components
- Implement virtual scrolling for long page/chapter lists
- Lazy load images in preview

### For Many Drafts
- Consider archiving old drafts
- Clean up localStorage periodically
- Monitor storage quota

## Testing Strategy

### Unit Testing (Next Step)
Each component should be testable:
```javascript
// Example: BlockEditor.test.jsx
import { BlockEditor } from './BlockEditor';

describe('BlockEditor', () => {
  it('should save callout tone changes', () => {
    // Test setup
    // Verify onChange called with correct value
  });
});
```

### Integration Testing
Test data flow between components:
```javascript
// Test saving a full manual with blocks
```

### E2E Testing
Test complete user workflows using Cypress/Playwright

## Adding New Features

### Add New Block Type
1. Update `createBlock()` in ManualEditorPage
2. Add case in BlockEditor.jsx render
3. Add case in ManualPreview.jsx render
4. Test saves and loads correctly

### Add New Manual Field
1. Update `createEmptyManual()` shape
2. Add field to ManualDetailsForm
3. Include in save payload
4. Update API if needed

### Add New Editor Scope
1. Add to `editorScope` prop type
2. Update `getDefaultSourceFolder()`
3. Test localStorage keys are scoped correctly
4. Update API endpoints if needed

## Common Patterns

### Updating Draft
```javascript
// Instead of direct mutation, use updater function
updateDraft((next) => {
  next.manual_id = value;
  next.chapters[0].id = id;
});
```

### Slugifying IDs
```javascript
// Always slugify when IDs are set/changed
const slugify = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');
```

### Cloning Data
```javascript
// Always clone before modifying to avoid mutations
const cloneManual = (manual) => JSON.parse(JSON.stringify(manual));
```

## Configuration

### Storage Key Format
```
manual_draft_{editorScope}_{manualId}

Examples:
- manual_draft_manuals_manual_1
- manual_draft_updates_dt_update_2025_04_01
- manual_draft_manuals_dc_manual_new
```

### Save Status Auto-Clear
```
Success indicator shows for 4 seconds:
setTimeout(() => setLastSaveStatus(null), 4000);
```

### Block Types
```javascript
const blockTypeOptions = [
  { value: 'heading', label: 'Heading' },
  { value: 'paragraph', label: 'Paragraph' },
  { value: 'bullet_list', label: 'Bullet List' },
  { value: 'image', label: 'Image' },
  { value: 'callout', label: 'Callout' },
];
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import not found | Check relative paths, ensure file exists |
| localStorage not working | Check browser allows storage, quota available |
| Component not rendering | Check export statement, import path |
| Unsaved changes lost | Verify useDraftManagement hook is attached |
| Callout not saving | Check console logs, verify async await |
| Save button disabled | Check isDrafty flag, verify draft has changes |

## Future Improvements

Potential enhancements for next iterations:

1. **Error Boundaries** - Wrap components to handle crashes gracefully
2. **Undo/Redo** - Implement history management
3. **Collaborative Editing** - Add real-time sync
4. **Keyboard Shortcuts** - Add Ctrl+S to save
5. **Block Templates** - Pre-built block configurations
6. **Version History** - Track manual changes over time
7. **Auto-save** - Periodic saving without user action
8. **Validation** - Pre-save validation of all fields
9. **Search** - Find text within manuals
10. **Bulk Operations** - Edit multiple manuals at once
