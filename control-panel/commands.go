package main

import (
	"encoding/json"
	"fmt"
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

// Commands encapsulates all remote command operations
type Commands struct {
	exec Executor
}

// NewCommands creates a new Commands instance
func NewCommands(exec Executor) *Commands {
	return &Commands{exec: exec}
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
	serviceOrder := []string{"data_sync", "excel_worker", "stream_relay", "looper_health"}
	serviceScripts := map[string]string{
		"data_sync":     "data_sync.py",
		"excel_worker":  "excel_worker.py",
		"stream_relay":  "stream_relay.py",
		"looper_health": "looper_health.py",
	}

	var statuses []HostServiceStatus

	// Check each service in order
	for _, svc := range serviceOrder {
		scriptName := serviceScripts[svc]
		status := HostServiceStatus{
			Name:    svc,
			Running: false,
		}

		// Check if process is running using PowerShell
		// Look for python/pythonw processes with the script name
		checkCmd := fmt.Sprintf(`$p = Get-WmiObject Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -like '*%s*' }; if ($p) { $p | Select-Object ProcessId | ConvertTo-Json -Compress } else { Write-Output 'none' }`, scriptName)
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

// StartHostService starts a host service and returns status message
func (c *Commands) StartHostService(serviceName string) error {
	// Map service names to their paths in host-services/
	servicePaths := map[string]string{
		"data_sync":     "host-services\\workers\\data_sync.py",
		"excel_worker":  "host-services\\workers\\excel_worker.py",
		"stream_relay":  "host-services\\workers\\stream_relay.py",
		"looper_health": "host-services\\watchdogs\\looper_health.py",
	}

	path, ok := servicePaths[serviceName]
	if !ok {
		return fmt.Errorf("unknown service: %s", serviceName)
	}

	// Start the service hidden using Start-Process with -WindowStyle Hidden
	cmd := fmt.Sprintf(`
		$appRoot = "$env:USERPROFILE\Documents\kpk-app"
		$scriptPath = Join-Path $appRoot '%s'
		$logDir = Join-Path $appRoot 'host-services\logs'
		$logFile = Join-Path $logDir '%s.log'

		# Ensure log directory exists
		if (-not (Test-Path $logDir)) {
			New-Item -ItemType Directory -Path $logDir -Force | Out-Null
		}

		if (-not (Test-Path $scriptPath)) {
			Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR: Script not found: $scriptPath"
			throw "Script not found: $scriptPath"
		}

		Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - INFO: Starting %s service..."

		# Start with pythonw (no console) - Start-Process returns immediately
		$proc = Start-Process -FilePath "pythonw" -ArgumentList $scriptPath -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru

		Add-Content -Path $logFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - INFO: %s launched (PID: $($proc.Id))"
		Write-Output "Launched %s (PID: $($proc.Id))"
	`, path, serviceName, serviceName, serviceName, serviceName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// StopHostService stops a host service
func (c *Commands) StopHostService(serviceName string) error {
	// Use Get-CimInstance (faster than Get-WmiObject) to find python processes by command line
	cmd := fmt.Sprintf(`Get-CimInstance Win32_Process -Filter "name like 'python%%'" | Where-Object { $_.CommandLine -like '*%s*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`, serviceName)
	_, err := c.exec.RunCommand(cmd)
	return err
}

// GetHostServiceLogs returns recent logs from a host service
func (c *Commands) GetHostServiceLogs(serviceName string, lines int) (string, error) {
	logFiles := map[string]string{
		"data_sync":     "host-services\\logs\\data_sync.log",
		"excel_worker":  "host-services\\logs\\excel_worker.log",
		"stream_relay":  "host-services\\logs\\stream_relay.log",
		"looper_health": "host-services\\logs\\looper_health.log",
	}

	logFile, ok := logFiles[serviceName]
	if !ok || logFile == "" {
		return "No log file available for this service", nil
	}

	// Check if file exists first, return friendly message if not
	cmd := fmt.Sprintf(`
		$path = "$env:USERPROFILE\Documents\kpk-app\%s"
		if (Test-Path $path) {
			Get-Content -Path $path -Tail %d
		} else {
			Write-Output "Log file not found: $path"
		}
	`, logFile, lines)
	return c.exec.RunCommand(cmd)
}

// --- Database Commands ---

// CreateBackup creates a database backup
func (c *Commands) CreateBackup() (string, error) {
	// Run the backup script
	cmd := `& "$env:USERPROFILE\Documents\kpk-app\local_machine_scripts\batch_scripts\backup_and_copy.bat"`
	return c.exec.RunCommand(cmd)
}

// ListBackups returns available backups
func (c *Commands) ListBackups() ([]string, error) {
	cmd := `Get-ChildItem -Path 'M:\kpkapp\backups' -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 10 -ExpandProperty Name`
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
func (c *Commands) RestoreBackup(backupName string) error {
	cmd := `& "$env:USERPROFILE\Documents\kpk-app\local_machine_scripts\batch_scripts\db_restore_latest_backup.bat"`
	_, err := c.exec.RunCommand(cmd)
	return err
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
	copyCmd := `docker cp "$env:USERPROFILE\Documents\kpk-app\nginx\nginx.conf" kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf`
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
	cmd := `Set-Location "$env:USERPROFILE\Documents\kpk-app"; docker compose -f docker-compose-PROD.yml up -d`
	if _, err := c.exec.RunCommand(cmd); err != nil {
		return fmt.Errorf("failed to start containers: %v", err)
	}

	// 3. Wait for database to be ready (simple delay for now)
	// The app containers have wait_for_db in their startup command

	// 4. Start host services
	services := []string{"data_sync", "excel_worker", "stream_relay", "looper_health"}
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
	services := []string{"data_sync", "excel_worker", "stream_relay", "looper_health"}
	for _, svc := range services {
		c.StopHostService(svc) // Ignore errors, some might not be running
	}

	// 2. Stop Docker containers
	cmd := `Set-Location "$env:USERPROFILE\Documents\kpk-app"; docker compose -f docker-compose-PROD.yml down`
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

// Helper function to safely get string from map
func getString(m map[string]interface{}, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}
