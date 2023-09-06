set backupdir="%date:~-10,2%"-"%date:~7,2%"-"%date:~-4,4%"-"backup"
mkdir %USERPROFILE%\desktop\%backupdir%
mkdir %USERPROFILE%\desktop\%backupdir%\full_db
mkdir %USERPROFILE%\desktop\%backupdir%\critical_tables
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_group" -d blendversedb -U postgres > "%USERPROFILE%\Desktop\auth_group_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_group_permissions" -d blendversedb -U postgres > "%USERPROFILE%\Desktop\auth_group_permissions_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_permission" -d blendversedb -U postgres > "%USERPROFILE%\Desktop\auth_permission_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_user" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\auth_user_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_user_groups" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\auth_user_groups_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.auth_user_user_permissions" -d blendversedb -U postgres > "%USERPROFILE%\Desktop\auth_user_user_permissions_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_blendingstep" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_blendingstep_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_blendinstruction" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_blendinstruction_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_checklistlog" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_checklistlog_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_checklistsubmissionrecord" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_checklistsubmissionrecord_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_itemlocation" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_itemlocation_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_deskoneschedule" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_deskoneschedule_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_desktwoschedule" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_desktwoschedule_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_foamfactor" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_foamfactor_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_forklift" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_forklift_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_lotnumrecord" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_lotnumrecord_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_storagetank" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_storagetank_dump.sql"
docker exec -t kpk-app_db_1 pg_dump --table="public.core_countrecord" -d blendversedb -U postgres > "%USERPROFILE%\desktop\%backupdir%\critical_tables\core_countrecord_dump.sql"
docker exec -t kpk-app_db_1 pg_dumpall -c -U postgres > "%USERPROFILE%\desktop\%backupdir%\full_db\full_db_dump.sql"
mkdir M:\kpkapp\backups\%backupdir%
ROBOCOPY "%USERPROFILE%\desktop\\%backupdir%" "M:\kpkapp\backups\\%backupdir%" /E
rmdir /s /q "%USERPROFILE%\desktop\%backupdir%"