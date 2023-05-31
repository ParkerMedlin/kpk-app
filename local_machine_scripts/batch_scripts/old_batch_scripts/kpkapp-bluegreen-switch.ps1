# Set the names of your upstream blocks here
$blue_upstream = "    server app_blue:8001;"
$green_upstream = "    server app_green:8002;"

# Fetch the current nginx.conf from the running Docker container
docker cp kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf .

# Check which app is currently active
if ((Get-Content -Path .\nginx.conf) -like "*$green_upstream*") {
    $current_upstream = $green_upstream
    $new_upstream = $blue_upstream
    $current_upstream_comment = "#$green_upstream"
    $new_upstream_comment = "$blue_upstream".Replace("#", "")
} else {
    $current_upstream = $blue_upstream
    $new_upstream = $green_upstream
    $current_upstream_comment = "#$blue_upstream"
    $new_upstream_comment = "$green_upstream".Replace("#", "")
}

# Display the current and new app names
Write-Host "Current upstream: $current_upstream"
Write-Host "Switching to: $new_upstream"

# Modify the nginx.conf file to use the new app
(Get-Content -Path .\nginx.conf).Replace($current_upstream, $current_upstream_comment) | Set-Content -Path .\nginx.conf
(Get-Content -Path .\nginx.conf).Replace($new_upstream_comment, $new_upstream) | Set-Content -Path .\nginx.conf

# Copy the updated nginx.conf back into the running Docker container and reload Nginx
docker cp .\nginx.conf kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf
docker exec kpk-app_nginx_1 nginx -s reload