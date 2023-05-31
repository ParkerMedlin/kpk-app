docker cp C:\Users\pmedl\Documents\kpk-app\nginx\nginx.conf kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf

docker exec kpk-app_nginx_1 nginx -s reload