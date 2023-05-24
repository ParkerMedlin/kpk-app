@echo OFF
setlocal EnableDelayedExpansion

for /f "tokens=1* delims==" %%a in (C:\Users\pmedlin\Documents\kpk-app\.env) do (
    set "%%a=%%b"
)

echo %ACTIVE_APP_CONTAINER%

@echo ON
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select * from core_lotnumrecord limit 5" 
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select COUNT(*) from core_lotnumrecord"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select * from core_blendinstruction limit 5"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select COUNT(*) from core_blendinstruction"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select * from core_foamfactor limit 5"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select COUNT(*) from core_foamfactor"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select * from core_forklift limit 5"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select COUNT(*) from core_forklift"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select * from core_countrecord limit 5"
docker exec -it ACTIVE_APP_CONTAINER python manage.py dbshell -- -c "select COUNT(*) from core_countrecord"