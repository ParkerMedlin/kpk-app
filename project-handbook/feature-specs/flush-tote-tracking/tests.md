Lab Technician Testing

  URL: /core/flush-tote-entry/

  Access Control
  ✅ Page loads when logged in as lab technician group member
  ✅ Page loads when logged in as staff user
  ✅ Page returns 403 or redirects when logged in as non-lab, non-staff user ("Lab technician access required.")

  Form Display
  ✅ Production Line dropdown shows all options (JB Line, INLINE, PD Line)
  ✅ Flush Type dropdown populates from BlendContainerClassification.flush_tote values
  ✅ All fields visible: Production Line, Flush Type, Line Personnel (text), Initial pH, Action Required, Final pH

  Validation - Happy Path
  ✅ Submit with all required fields + pH in range (5.1–10.9) → record created with status "Approved"
  ✅ Success toast appears after submission
  ✅ Form resets for next entry after successful submit

  Validation - Out of Range pH
  ✅ Enter initial pH < 5.1 → UI indicates action required
  ✅ Enter initial pH > 10.9 → UI indicates action required
  - Submit with out-of-range initial pH but no action text → blocked or status "Needs Action"
  - Submit with out-of-range initial pH + action text + in-range final pH → status "Approved"
  - Submit with out-of-range initial pH + action text + out-of-range final pH → status "Needs Action"

  Validation - Missing Fields
  ✅ Submit without production line → error shown
  ✅ Submit without flush type → error shown
  - Submit without line personnel name → error shown (if required)

  Record Creation
  ✅ Created record has lab_technician set to current user
  ✅ Created record has date auto-populated
  ✅ Created record has correct line_personnel value (FK or name text)

  ---
  Admin/Staff Testing

  URL: /core/flush-tote-records/

  Access Control
  ✅ Page loads when logged in as staff user
  - Page returns 403 or redirects when logged in as non-staff user (including lab-only users)

  Table Display
  ✅ Table shows all flush tote records
  - Records sorted by date (newest first)
  - Status badges display correctly: Approved (green), Needs Action (yellow), Pending (gray)
  - All columns visible: Date/Time, Production Line, Flush Type, Initial pH, Action Required, Final pH, Status, Line Personnel, Lab Technician

  Search/Filter
  - Search filters table rows as expected
  - Filter persists or clears appropriately

  Inline Editing
  - Click edit button → row switches to editable inputs
  - Can edit: Production Line, Flush Type, Initial pH, Action Required, Final pH
  - Save changes → row updates without page reload
  - Cancel edit → row reverts to previous values
  - Edit a record to have in-range final pH → status changes to "Approved"
  - Edit a record to have out-of-range pH without action → status changes to "Needs Action"

  Error Handling
  - Save with invalid pH (non-numeric) → error message shown
  - Save with missing required field → error message shown

  ---
  API Endpoints (optional manual/curl testing)

  List/Create: GET/POST /core/api/flush-totes/
  - GET returns list of recent totes as JSON
  - POST with valid data creates record, returns 201
  - POST with invalid data returns 400 with field errors

  Detail/Update: PATCH/PUT /core/api/flush-totes/<id>/
  - PATCH updates specified fields, returns updated record
  - PATCH with invalid data returns 400 with field errors
  - Non-existent ID returns 404

  ---
  Navigation

  - Admin navbar (Blending dropdown) contains link to /core/flush-tote-records/
  - Lab technician has access to /core/flush-tote-entry/ (check if nav link exists or they navigate directly)