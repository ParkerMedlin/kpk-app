# Discharge Testing – Test Suite

**URLs**:
- Entry: `/core/discharge-testing/`
- Records: `/core/discharge-testing-records/`
- API List/Create: `/core/api/discharge-testing/`
- API Detail: `/core/api/discharge-testing/<id>/`
- Material Search: `/core/api/discharge-material-search/`
- pH Check: `/core/api/discharge-material-ph-check/`

---

## 1. Access Control

### Entry Page (`/core/discharge-testing/`)

- [x] Page loads for user in "lab technician" group
- [x] Page loads for staff user
- [x] Page loads for superuser
- [x] Page returns 403 for authenticated user not in lab technician group and not staff
- [x] Page redirects to login for anonymous user

### Records Page (`/core/discharge-testing-records/`)

- [x] Page loads for staff user
- [x] Page loads for superuser
- [x] Page returns 403 for lab technician (non-staff)
- [x] Page returns 403 for regular authenticated user
- [x] Page redirects to login for anonymous user

### Navigation

- [x] "Discharge Testing" link appears in Blending dropdown for staff users
- [x] "Discharge Testing Records" link appears in Blending dropdown for staff users
- [x] Entry page link accessible to lab technician group members

---

## 2. Entry Form – Field Display

### Core Fields (Always Visible)

- [x] Discharge Source dropdown shows options (JB Line, INLINE, PD Line, Warehouse)
- [x] Discharge Type dropdown shows options: Acid, Base, Soap, Polish, Oil
- [x] Sampling Personnel dropdown shows active users with display names
- [x] Lab Technician field displays current user's name (readonly)
- [x] Final Disposition textarea visible and required

### Conditional Fields – Acid/Base Type

- [x] Selecting "Acid" shows Discharge Material field
- [x] Selecting "Base" shows Discharge Material field
- [x] Selecting "Soap" hides Discharge Material field
- [x] Selecting "Polish" hides Discharge Material field
- [x] Selecting "Oil" hides Discharge Material field
- [x] Changing from Acid to Soap clears and hides Discharge Material field

### Conditional Fields – Oil Type

- [x] Selecting "Oil" hides Initial pH field
- [x] Selecting "Oil" hides Final pH field
- [x] Selecting "Oil" hides Action Required field
- [x] Changing from Oil to Acid shows pH fields again
- [x] Changing to Oil clears any entered pH values

### pH Fields (Non-Oil Types)

- [x] Initial pH field visible for Acid, Base, Soap, Polish
- [x] Final pH field visible for Acid, Base, Soap, Polish
- [x] Action Required field visible for Acid, Base, Soap, Polish
- [x] pH range badge shows "5.1 - 10.9"

---

## 3. Material Autocomplete (Acid/Base)

### Search Behavior

- [x] Typing less than 2 characters shows no results
- [x] Typing 2+ characters triggers search after debounce delay (~250ms)
- [x] Search matches items where itemcodedesc starts with "BLEND" or "CHEM"
- [x] Search matches against itemcode (e.g., typing "030" finds "030050")
- [x] Search matches against itemcodedesc (e.g., typing "sodium" finds sodium items)
- [x] Results display as "itemcode: itemcodedesc" format
- [x] Maximum 20 results shown
- [x] "No matches" message when search has no results

### Selection Behavior

- [x] Clicking a result populates the display input with full label
- [x] Clicking a result stores only the itemcode in hidden field
- [x] Results dropdown closes after selection
- [x] Clicking outside dropdown closes it
- [x] Selecting a new material replaces previous selection

### pH Active Component Alert

- [x] Selecting a watch list item (030050, 030015, 030024, 200126, 030025, 240079) shows alert
- [x] Alert displays: "pH-affecting material detected: {code}: {description}"
- [x] Alert is bold and visually prominent (alert-warning)
- [x] Selecting a BLEND containing a watch list component shows alert with component code
- [x] Selecting a material NOT in watch list (and no watch list components) shows no alert
- [x] Changing discharge type away from Acid/Base clears alert
- [x] Form reset clears alert

---

## 4. pH Validation – Client Side

### Initial pH Feedback

- [x] Entering valid pH (5.1-10.9) shows success indicator
- [x] Entering pH below 5.1 shows warning: "Initial pH is outside 5.1 - 10.9. Action is required."
- [ ] Entering pH above 10.9 shows warning
- [ ] Entering non-numeric value shows error: "Enter a valid pH value."
- [ ] Leaving field empty shows no error (optional field)

### Final pH Feedback

- [ ] Entering final pH without initial pH shows error: "Initial pH must be recorded before final pH."
- [ ] Entering final pH outside range shows error: "Final pH must be between 5.1 and 10.9."
- [ ] Entering valid final pH (with valid initial pH) shows success indicator

### Action Required Validation

- [ ] Action Required not required when initial pH in range
- [ ] Action Required becomes required when initial pH out of range
- [ ] Submitting with out-of-range initial pH but no action text shows error

---

## 5. Form Submission – Happy Paths

### Basic Submission (Soap/Polish Type)

- [ ] Submit with: Discharge Source, Discharge Type (Soap), Sampling Personnel, Final Disposition
- [ ] Record created successfully
- [ ] Success toast appears: "Entry saved."
- [ ] Form resets after successful submission
- [ ] Focus returns to Discharge Source field

### Submission with pH (In Range)

- [ ] Submit with initial pH = 7.0, final pH = 7.5 → record created
- [ ] pH values stored correctly in database

### Submission with pH (Out of Range + Action)

- [ ] Submit with initial pH = 4.5 (out of range), action text provided, final pH = 7.0 → record created
- [ ] Action Required text stored in database

### Acid/Base Submission

- [ ] Submit Acid type with material selected → record created with discharge_material_code
- [ ] Submit Base type with material selected → record created with discharge_material_code
- [ ] ph_active_component auto-populated if material matches watch list

### Oil Submission

- [ ] Submit Oil type without any pH values → record created successfully
- [ ] pH fields remain null in database
- [ ] No pH validation errors

---

## 6. Form Submission – Validation Errors

### Missing Required Fields

- [ ] Submit without Discharge Source → error on field
- [ ] Submit without Discharge Type → error on field
- [ ] Submit without Sampling Personnel → error on field
- [ ] Submit without Final Disposition → error on field
- [ ] First error field receives focus

### Acid/Base Material Required

- [ ] Submit Acid type without material → error: "Discharge material is required for Acid or Base."
- [ ] Submit Base type without material → error on discharge material field

### pH Validation

- [ ] Submit with out-of-range initial pH, no action → error on Action Required
- [ ] Submit with final pH but no initial pH → error: "Initial pH must be recorded before final pH."
- [ ] Submit with out-of-range final pH → error on Final pH

### Server-Side Errors

- [ ] Server validation error displays on correct field
- [ ] Error toast shows summary message

---

## 7. Form Reset

- [ ] Reset button clears all field values
- [ ] Reset clears all validation feedback
- [ ] Reset hides material autocomplete results
- [ ] Reset hides pH alert
- [ ] Reset restores default field visibility based on empty discharge type
- [ ] Focus returns to Discharge Source after reset

---

## 8. Records Page – Display

### Table Structure

- [ ] Table displays all discharge testing records
- [ ] Columns visible: Date, Discharge Source, Discharge Type, Discharge Material, pH Active Component, Sampling Personnel, Lab Technician, Initial pH, Action Required, Final pH, Final Disposition
- [ ] Records sorted by date (newest first)
- [ ] Empty/null fields display appropriately (dash or empty)

### Field Display

- [ ] Date displays in readable format
- [ ] Sampling Personnel shows user's display name
- [ ] Lab Technician shows user's display name
- [ ] Discharge Material shows itemcode (when present)
- [ ] pH Active Component shows itemcode (when detected)
- [ ] pH values display with 2 decimal places

---

## 9. Records Page – Inline Editing

### Edit Mode

- [ ] Click edit button → row switches to editable inputs
- [ ] Editable fields: Discharge Source, Discharge Type, Initial pH, Action Required, Final pH, Final Disposition
- [ ] Non-editable fields: Date, Sampling Personnel, Lab Technician, Discharge Material, pH Active Component

### Save Changes

- [ ] Save valid changes → row updates without page reload
- [ ] Success feedback shown
- [ ] Updated values persist on page refresh

### Cancel Edit

- [ ] Cancel → row reverts to previous values
- [ ] No changes saved to database

### Validation in Edit Mode

- [ ] Save with invalid pH → error shown
- [ ] Save with missing required field → error shown

---

## 10. API Endpoints

### List/Create (`GET/POST /core/api/discharge-testing/`)

- [ ] GET returns list of records as JSON
- [ ] GET response includes all fields: id, date, discharge_source, discharge_type, discharge_material_code, ph_active_component, sampling_personnel_id, sampling_personnel_name, lab_technician_id, lab_technician_name, initial_pH, action_required, final_pH, final_disposition
- [ ] POST with valid data creates record, returns 201
- [ ] POST with invalid data returns 400 with field errors
- [ ] POST requires authentication

### Detail (`GET/PATCH /core/api/discharge-testing/<id>/`)

- [ ] GET returns single record
- [ ] PATCH updates specified fields
- [ ] PATCH returns updated record
- [ ] PATCH with invalid data returns 400
- [ ] Non-existent ID returns 404

### Material Search (`GET /core/api/discharge-material-search/`)

- [ ] Returns results matching `q` parameter
- [ ] Results have `value` (itemcode) and `label` (itemcode: itemcodedesc)
- [ ] Empty/short query returns empty results
- [ ] Requires authentication

### pH Check (`GET /core/api/discharge-material-ph-check/`)

- [ ] Returns `ph_active_component` and `ph_active_component_desc` for watch list item
- [ ] Returns `ph_active_component` for blend containing watch list component
- [ ] Returns null values for non-watch-list material
- [ ] Requires authentication

---

## 11. Data Integrity

### Record Creation

- [ ] `date` auto-populated with current date/time
- [ ] `lab_technician` set to current user (if lab tech or staff)
- [ ] `sampling_personnel` set to selected user
- [ ] `ph_active_component` auto-populated based on material + BOM lookup

### Watch List Detection

- [ ] Material code 030050 → ph_active_component = 030050
- [ ] Material code 030015 → ph_active_component = 030015
- [ ] Material code 030024 → ph_active_component = 030024
- [ ] Material code 200126 → ph_active_component = 200126
- [ ] Material code 030025 → ph_active_component = 030025
- [ ] Material code 240079 → ph_active_component = 240079
- [ ] BLEND containing 030050 as component → ph_active_component = 030050
- [ ] Material with no watch list connection → ph_active_component = null

---

## 12. WebSocket Broadcasts

- [ ] Creating a record broadcasts `tote_created` event
- [ ] Recording initial pH broadcasts `initial_ph_recorded` event
- [ ] Recording final pH broadcasts `final_ph_recorded` event
- [ ] Broadcast payload includes all serialized fields including `discharge_material_code` and `ph_active_component`

---

## 13. Edge Cases

### Special Characters

- [ ] Material search handles special characters in query
- [ ] Final disposition accepts multiline text
- [ ] Action required accepts multiline text

### Decimal Precision

- [ ] pH values accept up to 2 decimal places
- [ ] pH values round/quantize correctly (e.g., 7.256 → 7.26)

### Boundary Values

- [ ] pH = 5.1 exactly is in range (no action required)
- [ ] pH = 10.9 exactly is in range
- [ ] pH = 5.09 is out of range
- [ ] pH = 10.91 is out of range

### Null/Empty Handling

- [ ] Empty discharge_material_code for non-Acid/Base types
- [ ] Null pH values for Oil type
- [ ] Empty action_required when not needed

---

## Test Summary

| Section | Tests |
|---------|-------|
| 1. Access Control | 10 |
| 2. Entry Form – Field Display | 18 |
| 3. Material Autocomplete | 16 |
| 4. pH Validation – Client Side | 10 |
| 5. Form Submission – Happy Paths | 11 |
| 6. Form Submission – Validation Errors | 10 |
| 7. Form Reset | 6 |
| 8. Records Page – Display | 9 |
| 9. Records Page – Inline Editing | 7 |
| 10. API Endpoints | 14 |
| 11. Data Integrity | 12 |
| 12. WebSocket Broadcasts | 4 |
| 13. Edge Cases | 10 |
| **Total** | **137** |
