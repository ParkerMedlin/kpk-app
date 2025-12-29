@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: Locate latest backup folder
FOR /F "usebackq tokens=*" %%F IN (`powershell -Command "Get-ChildItem -Path 'M:\kpkapp\backups' | Where-Object { $_.PSIsContainer } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName"`) DO (
    SET "LATEST_BACKUP_FOLDER=%%F"
)

IF NOT DEFINED LATEST_BACKUP_FOLDER (
    echo No backup folder found.
    exit /b 1
)

SET "SQL_DUMP_FILE=!LATEST_BACKUP_FOLDER!\full_db_dump.sql"
SET "REDIS_DUMP_FILE=!LATEST_BACKUP_FOLDER!\redis_dump.rdb"
SET "REDIS_CONTAINER=kpk-app_redis_1"

IF NOT EXIST "!SQL_DUMP_FILE!" (
    echo SQL dump file not found at !SQL_DUMP_FILE!.
    exit /b 1
)

:: Load DB credentials (relative to script location: helper_scripts -> batch_scripts -> local_machine_scripts -> repo root)
set "ENV_FILE=%~dp0..\..\..\.env"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%ENV_FILE%"`) do set "%%A=%%B"

echo Restoring Postgres from !SQL_DUMP_FILE! ...
echo Dropping and recreating schema 'public' ...
docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U %DB_USER% -d %DB_NAME% -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO %DB_USER%; GRANT ALL ON SCHEMA public TO public;"
IF errorlevel 1 goto :error

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
echo Restore finished.
exit /b 0

:error
echo Restore failed. See messages above for details.
exit /b 1
