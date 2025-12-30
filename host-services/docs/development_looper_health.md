# Looper Health Development Guide

This guide explains the architecture and extension patterns for `looper_health.py`, the central watchdog service that monitors KPK App infrastructure and sends alerts to Microsoft Teams.

## Overview

`looper_health.py` is a Windows system tray application that:
1. Monitors Docker containers and host services for availability
2. Scans log files for error patterns
3. Sends alerts to Microsoft Teams via Adaptive Cards
4. Attempts auto-remediation for certain failure modes

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      looper_health.py                           │
├─────────────────────────────────────────────────────────────────┤
│  Threads:                                                       │
│  ├── Main Thread (pystray system tray icon)                     │
│  ├── email_monitor_thread (restart commands via email)          │
│  ├── looper_status_monitor_thread (HTTP health checks)          │
│  ├── alert_monitor_thread (log scanning + health checks)        │
│  └── start_https_server (REST endpoints for triggers)           │
├─────────────────────────────────────────────────────────────────┤
│  Alert System Components:                                       │
│  ├── AlertConfig          - Loads alert_rules.json              │
│  ├── AlertStateManager    - Persists scan positions & cooldowns │
│  ├── ContainerHealthChecker - Docker container monitoring       │
│  ├── HostServiceHealthChecker - Python process monitoring       │
│  ├── FileLogScanner       - Scans host service log files        │
│  ├── DockerLogScanner     - Scans Docker container logs         │
│  ├── AlertEngine          - Pattern matching & threshold logic  │
│  ├── Remediator           - Executes auto-fix actions           │
│  └── TeamsNotifier        - Sends Adaptive Cards to Teams       │
└─────────────────────────────────────────────────────────────────┘
```

## Core Primitives

### 1. AlertConfig

Loads and validates `host-services/config/alert_rules.json`. Provides access to:
- `rules` - List of pattern-matching alert rules
- `log_sources` - File and Docker log source definitions
- `critical_containers` - Docker containers to monitor for availability
- `critical_host_services` - Python processes to monitor for availability
- `webhook_url` - Teams webhook URL from environment

### 2. AlertStateManager

Persists state to `host-services/config/alert_state.json` to survive restarts:
- **Scan positions** - Byte offsets for file logs, timestamps for Docker logs
- **Alert history** - Recent matches and last alert time per rule (for cooldowns)
- **Container/service alert times** - Cooldown tracking for health checks

Key methods:
```python
get_scan_position(source_name) -> dict
set_scan_position(source_name, position)
get_alert_history(rule_name) -> dict
update_alert_history(rule_name, history)
get_container_alert_time(container_name) -> Optional[str]
set_container_alert_time(container_name, time_str)
get_host_service_alert_time(service_name) -> Optional[str]
set_host_service_alert_time(service_name, time_str)
```

### 3. Log Scanners

Abstract base class `LogScanner` with two implementations:

**FileLogScanner** - For host service logs (data_sync, excel_worker, etc.)
- Reads from saved byte offset to current EOF
- Handles log rotation (resets offset if file shrinks)
- Parses timestamps from log lines

**DockerLogScanner** - For container logs
- Runs `docker logs --tail N --timestamps <container>`
- Tracks last seen timestamp to avoid duplicate processing
- Combines stdout and stderr

Both return `list[(timestamp, line)]` from `get_new_lines()`.

### 4. Health Checkers

**ContainerHealthChecker**
- Uses `docker inspect --format '{{.State.Status}}'` to check if running
- Attempts `docker start <container>` if down
- Reports success/failure in Teams alert

**HostServiceHealthChecker**
- Uses WMIC to find Python processes matching a pattern
- Attempts restart with `pythonw <script>` if not found
- Verifies process started after 3 seconds

### 5. AlertEngine

The pattern matching and threshold engine:
1. Pre-compiles regex patterns from rules
2. For each rule, checks if source matches
3. Finds pattern matches in new log lines
4. Maintains sliding window of recent matches
5. Fires alert if threshold exceeded and not in cooldown
6. Executes remediation if configured

### 6. Remediator

Executes auto-fix actions when rules fire. Supported actions:
- `restart_host_service` - Terminate and restart a Python process
- `restart_container` - Restart a Docker container

### 7. TeamsNotifier

Sends Microsoft Teams Adaptive Cards via Workflow webhooks:
- Color-coded by severity (warning=yellow, error/critical=red)
- Shows "RESOLVED" in green when auto-fix succeeds
- Includes sample log lines and metadata

## Configuration Schema

### alert_rules.json Structure

```json
{
  "version": "1.0",
  "scan_interval_seconds": 30,
  "teams_webhook_env_var": "TEAMS_WEBHOOK_URL",
  "default_cooldown_seconds": 300,

  "critical_containers": ["container_name_1", ...],
  "container_check_cooldown_seconds": 300,

  "critical_host_services": [
    {
      "name": "service_id",
      "display_name": "Human Readable Name",
      "script": "relative/path/to/script.py",
      "process_pattern": "unique_string_in_cmdline"
    }
  ],
  "host_service_check_cooldown_seconds": 300,

  "log_sources": {
    "source_name": {
      "type": "file",
      "path": "logs/filename.log"
    },
    "docker_source": {
      "type": "docker",
      "container": "container_name",
      "tail_lines": 100
    }
  },

  "rules": [
    {
      "name": "rule_identifier",
      "description": "Human-readable description for Teams",
      "pattern": "regex_pattern",
      "sources": ["source1", "source2"],
      "severity": "warning|error|critical",
      "threshold_count": 5,
      "threshold_window_seconds": 300,
      "cooldown_seconds": 1800,
      "enabled": true,
      "remediation": {
        "action": "restart_host_service|restart_container",
        "service": "service_name",
        "container": "container_name"
      }
    }
  ]
}
```

### Rule Fields Explained

| Field | Description |
|-------|-------------|
| `name` | Unique identifier for the rule |
| `description` | Shown in Teams alert header |
| `pattern` | Regex pattern (case-insensitive) |
| `sources` | Which log sources to scan |
| `severity` | `warning`, `error`, or `critical` |
| `threshold_count` | Number of matches to trigger alert |
| `threshold_window_seconds` | Time window for threshold |
| `cooldown_seconds` | Minimum time between alerts |
| `enabled` | Set `false` to disable without deleting |
| `remediation` | Optional auto-fix action |

## Adding New Monitoring Targets

### Adding a New Container to Monitor

1. Add container name to `critical_containers` array:
```json
"critical_containers": [
  "existing_container",
  "kpk-app_new_container_1"
]
```

2. Optionally add as a log source to scan for patterns:
```json
"log_sources": {
  "new_container": {
    "type": "docker",
    "container": "kpk-app_new_container_1",
    "tail_lines": 100
  }
}
```

### Adding a New Host Service to Monitor

1. Add to `critical_host_services`:
```json
{
  "name": "my_worker",
  "display_name": "My Worker Service",
  "script": "host-services/workers/my_worker.py",
  "process_pattern": "my_worker"
}
```

The `process_pattern` must be unique enough to identify the process in WMIC output.

2. Add log source if the service writes logs:
```json
"log_sources": {
  "my_worker": {
    "type": "file",
    "path": "logs/my_worker.log"
  }
}
```

### Adding a New Alert Rule

1. Identify the error pattern in logs
2. Choose appropriate threshold (how many before alert?)
3. Choose cooldown (how often to re-alert?)
4. Add rule to `rules` array:

```json
{
  "name": "my_new_error",
  "description": "Something bad happened in my service",
  "pattern": "ERROR.*MyService|MyService.*failed",
  "sources": ["my_worker"],
  "severity": "error",
  "threshold_count": 3,
  "threshold_window_seconds": 300,
  "cooldown_seconds": 900,
  "enabled": true
}
```

## Adding New Remediation Actions

### Step 1: Add Action Handler to Remediator

In `looper_health.py`, add a new method to the `Remediator` class:

```python
def _my_custom_action(self, remediation_config: dict) -> tuple:
    """Execute custom remediation. Returns (success: bool, message: str)."""
    try:
        # Your remediation logic here
        return True, "Remediation succeeded"
    except Exception as e:
        return False, f"Remediation failed: {e}"
```

### Step 2: Register in execute()

Add the action to the `execute()` dispatcher:

```python
def execute(self, remediation_config: dict, alert_context: dict) -> tuple:
    action = remediation_config.get('action')

    if action == 'restart_host_service':
        return self._restart_host_service(remediation_config)
    elif action == 'restart_container':
        return self._restart_container(remediation_config)
    elif action == 'my_custom_action':
        return self._my_custom_action(remediation_config)
    else:
        return False, f"Unknown remediation action: {action}"
```

### Step 3: Configure in Rule

```json
{
  "name": "my_rule",
  "remediation": {
    "action": "my_custom_action",
    "custom_param": "value"
  }
}
```

## Windows Considerations

### Hiding Console Windows

All subprocess calls must hide the console window to avoid flashing:

```python
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = 0  # SW_HIDE

result = subprocess.run(
    ['command', 'args'],
    capture_output=True,
    text=True,
    timeout=30,
    startupinfo=startupinfo,
    creationflags=subprocess.CREATE_NO_WINDOW
)
```

### Process Detection

Use WMIC for cross-session process visibility:

```python
result = subprocess.run(
    ['powershell', '-Command',
     f"wmic process where \"name like '%python%' and commandline like '%{pattern}%'\" get ProcessId /format:csv"],
    ...
)
```

### Starting Background Processes

Use `pythonw` (not `python`) for windowless execution:

```python
subprocess.Popen(
    ['pythonw', script_path],
    cwd=KPK_APP_ROOT,
    startupinfo=startupinfo,
    creationflags=subprocess.CREATE_NO_WINDOW
)
```

## Testing & Debugging

### Viewing Alert State

Check `host-services/config/alert_state.json` to see:
- Current scan positions
- Recent matches per rule
- Last alert times

### Simulating Alerts

1. Write test patterns to a log file being monitored
2. Lower thresholds temporarily for faster triggering
3. Check looper_health.log for "Alert Monitor" messages

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Rule not firing | Pattern doesn't match | Test regex against actual log lines |
| Too many alerts | Threshold too low | Increase threshold_count or window |
| Alert spam | Cooldown too short | Increase cooldown_seconds |
| Missing log lines | Scanner fell behind | Increase scan_interval or tail_lines |
| Process not detected | Pattern too generic/specific | Adjust process_pattern |

## Best Practices

1. **Threshold tuning** - Start conservative (higher thresholds), then lower based on real-world noise
2. **Cooldown periods** - Match to expected resolution time (don't spam during outages)
3. **Severity levels** - Reserve `critical` for things that break user experience
4. **Remediation** - Only auto-fix idempotent operations (restarts are safe)
5. **Pattern specificity** - Avoid overly broad patterns that match normal operation
6. **Log sources** - Keep `tail_lines` reasonable to avoid slow scans
