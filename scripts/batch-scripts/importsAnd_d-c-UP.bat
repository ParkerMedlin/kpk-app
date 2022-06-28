docker exec kpk-app_app_1 sh -c "python manage.py import_batches --path /init-db-imports/lotnums.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_instructions --path /init-db-imports/blendinstructions.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_foamfactor --path /init-db-imports/foamfactor.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_forklifts --path /init-db-imports/forkliftinfo.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_blndcounts --path /init-db-imports/blndschcounts.csv"