set backupdir="%date:~-10,2%"-"%date:~7,2%"-"%date:~-4,4%"-"backup"
mkdir %USERPROFILE%\desktop\%backupdir%
mkdir %USERPROFILE%\desktop\%backupdir%\full_db
docker exec -t kpk-app_db_1 pg_dumpall -c -U postgres > "%USERPROFILE%\desktop\%backupdir%\full_db\full_db_dump.sql"
mkdir M:\kpkapp\backups\%backupdir%
ROBOCOPY "%USERPROFILE%\desktop\\%backupdir%" "M:\kpkapp\backups\\%backupdir%" /E
rmdir /s /q "%USERPROFILE%\desktop\%backupdir%"