@echo off
setlocal

echo Stopping running containers...
set "any_running="
for /f "delims=" %%i in ('docker ps -q') do (
    set any_running=1
    docker stop %%i
)

if not defined any_running (
    echo No running containers found.
) else (
    echo Waiting for containers to fully stop...
)

:wait_for_stop
set "still_running="
for /f "delims=" %%i in ('docker ps -q') do set still_running=1
if defined still_running (
    timeout /t 2 >nul
    goto :wait_for_stop
)

echo Containers are stopped.
echo Pruning all unused Docker data (images, containers, volumes)...
docker system prune -a --volumes -f

echo Done.
exit /b 0
