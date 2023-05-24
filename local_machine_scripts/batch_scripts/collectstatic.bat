@echo OFF
setlocal EnableDelayedExpansion

for /f "tokens=1* delims==" %%a in (C:\Users\pmedlin\Documents\kpk-app\.env) do (
    set "%%a=%%b"
)

echo %ACTIVE_APP_CONTAINER%

@echo ON
docker exec ACTIVE_APP_CONTAINER sh -c "python manage.py collectstatic --noinput"