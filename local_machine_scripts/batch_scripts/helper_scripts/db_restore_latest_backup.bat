@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: %1 = backup name (optional), %2 = backup root (optional)
IF "%~2"=="" (
    set "BACKUP_ROOT=\\KinPak-Svr1\apps\kpkapp\backups"
) ELSE (
    set "BACKUP_ROOT=%~2"
)
set "REDIS_CONTAINER=kpk-app_redis_1"

:: Check if backup name was provided as parameter
IF "%~1"=="" (
    echo No backup name provided, finding latest...
    FOR /F "usebackq tokens=*" %%F IN (`powershell -NoProfile -Command "Get-ChildItem -Path '%BACKUP_ROOT%' -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"`) DO (
        SET "BACKUP_NAME=%%F"
    )
) ELSE (
    SET "BACKUP_NAME=%~1"
)

IF NOT DEFINED BACKUP_NAME (
    echo No backup folder found.
    exit /b 1
)

SET "BACKUP_FOLDER=%BACKUP_ROOT%\!BACKUP_NAME!"
SET "SQL_DUMP_FILE=!BACKUP_FOLDER!\full_db_dump.sql"
SET "REDIS_DUMP_FILE=!BACKUP_FOLDER!\redis_dump.rdb"

echo Selected backup: !BACKUP_NAME!
echo Backup folder: !BACKUP_FOLDER!

IF NOT EXIST "!BACKUP_FOLDER!" (
    echo Backup folder not found: !BACKUP_FOLDER!
    exit /b 1
)

IF NOT EXIST "!SQL_DUMP_FILE!" (
    echo SQL dump file not found at !SQL_DUMP_FILE!
    exit /b 1
)

:: Load DB credentials (relative to script location: helper_scripts -> batch_scripts -> local_machine_scripts -> repo root)
set "ENV_FILE=%~dp0..\..\..\.env"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%ENV_FILE%"`) do set "%%A=%%B"

if not defined DB_USER (
    echo ERROR: DB_USER not found in .env
    exit /b 1
)

echo Restoring Postgres from !SQL_DUMP_FILE! ...
echo Dropping and recreating schema 'public' ...
docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U %DB_USER% -d %DB_NAME% -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO %DB_USER%; GRANT ALL ON SCHEMA public TO public;"
IF errorlevel 1 goto :error

echo Importing database dump...
docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U %DB_USER% -d %DB_NAME% < "!SQL_DUMP_FILE!"
IF errorlevel 1 goto :error

IF EXIST "!REDIS_DUMP_FILE!" (
    docker inspect %REDIS_CONTAINER% >nul 2>&1
    IF errorlevel 1 (
        echo Redis container %REDIS_CONTAINER% not found. Skipping Redis restore.
        goto :done
    )

    set "REDIS_RUNNING="
    for /f "delims=" %%s in ('docker inspect -f "{{.State.Running}}" %REDIS_CONTAINER% 2^>nul') do set "REDIS_RUNNING=%%s"
    IF /I "!REDIS_RUNNING!"=="true" (
        echo Stopping Redis container %REDIS_CONTAINER% ...
        docker stop %REDIS_CONTAINER% >nul
        IF errorlevel 1 goto :error
    )

    echo Restoring Redis from !REDIS_DUMP_FILE! ...
    docker cp "!REDIS_DUMP_FILE!" %REDIS_CONTAINER%:/data/dump.rdb
    IF errorlevel 1 goto :error

    echo Starting Redis container %REDIS_CONTAINER% ...
    docker start %REDIS_CONTAINER% >nul
    IF errorlevel 1 goto :error

    echo Redis restore complete.
) ELSE (
    echo Redis dump not found at !REDIS_DUMP_FILE!. Skipping Redis restore.
)

:done
echo Restore finished: !BACKUP_NAME!
exit /b 0

:error
echo Restore failed. See messages above for details.
exit /b 1
