@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Use PowerShell to get the latest backup folder
FOR /F "usebackq tokens=*" %%F IN (`powershell -Command "Get-ChildItem -Path 'M:\kpkapp\backups' | Where-Object { $_.PSIsContainer } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName"`) DO (
    SET "LATEST_BACKUP_FOLDER=%%F"
)

:: Check if the latest backup folder was found
IF NOT DEFINED LATEST_BACKUP_FOLDER (
    echo No backup folder found.
    exit /b 1
)

:: Set the path to the SQL dump file
SET "SQL_DUMP_FILE=!LATEST_BACKUP_FOLDER!\full_db_dump.sql"

:: Check if the SQL dump file exists
IF NOT EXIST "!SQL_DUMP_FILE!" (
    echo SQL dump file not found.
    exit /b 1
)

:: Restore the database
for /f "tokens=2 delims==" %%a in ('findstr "DB_PASS=" "%USERPROFILE%\Documents\kpk-app\.env"') do set DB_PASS=%%a
docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U postgres -d blendversedb < C:\Users\pmedlin\Desktop\full_db_dump.sql

ENDLOCAL