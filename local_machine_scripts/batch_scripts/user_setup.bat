docker exec kpk-app_app_1 sh -c "python manage.py createsuperuser --username=admin --email=admin@admin.com --noinput"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py change_admin_pw"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py setup_users"
ping -n 2 127.0.0.1 >NUL
docker exec kpk-app_app_1 sh -c "python manage.py add_users_to_groups"