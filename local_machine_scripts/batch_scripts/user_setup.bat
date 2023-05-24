@echo OFF
setlocal EnableDelayedExpansion

for /f "tokens=1* delims==" %%a in (C:\Users\pmedlin\Documents\kpk-app\.env) do (
    set "%%a=%%b"
)

echo %ACTIVE_APP_CONTAINER%

@echo ON
docker exec %ACTIVE_APP_CONTAINER% sh -c "python manage.py createsuperuser --username=admin --email=admin@admin.com --noinput"
ping -n 2 127.0.0.1 >NUL
docker exec %ACTIVE_APP_CONTAINER% sh -c "python manage.py change_admin_pw"
ping -n 2 127.0.0.1 >NUL
docker exec %ACTIVE_APP_CONTAINER% sh -c "python manage.py setup_users"