@echo off
setlocal

set "BACKUP_DIR=%USERPROFILE%\Desktop"
set "PG_DUMP_PATH=%BACKUP_DIR%\full_db_dump.sql"
set "REDIS_DUMP_PATH=%BACKUP_DIR%\redis_dump.rdb"
set "REDIS_SAFETY_DUMP=%BACKUP_DIR%\redis_dump_before_restore.rdb"
set "REDIS_CONTAINER=kpk-app_redis_1"

if not exist "%PG_DUMP_PATH%" (
    echo Postgres backup not found at %PG_DUMP_PATH%.
    goto :error
)

rem Load DB credentials from the local .env file
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%USERPROFILE%\Documents\kpk-app\.env"`) do set "%%A=%%B"

echo Restoring Postgres from %PG_DUMP_PATH% ...
echo Dropping and recreating schema 'public' ...
docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U %DB_USER% -d %DB_NAME% -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO %DB_USER%; GRANT ALL ON SCHEMA public TO public;"
if errorlevel 1 goto :error

docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U %DB_USER% -d %DB_NAME% < "%PG_DUMP_PATH%"
if errorlevel 1 goto :error

echo Creating safety backup of current Redis to %REDIS_SAFETY_DUMP% ...
set "REDIS_CONTAINER=%REDIS_CONTAINER%"
call "%~dp0redis_backup.bat" "%REDIS_SAFETY_DUMP%"
if errorlevel 1 goto :error

if not exist "%REDIS_DUMP_PATH%" (
    echo Redis dump not found at %REDIS_DUMP_PATH%. Skipping Redis restore.
    goto :done
)

docker inspect %REDIS_CONTAINER% >nul 2>&1
if errorlevel 1 (
    echo Redis container %REDIS_CONTAINER% not found. Skipping Redis restore.
    goto :done
)

set "REDIS_RUNNING="
for /f "delims=" %%s in ('docker inspect -f "{{.State.Running}}" %REDIS_CONTAINER% 2^>nul') do set "REDIS_RUNNING=%%s"
if /I "%REDIS_RUNNING%"=="true" (
    echo Stopping Redis container %REDIS_CONTAINER% ...
    docker stop %REDIS_CONTAINER% >nul
    if errorlevel 1 goto :error
)

echo Restoring Redis cache from %REDIS_DUMP_PATH% ...
docker cp "%REDIS_DUMP_PATH%" %REDIS_CONTAINER%:/data/dump.rdb
if errorlevel 1 goto :error

echo Starting Redis container %REDIS_CONTAINER% ...
docker start %REDIS_CONTAINER% >nul
if errorlevel 1 goto :error

echo Redis restore complete.

:done
echo Database and cache restore finished.
exit /b 0

:error
echo Restore failed. See messages above for details.
exit /b 1
