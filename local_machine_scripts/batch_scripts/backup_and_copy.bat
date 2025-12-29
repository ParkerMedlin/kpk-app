@echo off
setlocal

set backupdir=%date:~-10,2%-%date:~7,2%-%date:~-4,4%-%time:~0,2%-%time:~3,2%-%time:~6,2%-backup
set backupdir=%backupdir: =0%

REM Use temp folder relative to repo instead of USERPROFILE
set "REPO_ROOT=%~dp0..\.."
set "TEMP_DIR=%REPO_ROOT%\temp_backup"
set "SQL_DUMP=%TEMP_DIR%\full_db_dump.sql"
set "REDIS_DUMP=%TEMP_DIR%\redis_dump.rdb"
set "FINAL_DIR=\\KinPak-Svr1\apps\kpkapp\backups\%backupdir%"

REM Locate .env relative to script location (script is in local_machine_scripts/batch_scripts/)
set "ENV_FILE=%~dp0..\..\.env"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%ENV_FILE%"`) do set "%%A=%%B"

REM Debug: show what we're working with
echo ENV_FILE: %ENV_FILE%
echo DB_USER: %DB_USER%
echo DB_NAME: %DB_NAME%
echo TEMP_DIR: %TEMP_DIR%
echo FINAL_DIR: %FINAL_DIR%

if not defined DB_USER (
    echo ERROR: DB_USER not found in .env
    exit /b 1
)

mkdir "%TEMP_DIR%" 2>nul
echo Backing up Postgres to %SQL_DUMP% ...
docker exec -e PGPASSWORD=%DB_PASS% -i kpk-app_db_1 pg_dump -U %DB_USER% %DB_NAME% > "%SQL_DUMP%"
if errorlevel 1 goto :error

echo Backing up Redis to %REDIS_DUMP% ...
call "%~dp0helper_scripts\redis_backup.bat" "%REDIS_DUMP%"
if errorlevel 1 goto :error

mkdir "%FINAL_DIR%" 2>nul
echo Copying backups to %FINAL_DIR% ...
ROBOCOPY "%TEMP_DIR%" "%FINAL_DIR%" full_db_dump.sql redis_dump.rdb /E
if %ERRORLEVEL% GEQ 8 goto :error

rmdir /s /q "%TEMP_DIR%" 2>nul
echo Backup complete: %FINAL_DIR%
exit /b 0

:error
echo Backup failed. See messages above for details.
exit /b 1
