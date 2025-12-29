# KPK Control Panel Development

## Dual Implementation

The control panel has **two implementations** with identical command structures:

| Implementation | Files | Notes |
|----------------|-------|-------|
| **Go CLI** | `cli.go`, `commands.go`, `ssh.go`, `ui.go`, `main.go` | Compiled binary |
| **PowerShell** | `ps/KPK.psm1`, `ps/kpk.ps1` | Uses native Windows SSH |

Both must stay in sync. The PowerShell version exists to avoid AV false positives that can occur with Go binaries containing SSH libraries.

## When Adding/Modifying Commands

1. **Update Go implementation** in `cli.go` and/or `commands.go`
2. **Update PowerShell module** in `ps/KPK.psm1`
3. **Update PowerShell CLI wrapper** in `ps/kpk.ps1` (if command structure changes)
4. **Update documentation**:
   - `kpk-cli-reference.md` (project reference)
   - `~/.claude/skills/kpk-cli/reference.md` (global Claude skill)

## File Structure

```
control-panel/
├── main.go              # Entry point, GUI vs CLI detection
├── cli.go               # CLI argument parsing, command dispatch
├── commands.go          # Command implementations (shared by CLI & GUI)
├── ssh.go               # SSH client wrapper
├── ui.go                # Fyne GUI implementation
├── build.bat            # Build script
├── kpk-cli-reference.md # User-facing command reference
├── development.md       # This file
└── ps/
    ├── KPK.psm1         # PowerShell module (all logic)
    ├── kpk.ps1          # CLI wrapper script
    ├── kpk.cmd          # Batch wrapper for cmd.exe
    └── Install-KPK.ps1  # Installer script
```

## Command Mapping

| CLI Command | Go Function | PowerShell Cmdlet |
|-------------|-------------|-------------------|
| `status` | `cmdStatus()` | `Get-KPKStatus` |
| `loop status` | N/A (PS only) | `Get-KPKLoopStatus` |
| `start-missing` | `cmdStartMissing()` | `Start-KPKMissing` |
| `start-all` | `cmdColdStart()` | `Start-KPKAll` |
| `stop-all` | `cmdStopAll()` | `Stop-KPKAll` |
| `container list` | `cmdContainer()` | `Get-KPKContainerList` |
| `container logs` | `cmdContainer()` | `Get-KPKContainerLogs` |
| `container start` | `cmdContainer()` | `Start-KPKContainer` |
| `container stop` | `cmdContainer()` | `Stop-KPKContainer` |
| `container restart` | `cmdContainer()` | `Restart-KPKContainer` |
| `service list` | `cmdService()` | `Get-KPKHostServiceList` |
| `service logs` | `cmdService()` | `Get-KPKHostServiceLogs` |
| `service start` | `cmdService()` | `Start-KPKHostService` |
| `service stop` | `cmdService()` | `Stop-KPKHostService` |
| `backup create` | `cmdBackup()` | `New-KPKBackup` |
| `backup list` | `cmdBackup()` | `Get-KPKBackupList` |
| `backup restore` | `cmdBackup()` | `Restore-KPKBackup` |
| `git status` | `cmdGit()` | `Get-KPKGitStatus` |
| `git fetch` | `cmdGit()` | `Invoke-KPKGitFetch` |
| `git pull` | `cmdGit()` | `Invoke-KPKGitPull` |
| `git collectstatic` | `cmdGit()` | `Invoke-KPKCollectStatic` |
| `nginx reload` | `cmdNginx()` | `Invoke-KPKNginxReload` |

## Building

```batch
# Build Go binary
build.bat

# PowerShell requires no build step
```

## Testing

```powershell
# Test PowerShell module
powershell -NoProfile -ExecutionPolicy Bypass -File "ps\kpk.ps1" status

# Test Go binary
.\bin\kpk.exe status
```
