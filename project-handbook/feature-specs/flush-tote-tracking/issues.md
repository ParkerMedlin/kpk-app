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


