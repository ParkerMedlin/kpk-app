@echo off
REM Complete migration script for IM_ItemTransactionHistory incremental sync
REM This performs a full reset and rebuild with row_hash support

echo =======================================================
echo  KPK App - IM_ItemTransactionHistory Complete Reset
echo  and Incremental Sync Migration
echo =======================================================
echo.
echo WARNING: This will COMPLETELY REBUILD the table!
echo.
echo This will:
echo - DROP the existing im_itemtransactionhistory table
echo - Pull ALL data from Sage (2019 to present)
echo - Create new table with row_hash column
echo - Build all indexes for optimal performance
echo.
echo Estimated time: 15-30 minutes
echo.

set /p confirm="Continue with COMPLETE REBUILD? (y/N): "
if /i not "%confirm%"=="y" (
    echo Migration cancelled.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo Step 1: Dropping existing table...
echo =======================================================

psql -h localhost -p 5432 -U postgres -d blendversedb -c "DROP TABLE IF EXISTS im_itemtransactionhistory CASCADE;"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to drop existing table!
    pause
    exit /b 1
)

echo Table dropped successfully.
echo.
echo =======================================================
echo Step 2: Pulling fresh data from Sage (2019-present)...
echo =======================================================

REM Change to the python scripts directory
cd /d "%~dp0..\python_db_scripts"

REM Run the all transactions pull (gets everything from 2019+)
python -c "from app_db_mgmt import sage_to_postgres; sage_to_postgres.get_all_transactions()"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to pull data from Sage!
    pause
    exit /b 1
)

echo Data pulled successfully.
echo.
echo =======================================================
echo Step 3: Adding row_hash column and indexes...
echo =======================================================

REM Add the row_hash column and create indexes
psql -h localhost -p 5432 -U postgres -d blendversedb -c "ALTER TABLE im_itemtransactionhistory ADD COLUMN row_hash text;"

REM Backfill row_hash for all data
psql -h localhost -p 5432 -U postgres -d blendversedb -c "UPDATE im_itemtransactionhistory SET row_hash = md5((to_jsonb(im_itemtransactionhistory) - 'id' - 'row_hash')::text);"

REM Create the unique index on row_hash
psql -h localhost -p 5432 -U postgres -d blendversedb -c "CREATE UNIQUE INDEX im_itemtransactionhistory_row_hash_ux ON im_itemtransactionhistory(row_hash);"

REM Rebuild performance indexes
psql -h localhost -p 5432 -U postgres -d blendversedb -c "CREATE INDEX im_itemtxnhist_itemcode_idx ON im_itemtransactionhistory (itemcode);"
psql -h localhost -p 5432 -U postgres -d blendversedb -c "CREATE INDEX im_itemtxnhist_transactiondate_idx ON im_itemtransactionhistory (transactiondate);"
psql -h localhost -p 5432 -U postgres -d blendversedb -c "CREATE INDEX im_itemtxnhist_transactioncode_idx ON im_itemtransactionhistory (transactioncode);"
psql -h localhost -p 5432 -U postgres -d blendversedb -c "CREATE INDEX im_itemtxnhist_transactionqty_idx ON im_itemtransactionhistory (transactionqty);"

REM Analyze the table for optimal query planning
psql -h localhost -p 5432 -U postgres -d blendversedb -c "ANALYZE im_itemtransactionhistory;"

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to add row_hash or create indexes!
    pause
    exit /b 1
)

echo.
echo =======================================================
echo Step 4: Verification...
echo =======================================================

echo Checking row count and hash coverage...
psql -h localhost -p 5432 -U postgres -d blendversedb -c "SELECT COUNT(*) as total_rows, COUNT(row_hash) as rows_with_hash FROM im_itemtransactionhistory;"

echo.
echo Checking for duplicate hashes (should be 0)...
psql -h localhost -p 5432 -U postgres -d blendversedb -c "SELECT COUNT(*) as duplicate_hashes FROM (SELECT row_hash FROM im_itemtransactionhistory GROUP BY row_hash HAVING COUNT(*) > 1) dupes;"

echo.
echo =======================================================
echo Migration completed successfully!
echo =======================================================
echo.
echo The im_itemtransactionhistory table has been completely
echo rebuilt with incremental sync capabilities.
echo.
echo Next steps:
echo 1. Restart your data_looper.py process
echo 2. Monitor logs to confirm incremental sync is working
echo 3. Verify performance improvements
echo.

pause

