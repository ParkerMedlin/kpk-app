@echo off
setlocal

rem If caller already set REDIS_CONTAINER, respect it; otherwise default
if not defined REDIS_CONTAINER set "REDIS_CONTAINER=kpk-app_redis_1"

rem Allow caller to override output path as first argument
if "%~1"=="" (
    set "REDIS_DUMP_PATH=%USERPROFILE%\Desktop\redis_dump.rdb"
) else (
    set "REDIS_DUMP_PATH=%~1"
)

docker inspect %REDIS_CONTAINER% >nul 2>&1
if errorlevel 1 (
    echo Redis container %REDIS_CONTAINER% not found.
    exit /b 1
)

echo Creating Redis RDB snapshot in %REDIS_CONTAINER% ...
docker exec %REDIS_CONTAINER% redis-cli SAVE
if errorlevel 1 exit /b 1

echo Copying snapshot to %REDIS_DUMP_PATH% ...
docker cp %REDIS_CONTAINER%:/data/dump.rdb "%REDIS_DUMP_PATH%"
if errorlevel 1 exit /b 1

echo Redis backup complete: %REDIS_DUMP_PATH%
exit /b 0
