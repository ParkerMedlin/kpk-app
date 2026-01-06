# Host Services

Windows host-level background services that run **outside** the Docker container environment. These services handle tasks that require direct access to Windows resources (Excel COM automation, local file systems, camera hardware, etc.).

## Directory Structure

```
host-services/
├── workers/           # Long-running data processing services
│   ├── data_sync.py       # Core ETL engine (Sage 100, SharePoint → PostgreSQL)
│   ├── excel_worker.py    # Excel macro trigger service (blend sheets, GHS labels)
│   └── stream_relay.py    # Hikvision camera stream relay
├── watchdogs/         # Health monitoring and auto-recovery services
│   ├── looper_health.py   # Monitors data_sync, triggers restarts
│   └── backup_health.py   # Monitors daily backup existence
├── logs/              # Centralized log directory for all host services
└── README.md
```

## Services Overview

### Workers

| Service | Port | Description |
|---------|------|-------------|
| `data_sync.py` | N/A | Core ETL engine. Clones Sage 100 tables and builds calculated tables in PostgreSQL. Runs two parallel processes. |
| `excel_worker.py` | 9998 | HTTP server that triggers PowerShell scripts for Excel automation (blend sheets, GHS labels, pick sheets). Uses Redis queue for concurrent job processing. |
| `stream_relay.py` | N/A | Manages Hikvision camera WebSocket stream server. Auto-restarts on failure. |

### Watchdogs

| Service | Port | Description |
|---------|------|-------------|
| `looper_health.py` | 9999 (HTTPS) | Monitors data_sync health. Can trigger restarts via email command, HTTPS endpoint, or automatic detection. |
| `backup_health.py` | N/A | Checks for daily backup at 5:30 PM. Alerts via Teams if backup folder missing. |

## Starting Services

Each service runs as a Windows system tray application. Start them by running the Python script:

```powershell
# From kpk-app root directory

# Core ETL (required)
python host-services/workers/data_sync.py

# Excel automation (required for blend sheet generation)
python host-services/workers/excel_worker.py

# Camera stream relay (required for palletizer camera view)
pythonw host-services/workers/stream_relay.py

# Health watchdog (recommended)
pythonw host-services/watchdogs/looper_health.py

# Backup watchdog (recommended)
pythonw host-services/watchdogs/backup_health.py
```

> **Note:** Use `pythonw` for services that should run without a console window.

## Service Endpoints

### Excel Worker (port 9998)

```http
POST http://127.0.0.1:9998/run-excel-macro
Content-Type: application/json

{
    "macro_to_run": "generateProductionPackage",
    "data_for_macro": [lot_qty, lot_number, ..., item_code],
    "components_for_pick_sheet": [...]
}
```

**Endpoints:**
- `POST /run-excel-macro` - Trigger blend sheet/GHS label generation
- `POST /job-status` - Check async job status (for Redis queue jobs)

### Looper Health Watchdog (port 9999, HTTPS)

```http
GET https://127.0.0.1:9999/trigger-restart
GET https://127.0.0.1:9999/run-uv-freeze-audit
GET https://127.0.0.1:9999/service-status
```

**SSL Certificates:** Uses `nginx/ssl/kpkapp.lan.pem` and `nginx/ssl/kpkapp.lan.key`

## Logging

All services log to `host-services/logs/`:

| Service | Log File |
|---------|----------|
| data_sync.py | (console output only) |
| excel_worker.py | `excel_worker.log` |
| stream_relay.py | `stream_relay.log` |
| looper_health.py | `looper_health.log` |
| backup_health.py | `backup_health.log` |

## Dependencies

These services depend on modules in the legacy location:

- ETL modules: `local_machine_scripts/python_db_scripts/app_db_mgmt/`
- PowerShell scripts: `local_machine_scripts/python_systray_scripts/Invoke-DirectExcelEdit.ps1`
- Stream server: `local_machine_scripts/realtime_stream_server.pyw`

## Migration Notes

These services were migrated from `local_machine_scripts/python_systray_scripts/`:

| Old Name | New Location |
|----------|--------------|
| `PYSTRAY_data_looper.py` | `host-services/workers/data_sync.py` |
| `PYSTRAY_data_looper_restart_service.pyw` | `host-services/watchdogs/looper_health.py` |
| `PYSTRAY_excel_macro_trigger_service.pyw` | `host-services/workers/excel_worker.py` |
| `PYSTRAY_hikvision_stream.pyw` | `host-services/workers/stream_relay.py` |

The original files remain in place for backward compatibility but should be considered deprecated.
