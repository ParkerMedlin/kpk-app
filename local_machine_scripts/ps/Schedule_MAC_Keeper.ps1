# Schedule_MAC_Keeper.ps1
$scriptPath = Join-Path $env:USERPROFILE "Documents\MAC_Keeper.ps1"
$actionArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$scriptPath`""

$taskAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
$taskTrigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun

# Register the task with elevated privileges
Register-ScheduledTask -TaskName "MAC Address Keeper" `
    -Action $taskAction `
    -Trigger $taskTrigger `
    -Settings $taskSettings `
    -Description "Maintains current MAC address for Wake-on-LAN purposes" `
    -RunLevel Highest `
    -Force