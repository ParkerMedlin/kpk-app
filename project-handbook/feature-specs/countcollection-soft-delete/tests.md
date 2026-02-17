# Count Collection Soft Delete – Test Suite

**URLs**:
- Active Collections: `http://localhost:8000/core/display-count-collection-links/`
- Hidden Collections: `http://localhost:8000/core/hidden-count-collection-links/`
- Count List: `http://localhost:8000/core/count-list/display/?listId={id}&recordType={type}`
- Count Status Report: `http://localhost:8000/core/count-status/`

**Prerequisites**: At least 2 active (non-hidden) count collections should exist before starting. Log in as a staff user unless a test says otherwise.

---

## 1. Access Control

### Hidden Collections Page (`/core/hidden-count-collection-links/`)

- [x] Page loads for staff user
- [x] Page redirects to login for non-staff user
- [x] Page redirects to login for anonymous (logged out) user

### Active Collections Page – Staff Elements

- [x] Staff user sees the hide button (eye-slash icon) on each collection row
- [x] Non-staff user does NOT see the hide button
- [x] Staff user sees "View Hidden Collections" link/button on the page
- [x] Non-staff user does NOT see "View Hidden Collections" link

### Count List – Read-Only for Hidden Collections

- [x] Staff user can view a hidden collection's count list via the hidden collections page link
- [x] Non-staff user cannot navigate to a hidden collection (it doesn't appear in the active list)

---

## 2. Hide Action – Active Collections Page

### Happy Path

- [x] Click the eye-slash hide button on a collection → collection row disappears from the table
- [x] After hiding, refresh the page → hidden collection is NOT in the list
- [x] After hiding, the collection's `is_hidden` field is `True` in the database (check Django admin or shell)
- [x] The count records (BlendCountRecord / BlendComponentCountRecord) associated with the hidden collection still exist in the database (not deleted)

### UI Details

- [x] Hide button icon is `fa-eye-slash` (not the old trash icon `fa-trash-alt`)
- [x] Hide button style is `btn-outline-secondary` (not the old `btn-outline-danger`)
- [x] Hide button has class `hideCountLinkButton` (not the old `deleteCountLinkButton`)

---

## 3. Hide Action – Real-Time WebSocket Broadcast

### Setup: Open the active collections page in two separate browser tabs (both as staff)

- [x] Hide a collection in Tab A → the row disappears in Tab A
- [x] The same row also disappears in Tab B without refreshing
- [x] Both tabs maintain their WebSocket connection (green "Connected" indicator stays, if visible)

---

## 4. Active User Soft Transition (Count List Page)

### Setup: Open a count list in Tab A. Open the active collections page in Tab B (both as staff).

- [x] In Tab B, hide the collection that Tab A has open → Tab A shows a yellow warning banner: "This count list has been archived."
- [x] The banner is dismissible (click the X to close it)
- [x] After the banner appears, the user in Tab A can still enter count values (click "Enter >" button, type quantities)
- [x] After the banner appears, the user in Tab A can still check/uncheck the "Counted" checkbox
- [x] After the banner appears, the user in Tab A can still type in comment textareas
- [x] After the banner appears, the user in Tab A can still change the location dropdown
- [x] The WebSocket connection in Tab A stays connected (no disconnect, no redirect)
- [x] When the user in Tab A navigates away (clicks "Return to Count Links Page"), the hidden collection is no longer in the active list

---

## 5. Count List – Read-Only Mode (Viewing Hidden Collection)

### Setup: Hide a collection, then navigate to it from the hidden collections page.

- [x] The yellow archived banner ("This count list has been archived.") appears at the top
- [x] "Enter >" buttons are disabled (cannot open the container entry modal)
- [x] Comment textareas are `readonly`
- [x] Location dropdowns are disabled
- [x] "Counted" checkboxes are disabled
- [x] Qty refresh buttons are hidden
- [x] The "Add Item" button row is hidden (not visible at all)
- [x] Discard button cells are hidden (not visible at all)
- [x] The discard column header is hidden
- [x] Count data is still visible (item codes, descriptions, quantities, dates)

---

## 6. Hidden Collections Page – Display

### Setup: Hide at least 2 collections first.

- [x] Page title is "Hidden Count Collections"
- [x] "Back to Active Collections" button links to `/core/display-count-collection-links/`
- [x] Table shows all hidden collections
- [x] Each row shows: collection name, created date, restore button
- [x] Collection name is a clickable link
- [x] Clicking a collection name navigates to the count list page for that collection
- [x] Created date is formatted as `mm/dd/yyyy`
- [x] Restore button uses the `fa-rotate-left` icon with `btn-outline-success` style

### Empty State

- [ ] When no collections are hidden, the page shows "No hidden count collections." message

---

## 7. Restore Action – Hidden Collections Page

### Happy Path

- [ ] Click the restore button on a hidden collection → the row disappears from the hidden table
- [ ] After restoring, navigate to the active collections page → the restored collection appears in the active list
- [ ] After restoring, the collection's `is_hidden` field is `False` in the database
- [ ] The restored collection's name and count data are intact (nothing lost)

### Restore to Active Page – Real-Time

#### Setup: Open hidden collections page in Tab A, active collections page in Tab B.

- [ ] Restore a collection in Tab A → the row disappears from Tab A's hidden table
- [ ] Tab B's active collections table updates in real-time — the restored collection appears without refresh
- [ ] The restored collection row on Tab B has a working hide button and clickable link

### Last Item Restored

- [ ] Restore the last hidden collection → the table is now empty and "No hidden count collections." message appears

---

## 8. Hidden Collections Page – Real-Time Updates

### Setup: Open the hidden collections page in Tab A. Open the active collections page in Tab B. Both as staff.

- [ ] In Tab B, hide a collection → Tab A's hidden table gains a new row in real-time (without refreshing)
- [ ] The newly added row on Tab A has a working restore button
- [ ] The newly added row on Tab A has a clickable collection name link

---

## 9. Count Status Report

### Setup: Ensure at least one item has its latest count record in a hidden collection and at least one in an active collection.

- [ ] Navigate to `http://localhost:8000/core/count-status/`
- [ ] Items whose latest count is from a hidden collection show an eye-slash icon (`fa-eye-slash`) next to the item code
- [ ] The icon has a tooltip: "From archived collection"
- [ ] Items whose latest count is from an active (non-hidden) collection do NOT show the icon
- [ ] Items with no count records at all do NOT show the icon
- [ ] Filter by Record Type = Blends → icon still appears correctly on relevant rows
- [ ] Filter by Record Type = Components → icon still appears correctly on relevant rows

---

## 10. Navigation

- [ ] Active collections page has a "View Hidden Collections" link visible to staff users
- [ ] Clicking the "View Hidden Collections" link navigates to `/core/hidden-count-collection-links/`
- [ ] Hidden collections page has a "Back to Active Collections" link
- [ ] Clicking "Back to Active Collections" navigates to `/core/display-count-collection-links/`
- [ ] From the hidden collections page, clicking a collection name goes to the correct count list page

---

## 11. Data Integrity

- [ ] Hiding a collection does NOT delete any BlendCountRecord or BlendComponentCountRecord rows
- [ ] Restoring a collection does NOT duplicate or alter any count records
- [ ] The `count_id_list` JSONField on CountCollectionLink is unchanged after hide/restore
- [ ] An item's count status report data is unchanged after its collection is hidden (same counted date, quantity, variance)
- [ ] Creating a new collection still works normally after this feature (test the "Create Automated Blend Count List" button)
- [ ] Renaming a collection still works normally (edit the name input on the active collections page)
- [ ] Reordering collections (drag-and-drop if applicable) still works normally

---

## 12. Edge Cases

### Rapid Actions

- [ ] Hide a collection, then immediately restore it → collection ends up active, no errors
- [ ] Restore a collection, then immediately hide it again → collection ends up hidden, no errors

### Multiple Tabs/Users

- [ ] Two staff users hide different collections simultaneously → both collections disappear correctly from all tabs
- [ ] One staff user hides while another restores the same collection at the same time → final state is consistent (one wins, no crash)

### Page State After Actions

- [ ] Hide all collections on the active page → page shows "No counts needed now." message
- [ ] Restore a collection when the active page shows "No counts needed now." → the page updates (may need a refresh to show the table)

### Browser Refresh

- [ ] After hiding a collection, refresh the active page → hidden collection is NOT shown
- [ ] After restoring a collection, refresh the hidden page → restored collection is NOT shown
- [ ] After hiding a collection, refresh the hidden page → newly hidden collection IS shown

---

## Test Summary

| Section | Tests |
|---------|-------|
| 1. Access Control | 7 |
| 2. Hide Action – Active Page | 7 |
| 3. Hide Action – WebSocket Broadcast | 3 |
| 4. Active User Soft Transition | 8 |
| 5. Count List – Read-Only Mode | 10 |
| 6. Hidden Collections Page – Display | 9 |
| 7. Restore Action | 7 |
| 8. Hidden Page – Real-Time Updates | 3 |
| 9. Count Status Report | 7 |
| 10. Navigation | 5 |
| 11. Data Integrity | 7 |
| 12. Edge Cases | 8 |

**Total**: 81 tests
