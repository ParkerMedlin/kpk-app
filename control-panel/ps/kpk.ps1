<#
.SYNOPSIS
KPK Control Panel CLI - PowerShell version
Uses native Windows OpenSSH (no AV issues)

.DESCRIPTION
Manages Docker containers and host services on the KPK server.

.EXAMPLE
.\kpk.ps1 status
.\kpk.ps1 container logs blue -n 50
.\kpk.ps1 git pull
#>

param(
    [Parameter(Position=0)]
    [string]$Command,

    [Parameter(Position=1)]
    [string]$SubCommand,

    [Parameter(Position=2)]
    [string]$Arg1,

    [string][Alias("H")]$Server = "192.168.178.169",
    [string][Alias("p")]$Port = "22",
    [string][Alias("u")]$User = $env:USERNAME,
    [int][Alias("n")]$Lines = 100,
    [switch]$Local
)

$ErrorActionPreference = 'Stop'

# Import the module
$modulePath = Join-Path $PSScriptRoot "KPK.psm1"
if (-not (Test-Path $modulePath)) {
    Write-Error "KPK.psm1 not found at $modulePath"
    exit 1
}
Import-Module $modulePath -Force

# Configure connection
Set-KPKConfig -Host $Server -Port $Port -User $User -Lines $Lines
if ($Local) { Set-KPKConfig -Local }

function Show-Help {
    Write-Host "KPK Control Panel v1.0 (PowerShell)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\kpk.ps1 [command] [args] [flags]"
    Write-Host "  .\kpk.ps1                          # Show this help"
    Write-Host ""
    Write-Host "CONNECTION FLAGS:" -ForegroundColor Yellow
    Write-Host "  -H, -Server <host>     SSH host (default: 192.168.178.169)"
    Write-Host "  -p, -Port <port>       SSH port (default: 22)"
    Write-Host "  -u, -User <user>       SSH username (default: current user)"
    Write-Host "  -Local                 Use local mode instead of SSH"
    Write-Host "  -n, -Lines <n>         Number of log lines (default: 100)"
    Write-Host ""
    Write-Host "COMMANDS:" -ForegroundColor Yellow
    Write-Host "  status                 Show containers, services, and loop functions"
    Write-Host "  loop status            Show loop function status only"
    Write-Host "  start-missing          Start only stopped services"
    Write-Host "  start-all              Cold start everything"
    Write-Host "  stop-all               Stop all services and containers"
    Write-Host ""
    Write-Host "  container list                  List all containers"
    Write-Host "  container logs <name>           Show container logs"
    Write-Host "  container start <name>          Start a container"
    Write-Host "  container stop <name>           Stop a container"
    Write-Host "  container restart <name>        Restart a container"
    Write-Host ""
    Write-Host "  service list                    List all host services"
    Write-Host "  service logs <name>             Show service logs"
    Write-Host "  service start <name>            Start a host service"
    Write-Host "  service stop <name>             Stop a host service"
    Write-Host ""
    Write-Host "  backup create                   Create database backup"
    Write-Host "  backup list                     List available backups"
    Write-Host "  backup restore <name>           Restore from backup"
    Write-Host ""
    Write-Host "  git status                      Show git status"
    Write-Host "  git fetch                       Fetch from origin"
    Write-Host "  git pull                        Pull from origin/main"
    Write-Host "  git collectstatic               Run Django collectstatic"
    Write-Host ""
    Write-Host "  nginx reload                    Hot-reload nginx config"
    Write-Host ""
    Write-Host "  help                            Show this help"
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host "  .\kpk.ps1 status"
    Write-Host "  .\kpk.ps1 start-missing"
    Write-Host "  .\kpk.ps1 container logs app_blue -n 50"
    Write-Host "  .\kpk.ps1 service start data_sync"
    Write-Host "  .\kpk.ps1 git pull"
    Write-Host "  .\kpk.ps1 status -Local               # Local mode (on server)"
    Write-Host "  .\kpk.ps1 status -u otheruser         # Override username"
    Write-Host ""
    Write-Host "CONTAINER SHORT NAMES:" -ForegroundColor Yellow
    Write-Host "  app_blue, blue    -> kpk-app_app_blue_1"
    Write-Host "  app_green, green  -> kpk-app_app_green_1"
    Write-Host "  nginx             -> kpk-app_nginx_1"
    Write-Host "  postgres, db      -> kpk-app_postgres_1"
    Write-Host "  redis             -> kpk-app_redis_1"
    Write-Host "  celery            -> kpk-app_celery_worker_1"
    Write-Host ""
    Write-Host "HOST SERVICES:" -ForegroundColor Yellow
    Write-Host "  data_sync, excel_worker, stream_relay, looper_health"
}

# Main command dispatch
try {
    switch ($Command) {
        "" { Show-Help }
        "help" { Show-Help }
        "-h" { Show-Help }
        "--help" { Show-Help }

        "status" { Get-KPKStatus }
        "start-missing" { Start-KPKMissing }
        "start-all" { Start-KPKAll }
        "cold-start" { Start-KPKAll }
        "stop-all" { Stop-KPKAll }

        "container" {
            switch ($SubCommand) {
                "list" { Get-KPKContainerList }
                "logs" {
                    if (-not $Arg1) { throw "Usage: container logs <name>" }
                    Get-KPKContainerLogs -Name $Arg1 -Lines $Lines
                }
                "start" {
                    if (-not $Arg1) { throw "Usage: container start <name>" }
                    Start-KPKContainer -Name $Arg1
                }
                "stop" {
                    if (-not $Arg1) { throw "Usage: container stop <name>" }
                    Stop-KPKContainer -Name $Arg1
                }
                "restart" {
                    if (-not $Arg1) { throw "Usage: container restart <name>" }
                    Restart-KPKContainer -Name $Arg1
                }
                default { throw "Unknown container command: $SubCommand" }
            }
        }

        "service" {
            switch ($SubCommand) {
                "list" { Get-KPKHostServiceList }
                "logs" {
                    if (-not $Arg1) { throw "Usage: service logs <name>" }
                    Get-KPKHostServiceLogs -Name $Arg1 -Lines $Lines
                }
                "start" {
                    if (-not $Arg1) { throw "Usage: service start <name>" }
                    Start-KPKHostService -Name $Arg1
                }
                "stop" {
                    if (-not $Arg1) { throw "Usage: service stop <name>" }
                    Stop-KPKHostService -Name $Arg1
                }
                default { throw "Unknown service command: $SubCommand" }
            }
        }

        "backup" {
            switch ($SubCommand) {
                "create" { New-KPKBackup }
                "list" { Get-KPKBackupList }
                "restore" {
                    if (-not $Arg1) { throw "Usage: backup restore <name>" }
                    Restore-KPKBackup -Name $Arg1
                }
                default { throw "Unknown backup command: $SubCommand" }
            }
        }

        "git" {
            switch ($SubCommand) {
                "status" { Get-KPKGitStatus }
                "fetch" { Invoke-KPKGitFetch }
                "pull" { Invoke-KPKGitPull }
                "collectstatic" { Invoke-KPKCollectStatic }
                default { throw "Unknown git command: $SubCommand" }
            }
        }

        "nginx" {
            switch ($SubCommand) {
                "reload" { Invoke-KPKNginxReload }
                default { throw "Unknown nginx command: $SubCommand" }
            }
        }

        "loop" {
            switch ($SubCommand) {
                "status" { Get-KPKLoopStatus }
                "" { Get-KPKLoopStatus }
                default { throw "Unknown loop command: $SubCommand" }
            }
        }

        default {
            Write-Error "Unknown command: $Command"
            Write-Host "Run '.\kpk.ps1 help' for usage"
            exit 1
        }
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
