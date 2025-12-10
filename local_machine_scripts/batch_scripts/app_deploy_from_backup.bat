@echo off
echo Starting Docker...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

:loop
timeout /t 1 >nul
docker info >nul 2>&1
if errorlevel 1 (
    echo Waiting for Docker to start...
    goto loop
)

echo Docker started.

echo Running the app...
cd %USERPROFILE%/Documents/kpk-app
docker-compose -p kpk-app -f docker-compose-PROD.yml up -d

set /p UserInput=Do you want to restore the DB and Redis backups? (y/n): 
if /I "%UserInput%" EQU "y" (
    echo Restoring the latest DB and Redis backups...
    cd %USERPROFILE%/Documents/kpk-app/local_machine_scripts/batch_scripts/helpers
    call db_restore_latest_backup.bat
)