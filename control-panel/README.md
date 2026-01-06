# KPK Control Panel

A lightweight, portable control panel for managing the KPK App infrastructure via SSH.

**Version:** 0.4.1

## Features

- **View Status** - Real-time status of Docker containers and host services
- **View Logs** - Tail logs from any container or host service
- **Start/Stop Services** - Control individual containers and host services
- **Container Exec** - Open interactive shell into any container
- **Database Backup** - Create backups to network share (\\\\KinPak-Svr1\\apps\\kpkapp\\backups\\)
- **Database Restore** - Restore from available backups
- **Start Missing** - Start only services that aren't currently running
- **Stop All** - Graceful shutdown of all services (kills process trees to clean up child processes)
- **Reload Nginx Config** - Hot-reload nginx configuration without restart
- **Git Control** - Remote git management (pull updates, view status, run collectstatic)
- **CLI Mode** - All operations available via command-line for scripting and automation
- **AI Assistant** - Claude-powered chat assistant that can diagnose issues, check logs, and fix problems with user confirmation

## CLI Usage

The control panel supports both GUI and CLI modes in a single binary. Running without arguments shows the help reference; use `kpk gui` to launch the GUI.

### Connection Flags

```
-H, --host <host>      SSH host (default: 192.168.178.169)
-p, --port <port>      SSH port (default: 22)
-u, --user <user>      SSH username (default: current user)
-P, --password <pass>  SSH password (or use SSH key)
--local                Use local mode instead of SSH
-n, --lines <n>        Number of log lines (default: 100)
```

### Commands

```powershell
# Show all containers and host services
kpk status

# Start only stopped services
kpk start-missing

# Cold start everything (Docker + all services)
kpk start-all

# Stop all services and containers
kpk stop-all

# Container operations
kpk container list
kpk container logs app_blue -n 50
kpk container start app_blue
kpk container stop app_blue
kpk container restart app_blue

# Host service operations
kpk service list
kpk service logs data_sync
kpk service start data_sync
kpk service stop data_sync

# Database backup operations
kpk backup create
kpk backup list
kpk backup restore <backup-name>

# Git operations
kpk git status
kpk git fetch
kpk git pull
kpk git collectstatic

# Nginx
kpk nginx reload

# Local mode (run on the server itself)
kpk status --local

# Override username if needed
kpk status -u otheruser

# Launch GUI
kpk gui
```

### Container Short Names

For convenience, container names can be shortened:

| Short Name | Full Name |
|------------|-----------|
| `app_blue`, `blue` | `kpk-app_app_blue_1` |
| `app_green`, `green` | `kpk-app_app_green_1` |
| `nginx` | `kpk-app_nginx_1` |
| `postgres`, `db` | `kpk-app_postgres_1` |
| `redis` | `kpk-app_redis_1` |
| `celery` | `kpk-app_celery_worker_1` |

## AI Assistant Setup

The AI Assistant feature requires an Anthropic API key:

1. Copy `secrets.go.example` to `secrets.go`
2. Replace `YOUR-KEY-HERE` with your Anthropic API key
3. Rebuild the application

The `secrets.go` file is gitignored and will not be committed.

**Usage:** Click the "AI Assistant" button in the GUI header to open the chat panel. Ask questions like:
- "What's the status of the app?"
- "Why isn't data_sync running?"
- "Check the app_blue logs for errors"
- "Start missing services"

The assistant will check statuses, read logs, and suggest fixes. Write operations (start/stop/restart) require confirmation before execution.

## Requirements

- Go 1.23+ (for building)
- SSH access to the KPK App server
- OpenSSH server running on target machine (Windows 10+ has this built-in)
- **PsExec** on target server (for starting host services with system tray icons)
- Python 3.11 installed at `C:\Users\pmedlin\AppData\Local\Programs\Python\Python311\`
- ImageMagick (for rebuilding icons, optional)
- MinGW/GCC with windres (for embedding exe icon, optional)

## Building

```powershell
# From the control-panel directory
.\build.bat
```

This will:
1. Build the exe with embedded icon
2. Output to `bin\kpk.exe`
3. Deploy to `M:\kpkapp\control-panel\` (network share)

### Manual Build

```powershell
go mod tidy

# Rebuild icon resources (if icon.png changed)
magick icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
windres -o app.syso app.rc

# Build
go build -ldflags="-s -w -H windowsgui" -o bin\kpk.exe .
```

## Distribution

Built executables are deployed to `M:\kpkapp\control-panel\`:
- `kpk.exe` - The application (GUI + CLI)
- `icon.png` - Application icon (loaded at runtime for taskbar)

Users can run the exe directly from the network share or copy it locally.

## Usage

1. Run `kpk.exe` (or `kpk` from command line)
2. Enter SSH connection details:
   - Host: Server IP or hostname (default: 192.168.178.169)
   - Port: SSH port (default: 22)
   - Username: Your Windows username on the server
   - Password: Your password
3. Click Connect
4. Use the control panel to manage services

## Architecture

```
┌─────────────────────┐         ┌─────────────────────────────────────┐
│  Control Panel      │   SSH   │        KPK App Server               │
│  (this app)         │────────►│  - Docker commands                  │
│                     │   :22   │  - PowerShell (host services)       │
│                     │         │  - File access (logs, backups)      │
└─────────────────────┘         └─────────────────────────────────────┘
```

All operations are executed remotely via SSH. No additional services need to run on the server beyond the standard OpenSSH server.

## File Structure

```
control-panel/
├── main.go       # Entry point, CLI/GUI mode detection, window setup
├── cli.go        # CLI argument parsing and command handlers
├── ssh.go        # SSH connection handling
├── executor.go   # Executor interface (SSH vs Local mode)
├── commands.go   # Remote command execution (Docker, host services, backups)
├── ui.go         # Fyne UI components
├── build.bat     # Build script (builds + deploys to M:\)
├── icon.png      # Application icon (PNG for taskbar)
├── icon.ico      # Application icon (ICO for exe)
├── app.rc        # Windows resource file
├── app.syso      # Compiled resource (auto-included by Go)
├── go.mod        # Go module definition
└── README.md
```

## Security Notes

- Credentials are only held in memory during the session
- SSH connection uses standard authentication (password or key-based)
- Host key verification is currently disabled (TODO: implement proper verification)
- All operations require authenticated SSH connection

## SSH and Host Service Architecture

When connecting via SSH from a different user (e.g., `jdavis`) to manage services that run under another user's session (e.g., `pmedlin`), several challenges arise:

### Key Issues Solved

1. **Path Resolution**: SSH sessions don't inherit the target user's environment. `$env:USERPROFILE` resolves to the SSH user's profile, not `pmedlin`'s. Solution: All paths are hardcoded to `C:/Users/pmedlin/Documents/kpk-app/`.

2. **Environment Variables**: Python scripts use `os.path.expanduser('~')` which resolves based on `USERPROFILE`. Solution: Use a VBS launcher that sets `USERPROFILE`, `HOME`, and working directory before launching Python.

3. **Python PATH**: Python may not be in PATH for SSH sessions. Solution: Use explicit path `C:/Users/pmedlin/AppData/Local/Programs/Python/Python311/pythonw.exe`.

4. **Session Isolation**: Processes started via SSH run in a different Windows session than the interactive desktop. System tray icons (pystray) require the desktop session. Solution: Use **PsExec** with `-i 1 -d` flags to run processes in the interactive session.

5. **Silent Launch**: PsExec with `cmd` or `powershell` opens visible windows. Solution: Use `wscript.exe` to run a VBS script that launches pythonw silently.

6. **Cross-User Process Visibility**: `Get-CimInstance`/`Get-WmiObject` may not see processes in other user sessions. Solution: Use `wmic` for process detection.

7. **Path Encoding**: Backslashes in PowerShell commands can get mangled through SSH base64 encoding. Solution: Use forward slashes (`C:/Users/...`) which PowerShell handles fine.

8. **Child Process Cleanup**: Python `multiprocessing` spawns child processes that become orphans when parent is killed. Solution: Use `taskkill /F /T /PID` (tree kill) to terminate entire process trees.

### PsExec Setup

1. Download PsExec from [Sysinternals](https://docs.microsoft.com/en-us/sysinternals/downloads/psexec)
2. Place `PsExec.exe` in one of these locations on the server:
   - `C:\Windows\System32\PsExec.exe` (recommended)
   - `C:\SysinternalsSuite\PsExec.exe`
   - `C:\Tools\PsExec.exe`

The control panel will automatically detect and use PsExec if available, falling back to regular `Start-Process` (no tray icon) if not found.

### How Host Services Start

```
SSH User (jdavis) ──► SSH to server ──► PowerShell via SSH
                                              │
                                              ▼
                                    Create launcher.vbs
                                    (sets USERPROFILE, HOME, CWD)
                                              │
                                              ▼
                                    PsExec -i 1 -d wscript.exe launcher.vbs
                                              │
                                              ▼
                                    pmedlin's Desktop Session (silent)
                                              │
                                              ▼
                                    pythonw.exe data_sync.py
                                              │
                                              ▼
                                    System Tray Icon appears
```

### How Host Services Stop

```
SSH User (jdavis) ──► SSH to server ──► PowerShell via SSH
                                              │
                                              ▼
                                    wmic process ... get ProcessId
                                    (finds main process PIDs)
                                              │
                                              ▼
                                    taskkill /F /T /PID <pid>
                                    (kills process tree including children)
```

## Host Services

| Service | Script | Description |
|---------|--------|-------------|
| data_sync | `host-services/workers/data_sync.py` | Syncs data from Sage/Excel to PostgreSQL |
| excel_worker | `host-services/workers/excel_worker.py` | Processes Excel automation tasks |
| stream_relay | `host-services/workers/stream_relay.py` | Relays RTSP streams |
| looper_health | `host-services/watchdogs/looper_health.py` | Monitors data_sync health, provides restart endpoints |
| backup_health | `host-services/watchdogs/backup_health.py` | Checks for daily backup at 5:30 PM, alerts via Teams |

## Git Control

The Git Control view provides remote repository management:

| Action | Description |
|--------|-------------|
| Refresh Status | Fetches from origin and shows current branch, commit, and ahead/behind status |
| Git Pull | Pulls latest changes from origin/main |
| Collect Static | Runs `python manage.py collectstatic --noinput` in the app_blue container |

Access Git Control via the "Git Control" button in Quick Actions. Use the "Back" button to return to the main services view.

## TODO

- [ ] SSH key-based authentication option
- [ ] Save connection settings (encrypted)
- [ ] Proper SSH host key verification
- [ ] Blue-green deployment switching
- [ ] Auto-reconnect on connection drop
- [ ] Auto-update check from network share
