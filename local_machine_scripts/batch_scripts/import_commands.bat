docker exec kpk-app_app_1 sh -c "python manage.py import_batches --path /db_imports/lotnums.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_instructions --path /db_imports/blendinstructions.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_foamfactor --path /db_imports/foamfactor.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_forklifts --path /db_imports/forkliftinfo.csv"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py import_countrecords --path /db_imports/blndschcounts.csv"