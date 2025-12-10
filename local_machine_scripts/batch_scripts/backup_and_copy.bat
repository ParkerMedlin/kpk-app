set backupdir=%date:~-10,2%-%date:~7,2%-%date:~-4,4%-%time:~0,2%-%time:~3,2%-%time:~6,2%-backup
set backupdir=%backupdir: =0%
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%USERPROFILE%\Documents\kpk-app\.env"`) do set "%%A=%%B"
mkdir "%USERPROFILE%\Desktop\full_db" 2>nul
docker exec -e PGPASSWORD=%DB_PASS% -i kpk-app_db_1 pg_dump -U %DB_USER% %DB_NAME% > "%USERPROFILE%\Desktop\full_db\full_db_dump.sql"
mkdir "M:\kpkapp\backups\%backupdir%" 2>nul
ROBOCOPY "%USERPROFILE%\Desktop\full_db" "M:\kpkapp\backups\%backupdir%" full_db_dump.sql /E
rmdir /s /q "%USERPROFILE%\Desktop\full_db" 2>nul