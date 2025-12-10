@echo off
setlocal

set backupdir=%date:~-10,2%-%date:~7,2%-%date:~-4,4%-%time:~0,2%-%time:~3,2%-%time:~6,2%-backup
set backupdir=%backupdir: =0%

set "TEMP_DIR=%USERPROFILE%\Desktop\full_db"
set "SQL_DUMP=%TEMP_DIR%\full_db_dump.sql"
set "REDIS_DUMP=%TEMP_DIR%\redis_dump.rdb"
set "FINAL_DIR=M:\kpkapp\backups\%backupdir%"

for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%USERPROFILE%\Documents\kpk-app\.env"`) do set "%%A=%%B"

mkdir "%TEMP_DIR%" 2>nul
echo Backing up Postgres to %SQL_DUMP% ...
docker exec -e PGPASSWORD=%DB_PASS% -i kpk-app_db_1 pg_dump -U %DB_USER% %DB_NAME% > "%SQL_DUMP%"
if errorlevel 1 goto :error

echo Backing up Redis to %REDIS_DUMP% ...
call "%~dp0redis_backup.bat" "%REDIS_DUMP%"
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
