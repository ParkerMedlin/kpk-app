package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// ContainerStatus represents a Docker container's status
type ContainerStatus struct {
	Name    string
	ID      string
	Image   string
	Status  string
	State   string // running, exited, etc.
	Ports   string
	Created string
}

// HostServiceStatus represents a host service's status
type HostServiceStatus struct {
	Name      string
	ProcessID int
	Running   bool
	CPU       string
	Memory    string
}

// GitStatus represents the current git repository status
type GitStatus struct {
	Branch     string
	CommitHash string
	CommitMsg  string
	Behind     int  // commits behind remote
	Ahead      int  // commits ahead of remote
	HasChanges bool // uncommitted changes
}

// Commands encapsulates all remote command operations
type Commands struct {
	exec     Executor
	repoRoot string // Path to kpk-app repo root (works locally and via SSH)
}

// findRepoRoot determines the kpk-app repo root from executable location
func findRepoRoot() string {
	// Try to find repo root from executable location
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		// Executable could be in control-panel/ or control-panel/bin/
		// Go up until we find local_machine_scripts/ (confirms repo root)
		candidates := []string{
			filepath.Join(exeDir, ".."),          // control-panel/kpk.exe -> kpk-app/
			filepath.Join(exeDir, "..", ".."),    // control-panel/bin/kpk.exe -> kpk-app/
			filepath.Join(exeDir, "..", "..", ".."), // control-panel/dev/kpk.exe -> kpk-app/
		}
		for _, candidate := range candidates {
			checkPath := filepath.Join(candidate, "local_machine_scripts")
			if _, err := os.Stat(checkPath); err == nil {
				// Found it - convert to forward slashes for PowerShell compatibility
				absPath, _ := filepath.Abs(candidate)
				return filepath.ToSlash(absPath)
			}
		}
	}
	// Fallback to hardcoded path (for SSH where executable location doesn't matter)
	return "C:/Users/pmedlin/Documents/kpk-app"
}

// NewCommands creates a new Commands instance
func NewCommands(exec Executor) *Commands {
	// Determine the repo root based on executor type
	var repoRoot string
	if _, ok := exec.(*SSHClient); ok {
		// SSH connection - always use the remote path
		repoRoot = "C:/Users/pmedlin/Documents/kpk-app"
	} else {
		// Local execution - find the local repo
		repoRoot = findRepoRoot()
	}

	return &Commands{
		exec:     exec,
		repoRoot: repoRoot,
	}
}

// --- Docker Commands ---

// GetContainerStatuses returns status of all kpk-app containers
func (c *Commands) GetContainerStatuses() ([]ContainerStatus, error) {
	// Use docker ps with JSON format for easy parsing
	cmd := `docker ps -a --filter "name=kpk-app" --format "{{json .}}"`
	output, err := c.exec.RunCommand(cmd)
	if err != nil {
		return nil, err
	}

	var statuses []ContainerStatus
	lines := strings.Split(strings.TrimSpace(output), "\n")
	for _, line := range lines {
		if line == "" {
			continue
		}
		var raw map[string]interface{}
		if err := json.Unmarshal([]byte(line), &raw); err != nil {
			continue
		}
		status := ContainerStatus{
			Name:    getString(raw, "Names"),
			ID:      getString(raw, "ID"),
			Image:   getString(raw, "Image"),
			Status:  getString(raw, "Status"),
			State:   getString(raw, "State"),
			Ports:   getString(raw, "Ports"),
			Created: getString(raw, "CreatedAt"),
		}
		statuses = append(statuses, status)
	}
	return statuses, nil
}

// GetContainerLogs returns recent logs from a container
func (c *Commands) GetContainerLogs(containerName string, lines int) (string, error) {
	cmd := fmt.Sprintf("docker logs --tail %d %s 2>&1", lines, containerName)
	return c.exec.RunCommand(cmd)
}

// RestartContainer restarts a Docker container
func (c *Commands) RestartContainer(containerName string) error {
	cmd := fmt.Sprintf("docker restart %s", containerName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// StartContainer starts a Docker container
func (c *Commands) StartContainer(containerName string) error {
	cmd := fmt.Sprintf("docker start %s", containerName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// StopContainer stops a Docker container
func (c *Commands) StopContainer(containerName string) error {
	cmd := fmt.Sprintf("docker stop %s", containerName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// OpenContainerExec opens an interactive terminal into a container
func (c *Commands) OpenContainerExec(containerName string) error {
	// Open a new Windows Terminal/cmd window with docker exec
	// This launches a separate terminal window for the interactive session
	// Use sh instead of bash since many containers (Alpine-based) don't have bash
	cmd := fmt.Sprintf(`Start-Process cmd -ArgumentList '/k docker exec -it %s /bin/sh'`, containerName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// --- Host Service Commands ---

// GetHostServiceStatuses returns status of all host services
func (c *Commands) GetHostServiceStatuses() ([]HostServiceStatus, error) {
	// Ordered list of services (maintains consistent display order)
	serviceOrder := []string{"data_sync", "excel_worker", "stream_relay", "looper_health", "tank_leak_detector"}
	serviceScripts := map[string]string{
		"data_sync":          "data_sync.py",
		"excel_worker":       "excel_worker.py",
		"stream_relay":       "stream_relay.py",
		"looper_health":      "looper_health.py",
		"tank_leak_detector": "tank_leak_detector.py",
	}

	var statuses []HostServiceStatus

	// Check each service in order
	for _, svc := range serviceOrder {
		scriptName := serviceScripts[svc]
		status := HostServiceStatus{
			Name:    svc,
			Running: false,
		}

		// Check if process is running using wmic which can see processes across all users
		// wmic is more reliable for cross-user process visibility than Get-CimInstance
		checkCmd := fmt.Sprintf(`$result = wmic process where "name like '%%python%%'" get ProcessId,CommandLine /format:csv 2>$null | Select-String '%s'; if ($result) { $parts = ($result -split ','); @{ProcessId=[int]$parts[-1]} | ConvertTo-Json -Compress } else { Write-Output 'none' }`, scriptName)
		procOutput, err := c.exec.RunCommand(checkCmd)

		procOutput = strings.TrimSpace(procOutput)

		if err == nil && procOutput != "" && procOutput != "none" && procOutput != "null" {
			// Try to parse process info - could be single object or array
			var pid int

			// Try single object first
			var procInfo map[string]interface{}
			if err := json.Unmarshal([]byte(procOutput), &procInfo); err == nil {
				if pidVal, ok := procInfo["ProcessId"].(float64); ok && pidVal > 0 {
					pid = int(pidVal)
				}
			} else {
				// Try array (multiple processes)
				var procArray []map[string]interface{}
				if err := json.Unmarshal([]byte(procOutput), &procArray); err == nil && len(procArray) > 0 {
					if pidVal, ok := procArray[0]["ProcessId"].(float64); ok && pidVal > 0 {
						pid = int(pidVal)
					}
				}
			}

			if pid > 0 {
				status.Running = true
				status.ProcessID = pid
			}
		}

		statuses = append(statuses, status)
	}

	return statuses, nil
}

// getServicePath returns the script path for a service name
func getServicePath(serviceName string) (string, bool) {
	servicePaths := map[string]string{
		"data_sync":          "host-services/workers/data_sync.py",
		"excel_worker":       "host-services/workers/excel_worker.py",
		"stream_relay":       "host-services/workers/stream_relay.py",
		"looper_health":      "host-services/watchdogs/looper_health.py",
		"tank_leak_detector": "host-services/watchdogs/tank_leak_detector.py",
	}
	path, ok := servicePaths[serviceName]
	return path, ok
}

// StartHostService starts a host service and returns status message
func (c *Commands) StartHostService(serviceName string) error {
	_, err := c.StartHostServiceWithOutput(serviceName)
	return err
}

// StartHostServiceWithOutput starts a host service and returns output and error
func (c *Commands) StartHostServiceWithOutput(serviceName string) (string, error) {
	path, ok := getServicePath(serviceName)
	if !ok {
		return "", fmt.Errorf("unknown service: %s", serviceName)
	}

	// Use PsExec to run AS pmedlin in pmedlin's interactive desktop session (for tray icon)
	// Credentials loaded from .env (PSEXEC_USER, PSEXEC_PASS)
	cmd := fmt.Sprintf(`
$ErrorActionPreference = 'SilentlyContinue'
$root = "%s"
$py = "$root/../AppData/Local/Programs/Python/Python311/pythonw.exe"`, c.repoRoot) + fmt.Sprintf(`
$script = "$root/%s"

# Load PSEXEC_USER/PSEXEC_PASS from .env
$u=$null; $p=$null
Get-Content "$root/.env" 2>$null | ForEach-Object {
    if ($_ -match '^PSEXEC_USER=(.+)$') { $u = $Matches[1] }
    if ($_ -match '^PSEXEC_PASS=(.+)$') { $p = $Matches[1] }
}

# Get pmedlin's session ID
$sid = 1
$q = query user 2>$null | Select-String "pmedlin"
if ($q) { $q -split '\s+' | ForEach-Object { if ($_ -match '^\d+$' -and [int]$_ -gt 0) { $sid = $_; return } } }

# Find PsExec
$px = "C:/Windows/System32/PsExec.exe"
if (!(Test-Path $px)) { $px = "C:/SysinternalsSuite/PsExec.exe" }

# Create VBS launcher
$vbs = "$root/host-services/launcher.vbs"
$userHome = Split-Path (Split-Path $root -Parent) -Parent  # e.g., C:\Users\pmedlin from C:\Users\pmedlin\Documents\kpk-app
@"
Set s=CreateObject("WScript.Shell")
s.Environment("Process")("USERPROFILE")="$userHome"
s.Environment("Process")("HOME")="$userHome"
s.CurrentDirectory="$root"
s.Run """$py"" ""$script""",0,False
"@ | Set-Content $vbs -Force

# Run PsExec (suppress stderr noise)
if ($u -and $p) {
    $null = & $px -accepteula -i $sid -d -u $u -p $p wscript.exe $vbs 2>$null
} else {
    $null = & $px -accepteula -i $sid -d wscript.exe $vbs 2>$null
}
Write-Output "Started %s (session $sid)"
`, path, serviceName)

	output, err := c.exec.RunCommand(cmd)
	return output, err
}

// StopHostService stops a host service and all its child processes
func (c *Commands) StopHostService(serviceName string) error {
	// Find the main process by command line, then kill it and all children using taskkill /T (tree kill)
	// Note: $pid is a reserved variable in PowerShell, so we use $procId instead
	cmd := fmt.Sprintf(`
$procs = wmic process where "name like '%%python%%' and commandline like '%%%s%%'" get ProcessId /format:csv 2>$null | Select-String '\d+' | ForEach-Object { ($_ -split ',')[-1].Trim() }
foreach ($procId in $procs) {
    if ($procId) {
        Write-Output "Killing process tree for PID: $procId"
        taskkill /F /T /PID $procId 2>$null
    }
}
`, serviceName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// GetHostServiceLogs returns recent logs from a host service
func (c *Commands) GetHostServiceLogs(serviceName string, lines int) (string, error) {
	logFiles := map[string]string{
		"data_sync":          "host-services/logs/data_sync.log",
		"excel_worker":       "host-services/logs/excel_worker.log",
		"stream_relay":       "host-services/logs/stream_relay.log",
		"looper_health":      "host-services/logs/looper_health.log",
		"tank_leak_detector": "host-services/logs/tank_leak_detector.log",
	}

	logFile, ok := logFiles[serviceName]
	if !ok || logFile == "" {
		return "No log file available for this service", nil
	}

	// Check if file exists first, return friendly message if not
	// Use Join-Path to normalize slashes properly
	cmd := fmt.Sprintf(`
		$appRoot = "%s"
		$path = Join-Path $appRoot "%s"
		if (Test-Path $path) {
			Get-Content -Path $path -Tail %d
		} else {
			Write-Output "Log file not found: $path"
			Write-Output "Running on: $env:COMPUTERNAME as $env:USERNAME"
			Write-Output "Checking dir exists: $(Test-Path $appRoot)"
			Get-ChildItem $appRoot -ErrorAction SilentlyContinue | Select-Object -First 5
		}
	`, c.repoRoot, logFile, lines)
	return c.exec.RunCommand(cmd)
}

// --- Database Commands ---

// CreateBackup creates a database backup
func (c *Commands) CreateBackup() (string, error) {
	// Run the backup script
	// Use cmd /c to run batch file and capture both stdout and stderr
	cmd := fmt.Sprintf(`
$batFile = "%s/local_machine_scripts/batch_scripts/backup_and_copy.bat"
if (-not (Test-Path $batFile)) {
    Write-Output "ERROR: Batch file not found at $batFile"
    exit 1
}
Write-Output "Running: $batFile"
$output = cmd /c $batFile 2>&1
Write-Output $output
exit $LASTEXITCODE
`, c.repoRoot)
	return c.exec.RunCommand(cmd)
}

// ListBackups returns available backups
func (c *Commands) ListBackups() ([]string, error) {
	// Use cmd /c dir for UNC paths - PowerShell Get-ChildItem has auth issues over SSH
	cmd := `cmd /c "dir /b /ad /o-d \\KinPak-Svr1\apps\kpkapp\backups 2>nul" | Select-Object -First 10`
	output, err := c.exec.RunCommand(cmd)
	if err != nil {
		return nil, err
	}

	lines := strings.Split(strings.TrimSpace(output), "\n")
	var backups []string
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line != "" {
			backups = append(backups, line)
		}
	}
	return backups, nil
}

// RestoreBackup restores from a specific backup
func (c *Commands) RestoreBackup(backupName string) (string, error) {
	// Run restore script with backup name parameter
	// Use cmd /c to run batch file and capture output
	cmd := fmt.Sprintf(`
$batFile = "%s/local_machine_scripts/batch_scripts/helper_scripts/db_restore_latest_backup.bat"
if (-not (Test-Path $batFile)) {
    Write-Output "ERROR: Batch file not found at $batFile"
    exit 1
}
Write-Output "Running restore for: %s"
$output = cmd /c $batFile "%s" 2>&1
Write-Output $output
exit $LASTEXITCODE
`, c.repoRoot, backupName, backupName)
	return c.exec.RunCommand(cmd)
}

// --- Deployment Commands ---

// SwitchBlueGreen switches between blue and green deployments
func (c *Commands) SwitchBlueGreen() error {
	// This would modify nginx.conf and reload nginx
	// For now, just a placeholder
	return fmt.Errorf("blue-green switch not yet implemented")
}

// ReloadNginxConfig copies the local nginx.conf into the nginx container and restarts it
func (c *Commands) ReloadNginxConfig() error {
	// Copy local nginx.conf to the container (goes to conf.d directory)
	copyCmd := fmt.Sprintf(`docker cp "%s/nginx/nginx.conf" kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf`, c.repoRoot)
	if _, err := c.exec.RunCommand(copyCmd); err != nil {
		return fmt.Errorf("failed to copy nginx.conf: %v", err)
	}

	// Restart the nginx container to apply changes
	restartCmd := `docker restart kpk-app_nginx_1`
	if _, err := c.exec.RunCommand(restartCmd); err != nil {
		return fmt.Errorf("failed to restart nginx: %v", err)
	}

	return nil
}

// ColdStart performs a full cold start of all services
func (c *Commands) ColdStart() error {
	// 1. Start Docker Desktop and wait for it to be ready
	startDockerCmd := `
		# Start Docker Desktop
		Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

		# Wait for Docker to be ready (max 60 seconds)
		$timeout = 60
		$elapsed = 0
		while ($elapsed -lt $timeout) {
			$result = docker info 2>&1
			if ($LASTEXITCODE -eq 0) {
				Write-Output "Docker is ready"
				break
			}
			Start-Sleep -Seconds 2
			$elapsed += 2
		}
		if ($elapsed -ge $timeout) {
			throw "Docker failed to start within $timeout seconds"
		}
	`
	if _, err := c.exec.RunCommand(startDockerCmd); err != nil {
		return fmt.Errorf("failed to start Docker: %v", err)
	}

	// 2. Start Docker containers
	cmd := fmt.Sprintf(`Set-Location "%s"; docker compose -f docker-compose-PROD.yml up -d`, c.repoRoot)
	if _, err := c.exec.RunCommand(cmd); err != nil {
		return fmt.Errorf("failed to start containers: %v", err)
	}

	// 3. Wait for database to be ready (simple delay for now)
	// The app containers have wait_for_db in their startup command

	// 4. Start host services
	services := []string{"data_sync", "excel_worker", "stream_relay", "looper_health", "tank_leak_detector"}
	for _, svc := range services {
		if err := c.StartHostService(svc); err != nil {
			return fmt.Errorf("failed to start %s: %v", svc, err)
		}
	}

	return nil
}

// StopAll stops all services
func (c *Commands) StopAll() error {
	// 1. Stop host services
	services := []string{"data_sync", "excel_worker", "stream_relay", "looper_health", "tank_leak_detector"}
	for _, svc := range services {
		c.StopHostService(svc) // Ignore errors, some might not be running
	}

	// 2. Stop Docker containers
	cmd := fmt.Sprintf(`Set-Location "%s"; docker compose -f docker-compose-PROD.yml down`, c.repoRoot)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// StartMissingWithLog starts only the services that aren't currently running, with progress logging
func (c *Commands) StartMissingWithLog(logFunc func(string)) error {
	log := func(msg string) {
		if logFunc != nil {
			logFunc(msg)
		}
	}

	// 1. Check if Docker is running, start if needed
	log("Checking Docker status...")
	startDockerCmd := `
		# Start Docker Desktop if not running
		$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
		if (-not $dockerProcess) {
			Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
		}

		# Wait for Docker to be ready (max 60 seconds)
		$timeout = 60
		$elapsed = 0
		while ($elapsed -lt $timeout) {
			$result = docker info 2>&1
			if ($LASTEXITCODE -eq 0) {
				Write-Output "Docker is ready"
				break
			}
			Start-Sleep -Seconds 2
			$elapsed += 2
		}
		if ($elapsed -ge $timeout) {
			throw "Docker failed to start within $timeout seconds"
		}
	`
	if _, err := c.exec.RunCommand(startDockerCmd); err != nil {
		return fmt.Errorf("failed to start Docker: %v", err)
	}
	log("Docker is ready")

	// 2. Check container statuses and only start stopped ones
	log("Checking container statuses...")
	containerStatuses, err := c.GetContainerStatuses()
	if err != nil {
		return fmt.Errorf("failed to get container statuses: %v", err)
	}

	// Start only containers that are not running
	stoppedContainers := 0
	for _, container := range containerStatuses {
		if container.State != "running" {
			stoppedContainers++
			log(fmt.Sprintf("Starting container: %s", container.Name))
			if err := c.StartContainer(container.Name); err != nil {
				log(fmt.Sprintf("  ERROR: %v", err))
			} else {
				log(fmt.Sprintf("  Started: %s", container.Name))
			}
		}
	}
	if stoppedContainers == 0 {
		log("All containers already running")
	}

	// 3. Start host services that aren't running (start all, don't stop on first error)
	log("Checking host service statuses...")
	hostStatuses, _ := c.GetHostServiceStatuses()
	var startErrors []string
	stoppedServices := 0
	for _, status := range hostStatuses {
		if !status.Running {
			stoppedServices++
			log(fmt.Sprintf("Starting service: %s", status.Name))
			if err := c.StartHostService(status.Name); err != nil {
				log(fmt.Sprintf("  ERROR: %v", err))
				startErrors = append(startErrors, fmt.Sprintf("%s: %v", status.Name, err))
			} else {
				log(fmt.Sprintf("  Started: %s", status.Name))
			}
		}
	}
	if stoppedServices == 0 {
		log("All host services already running")
	}

	if len(startErrors) > 0 {
		return fmt.Errorf("failed to start some services: %s", strings.Join(startErrors, "; "))
	}

	log("Done!")
	return nil
}

// StartMissing starts only the services that aren't currently running (no logging)
func (c *Commands) StartMissing() error {
	return c.StartMissingWithLog(nil)
}

// --- Git Commands ---

// ensureGitSafeDirectory adds the repo to git's safe.directory list (needed when SSH user differs from repo owner)
func (c *Commands) ensureGitSafeDirectory() error {
	cmd := fmt.Sprintf(`git config --global --add safe.directory "%s" 2>$null; $true`, c.repoRoot)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// ensureGitHubHostKey adds GitHub's SSH host key to known_hosts if not present
func (c *Commands) ensureGitHubHostKey() error {
	cmd := `
$knownHosts = "$env:USERPROFILE\.ssh\known_hosts"
if (-not (Test-Path "$env:USERPROFILE\.ssh")) {
    New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force | Out-Null
}
if (-not (Test-Path $knownHosts) -or -not (Select-String -Path $knownHosts -Pattern "github.com" -Quiet)) {
    # Add GitHub's SSH host keys
    Add-Content -Path $knownHosts -Value "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"
    Add-Content -Path $knownHosts -Value "github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg="
    Add-Content -Path $knownHosts -Value "github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk="
}
$true
`
	_, err := c.exec.RunCommand(cmd)
	return err
}

// GetGitStatus returns current branch, commit info, and sync status
func (c *Commands) GetGitStatus() (GitStatus, error) {
	c.ensureGitSafeDirectory()
	status := GitStatus{}

	// Get current branch
	branchCmd := fmt.Sprintf(`git -C "%s" rev-parse --abbrev-ref HEAD`, c.repoRoot)
	branch, err := c.exec.RunCommand(branchCmd)
	if err != nil {
		return status, fmt.Errorf("failed to get branch: %v", err)
	}
	status.Branch = strings.TrimSpace(branch)

	// Get latest commit hash and message
	logCmd := fmt.Sprintf(`git -C "%s" log -1 --format="%%h %%s"`, c.repoRoot)
	logOutput, err := c.exec.RunCommand(logCmd)
	if err != nil {
		return status, fmt.Errorf("failed to get commit info: %v", err)
	}
	logOutput = strings.TrimSpace(logOutput)
	if parts := strings.SplitN(logOutput, " ", 2); len(parts) >= 2 {
		status.CommitHash = parts[0]
		status.CommitMsg = parts[1]
	} else if len(parts) == 1 {
		status.CommitHash = parts[0]
	}

	// Check for uncommitted changes
	statusCmd := fmt.Sprintf(`git -C "%s" status --porcelain`, c.repoRoot)
	statusOutput, _ := c.exec.RunCommand(statusCmd)
	status.HasChanges = strings.TrimSpace(statusOutput) != ""

	// Get ahead/behind counts (requires fetch first, but don't fail if remote unavailable)
	behindCmd := fmt.Sprintf(`git -C "%s" rev-list --count HEAD..origin/%s 2>$null`, c.repoRoot, status.Branch)
	behindOutput, _ := c.exec.RunCommand(behindCmd)
	if behindOutput = strings.TrimSpace(behindOutput); behindOutput != "" {
		fmt.Sscanf(behindOutput, "%d", &status.Behind)
	}

	aheadCmd := fmt.Sprintf(`git -C "%s" rev-list --count origin/%s..HEAD 2>$null`, c.repoRoot, status.Branch)
	aheadOutput, _ := c.exec.RunCommand(aheadCmd)
	if aheadOutput = strings.TrimSpace(aheadOutput); aheadOutput != "" {
		fmt.Sscanf(aheadOutput, "%d", &status.Ahead)
	}

	return status, nil
}

// GitFetch fetches from remote without merging
func (c *Commands) GitFetch() (string, error) {
	c.ensureGitSafeDirectory()
	c.ensureGitHubHostKey()
	// Git writes progress/info to stderr which PowerShell treats as errors
	// Use SilentlyContinue to suppress PowerShell's NativeCommandError output
	// Then check $LASTEXITCODE to detect actual git failures
	cmd := fmt.Sprintf(`
$ErrorActionPreference = 'SilentlyContinue'
$env:GIT_TERMINAL_PROMPT=0
$userHome = Split-Path (Split-Path "%s" -Parent) -Parent
$sshKey = "$userHome/.ssh/id_ed25519"
$env:GIT_SSH_COMMAND="ssh -i $sshKey -o IdentitiesOnly=yes"
$output = git -C "%s" fetch origin 2>&1 | Out-String
$exitCode = $LASTEXITCODE
$ErrorActionPreference = 'Continue'
Write-Output $output.Trim()
if ($exitCode -ne 0) { exit $exitCode }
`, c.repoRoot, c.repoRoot)
	return c.exec.RunCommand(cmd)
}

// GitPull pulls latest changes from origin
func (c *Commands) GitPull() (string, error) {
	c.ensureGitSafeDirectory()
	c.ensureGitHubHostKey()
	// Git writes progress/info to stderr which PowerShell treats as errors
	// Use SilentlyContinue to suppress PowerShell's NativeCommandError output
	// Then check $LASTEXITCODE to detect actual git failures
	cmd := fmt.Sprintf(`
$ErrorActionPreference = 'SilentlyContinue'
$env:GIT_TERMINAL_PROMPT=0
$userHome = Split-Path (Split-Path "%s" -Parent) -Parent
$sshKey = "$userHome/.ssh/id_ed25519"
$env:GIT_SSH_COMMAND="ssh -i $sshKey -o IdentitiesOnly=yes"
$output = git -C "%s" pull origin main 2>&1 | Out-String
$exitCode = $LASTEXITCODE
$ErrorActionPreference = 'Continue'
Write-Output $output.Trim()
if ($exitCode -ne 0) { exit $exitCode }
`, c.repoRoot, c.repoRoot)
	return c.exec.RunCommand(cmd)
}

// RunCollectStatic runs Django's collectstatic command in the app_blue container
func (c *Commands) RunCollectStatic() (string, error) {
	cmd := `docker exec kpk-app_app_blue_1 python manage.py collectstatic --noinput 2>&1`
	return c.exec.RunCommand(cmd)
}

// Helper function to safely get string from map
func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}
