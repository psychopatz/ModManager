# ModManager Manual Editor - Testing Guide

## Quick Start Verification

### 1. Test Draft Persistence (Most Important Fix)

**Test: Create and Persist Changes**
```
1. Open the Manual Editor
2. Click "New Manual" or select an existing one
3. Fill in the Title field with test text: "Test Manual Title"
4. Add a Chapter with ID "chapter1" and Title "Chapter One"
5. Take note of the changes - there should be a yellow dot on "Save Manual" button
6. DO NOT SAVE - Refresh the page (F5)
7. ✅ EXPECTED: Your title and chapter should still be there!
8. ✅ Check browser console: Ctrl+Shift+K → Application tab → localStorage
   - Look for keys like: manual_draft_manuals_manual_new
   - This is the per-manual scoped draft storage (NEW FEATURE)
```

**Test: Multiple Manuals**
```
1. Create Manual A with title "Manual A"
2. Create Manual B with title "Manual B"  
3. Switch to Manual A (click it in the list)
4. Modify Manual A's title to "Manual A Modified"
5. Switch to Manual B
6. ✅ EXPECTED: Manual B should still have its original title
7. Switch back to Manual A
8. ✅ EXPECTED: Manual A should still have "Manual A Modified"
9. Refresh page
10. ✅ EXPECTED: All changes still persist!
```

### 2. Test Callout Blocks (Support Content Fix)

**Test: Create and Save Callout**
```
1. Create or select a manual
2. Add a Page if needed
3. Click "Add Block" and select "Callout" from dropdown
4. Fill in:
   - Tone: Select "warn"
   - Title: "Important Notice"
   - Body: "This is a test callout"
5. Open browser console: Ctrl+Shift+K
6. Watch console as you edit - you should see logs like:
   "Callout title changed: Important Notice"
   "Callout text changed: This is a test callout"
7. ✅ Check localStorage shows the callout in draft_manuals_*
8. Click "Save Manual"
9. ✅ EXPECTED: Save should succeed
10. Refresh page and select manual
11. ✅ EXPECTED: Callout content should be exactly as you entered it
```

**Test: Edit Existing Callout**
```
1. Find a manual with a callout block
2. Click the page with the callout
3. Edit the callout title and text
4. Check console logs confirm changes
5. Switch to another manual (don't save)
6. ✅ EXPECTED: Callout draft changes should be preserved in localStorage
7. Click your manual again
8. ✅ EXPECTED: Callout changes should still be there
```

### 3. Test Save Button Feedback (UI/UX Fix)

**Test: Save Status Indicators**
```
1. Open a manual
2. Make a change (edit title, add text)
3. ✅ Watch "Save Manual" button - should show YELLOW DOT indicator
4. Hover over button - should show tooltip "Click to save your changes"
5. Click "Save Manual"
6. ✅ EXPECTED: Button shows spinner, text changes to "Saving Manual..."
7. ✅ After save completes: Green checkmark appears, tooltip shows "All changes saved"
8. Wait 4 seconds
9. ✅ EXPECTED: Success indicator disappears automatically
```

**Test: Error Handling**
```
1. Disconnect internet or block network request in DevTools
2. Make a change to a manual
3. Click "Save Manual"
4. ✅ EXPECTED: Button shows RED ERROR icon
5. Hover tooltip should say "Save failed - Click to retry"
6. Restore internet connection
7. Click button again
8. ✅ EXPECTED: Save succeeds, green checkmark shows
```

**Test: Save Button States**
```
State 1 - No Changes:
✅ Button is grayed out/disabled
✅ Tooltip: "No unsaved changes"

State 2 - Has Changes (Draft):
✅ Button shows yellow dot badge
✅ Tooltip: "Click to save your changes"
✅ Button is clickable

State 3 - Saving In Progress:
✅ Button shows spinner icon
✅ Text changes to "Saving Manual..."
✅ Button is disabled

State 4 - Save Successful:
✅ Green checkmark appears
✅ Tooltip: "All changes saved"
✅ Clears after 4 seconds

State 5 - Save Failed:
✅ Red error icon appears
✅ Tooltip: "Save failed - Click to retry"
✅ Stays visible until retry/success
```

### 4. Test Modular Code Organization

**Test: Component Isolation**
```
1. Open browser DevTools → Components tab (React DevTools)
2. Look for component tree structure
3. ✅ You should see:
   - ManualEditorPage (root)
   ├── ManualDetailsForm
   ├── ChaptersEditor
   ├── PagesEditor
   │  └── BlockEditor (multiple)
   ├── ManualPreview
   └── SaveStatusIndicator

4. Each component should be independently selectable and inspectable
```

**Test: Backward Compatibility**
```
1. The old import should still work:
   import ManualEditorPage from './components/ManualEditorPage'
2. ✅ Should work exactly the same as before
3. New modular imports also work:
   import { ManualDetailsForm } from './components/ManualEditor/ManualDetailsForm'
```

### 5. Test Block Types

**Test: All Block Types Save Properly**
```
1. Create a new page
2. Add each block type and fill with test content:

   HEADING: 
   - ID: section1
   - Level: 2
   - Text: "Test Heading"
   
   PARAGRAPH:
   - Text: "This is test paragraph content"
   
   BULLET_LIST:
   - Items: 
     • First item
     • Second item
     • Third item
   
   IMAGE:
   - Upload a test image or enter path
   - Caption: "Test Image"
   - Width: 250
   - Height: 150
   
   CALLOUT (Most Important):
   - Tone: info
   - Title: "Info Title"
   - Text: "Callout content here"

3. DO NOT SAVE - Refresh page
4. ✅ EXPECTED: All blocks should still be there with all values intact
5. Now click Save
6. ✅ EXPECTED: All blocks save successfully
7. Load manual again
8. ✅ EXPECTED: All blocks present with correct values
```

### 6. Test Draft Alerts

**Test: Unsaved Changes Warning**
```
1. Make changes to a manual (don't save)
2. ✅ EXPECTED: Orange/yellow alert appears at top:
   "You have unsaved changes. [Discard Draft]"
3. Click "Discard Draft"
4. ✅ EXPECTED: All changes are removed, alert disappears
5. Manual reverts to last saved state
```

**Test: Discard Draft Button in Toolbar**
```
1. Make changes to a manual
2. Click "Discard Draft" button in top toolbar
3. ✅ EXPECTED: Changes are removed
4. ✅ Expected alert shows: "Draft discarded."
```

## Browser Console (DevTools) Checks

**Open: Ctrl+Shift+K (Windows/Linux) or Cmd+Option+K (Mac)**

### Check localStorage
```
1. Click Application tab
2. Click Storage → localStorage
3. Look for entries like:
   - manual_draft_manuals_manual_1
   - manual_draft_manuals_dc_manual_new
   - manual_draft_updates_dt_update_2025_04_01
   
✅ EXPECTED: One entry per manual being edited
✅ Keys should follow pattern: manual_draft_{scope}_{manual_id}
```

### Check Console Logs
```
When editing callout blocks, you should see logs:
- "Callout title changed: [value]"
- "Callout text changed: [value]"

This helps debug if callouts aren't saving.
```

### Check for Errors
```
✅ EXPECTED: No errors in console
✅ No red X marks in console tab
✅ Warnings are okay, but errors should be investigated
```

## Performance Checks

**Test: Responsiveness**
```
1. Add many chapters (20+)
2. Add many pages (50+)
3. Add many blocks per page (30+)
✅ EXPECTED: Editor should still be responsive
✅ No lag when scrolling or editing
✅ Save still works quickly
```

## Common Issues to Check

### Issue: Changes not saving
**Solution**: 
- ✅ Check localStorage in DevTools
- ✅ Check browser console for errors
- ✅ Verify network requests complete
- ✅ Check if save button error state appears

### Issue: Callout not saving
**Solution**:
- ✅ Fill all three fields (tone, title, text)
- ✅ Check console logs confirm changes
- ✅ Try saving and check network request
- ✅ Check error in response

### Issue: Changes lost on refresh
**Solution**:
- ✅ Check localStorage is not disabled
- ✅ Check storage quota not exceeded
- ✅ Try in private/incognito window
- ✅ Check for storage permission issues

### Issue: Save button always disabled
**Solution**:
- ✅ Make a change first
- ✅ Wait a moment for state update
- ✅ Hard refresh page (Ctrl+F5)
- ✅ Check React DevTools for isDrafty prop

## Sign of Success ✅

All of these should work:
1. ✅ Make changes → they persist in localStorage per-manual
2. ✅ Callout blocks save all fields correctly
3. ✅ Save button shows clear status (yellow dot, spinner, green check)
4. ✅ Multiple manuals maintain independent drafts
5. ✅ Refresh page → changes still there
6. ✅ Save succeeds and syncs to backend
7. ✅ Code is organized into focused components
8. ✅ No monolithic file anymore

## Rollback Instructions

If anything goes wrong:
1. Old version backed up in git history
2. To revert: `git checkout HEAD~1 frontend/src/components/ManualEditorPage.jsx`
3. Old file: `ManualEditorPage.jsx` (was 1200+ lines)
4. New files automatically created in `ManualEditor/` subfolder
