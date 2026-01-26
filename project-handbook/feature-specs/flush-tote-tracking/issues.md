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


