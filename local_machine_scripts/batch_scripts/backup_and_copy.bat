set backupdir="%date:~-10,2%"-"%date:~7,2%"-"%date:~-4,4%"-"backup"
mkdir %USERPROFILE%\desktop\%backupdir%
mkdir %USERPROFILE%\desktop\%backupdir%\full_db
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "DB_USER= DB_PASS= DB_NAME=" "%USERPROFILE%\Documents\kpk-app\.env"`) do set "%%A=%%B"
docker exec -e PGPASSWORD=%DB_PASS% -i kpk-app_db_1 pg_dump -U %DB_USER% %DB_NAME% > "%USERPROFILE%\Desktop\full_db\full_db_dump.sql"
mkdir M:\kpkapp\backups\%backupdir%
ROBOCOPY "%USERPROFILE%\desktop\\%backupdir%" "M:\kpkapp\backups\\%backupdir%" /E
rmdir /s /q "%USERPROFILE%\desktop\%backupdir%"