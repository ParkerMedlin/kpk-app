# KPK Control Panel Development

## Architecture

| Component | Implementation | Files |
|-----------|----------------|-------|
| **GUI** | Go (Fyne) | `main.go`, `ui.go`, `commands.go`, `ssh.go` |
| **CLI** | PowerShell | `ps/KPK.psm1`, `ps/kpk.ps1` |

The Go app is GUI-only. The CLI is purely PowerShell to avoid AV false positives with Go SSH libraries.

## When Adding/Modifying Commands

1. **GUI**: Update `commands.go` (shared logic) and `ui.go` (GUI bindings)
2. **CLI**: Update `ps/KPK.psm1` (module) and `ps/kpk.ps1` (CLI wrapper)
3. **Documentation**:
   - `kpk-cli-reference.md` (project reference)
   - `~/.claude/skills/kpk-cli/reference.md` (global Claude skill)

## File Structure

```
control-panel/
├── main.go              # GUI entry point
├── ui.go                # Fyne GUI implementation
├── commands.go          # Command implementations (used by GUI)
├── ssh.go               # SSH client wrapper
├── build.bat            # Build script for GUI
├── kpk-cli-reference.md # CLI command reference
├── development.md       # This file
└── ps/
    ├── KPK.psm1         # PowerShell module (CLI logic)
    ├── kpk.ps1          # CLI wrapper script
    ├── kpk.cmd          # Batch wrapper for cmd.exe
    └── Install-KPK.ps1  # Installer script
```

## CLI Command → PowerShell Cmdlet

| CLI Command | PowerShell Cmdlet |
|-------------|-------------------|
| `status` | `Get-KPKStatus` |
| `loop status` | `Get-KPKLoopStatus` |
| `start-missing` | `Start-KPKMissing` |
| `start-all` | `Start-KPKAll` |
| `stop-all` | `Stop-KPKAll` |
| `container list` | `Get-KPKContainerList` |
| `container logs` | `Get-KPKContainerLogs` |
| `container start` | `Start-KPKContainer` |
| `container stop` | `Stop-KPKContainer` |
| `container restart` | `Restart-KPKContainer` |
| `service list` | `Get-KPKHostServiceList` |
| `service logs` | `Get-KPKHostServiceLogs` |
| `service start` | `Start-KPKHostService` |
| `service stop` | `Stop-KPKHostService` |
| `backup create` | `New-KPKBackup` |
| `backup list` | `Get-KPKBackupList` |
| `backup restore` | `Restore-KPKBackup` |
| `git status` | `Get-KPKGitStatus` |
| `git fetch` | `Invoke-KPKGitFetch` |
| `git pull` | `Invoke-KPKGitPull` |
| `git collectstatic` | `Invoke-KPKCollectStatic` |
| `nginx reload` | `Invoke-KPKNginxReload` |

## Building

```batch
# Build Go GUI
build.bat

# PowerShell CLI requires no build step
```

## Testing

```powershell
# Test CLI
powershell -NoProfile -ExecutionPolicy Bypass -File "ps\kpk.ps1" status

# Test GUI
.\bin\kpk.exe
```

## PowerShell Output Handling (GUI)

The GUI runs commands on the remote server via SSH + PowerShell. There are several gotchas:

### CLIXML Progress Noise

PowerShell writes progress updates to stderr as CLIXML (e.g., "Preparing modules for first use").
This pollutes error output with XML like:
```
#< CLIXML
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04">...
```

**Solution** (implemented in `ssh.go` `RunCommand`):
- Prefix all commands with `$ProgressPreference = 'SilentlyContinue'`
- Use `powershell -NoProfile -NoLogo -EncodedCommand ...`

### Stdout vs Stderr

When a command fails, we need BOTH stdout (actual output) and stderr (errors). The SSH executor
combines them so output isn't lost on failure.

### Running Batch Files

Batch files (.bat) run in cmd.exe, not PowerShell. To capture output properly:
```powershell
$output = cmd /c "path\to\script.bat" 2>&1
Write-Output $output
exit $LASTEXITCODE
```

### Path Resolution in Batch Scripts

Batch scripts run via SSH may run as a different user. Never use `%USERPROFILE%` to locate
repo files. Instead, use paths relative to the script:
```batch
REM %~dp0 = directory containing the script
set "REPO_ROOT=%~dp0..\.."
set "ENV_FILE=%REPO_ROOT%\.env"
```

### Network Drives (UNC Paths)

Mapped drive letters (M:, N:, etc.) are per-user and per-session. They won't be available
in SSH sessions. Always use UNC paths for network locations:
```batch
REM BAD - drive letter may not exist in SSH session
set "BACKUP_DIR=M:\kpkapp\backups"

REM GOOD - UNC path works regardless of drive mappings
set "BACKUP_DIR=\\KinPak-Svr1\apps\kpkapp\backups"
```

### Checklist for New Commands

When adding commands that display output in the GUI:

1. Ensure stdout contains the useful output (not just stderr)
2. Test with a user account different from the repo owner
3. If calling batch files, use `cmd /c` wrapper with `2>&1`
4. Don't rely on `%USERPROFILE%` - use script-relative paths
