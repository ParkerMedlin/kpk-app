docker exec -t kpk-app_db_1 pg_dump --table="public.core_lotnumrecord" -d blendversedb -U postgres > "C:\Users\pmedl\Desktop\core_lotnumrecord_dump.sql"