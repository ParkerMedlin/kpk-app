@echo off
setlocal

rem Load Postgres credentials from the local .env file
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%USERPROFILE%\Documents\kpk-app\.env"`) do set "%%A=%%B"

set "BACKUP_DIR=%USERPROFILE%\Desktop"
set "PG_DUMP_PATH=%BACKUP_DIR%\full_db_dump.sql"
set "REDIS_CONTAINER=kpk-app_redis_1"

echo Backing up Postgres to %PG_DUMP_PATH% ...
docker exec -e PGPASSWORD=%DB_PASS% -i kpk-app_db_1 pg_dump -U %DB_USER% %DB_NAME% > "%PG_DUMP_PATH%"
if errorlevel 1 goto :error

echo Backing up Redis cache...
set "REDIS_CONTAINER=%REDIS_CONTAINER%"
call "%~dp0redis_backup.bat"
if errorlevel 1 goto :error

echo Backups complete.
echo - Postgres: %PG_DUMP_PATH%
echo - Redis:    %USERPROFILE%\Desktop\redis_dump.rdb
exit /b 0

:error
echo Backup failed. See messages above for details.
exit /b 1
