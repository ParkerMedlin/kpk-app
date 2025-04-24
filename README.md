# ✨ Blendverse App ✨

Welcome to Blendverse! This app provides a centralized hub for reporting and record-keeping within the blending department at Kinpak, Inc., a chemical manufacturing facility. Our goal is to replace a complex system of spreadsheets that interface with our ERP system, thereby enhancing our Material Requirements Planning (MRP), inventory tracking, and production analysis capabilities.

---

## 🚀 Current Live Functions

###  forklift Safety Checklist 🚦

*   Forklift drivers can complete a daily safety inspection checklist for their vehicles.
*   The safety manager receives two daily email reports:
    *   A report detailing all inspections with comments or safety concerns.
    *   A report listing forklifts missing their daily checklist submission.

### Lot Number Records 🔢

*   Maintains a database of batch history, identified by lot numbers.
*   Admin users can create new lot number records directly through the app.

### Materials & Resource Planning (MRP) 📊

*   Continuously updated database mirroring Sage 100 ERP tables (inventory, purchasing, accounting).
*   Continuously updated tables detailing the production order sequence.
*   Calculates shortages of blends required for production orders.
*   Calculates raw material shortages needed for blend production.
    *   The `Chem Shortages` report precisely predicts the final production run possible before exhausting a specific chemical.

### Blend Scheduling 🗓️

*   Provides rudimentary scheduling for blends and tracks their completion status.

### Production Batch Issue Sheets 📄

*   Generates paperwork indicating which blend batches are issued to production lines for bottling.

---

## 🛠️ Functions Under Development

### Blend Sheets

*   **Goal:** Display blend formulas to the crew and track the steps taken during batch creation.
*   **Current System:** Blend formulas are stored in Excel, printed, and manually distributed.
*   **Development:** A module is being built to replace this manual process and digitally store all blend creation information.

### Blend Inventory Counts

*   **Goal:** Display a list of blends needing manual counts and allow direct database entry.
*   **Current System:** Uses a spreadsheet showing upcoming blends, transaction history, and count dates to decide which blends need counting. The list is printed, counts are manually recorded, entered back into the spreadsheet by the manager, emailed to the production manager, and finally entered into the ERP.
*   **Development:** A module will display the list, allow inventory crew data entry, and present results directly to the production manager, streamlining the process.

---

## 💻 System Requirements

### Hardware

*   **Minimum:** 8GB RAM (may struggle), 2.4GHz+ Quad-core processor.
*   **Note:** Performance tests across various hardware are limited.

### Deployment

*   The application is designed for **on-site deployment** over the local network.
*   `pyodbc` connections for Sage 100 table updates require the server to be a trusted member of the local network.
*   Off-site test runs might be possible using CSV data from `db_imports`.

---

## ⚙️ Technical Specifications & Conventions

### Versions

*   **Bootstrap:** 5
*   **jQuery:** 3.6.0
*   **Python:** 3.9
*   **Postgres:** 13

### Naming Conventions (PEP 8)

*   **Functions:** `lowercase_with_underscores` (start with a verb)
*   **Variables:** `lowercase_with_underscores`
*   **Classes (incl. Models):** `CamelCase`
*   **URL Path Names:** `lowercase-with-dashes`
*   **HTML Templates:** `lowercasenopunctuation.html`
*   **Script Files:** `lowercase_with_underscores.py`

### Internal Database Notes

Tables requiring preservation (not programmatically updated):

```
auth_user
core_blendingstep
core_blendinstruction
core_checklistlog
core_checklistsubmissionrecord
core_itemlocation
core_countrecord
core_deskoneschedule
core_desktwoschedule
core_foamfactor
core_forklift
core_storagetank
core_lotnumrecord