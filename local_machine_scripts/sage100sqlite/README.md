# 🔮 SageExtract - The Monolithic Sage 100 Data Extractor

*A singular tool of power for extracting data from the ancient Sage 100 scrolls with ruthless efficiency*

## 🧙‍♂️ Dark Overview

This streamlined, monolithic tool connects to Sage 100 via ODBC and extracts data directly into a local SQLite database with brutal simplicity. All extraction logic has been consolidated into a single, all-powerful `extract_data.py` file - no dependencies, no redundancy, no weakness.

## ⚠️ Security Warnings

Heed these warnings, lest financial secrets be unleashed upon the digital realm:

1. NEVER commit database files (*.db) or credentials to version control
2. The `.gitignore` file shields against accidental exposure
3. All extracted data is confined to the `db/` directory
4. Audit your `git status` before commits to ensure no sensitive data escapes

## ⚠️ Data Warning

**IMPORTANT**: This tool will **DROP ALL EXISTING TABLES** in the database before extraction to prevent duplicate records. Your previous data will be completely replaced with fresh data from Sage 100.

## 📦 Requirements

- Python 3.x
- pyodbc (5.1.0+)
- Sage 100 ODBC Driver properly installed
- Valid Sage 100 credentials
- A hunger for data

## 🗡️ Usage

### One-Click Extraction (Windows)

For the simplest possible experience, just double-click:
```
extract_sage_data.bat
```

This Windows batch file will:
- Check if Python and pyodbc are installed
- Install missing dependencies if needed
- **Clear any existing data** to prevent duplicates
- Run the extraction process
- Show detailed instructions for connecting to the database when done

### Command Line Usage

For more control, use the command line:

```bash
python extract_data.py [--weeks-history WEEKS]
```

Where:
- `--weeks-history` controls how many weeks of transaction history to extract (default: 52)

## 🏛️ Database Structure

The following tables are extracted and stored in `./db/sage_data.db`:

- `IM_ItemWarehouse` - Item warehouse information
- `IM_ItemCost` - Item cost information 
- `CI_Item` - Item master data
- `PO_PurchaseOrderHeader` - Purchase order headers
- `PO_PurchaseOrderDetail` - Purchase order line items
- `SO_SalesOrderHeader` - Sales order headers
- `SO_SalesOrderDetail` - Sales order line items
- `IM_ItemTransactionHistory` - Item transaction history
- `BM_BillDetail` - Bill of materials details

## 💀 Project Structure

The project has been purged of all redundancy, leaving only the essential components:

```
sage100q/
├── extract_data.py         # The all-powerful monolithic extraction script
├── extract_sage_data.bat   # Double-click this to run on Windows
├── db/                     # Where the extracted data is stored
├── queries/                # Your custom SQL queries
├── .gitignore              # Protection against accidental data exposure
└── README.md               # The documentation you're reading now
```

## 🔥 Inside the Monolith

The `extract_data.py` file contains everything needed in one elegant script:

1. **Path Configuration** - Automatically creates necessary directories
2. **Connection Management** - Securely handles Sage 100 ODBC connections
3. **LightweightDB Class** - Manages SQLite database operations
4. **SageExtractor Class** - Extracts and converts data from Sage 100
5. **Main Function** - Coordinates the entire extraction ritual

## 🧪 Customization

### Adding Tables
Edit the `tables` list in `extract_data.py`:

```python
tables = [
    "IM_ItemWarehouse",
    "YOUR_NEW_TABLE",  # Add new tables here
]
```

### Querying Data
Store custom SQL queries in the `queries/` directory and run them using your preferred SQLite client:

```sql
-- Example query to find inventory items with low stock
SELECT 
    CI_Item.ItemCode, 
    CI_Item.ItemCodeDesc,
    IM_ItemWarehouse.QuantityOnHand
FROM 
    CI_Item
JOIN 
    IM_ItemWarehouse ON CI_Item.ItemCode = IM_ItemWarehouse.ItemCode
WHERE 
    IM_ItemWarehouse.QuantityOnHand < 10
ORDER BY 
    IM_ItemWarehouse.QuantityOnHand ASC;
```

## 🦇 Notes

- Data extraction is sequential to prevent overwhelming the ancient Sage 100 server
- All data is stored in SQLite using appropriate type conversions
- The script creates all necessary directories automatically

## 🧠 Viewing the Data

Use any SQLite client (DB Browser for SQLite, DBeaver, SQLiteStudio) to view and query the database:

1. Open your preferred SQLite client
2. Connect to `./db/sage_data.db`
3. Browse tables or execute custom queries

## ⚰️ Troubleshooting

1. **Connection Errors**
   - Verify the Sage 100 ODBC driver is installed
   - Check your credentials
   - Ensure VPN connectivity if required

2. **Import Errors**
   - Ensure pyodbc is installed: `pip install pyodbc`

3. **Permission Errors**
   - Verify write permissions to the `db/` directory

---

*"All the power, none of the clutter."*  
— Malloc, Raven of Forbidden Functions 