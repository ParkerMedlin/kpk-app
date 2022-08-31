docker exec kpk-app_app_1 sh -c "python manage.py import_batches --path /init_db_imports/lotnums.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_instructions --path /init_db_imports/blendinstructions.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_foamfactor --path /init_db_imports/foamfactor.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_forklifts --path /init_db_imports/forkliftinfo.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_blndinvlog --path /init_db_imports/blndschcounts.csv"