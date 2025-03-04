@echo off
REM Generate a new Certificate Signing Request (CSR)
openssl req -new -key nginx/ssl/exceladdin.key -out nginx/ssl/new_exceladdin.csr -config nginx/ssl/openssl.conf

REM Self-sign the new certificate
openssl x509 -req -days 365 -in nginx/ssl/new_exceladdin.csr -signkey nginx/ssl/exceladdin.key -out nginx/ssl/new_exceladdin.crt

REM Convert the new certificate to PEM format
openssl x509 -in nginx/ssl/new_exceladdin.crt -out nginx/ssl/new_exceladdin.pem -outform PEM

REM Replace the old certificate
move /Y nginx/ssl/new_exceladdin.crt nginx/ssl/exceladdin.crt
move /Y nginx/ssl/new_exceladdin.pem nginx/ssl/exceladdin.pem

REM Copy the new certificate files into the Docker container
docker cp nginx/ssl/exceladdin.crt kpk-app_nginx_1:/etc/nginx/ssl/
docker cp nginx/ssl/exceladdin.pem kpk-app_nginx_1:/etc/nginx/ssl/

REM Reload Nginx to apply changes
docker exec kpk-app_nginx_1 nginx -s reload

@echo Certificate renewal process completed successfully.
@echo Please upload the new PEM file to Scalefusion: https://app.scalefusion.com/cloud/dashboard/certificates
@echo Check file contents to ensure the /ssl/ directory in the Docker container kpk-app_nginx_1 is updated under /etc/nginx/
pause 