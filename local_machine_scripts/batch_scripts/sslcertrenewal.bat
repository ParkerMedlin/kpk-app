@echo off
REM Generate a new Certificate Signing Request (CSR)
openssl req -new -key nginx/ssl/exceladdin.key -out nginx/ssl/new_exceladdin.csr -config nginx/ssl/openssl.conf

REM Self-sign the new certificate
openssl x509 -req -days 365 -in nginx/ssl/new_exceladdin.csr -signkey nginx/ssl/exceladdin.key -out nginx/ssl/new_exceladdin.crt

REM Replace the old certificate
move /Y nginx/ssl/new_exceladdin.crt nginx/ssl/exceladdin.crt

REM Reload Nginx to apply changes
docker exec kpk-app_nginx_1 nginx -s reload

@echo Certificate renewal process completed successfully.
pause 