set backupdir="%date:~-10,2%"-"%date:~7,2%"-"%date:~-4,4%"-"backup"
mkdir %USERPROFILE%\desktop\%backupdir%
mkdir %USERPROFILE%\desktop\%backupdir%\full_db
mkdir %USERPROFILE%\desktop\%backupdir%\critical_tables
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_user" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\auth_user_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_blendingstep" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_blendingstep_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_blendinstruction" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_blendinstruction_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_checklistlog" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_checklistlog_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_checklistsubmissionrecord" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_checklistsubmissionrecord_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_chemlocation" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_chemlocation_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_deskoneschedule" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_deskoneschedule_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_desktwoschedule" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_desktwoschedule_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_foamfactor" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_foamfactor_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_forklift" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_forklift_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_lotnumrecord" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_lotnumrecord_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_storagetank" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_storagetank_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_countrecord" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\db_backups\countrecord_dump.sql"
docker exec -t kpk-app_db_1 pg_dumpall -c -U postgres > "%USERPROFILE%\desktop\%backupdir%\full_db\full_db_dump.sql"
mkdir M:\kpkapp\backups\%backupdir%
ROBOCOPY "%USERPROFILE%\desktop\\%backupdir%" "M:\kpkapp\backups\\%backupdir%" /E
rmdir /s /q "%USERPROFILE%\desktop\%backupdir%"