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

echo Updating the database...
cd %USERPROFILE%/Documents/kpk-app
python %USERPROFILE%/Documents/kpk-app/local_machine_scripts/python_db_scripts/data_looper.py