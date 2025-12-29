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
