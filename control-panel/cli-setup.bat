@echo off
echo Setting up KPK CLI alias...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$profilePath = $PROFILE; " ^
    "$aliasLine = 'Set-Alias kpk \"M:\kpkapp\control-panel\kpk.ps1\"'; " ^
    "if (!(Test-Path $profilePath)) { New-Item -Path $profilePath -ItemType File -Force | Out-Null }; " ^
    "$content = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue; " ^
    "if ($content -notmatch 'Set-Alias kpk') { Add-Content -Path $profilePath -Value \"`n$aliasLine\"; Write-Host 'Alias added to PowerShell profile.' -ForegroundColor Green } else { Write-Host 'Alias already exists in profile.' -ForegroundColor Yellow }"

echo.
echo Done! Restart PowerShell and type 'kpk status' to test.
pause
