@echo off
REM Migration script to enable incremental sync for IM_ItemTransactionHistory
REM Run this once before switching to incremental sync mode

echo =======================================================
echo  KPK App - IM_ItemTransactionHistory Incremental Sync
echo  Migration Script
echo =======================================================
echo.
echo This will:
echo - Add row_hash column to im_itemtransactionhistory
echo - Backfill hashes for existing 4M+ rows
echo - Create unique index for deduplication 
echo - Rebuild performance indexes
echo.
echo Estimated time: 5-15 minutes
echo.

set /p confirm="Continue with migration? (y/N): "
if /i not "%confirm%"=="y" (
    echo Migration cancelled.
    pause
    exit /b 1
)

echo.
echo Starting migration...
echo.

REM Execute the SQL migration
psql -h localhost -p 5432 -U postgres -d blendversedb -f "%~dp0..\sql_migrations\migrate_im_itemtransactionhistory_incremental.sql"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Migration failed!
    echo Check the error messages above.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo Migration completed successfully!
echo =======================================================
echo.
echo The im_itemtransactionhistory table is now ready for
echo incremental synchronization.
echo.
echo Next steps:
echo 1. Restart your data_looper.py process
echo 2. Monitor logs to confirm incremental sync is working
echo 3. Verify performance improvements
echo.

pause

