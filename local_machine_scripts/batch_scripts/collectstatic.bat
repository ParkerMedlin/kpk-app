docker exec kpk-app_app_green_1 sh -c "python manage.py collectstatic --noinput"
docker exec kpk-app_app_blue_1 sh -c "python manage.py collectstatic --noinput"