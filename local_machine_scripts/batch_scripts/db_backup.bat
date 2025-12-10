@echo off
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%USERPROFILE%\Documents\kpk-app\.env"`) do set "%%A=%%B"
docker exec -e PGPASSWORD=%DB_PASS% -i kpk-app_db_1 pg_dump -U %DB_USER% %DB_NAME% > "%USERPROFILE%\Desktop\full_db_dump.sql"