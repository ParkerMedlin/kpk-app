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
SET "SQL_DUMP_FILE=!LATEST_BACKUP_FOLDER!\full_db\full_db_dump.sql"

:: Check if the SQL dump file exists
IF NOT EXIST "!SQL_DUMP_FILE!" (
    echo SQL dump file not found.
    exit /b 1
)

:: Restore the database
SET "PGPASSWORD=blend2021" && "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d postgres -f "!SQL_DUMP_FILE!"

ENDLOCAL