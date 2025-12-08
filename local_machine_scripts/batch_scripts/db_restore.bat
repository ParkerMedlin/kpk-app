@echo off
for /f "tokens=2 delims==" %%a in ('findstr "DB_PASS=" "%USERPROFILE%\Documents\kpk-app\.env"') do set DB_PASS=%%a
docker exec -i -e PGPASSWORD=%DB_PASS% kpk-app_db_1 psql -U postgres -d blendversedb < "%USERPROFILE%\Desktop\full_db_dump.sql"