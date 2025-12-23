# KPK Control Panel - PowerShell Module
# Uses native Windows OpenSSH client (no AV issues)

$script:KPKConfig = @{
    Host = "192.168.178.169"
    Port = "22"
    User = $env:USERNAME
    Local = $false
    Lines = 100
}

$script:ContainerShortNames = @{
    "app_blue" = "kpk-app_app_blue_1"
    "blue" = "kpk-app_app_blue_1"
    "app_green" = "kpk-app_app_green_1"
    "green" = "kpk-app_app_green_1"
    "nginx" = "kpk-app_nginx_1"
    "postgres" = "kpk-app_postgres_1"
    "db" = "kpk-app_postgres_1"
    "redis" = "kpk-app_redis_1"
    "celery" = "kpk-app_celery_worker_1"
    "celery_worker" = "kpk-app_celery_worker_1"
    "celery_beat" = "kpk-app_celery_beat_1"
}

$script:HostServices = @{
    "data_sync" = "host-services/workers/data_sync.py"
    "excel_worker" = "host-services/workers/excel_worker.py"
    "stream_relay" = "host-services/workers/stream_relay.py"
    "looper_health" = "host-services/watchdogs/looper_health.py"
}

$script:HostServiceLogs = @{
    "data_sync" = "host-services/logs/data_sync.log"
    "excel_worker" = "host-services/logs/excel_worker.log"
    "stream_relay" = "host-services/logs/stream_relay.log"
    "looper_health" = "host-services/logs/looper_health.log"
}

$script:GitRepoPath = "C:/Users/pmedlin/Documents/kpk-app"

#region Configuration

function Set-KPKConfig {
    param(
        [string]$Host,
        [string]$Port,
        [string]$User,
        [switch]$Local,
        [int]$Lines
    )
    if ($Host) { $script:KPKConfig.Host = $Host }
    if ($Port) { $script:KPKConfig.Port = $Port }
    if ($User) { $script:KPKConfig.User = $User }
    if ($Local) { $script:KPKConfig.Local = $true }
    if ($Lines -gt 0) { $script:KPKConfig.Lines = $Lines }
}

function Get-KPKConfig {
    return $script:KPKConfig
}

#endregion

#region SSH Execution

function Invoke-KPKCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Command,
        [switch]$RawOutput
    )

    if ($script:KPKConfig.Local) {
        try {
            $result = Invoke-Expression $Command 2>&1
            if ($RawOutput) { return $result }
            return ($result | Out-String).Trim()
        } catch {
            throw "Local command failed: $_"
        }
    }

    $sshHost = "$($script:KPKConfig.User)@$($script:KPKConfig.Host)"
    $sshPort = $script:KPKConfig.Port

    # Base64 encode for safe transport
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($Command)
    $encoded = [Convert]::ToBase64String($bytes)
    $psCmd = "powershell -NoProfile -EncodedCommand $encoded"

    try {
        $result = & ssh -p $sshPort -o BatchMode=yes -o StrictHostKeyChecking=accept-new $sshHost $psCmd 2>&1
        $exitCode = $LASTEXITCODE

        if ($RawOutput) { return $result }
        $output = ($result | Out-String).Trim()
        if ($exitCode -ne 0 -and -not $output) {
            throw "SSH command failed with exit code $exitCode"
        }
        return $output
    } catch {
        throw "SSH connection failed: $_"
    }
}

function Resolve-ContainerName {
    param([string]$Name)
    if ($Name.StartsWith("kpk-app")) { return $Name }
    if ($script:ContainerShortNames.ContainsKey($Name)) {
        return $script:ContainerShortNames[$Name]
    }
    return "kpk-app_${Name}_1"
}

#endregion

#region Status Commands

function Get-KPKStatus {
    param(
        [switch]$SkipLoopStatus
    )

    Write-Host "=== Docker Containers ===" -ForegroundColor Cyan

    $containers = Get-KPKContainerList -Detailed
    foreach ($c in $containers) {
        $icon = if ($c.State -eq "running") { "[+]" } else { "[-]" }
        $color = if ($c.State -eq "running") { "Green" } else { "Red" }
        Write-Host "$icon " -ForegroundColor $color -NoNewline
        Write-Host ("{0,-30} {1}" -f $c.Name, $c.Status)
    }

    Write-Host ""
    Write-Host "=== Host Services ===" -ForegroundColor Cyan

    $services = Get-KPKHostServiceList -Detailed
    foreach ($s in $services) {
        $icon = if ($s.Running) { "[+]" } else { "[-]" }
        $color = if ($s.Running) { "Green" } else { "Red" }
        Write-Host "$icon " -ForegroundColor $color -NoNewline
        Write-Host ("{0,-20}" -f $s.Name) -NoNewline
        if ($s.Running -and $s.ProcessId) {
            Write-Host " (PID: $($s.ProcessId))"
        } else {
            Write-Host ""
        }
    }

    # Include loop function status unless skipped
    if (-not $SkipLoopStatus) {
        Write-Host ""
        Get-KPKLoopStatus
    }
}

function Get-KPKLoopStatus {
    <#
    .SYNOPSIS
    Get detailed status of data sync loop functions from the web API.

    .DESCRIPTION
    Queries the kpkapp.lan API for loop function status, showing which
    functions are healthy, failed, or stale.
    #>

    Write-Host "=== Loop Functions ===" -ForegroundColor Cyan

    # Call the API via SSH on the server using curl.exe (not the PowerShell alias)
    $apiCmd = 'curl.exe -sk https://localhost/core/api/loop-status/ 2>&1'

    try {
        $output = Invoke-KPKCommand -Command $apiCmd

        if (-not $output) {
            Write-Host "[-] " -ForegroundColor Red -NoNewline
            Write-Host "Unable to reach loop status API"
            return
        }

        $data = $output | ConvertFrom-Json

        if ($data.status -eq "error") {
            Write-Host "[-] " -ForegroundColor Red -NoNewline
            Write-Host "API error: $($data.error)"
            return
        }

        # Show overall status
        $overallIcon = switch ($data.status) {
            "up" { "[+]" }
            "degraded" { "[!]" }
            "down" { "[-]" }
            default { "[?]" }
        }
        $overallColor = switch ($data.status) {
            "up" { "Green" }
            "degraded" { "Yellow" }
            "down" { "Red" }
            default { "Gray" }
        }
        Write-Host "$overallIcon " -ForegroundColor $overallColor -NoNewline
        Write-Host "Overall: $($data.status.ToUpper()) ($($data.healthy_count)/$($data.function_count) healthy)"

        # Show each function
        foreach ($func in $data.functions) {
            $icon = if ($func.is_healthy) { "[+]" } else { "[-]" }
            $color = if ($func.is_healthy) { "Green" } elseif ($func.is_error) { "Red" } else { "Yellow" }

            Write-Host "$icon " -ForegroundColor $color -NoNewline

            # Format the time ago
            $timeAgo = if ($func.minutes_ago -ge 0) {
                if ($func.minutes_ago -lt 60) {
                    "$($func.minutes_ago) min ago"
                } else {
                    "$([math]::Floor($func.minutes_ago / 60)) hr ago"
                }
            } else {
                "unknown"
            }

            Write-Host ("{0,-30}" -f $func.function_name) -NoNewline

            if ($func.is_error) {
                # Truncate long error messages
                $result = $func.function_result
                if ($result.Length -gt 40) {
                    $result = $result.Substring(0, 37) + "..."
                }
                Write-Host " $result" -ForegroundColor Red -NoNewline
                Write-Host " ($timeAgo)" -ForegroundColor Gray
            } elseif ($func.is_stale) {
                Write-Host " STALE ($timeAgo)" -ForegroundColor Yellow
            } else {
                Write-Host " $timeAgo" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Host "[-] " -ForegroundColor Red -NoNewline
        Write-Host "Failed to get loop status: $_"
    }
}

function Start-KPKMissing {
    Write-Host "Checking Docker status..." -ForegroundColor Yellow

    $dockerCheckCmd = '$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue; if (-not $dockerProcess) { Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" }; $timeout = 60; $elapsed = 0; while ($elapsed -lt $timeout) { $result = docker info 2>&1; if ($LASTEXITCODE -eq 0) { Write-Output "Docker is ready"; break }; Start-Sleep -Seconds 2; $elapsed += 2 }; if ($elapsed -ge $timeout) { throw "Docker failed to start" }'
    Invoke-KPKCommand -Command $dockerCheckCmd | Write-Host
    Write-Host "Docker is ready" -ForegroundColor Green

    Write-Host "Checking container statuses..." -ForegroundColor Yellow
    $containers = Get-KPKContainerList -Detailed
    $stoppedContainers = $containers | Where-Object { $_.State -ne "running" }

    if ($stoppedContainers.Count -eq 0) {
        Write-Host "All containers already running" -ForegroundColor Green
    } else {
        foreach ($c in $stoppedContainers) {
            Write-Host "Starting container: $($c.Name)" -ForegroundColor Yellow
            Start-KPKContainer -Name $c.Name
            Write-Host "  Started: $($c.Name)" -ForegroundColor Green
        }
    }

    Write-Host "Checking host service statuses..." -ForegroundColor Yellow
    $services = Get-KPKHostServiceList -Detailed
    $stoppedServices = $services | Where-Object { -not $_.Running }

    if ($stoppedServices.Count -eq 0) {
        Write-Host "All host services already running" -ForegroundColor Green
    } else {
        foreach ($s in $stoppedServices) {
            Write-Host "Starting service: $($s.Name)" -ForegroundColor Yellow
            try {
                Start-KPKHostService -Name $s.Name
                Write-Host "  Started: $($s.Name)" -ForegroundColor Green
            } catch {
                Write-Host "  ERROR: $_" -ForegroundColor Red
            }
        }
    }
    Write-Host "Done!" -ForegroundColor Green
}

function Start-KPKAll {
    Write-Host "Performing cold start..." -ForegroundColor Yellow

    Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
    $startDockerCmd = 'Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"; $timeout = 60; $elapsed = 0; while ($elapsed -lt $timeout) { $result = docker info 2>&1; if ($LASTEXITCODE -eq 0) { Write-Output "Docker is ready"; break }; Start-Sleep -Seconds 2; $elapsed += 2 }; if ($elapsed -ge $timeout) { throw "Docker failed to start" }'
    Invoke-KPKCommand -Command $startDockerCmd | Write-Host
    Write-Host "Docker is ready" -ForegroundColor Green

    Write-Host "Starting containers..." -ForegroundColor Yellow
    $cmd = 'Set-Location "C:/Users/pmedlin/Documents/kpk-app"; docker compose -f docker-compose-PROD.yml up -d'
    Invoke-KPKCommand -Command $cmd | Write-Host
    Write-Host "Containers started" -ForegroundColor Green

    foreach ($svc in $script:HostServices.Keys) {
        Write-Host "Starting service: $svc" -ForegroundColor Yellow
        try {
            Start-KPKHostService -Name $svc
            Write-Host "  Started: $svc" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR: $_" -ForegroundColor Red
        }
    }
    Write-Host "Cold start complete!" -ForegroundColor Green
}

function Stop-KPKAll {
    Write-Host "Stopping all services..." -ForegroundColor Yellow

    foreach ($svc in $script:HostServices.Keys) {
        Write-Host "Stopping service: $svc" -ForegroundColor Yellow
        try { Stop-KPKHostService -Name $svc } catch { }
    }

    Write-Host "Stopping containers..." -ForegroundColor Yellow
    $cmd = 'Set-Location "C:/Users/pmedlin/Documents/kpk-app"; docker compose -f docker-compose-PROD.yml down'
    Invoke-KPKCommand -Command $cmd | Write-Host
    Write-Host "All services stopped." -ForegroundColor Green
}

#endregion

#region Container Commands

function Get-KPKContainerList {
    param([switch]$Detailed)

    $cmd = 'docker ps -a --filter "name=kpk-app" --format "{{json .}}"'
    $output = Invoke-KPKCommand -Command $cmd

    $containers = @()
    foreach ($line in ($output -split "`n")) {
        $line = $line.Trim()
        if (-not $line) { continue }
        try {
            $json = $line | ConvertFrom-Json
            $containers += [PSCustomObject]@{
                Name = $json.Names
                ID = $json.ID
                Image = $json.Image
                Status = $json.Status
                State = $json.State
                Ports = $json.Ports
            }
        } catch { continue }
    }

    if ($Detailed) { return $containers }
    $containers | ForEach-Object { $_.Name }
}

function Get-KPKContainerLogs {
    param(
        [Parameter(Mandatory)][string]$Name,
        [int]$Lines = 100
    )
    $fullName = Resolve-ContainerName -Name $Name
    $cmd = "docker logs --tail $Lines $fullName 2>&1"
    Invoke-KPKCommand -Command $cmd
}

function Start-KPKContainer {
    param([Parameter(Mandatory)][string]$Name)
    $fullName = Resolve-ContainerName -Name $Name
    Write-Host "Starting container $fullName..." -ForegroundColor Yellow
    Invoke-KPKCommand -Command "docker start $fullName" | Out-Null
    Write-Host "Started." -ForegroundColor Green
}

function Stop-KPKContainer {
    param([Parameter(Mandatory)][string]$Name)
    $fullName = Resolve-ContainerName -Name $Name
    Write-Host "Stopping container $fullName..." -ForegroundColor Yellow
    Invoke-KPKCommand -Command "docker stop $fullName" | Out-Null
    Write-Host "Stopped." -ForegroundColor Green
}

function Restart-KPKContainer {
    param([Parameter(Mandatory)][string]$Name)
    $fullName = Resolve-ContainerName -Name $Name
    Write-Host "Restarting container $fullName..." -ForegroundColor Yellow
    Invoke-KPKCommand -Command "docker restart $fullName" | Out-Null
    Write-Host "Restarted." -ForegroundColor Green
}

#endregion

#region Host Service Commands

function Get-KPKHostServiceList {
    param([switch]$Detailed)

    $services = @()
    foreach ($svc in @("data_sync", "excel_worker", "stream_relay", "looper_health")) {
        $scriptName = switch ($svc) {
            "data_sync" { "data_sync.py" }
            "excel_worker" { "excel_worker.py" }
            "stream_relay" { "stream_relay.py" }
            "looper_health" { "looper_health.py" }
        }

        $checkCmd = '$result = wmic process where "name like ''%python%''" get ProcessId,CommandLine /format:csv 2>$null | Select-String ''' + $scriptName + '''; if ($result) { $parts = ($result -split '',''); @{ProcessId=[int]$parts[-1]} | ConvertTo-Json -Compress } else { Write-Output ''none'' }'
        $output = Invoke-KPKCommand -Command $checkCmd

        $running = $false
        $pid = $null

        if ($output -and $output -ne "none" -and $output -ne "null") {
            try {
                $procInfo = $output | ConvertFrom-Json
                if ($procInfo.ProcessId -and $procInfo.ProcessId -gt 0) {
                    $running = $true
                    $pid = $procInfo.ProcessId
                }
            } catch { }
        }

        $services += [PSCustomObject]@{
            Name = $svc
            Running = $running
            ProcessId = $pid
        }
    }

    if ($Detailed) { return $services }
    $services | ForEach-Object { $_.Name }
}

function Get-KPKHostServiceLogs {
    param(
        [Parameter(Mandatory)][string]$Name,
        [int]$Lines = 100
    )

    if (-not $script:HostServiceLogs.ContainsKey($Name)) {
        throw "Unknown service: $Name"
    }

    $logFile = $script:HostServiceLogs[$Name]
    $cmd = '$appRoot = "C:/Users/pmedlin/Documents/kpk-app"; $path = Join-Path $appRoot "' + $logFile + '"; if (Test-Path $path) { Get-Content -Path $path -Tail ' + $Lines + ' } else { Write-Output "Log file not found: $path" }'
    Invoke-KPKCommand -Command $cmd
}

function Start-KPKHostService {
    param([Parameter(Mandatory)][string]$Name)

    if (-not $script:HostServices.ContainsKey($Name)) {
        throw "Unknown service: $Name"
    }

    $path = $script:HostServices[$Name]
    # PsExec writes to stderr even on success, so we redirect 2>&1 and check exit code
    $cmd = @'
$py = "C:/Users/pmedlin/AppData/Local/Programs/Python/Python311/pythonw.exe"
$script = "C:/Users/pmedlin/Documents/kpk-app/YOURPATH"
if (-not (Test-Path $py)) { throw "Python not found at $py" }
if (-not (Test-Path $script)) { throw "Script not found: $script" }
$sessionId = $null
$queryResult = query user 2>$null | Select-String "pmedlin"
if ($queryResult) {
    $parts = $queryResult -split '\s+'
    foreach ($part in $parts) {
        if ($part -match '^\d+$' -and [int]$part -gt 0) { $sessionId = $part; break }
    }
}
if (-not $sessionId) { $sessionId = (Get-Process -Id $PID).SessionId; if ($sessionId -eq 0) { $sessionId = 1 } }
$psexec = "C:/Windows/System32/PsExec.exe"
if (-not (Test-Path $psexec)) { $psexec = "C:/SysinternalsSuite/PsExec.exe" }
if (-not (Test-Path $psexec)) { $psexec = "C:/Tools/PsExec.exe" }
if (Test-Path $psexec) {
    $vbsPath = "C:/Users/pmedlin/Documents/kpk-app/host-services/launcher.vbs"
    $vbsContent = "Set objShell = CreateObject(`"WScript.Shell`")`r`nSet objEnv = objShell.Environment(`"Process`")`r`nobjEnv(`"USERPROFILE`") = `"C:\Users\pmedlin`"`r`nobjEnv(`"HOME`") = `"C:\Users\pmedlin`"`r`nobjEnv(`"HOMEPATH`") = `"\Users\pmedlin`"`r`nobjEnv(`"HOMEDRIVE`") = `"C:`"`r`nobjShell.CurrentDirectory = `"C:\Users\pmedlin\Documents\kpk-app`"`r`nobjShell.Run `"`"`"$py`"`" `"`"$script`"`"`", 0, False"
    Set-Content -Path $vbsPath -Value $vbsContent -Force
    $null = & $psexec -accepteula -i $sessionId -d wscript.exe $vbsPath 2>&1
    Write-Output "Started via PsExec (session $sessionId)"
} else {
    $p = Start-Process -FilePath $py -ArgumentList $script -WorkingDirectory "C:/Users/pmedlin/Documents/kpk-app" -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    if ($p.HasExited) { throw "Process died immediately" }
    Write-Output "Started (PID: $($p.Id))"
}
'@
    $cmd = $cmd -replace 'YOURPATH', $path
    $output = Invoke-KPKCommand -Command $cmd
    Write-Host $output -ForegroundColor Green
}

function Stop-KPKHostService {
    param([Parameter(Mandatory)][string]$Name)

    if (-not $script:HostServices.ContainsKey($Name)) {
        throw "Unknown service: $Name"
    }

    $cmd = '$procs = wmic process where "name like ''%python%'' and commandline like ''%' + $Name + '%''" get ProcessId /format:csv 2>$null | Select-String ''\d+'' | ForEach-Object { ($_ -split '','')[-1].Trim() }; foreach ($p in $procs) { if ($p) { taskkill /F /T /PID $p 2>$null } }'
    Invoke-KPKCommand -Command $cmd
    Write-Host "Stopped." -ForegroundColor Green
}

#endregion

#region Backup Commands

function New-KPKBackup {
    Write-Host "Creating database backup..." -ForegroundColor Yellow
    $cmd = '& "C:/Users/pmedlin/Documents/kpk-app/local_machine_scripts/batch_scripts/backup_and_copy.bat"'
    $output = Invoke-KPKCommand -Command $cmd
    if ($output) { Write-Host $output }
    Write-Host "Backup created." -ForegroundColor Green
}

function Get-KPKBackupList {
    $cmd = "Get-ChildItem -Path 'M:\kpkapp\backups' -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 10 -ExpandProperty Name"
    $output = Invoke-KPKCommand -Command $cmd
    $backups = ($output -split "`n") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    if ($backups.Count -eq 0) { Write-Host "No backups found." }
    else { $backups }
}

function Restore-KPKBackup {
    param([Parameter(Mandatory)][string]$Name)
    Write-Host "Restoring from backup $Name..." -ForegroundColor Yellow
    $cmd = '& "C:/Users/pmedlin/Documents/kpk-app/local_machine_scripts/batch_scripts/db_restore_latest_backup.bat"'
    Invoke-KPKCommand -Command $cmd | Write-Host
    Write-Host "Backup restored." -ForegroundColor Green
}

#endregion

#region Git Commands

function Get-KPKGitStatus {
    $repoPath = $script:GitRepoPath
    Invoke-KPKCommand -Command "git config --global --add safe.directory `"$repoPath`" 2>`$null; `$true" | Out-Null

    $branch = Invoke-KPKCommand -Command "git -C `"$repoPath`" rev-parse --abbrev-ref HEAD"
    Write-Host "Branch: $branch"

    $log = Invoke-KPKCommand -Command "git -C `"$repoPath`" log -1 --format=`"%h %s`""
    Write-Host "Commit: $log"

    try {
        $behind = Invoke-KPKCommand -Command "git -C `"$repoPath`" rev-list --count HEAD..origin/$branch 2>`$null"
        if ($behind -and [int]$behind -gt 0) {
            Write-Host "Behind: $behind commits" -ForegroundColor Yellow
        }
    } catch { }

    try {
        $ahead = Invoke-KPKCommand -Command "git -C `"$repoPath`" rev-list --count origin/${branch}..HEAD 2>`$null"
        if ($ahead -and [int]$ahead -gt 0) {
            Write-Host "Ahead: $ahead commits" -ForegroundColor Cyan
        }
    } catch { }

    $status = Invoke-KPKCommand -Command "git -C `"$repoPath`" status --porcelain"
    if ($status) {
        Write-Host "Has uncommitted changes" -ForegroundColor Yellow
    }
}

function Invoke-KPKGitFetch {
    Write-Host "Fetching from origin..." -ForegroundColor Yellow
    $repoPath = $script:GitRepoPath
    $cmd = 'git config --global --add safe.directory "' + $repoPath + '" 2>$null; $env:GIT_TERMINAL_PROMPT=0; $env:GIT_SSH_COMMAND="ssh -i C:/Users/pmedlin/.ssh/id_ed25519 -o IdentitiesOnly=yes"; git -C "' + $repoPath + '" fetch origin 2>&1'
    $output = Invoke-KPKCommand -Command $cmd
    if ($output) { Write-Host $output }
    Write-Host "Fetch complete." -ForegroundColor Green
}

function Invoke-KPKGitPull {
    Write-Host "Pulling from origin/main..." -ForegroundColor Yellow
    $repoPath = $script:GitRepoPath
    $cmd = 'git config --global --add safe.directory "' + $repoPath + '" 2>$null; $env:GIT_TERMINAL_PROMPT=0; $env:GIT_SSH_COMMAND="ssh -i C:/Users/pmedlin/.ssh/id_ed25519 -o IdentitiesOnly=yes"; git -C "' + $repoPath + '" pull origin main 2>&1'
    try {
        $output = Invoke-KPKCommand -Command $cmd
        Write-Host $output
        Write-Host "Pull complete." -ForegroundColor Green
    } catch {
        # Git writes progress to stderr which PowerShell sees as errors
        # Check if it's actually an error or just git's normal output
        $errMsg = $_.Exception.Message
        if ($errMsg -match "From github\.com" -or $errMsg -match "Already up to date" -or $errMsg -match "Updating .+\.\..+") {
            # This is normal git output, not an error
            Write-Host ($errMsg -replace "^SSH connection failed: ", "")
            Write-Host "Pull complete." -ForegroundColor Green
        } else {
            throw $_
        }
    }
}

function Invoke-KPKCollectStatic {
    Write-Host "Running collectstatic..." -ForegroundColor Yellow
    $cmd = 'docker exec kpk-app_app_blue_1 python manage.py collectstatic --noinput 2>&1'
    Invoke-KPKCommand -Command $cmd
}

#endregion

#region Nginx Commands

function Invoke-KPKNginxReload {
    Write-Host "Reloading nginx config..." -ForegroundColor Yellow
    Invoke-KPKCommand -Command 'docker cp "C:/Users/pmedlin/Documents/kpk-app/nginx/nginx.conf" kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf' | Out-Null
    Invoke-KPKCommand -Command 'docker restart kpk-app_nginx_1' | Out-Null
    Write-Host "Nginx config reloaded." -ForegroundColor Green
}

#endregion

Export-ModuleMember -Function @(
    'Set-KPKConfig', 'Get-KPKConfig', 'Invoke-KPKCommand',
    'Get-KPKStatus', 'Get-KPKLoopStatus', 'Start-KPKMissing', 'Start-KPKAll', 'Stop-KPKAll',
    'Get-KPKContainerList', 'Get-KPKContainerLogs', 'Start-KPKContainer', 'Stop-KPKContainer', 'Restart-KPKContainer',
    'Get-KPKHostServiceList', 'Get-KPKHostServiceLogs', 'Start-KPKHostService', 'Stop-KPKHostService',
    'New-KPKBackup', 'Get-KPKBackupList', 'Restore-KPKBackup',
    'Get-KPKGitStatus', 'Invoke-KPKGitFetch', 'Invoke-KPKGitPull', 'Invoke-KPKCollectStatic',
    'Invoke-KPKNginxReload'
)
