# Discharge Testing – Manual Test Checklist (v2)

Post-refactor testing after Issues 1-9 resolved. Sampling personnel is now stored as a string name, not a FK.

---

## Entry Page (`/core/discharge-testing/`)

### Page Load

- [x] Page loads without errors
- [x] Discharge Source dropdown shows: JB Line, INLINE, PD Line, Warehouse
- [x] Discharge Type dropdown shows: Acid, Base, Oil, Polish, Soap
- [x] Sampling Personnel dropdown shows active users in eligible groups
- [x] Lab Technician field shows current user's name (read-only)
- [x] pH range badge displays "pH range 5.1 - 10.9"

### Field Visibility by Discharge Type

- [x] Select "Acid" → Initial pH and Final pH fields visible
- [x] Select "Base" → Initial pH and Final pH fields visible
- [x] Select "Soap" → Initial pH and Final pH fields visible
- [x] Select "Oil" → Initial pH and Final pH fields hidden
- [x] Select "Polish" → Initial pH and Final pH fields hidden
- [x] Switch from "Oil" to "Acid" → pH fields reappear

### Validation – Required Fields

- [x] Submit empty form → errors on Discharge Source, Discharge Type, Sampling Personnel, Initial pH
- [x] Submit with only Discharge Source filled → errors on remaining required fields
- [x] Submit Acid type without Initial pH → "Initial pH is required."
- [x] Submit Oil type without Initial pH → succeeds (pH not required for Oil)

### Validation – pH Values

- [x] Enter "abc" in Initial pH → "Enter a valid pH value."
- [x] Enter "7.5" in Initial pH → field shows valid (green border or no error)
- [x] Enter "4.0" in Initial pH → warning shown (out of range but allowed)
- [x] Enter Final pH without Initial pH → "Initial pH must be recorded before final pH."
- [x] Enter "3.0" in Final pH (out of range) → "Final pH must be between 5.1 and 10.9."
- [x] Enter "7.0" in Final pH with valid Initial pH → field shows valid

### Successful Submission

- [x] Fill all required fields with valid data, submit → success toast "Entry saved."
- [x] After success → form clears automatically
- [x] After success → focus returns to Discharge Source field

### Clear Button

- [x] Fill form partially, click Clear → all fields reset
- [x] After Clear → fields remain interactive (no freeze/loop)
- [x] After Clear → focus returns to Discharge Source

---

## Records Page (`/core/discharge-testing-records/`)

### Page Load

- [x] Page loads without errors
- [x] Table shows existing records with columns: Date/Time, Discharge Source, Discharge Type, Initial pH, Final pH, Sampling Personnel, Lab Technician, Edit, Delete
- [x] Dates display as `YYYY-MM-DD HH:MM`
- [x] pH values show 2 decimal places; missing values show `--`
- [x] Sampling Personnel shows name string (not "--" for valid records)
- [x] Lab Technician shows name or `--` if none


### Filter/Search

- [x] Type in search box → rows filter by matching text in any column
- [x] Clear search box → all rows reappear

### Enter Edit Mode

- [x] Click Edit button → row highlights yellow
- [x] Date field becomes datetime-local input with current value
- [x] Discharge Source becomes text input with current value
- [x] Discharge Type becomes text input with current value
- [x] Initial pH becomes text input (no spinner arrows) with current value
- [x] Final pH becomes text input (no spinner arrows) with current value
- [x] Sampling Personnel becomes dropdown with current value selected
- [x] Delete button remains visible and unchanged
- [x] Save (checkmark) and Cancel (X) buttons appear

### Edit Mode – Sampling Personnel Dropdown

- [x] Dropdown includes all eligible active users
- [x] Current sampling personnel is preselected (even if user no longer in eligible groups)
- [x] Can select a different person from dropdown

### Cancel Edit

- [x] Click Cancel → row exits edit mode
- [x] Original values restored (no changes saved)
- [x] Row no longer highlighted

### Save Edit – No Changes

- [x] Enter edit mode, make no changes, click Save → row exits edit mode quietly

### Save Edit – Valid Changes

- [x] Change Discharge Source, Save → success toast, new value displayed
- [x] Change Discharge Type, Save → success toast, new value displayed
- [x] Change Initial pH to valid value, Save → success toast, new value displayed
- [x] Change Final pH to valid value (with Initial pH present), Save → success toast
- [x] Change Sampling Personnel, Save → success toast, new name displayed
- [x] Change Date, Save → success toast, new date displayed

### Save Edit – Validation Errors

- [x] Clear Sampling Personnel dropdown, Save → "Sampling personnel is required."
- [x] Enter invalid pH value, Save → "Enter a valid pH value."
- [x] Enter Final pH out of range, Save → range error message
- [x] Enter Final pH when Initial pH is empty → "Initial pH must be recorded before final pH."

### Edit Another Row

- [x] While editing row A, click Edit on row B → prompt "You have unsaved changes... Abandon them?"
- [x] Click OK → row A reverts, row B enters edit mode
- [x] Click Cancel → stay on row A

### Delete Record

- [x] Click Delete → confirmation dialog "Are you sure you want to delete this record?"
- [x] Click Cancel on confirmation → record remains
- [x] Click OK on confirmation → record removed, success toast

### Data Persistence

- [x] Create entry on Entry page → appears on Records page after refresh
- [x] Edit record on Records page, refresh → changes persisted
- [x] Delete record on Records page, refresh → record gone

---

## Cross-Cutting

### pH Display (Records Page)

- [x] pH cells show only the numeric value (no timestamp, no user name sub-lines)
- [x] Missing pH shows `--`

### Sampling Personnel Name Persistence

- [x] Historical records with sampling personnel still display the name correctly
- [x] Editing a historical record preserves the sampling personnel name if unchanged
- [x] Changing sampling personnel on edit stores the new name correctly

---

## Access Control

### Entry Page

- [x] Staff user → can access
- [x] Lab technician (non-staff) → can access
- [x] Anonymous → redirect to login

### Records Page

- [x] Logged in user → can access
- [x] Anonymous → redirect to login
