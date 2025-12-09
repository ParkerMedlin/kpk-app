# KPK Control Panel

A lightweight, portable control panel for managing the KPK App infrastructure via SSH.

## Features

- **View Status** - Real-time status of Docker containers and host services
- **View Logs** - Tail logs from any container or host service
- **Start/Stop Services** - Control individual containers and host services
- **Container Exec** - Open interactive shell into any container
- **Database Backup** - Create backups to M:\kpkapp\backups\
- **Database Restore** - Restore from available backups
- **Cold Start All** - Full system boot: starts Docker containers via `docker-compose-PROD.yml`, then starts all host services (data_sync, excel_worker, stream_relay, looper_health)
- **Stop All** - Graceful shutdown of all services

## Requirements

- Go 1.21+ (for building)
- SSH access to the KPK App server
- OpenSSH server running on target machine (Windows 10+ has this built-in)

## Building

```powershell
# From the control-panel directory
.\build.bat

# Or manually:
go mod tidy
go build -ldflags="-s -w -H windowsgui" -o bin\kpk-control-panel.exe .
```

The output is a single portable executable: `bin\kpk-control-panel.exe`

## Usage

1. Run `kpk-control-panel.exe`
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
├── main.go       # Entry point, window setup
├── ssh.go        # SSH connection handling
├── executor.go   # Executor interface (SSH vs Local mode)
├── commands.go   # Remote command execution (Docker, host services, backups)
├── ui.go         # Fyne UI components
├── build.bat     # Build script
├── go.mod        # Go module definition
└── README.md
```

## Security Notes

- Credentials are only held in memory during the session
- SSH connection uses standard authentication (password or key-based)
- Host key verification is currently disabled (TODO: implement proper verification)
- All operations require authenticated SSH connection

## TODO

- [ ] SSH key-based authentication option
- [ ] Save connection settings (encrypted)
- [ ] Proper SSH host key verification
- [ ] Blue-green deployment switching
- [ ] Auto-reconnect on connection drop
