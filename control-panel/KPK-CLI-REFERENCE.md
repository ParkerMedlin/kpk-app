# KPK CLI Reference

## Implementations

Two implementations are available with identical command structures:

| Version | Location | Notes |
|---------|----------|-------|
| **Go binary** | `M:\kpkapp\control-panel\kpk.exe` | Standalone executable |
| **PowerShell** | `control-panel\ps\` | Uses native Windows SSH (avoids AV false positives) |

### Go Binary
```
kpk status
kpk container logs blue
```

### PowerShell Script
```powershell
.\kpk.ps1 status
.\kpk.ps1 container logs blue
```

### Installing PowerShell Version
```powershell
# Install for current user (adds to PATH)
.\Install-KPK.ps1

# Install for all users (requires admin)
.\Install-KPK.ps1 -AllUsers

# After install, use from cmd.exe:
kpk status
```

## Connection

SSH uses current Windows username by default (uses SSH key at `~/.ssh/id_rsa`).
Override with `-u <username>` if needed. Use `--local` when running on the server.

## Commands

```
kpk                                     # Show this help
kpk gui                                 # Launch GUI

kpk status                              # Show containers, services, AND loop functions
kpk loop status                         # Show loop function status only
kpk start-missing                       # Start only stopped services
kpk start-all                           # Cold start everything
kpk stop-all                            # Stop all services

kpk container list                      # List containers
kpk container logs <name>               # View logs (-n 50 for line count)
kpk container start <name>              # Start container
kpk container stop <name>               # Stop container
kpk container restart <name>            # Restart container

kpk service list                        # List host services
kpk service logs <name>                 # View service logs
kpk service start <name>                # Start service
kpk service stop <name>                 # Stop service

kpk backup create                       # Create database backup
kpk backup list                         # List available backups
kpk backup restore <name>               # Restore from backup

kpk git status                          # Show git status
kpk git fetch                           # Fetch from origin
kpk git pull                            # Pull from origin/main
kpk git collectstatic                   # Run Django collectstatic

kpk nginx reload                        # Hot-reload nginx config

kpk status -u otheruser                 # Override username
kpk status --local                      # Local mode (on server)
```

## Container Short Names

| Short | Full Name |
|-------|-----------|
| `blue`, `app_blue` | `kpk-app_app_blue_1` |
| `green`, `app_green` | `kpk-app_app_green_1` |
| `nginx` | `kpk-app_nginx_1` |
| `db`, `postgres` | `kpk-app_postgres_1` |
| `redis` | `kpk-app_redis_1` |
| `celery` | `kpk-app_celery_worker_1` |
| `celery_beat` | `kpk-app_celery_beat_1` |

## Host Services

`data_sync`, `excel_worker`, `stream_relay`, `looper_health`

## Output

- `status` shows `[+]` for running, `[-]` for stopped
- Commands print progress and success/error messages to stdout/stderr
- Exit code 0 = success, 1 = error

## Loop Function Status

The `status` command now includes loop function health from the Django API (`/core/api/loop-status/`):
- **[+] UP** - All functions healthy and running recently
- **[!] DEGRADED** - Some functions have errors but timestamps are recent
- **[-] DOWN** - Functions are stale (not updated in 5+ minutes)

Individual function status shows:
- Function name
- Time since last execution (e.g., "2 min ago")
- Error message if the function failed

This provides visibility into the data sync loop beyond just "is the Python process alive".

## PowerShell Module Cmdlets

After installing, you can also `Import-Module KPK` and use cmdlets directly:

```powershell
# Configuration
Set-KPKConfig -Host "192.168.178.169" -User "myuser"
Set-KPKConfig -Local    # Switch to local mode

# Status
Get-KPKStatus                       # Full status including loop functions
Get-KPKStatus -SkipLoopStatus       # Skip loop function check (faster)
Get-KPKLoopStatus                   # Loop functions only
Start-KPKMissing                    # Same as: kpk start-missing
Start-KPKAll                        # Same as: kpk start-all
Stop-KPKAll                         # Same as: kpk stop-all

# Containers
Get-KPKContainerList
Get-KPKContainerLogs -Name blue -Lines 50
Start-KPKContainer -Name blue
Stop-KPKContainer -Name blue
Restart-KPKContainer -Name blue

# Host Services
Get-KPKHostServiceList
Get-KPKHostServiceLogs -Name data_sync -Lines 50
Start-KPKHostService -Name data_sync
Stop-KPKHostService -Name data_sync

# Backups
New-KPKBackup
Get-KPKBackupList
Restore-KPKBackup -Name "backup_name"

# Git
Get-KPKGitStatus
Invoke-KPKGitFetch
Invoke-KPKGitPull
Invoke-KPKCollectStatic

# Nginx
Invoke-KPKNginxReload
```
