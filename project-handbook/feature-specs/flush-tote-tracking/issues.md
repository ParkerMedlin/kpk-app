# Discharge Testing – Issues

Discovered during test suite validation.

---

## Issue 1: Records Page Access Too Permissive

**Problem:** Any authenticated user can access and edit `/core/discharge-testing-records/`. Should be restricted to staff users only.

**Expected Behavior:**
- Staff users: Full access
- Superusers: Full access
- Non-staff (including lab technicians): 403 Forbidden

### Tasks

- [x] 1.1 Update `DischargeTestingRecordsView` to check `user.is_staff` instead of just `is_authenticated`
- [x] 1.2 Return 403 response for non-staff authenticated users
- [x] 1.3 Verify redirect to login for anonymous users still works
- [x] 1.4 Test: Staff user can access records page
- [x] 1.5 Test: Lab technician (non-staff) gets 403
- [x] 1.6 Test: Regular authenticated user gets 403

---

## Issue 2: Entry Page Blocks Lab Technicians

**Problem:** `/core/discharge-testing/` does not allow non-staff lab technicians to access. Should be open to anyone in the "lab technician" group.

**Expected Behavior:**
- Staff users: Full access
- Superusers: Full access
- Lab technician group members (even if not staff): Full access
- Other authenticated users: 403 Forbidden

### Tasks

- [x] 2.1 Update `DischargeTestingEntryView` permission check to allow `is_staff OR in_group("lab technician")`
- [x] 2.2 Add helper function or mixin for lab technician group check if not already present
- [x] 2.3 Return 403 for authenticated users who are neither staff nor lab technician
- [x] 2.4 Test: Staff user can access entry page
- [x] 2.5 Test: Non-staff lab technician can access entry page
- [x] 2.6 Test: Regular authenticated user (not lab tech, not staff) gets 403
- [x] 2.7 Test: Anonymous user redirects to login

---

## Issue 3: No "line personnel" group

**Problem:** Several references to "line personnel" user group, which does not exist. Any authenticated user should be able to be the sampling personnel.

**Expected Behavior:**
Any authenticated user should be able to be the sampling personnel.

### Tasks

- [x] 3.1 Replace "line personnel"-based validation in api.py and discharge_testing_services.py with straight user auth checks
- [x] Test to make sure everything still works

---

## Issue 4: Clear Button Causes Infinite Reset Loop

**Problem:** Clicking the "Clear" button on the entry form causes all fields to become unresponsive. Only resolved by refreshing the page.

**Root Cause Analysis:**

The `handleReset()` method (line 747-749) schedules `resetForm()` via `setTimeout`. However, `resetForm()` (line 719-745) calls `this.form.reset()` on line 721, which fires another `reset` event, creating an infinite loop:

```
Click Clear → reset event → handleReset() → setTimeout → resetForm()
           → this.form.reset() → reset event → handleReset() → ...
```

Each iteration:
1. Steals focus back to `dischargeSource` (line 742-744), making other fields seem unclickable
2. Creates/removes feedback DOM elements
3. Runs visibility sync methods

The fields aren't disabled—focus is being stolen every ~0ms.

**Code Locations:**
- `DischargeTestingEntry.js` lines 719-749

**Fix Approach:**
Remove the redundant `this.form.reset()` call from `resetForm()`. The native form reset already happened before `handleReset()` was invoked. The `resetForm()` method should only handle:
- Clearing feedback
- Resetting hidden fields and autocomplete state
- Syncing visibility
- Setting focus

### Tasks

- [x] 4.1 Remove `this.form.reset()` call from `resetForm()` method (line 720-722)
- [x] 4.2 Verify `resetForm()` still clears material code hidden field and display input
- [x] 4.3 Verify `resetForm()` still hides material results dropdown
- [x] 4.4 Verify `resetForm()` still hides pH alert
- [x] 4.5 Verify `resetForm()` still syncs field visibility (material, pH fields)
- [x] 4.6 Verify focus returns to Discharge Source after reset
- [x] 4.7 Test: Click Clear → all fields remain interactive
- [x] 4.8 Test: Click Clear → form values are cleared
- [x] 4.9 Test: Click Clear → validation feedback is cleared
- [x] 4.10 Test: Submit success calls `resetForm()` directly without infinite loop

---

## Issue 5: Initial pH Should Be Required

**Problem:** The initial pH field is currently optional. It should be required for all non-Oil discharge types.

**Expected Behavior:**
- Initial pH is required for Acid, Base, Soap, and Polish discharge types
- Initial pH remains hidden (and not required) for Oil discharge type
- Form cannot be submitted without initial pH (for applicable types)
- Server-side validation enforces this requirement

**Code Locations:**
- `discharge_testing_entry.html` - add `required` attribute to initial pH input
- `DischargeTestingEntry.js` - add client-side validation for initial pH
- `discharge_testing_services.py` - add server-side validation for initial pH

### Tasks

- [x] 5.1 Add `required` attribute to initial pH input in `discharge_testing_entry.html`
- [x] 5.2 Update `collectPayload()` in JS to validate initial pH is provided (non-Oil types)
- [x] 5.3 Update `create_discharge_test()` service to require initial pH for non-Oil types
- [x] 5.4 Ensure Oil type bypasses initial pH requirement (client and server)
- [x] 5.5 Test: Submit Acid type without initial pH → validation error
- [x] 5.6 Test: Submit Soap type without initial pH → validation error
- [x] 5.7 Test: Submit Oil type without initial pH → success
- [x] 5.8 Test: Submit with valid initial pH → success

---

## Issue 6: Edit Mode Replaces Delete Button With Empty Input

**Problem:** Clicking the Edit button on a records row replaces the trash/delete button with an empty text input field. Exiting edit mode (save or cancel) does not restore it.

**Root Cause Analysis:**

`enterEditMode()` (`DischargeTestingRecords.js` line 405) iterates every `[data-field]` cell in the row and converts each one into an editable input, unless the field name appears in the skip list (lines 407-419). The delete button's cell uses `data-field="delete"` (template line 164), which is **not** in the skip list. It falls through to the generic text input branch (lines 433-437):

```
cell.innerHTML = '';          // destroys the trash button
cell.appendChild(input);      // replaces it with an empty <input type="text">
```

On exit, `applyRowData()` (line 717) restores the `actions` cell (line 780-783) but has no handling for the `delete` cell, so the trash button is never restored.

Additionally, `getRowSnapshot()` (line 286) only skips `actions`, not `delete`, so a spurious `delete: ""` key is captured in the snapshot.

**Affected Code Locations:**
- `DischargeTestingRecords.js` line 405-441 — `enterEditMode()` field iteration
- `DischargeTestingRecords.js` line 286-305 — `getRowSnapshot()` field iteration

**Fix Approach:**
Add `'delete'` to the skip conditions in both methods. If `enterEditMode` never touches the delete cell, the button stays intact through edit/cancel/save and no restoration logic is needed.

### Tasks

- [x] 6.1 Add `field === 'delete'` to the skip condition in `enterEditMode()` (line 411-419)
- [x] 6.2 Add `field === 'delete'` to the skip condition in `getRowSnapshot()` (line 294)
- [x] 6.3 Test: Click Edit → delete button remains visible and unchanged
- [x] 6.4 Test: Click Cancel → delete button still functional
- [x] 6.5 Test: Click Save → delete button still functional
- [x] 6.6 Test: Delete button works correctly after editing and saving a row

---

## Issue 7: Records Page pH Cell Clutter and Input Spinners

### 7a: pH Cells Show Redundant Date/User Info

**Problem:** Each pH cell (Initial pH and Final pH) renders three lines: the pH value, the lab technician name, and a timestamp. This makes the table visually cluttered with information that adds little value in a dense table view.

**Current rendering** (template lines 90-103 and 119-132, JS `setPhCell` lines 804-818):

```
7.20                    ← pH value (bold)
John Smith              ← lab technician name (small muted)
2026-01-25 14:30        ← timestamp (small muted)
```

**Expected:** Show only the pH value. Remove the updated-by and updated-at sub-lines.

**Code Locations:**
- `discharge_testing_records.html` lines 90-103 (initial pH cell) and lines 119-132 (final pH cell)
- `DischargeTestingRecords.js` lines 804-818 (`setPhCell` method)

### 7b: pH Edit Inputs Show Browser Spinner Buttons

**Problem:** When a row enters edit mode, the pH fields render as `<input type="number">` (JS line 427-431), which displays browser-native increment/decrement spinner arrows. These are unnecessary for pH entry and add visual noise.

**Code Location:**
- `DischargeTestingRecords.js` lines 427-431 — `createTextInput` called with `type: 'number'`

**Fix Approach:** Switch pH inputs to `type="text"` with `inputMode="decimal"` to get the numeric keyboard on mobile without the spinner arrows. The existing `parsePhValue()` already handles string-to-number parsing, so no validation changes are needed.

### Tasks

- [x] 7.1 Remove updated-by and updated-at divs from initial pH cell in template (lines 94-103)
- [x] 7.2 Remove updated-by and updated-at divs from final pH cell in template (lines 123-132)
- [x] 7.3 Simplify `setPhCell()` in JS to render only the pH value without updated-by/updated-at lines
- [x] 7.4 Change pH edit inputs from `type: 'number'` to `type: 'text'` with `inputMode: 'decimal'`
- [x] 7.5 Remove `step: '0.01'` (only relevant for `type="number"`)
- [x] 7.6 Test: pH cells display only the value, no sub-lines
- [x] 7.7 Test: pH edit inputs have no spinner arrows
- [x] 7.8 Test: pH values still parse and validate correctly after type change

---

## Issue 8: Sampling Personnel Cleared When Entering Edit Mode

**Problem:** When clicking the Edit button on a records row, the Sampling Personnel dropdown shows "Select sampling personnel..." instead of the currently assigned person. This makes it appear as if the value was cleared.

**Root Cause Analysis:**

The `#sampling-personnel-options` hidden select element (used as a template for edit mode dropdowns) is populated by `get_sampling_personnel_options()` in `app/core/selectors/discharge_testing_selectors.py:34-47`. This function only includes users who are:
- Active (`is_active=True`)
- In groups: `blend_crew`, `blending_line_service`, `line_leader`, OR `lab`

When `createSelectInput()` (`DischargeTestingRecords.js` lines 351-366) builds the edit dropdown:
1. It copies options from `#sampling-personnel-options`
2. It sets `select.value = String(currentSamplingPersonnelId)`
3. If no `<option>` exists with that value (user no longer in eligible groups or inactive), the browser silently fails
4. The select displays the first option: "Select sampling personnel..."

The original cell still has the correct `data-value` and displays the correct name, but the edit dropdown cannot represent that user.

**Scenario:**
1. Record created with `sampling_personnel_id = 42` (user "John Doe" in `blend_crew` group)
2. John Doe is later removed from `blend_crew` group (or becomes inactive)
3. Page loads: cell correctly shows "John Doe" (from `tote.sampling_personnel.get_full_name`)
4. User clicks Edit
5. Dropdown has no option for ID 42
6. `select.value = "42"` fails silently
7. User sees "Select sampling personnel..." instead of "John Doe"

**Affected Code Locations:**
- `DischargeTestingRecords.js` lines 351-366 — `createSelectInput()` method
- `discharge_testing_selectors.py` lines 34-47 — `get_sampling_personnel_options()`

**Fix Approach:**
Modify `createSelectInput()` to check if the desired value exists in the options after populating from the template. If not, dynamically add an option using:
- The value from `cell.dataset.value` (the user ID)
- The display name from the snapshot's `sampling_personnel_name` (captured from cell text in `getRowSnapshot()` at line 297)

This preserves historical data without changing the eligibility criteria for new entries.

### Tasks

- [x] 8.1 Update `createSelectInput()` to accept an optional `displayName` parameter
- [x] 8.2 After setting `select.innerHTML`, check if an option with the target value exists
- [x] 8.3 If missing, create and prepend a new `<option>` with the value and display name
- [x] 8.4 Update `enterEditMode()` to pass the snapshot's `sampling_personnel_name` to `createSelectInput()`
- [x] 8.5 Test: Edit record where sampling_personnel is still in eligible groups → correct selection shown
- [x] 8.6 Test: Edit record where sampling_personnel is no longer in eligible groups → correct selection shown (dynamically added)
- [x] 8.7 Test: Edit record where sampling_personnel is inactive → correct selection shown (dynamically added)
- [x] 8.8 Test: Save after editing a record with historical sampling_personnel → value preserved
- [x] 8.9 Test: New entries still show only eligible users in dropdown

---


