package main

import (
	"fmt"
	"os/exec"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/layout"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"
)

// ContainerStateChange tracks when a container changed state
type ContainerStateChange struct {
	State     string
	Timestamp time.Time
}

// UI manages the application user interface
type UI struct {
	window        fyne.Window
	executor      Executor
	commands      *Commands
	authenticated bool
	isLocalMode   bool

	// Connection fields
	hostEntry     *widget.Entry
	portEntry     *widget.Entry
	userEntry     *widget.Entry
	passwordEntry *widget.Entry
	connectBtn    *widget.Button
	localModeBtn  *widget.Button
	statusLabel   *widget.Label

	// Status displays
	containerList   *widget.List
	hostServiceList *widget.List
	containers      []ContainerStatus
	hostServices    []HostServiceStatus

	// Loading indicators
	containerLoading   *widget.ProgressBarInfinite
	hostServiceLoading *widget.ProgressBarInfinite

	// Shimmer tracking for restarting containers
	restartingContainers map[string]bool

	// Restart loop detection - tracks state changes per container
	containerStateHistory map[string][]ContainerStateChange
	crashLoopContainers   map[string]bool

	// Health status
	statusBanner    *widget.Label
	startRestartBtn *widget.Button

	// Log viewer
	logText *widget.Entry

	// Main content
	mainContent *fyne.Container
}

// NewUI creates a new UI instance
func NewUI(w fyne.Window) *UI {
	return &UI{
		window:                w,
		authenticated:         false,
		containers:            []ContainerStatus{},
		hostServices:          []HostServiceStatus{},
		restartingContainers:  make(map[string]bool),
		containerStateHistory: make(map[string][]ContainerStateChange),
		crashLoopContainers:   make(map[string]bool),
	}
}

// Build constructs and returns the main UI
func (u *UI) Build() fyne.CanvasObject {
	// Start with login screen
	return u.buildLoginScreen()
}

// buildLoginScreen creates the authentication screen
func (u *UI) buildLoginScreen() fyne.CanvasObject {
	u.hostEntry = widget.NewEntry()
	u.hostEntry.SetPlaceHolder("192.168.178.x or hostname")
	u.hostEntry.SetText("192.168.178.169") // Default to kpkapp server

	u.portEntry = widget.NewEntry()
	u.portEntry.SetText("22")

	u.userEntry = widget.NewEntry()
	u.userEntry.SetPlaceHolder("username")

	u.passwordEntry = widget.NewPasswordEntry()
	u.passwordEntry.SetPlaceHolder("password")
	u.passwordEntry.OnSubmitted = func(_ string) { u.handleConnect() }

	u.statusLabel = widget.NewLabel("")

	u.connectBtn = widget.NewButton("Connect via SSH", u.handleConnect)
	u.connectBtn.Importance = widget.HighImportance

	u.localModeBtn = widget.NewButton("Run Locally (No SSH)", u.handleLocalMode)

	// Check if we're on the server
	localIPs := GetLocalIPSummary()
	localInfo := widget.NewLabel(fmt.Sprintf("This machine: %s", localIPs))

	form := container.NewVBox(
		widget.NewLabel("Remote Connection (SSH)"),
		widget.NewSeparator(),
		container.NewGridWithColumns(2,
			widget.NewLabel("Host:"),
			u.hostEntry,
			widget.NewLabel("Port:"),
			u.portEntry,
			widget.NewLabel("Username:"),
			u.userEntry,
			widget.NewLabel("Password:"),
			u.passwordEntry,
		),
		layout.NewSpacer(),
		u.connectBtn,
		widget.NewSeparator(),
		widget.NewLabel("Or run on this machine:"),
		u.localModeBtn,
		localInfo,
		u.statusLabel,
	)

	// Center the form
	return container.NewCenter(
		container.NewVBox(
			widget.NewLabelWithStyle("KPK Control Panel", fyne.TextAlignCenter, fyne.TextStyle{Bold: true}),
			widget.NewLabelWithStyle("v"+AppVersion, fyne.TextAlignCenter, fyne.TextStyle{}),
			layout.NewSpacer(),
			container.NewPadded(form),
		),
	)
}

// handleConnect attempts SSH connection
func (u *UI) handleConnect() {
	u.statusLabel.SetText("Connecting...")
	u.connectBtn.Disable()
	u.localModeBtn.Disable()

	go func() {
		sshClient := NewSSHClient(u.hostEntry.Text, u.portEntry.Text, u.userEntry.Text)
		err := sshClient.ConnectWithPassword(u.passwordEntry.Text)

		if err != nil {
			u.statusLabel.SetText(fmt.Sprintf("Failed: %v", err))
			u.connectBtn.Enable()
			u.localModeBtn.Enable()
			return
		}

		u.executor = sshClient
		u.commands = NewCommands(u.executor)
		u.authenticated = true
		u.isLocalMode = false
		u.statusLabel.SetText("Connected!")

		// Switch to main UI
		u.window.SetContent(u.buildMainScreen())

		// Start status refresh loop
		go u.refreshStatusLoop()
	}()
}

// handleLocalMode starts in local mode (no SSH)
func (u *UI) handleLocalMode() {
	u.executor = NewLocalExecutor()
	u.commands = NewCommands(u.executor)
	u.authenticated = true
	u.isLocalMode = true

	// Switch to main UI
	u.window.SetContent(u.buildMainScreen())

	// Start status refresh loop
	go u.refreshStatusLoop()
}

// buildMainScreen creates the main control panel UI
func (u *UI) buildMainScreen() fyne.CanvasObject {
	// Header
	var modeLabel string
	if u.isLocalMode {
		modeLabel = "Running Locally"
	} else if sshClient, ok := u.executor.(*SSHClient); ok {
		modeLabel = fmt.Sprintf("SSH: %s", sshClient.Host)
	}

	header := container.NewHBox(
		widget.NewLabelWithStyle("KPK Control Panel", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
		layout.NewSpacer(),
		widget.NewLabel(modeLabel),
		widget.NewButtonWithIcon("Disconnect", theme.LogoutIcon(), u.handleDisconnect),
	)

	// Container services panel
	containerPanel := u.buildContainerPanel()

	// Host services panel
	hostServicePanel := u.buildHostServicePanel()

	// Quick actions panel
	actionsPanel := u.buildActionsPanel()

	// Log viewer panel
	logPanel := u.buildLogPanel()

	// Layout: two columns on top, log viewer on bottom
	topRow := container.NewGridWithColumns(2, containerPanel, hostServicePanel)
	middleRow := actionsPanel
	bottomRow := logPanel

	// Create inner split (status panels + actions)
	innerSplit := container.NewVSplit(topRow, middleRow)
	innerSplit.SetOffset(0.85) // Actions panel gets small portion at bottom

	// Create outer split (main content + logs)
	outerSplit := container.NewVSplit(innerSplit, bottomRow)
	outerSplit.SetOffset(0.75) // Logs get 25% at bottom initially

	content := container.NewBorder(
		container.NewVBox(header, widget.NewSeparator()),
		nil, nil, nil,
		outerSplit,
	)

	return content
}

// buildContainerPanel creates the Docker container status panel
func (u *UI) buildContainerPanel() fyne.CanvasObject {
	u.containerList = widget.NewList(
		func() int { return len(u.containers) },
		func() fyne.CanvasObject {
			return container.NewHBox(
				widget.NewIcon(theme.MediaPlayIcon()),
				widget.NewLabel("Container Name"),
				layout.NewSpacer(),
				widget.NewLabel("Status"),
				widget.NewButtonWithIcon("", theme.DocumentIcon(), nil),     // Logs
				widget.NewButtonWithIcon("", theme.ComputerIcon(), nil),     // Exec
				widget.NewButtonWithIcon("", theme.ViewRefreshIcon(), nil),  // Restart
			)
		},
		func(id widget.ListItemID, obj fyne.CanvasObject) {
			if id >= len(u.containers) {
				return
			}
			c := u.containers[id]
			box := obj.(*fyne.Container)

			// Status icon - show warning if crash looping
			icon := box.Objects[0].(*widget.Icon)
			if u.crashLoopContainers[c.Name] {
				icon.SetResource(theme.WarningIcon())
			} else if c.State == "running" {
				icon.SetResource(theme.MediaPlayIcon())
			} else {
				icon.SetResource(theme.MediaStopIcon())
			}

			// Name - add warning prefix if crash looping
			nameLabel := box.Objects[1].(*widget.Label)
			if u.crashLoopContainers[c.Name] {
				nameLabel.SetText("⚠ " + c.Name)
			} else {
				nameLabel.SetText(c.Name)
			}

			// Status text
			box.Objects[3].(*widget.Label).SetText(c.Status)

			// Logs button
			logsBtn := box.Objects[4].(*widget.Button)
			logsBtn.OnTapped = func() { u.showContainerLogs(c.Name) }

			// Exec button - opens terminal with docker exec
			execBtn := box.Objects[5].(*widget.Button)
			execBtn.OnTapped = func() { u.openContainerExec(c.Name) }

			// Restart button
			restartBtn := box.Objects[6].(*widget.Button)
			restartBtn.OnTapped = func() { u.restartContainer(c.Name) }
		},
	)

	u.containerLoading = widget.NewProgressBarInfinite()
	u.containerLoading.Start()

	return container.NewBorder(
		container.NewVBox(
			widget.NewLabelWithStyle("Container Services", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
			u.containerLoading,
		),
		nil, nil, nil,
		u.containerList,
	)
}

// buildHostServicePanel creates the host services status panel
func (u *UI) buildHostServicePanel() fyne.CanvasObject {
	u.hostServiceList = widget.NewList(
		func() int { return len(u.hostServices) },
		func() fyne.CanvasObject {
			return container.NewHBox(
				widget.NewIcon(theme.MediaPlayIcon()),
				widget.NewLabel("Service Name"),
				layout.NewSpacer(),
				widget.NewLabel("Status"),
				widget.NewButtonWithIcon("", theme.DocumentIcon(), nil),
				widget.NewButtonWithIcon("", theme.ViewRefreshIcon(), nil),
			)
		},
		func(id widget.ListItemID, obj fyne.CanvasObject) {
			if id >= len(u.hostServices) {
				return
			}
			s := u.hostServices[id]
			box := obj.(*fyne.Container)

			// Status icon
			icon := box.Objects[0].(*widget.Icon)
			if s.Running {
				icon.SetResource(theme.MediaPlayIcon())
			} else {
				icon.SetResource(theme.MediaStopIcon())
			}

			// Name
			box.Objects[1].(*widget.Label).SetText(s.Name)

			// Status text
			statusText := "Stopped"
			if s.Running {
				statusText = fmt.Sprintf("Running (PID: %d)", s.ProcessID)
			}
			box.Objects[3].(*widget.Label).SetText(statusText)

			// Logs button
			logsBtn := box.Objects[4].(*widget.Button)
			logsBtn.OnTapped = func() { u.showHostServiceLogs(s.Name) }

			// Start/Stop button
			actionBtn := box.Objects[5].(*widget.Button)
			if s.Running {
				actionBtn.SetIcon(theme.MediaStopIcon())
				actionBtn.OnTapped = func() { u.stopHostService(s.Name) }
			} else {
				actionBtn.SetIcon(theme.MediaPlayIcon())
				actionBtn.OnTapped = func() { u.startHostService(s.Name) }
			}
		},
	)

	u.hostServiceLoading = widget.NewProgressBarInfinite()
	u.hostServiceLoading.Start()

	return container.NewBorder(
		container.NewVBox(
			widget.NewLabelWithStyle("Host Services", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
			u.hostServiceLoading,
		),
		nil, nil, nil,
		u.hostServiceList,
	)
}

// buildActionsPanel creates the quick actions panel
func (u *UI) buildActionsPanel() fyne.CanvasObject {
	// Status banner showing overall health
	u.statusBanner = widget.NewLabel("Checking services...")

	backupBtn := widget.NewButtonWithIcon("Create DB Backup", theme.DocumentSaveIcon(), u.createBackup)
	restoreBtn := widget.NewButtonWithIcon("Restore from Backup", theme.DownloadIcon(), u.restoreBackup)

	// Dynamic button: "Start Missing" when services are down, "Restart All" when all running
	u.startRestartBtn = widget.NewButtonWithIcon("Start Missing", theme.MediaPlayIcon(), u.startMissingOrRestartAll)
	u.startRestartBtn.Importance = widget.HighImportance

	stopAllBtn := widget.NewButtonWithIcon("Stop All", theme.MediaStopIcon(), u.stopAll)
	stopAllBtn.Importance = widget.DangerImportance

	reloadNginxBtn := widget.NewButtonWithIcon("Reload Nginx Config", theme.ViewRefreshIcon(), u.reloadNginxConfig)

	return container.NewVBox(
		u.statusBanner,
		widget.NewSeparator(),
		widget.NewLabelWithStyle("Quick Actions", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
		container.NewGridWithColumns(5,
			backupBtn,
			restoreBtn,
			u.startRestartBtn,
			stopAllBtn,
			reloadNginxBtn,
		),
	)
}

// buildLogPanel creates the log viewer panel
func (u *UI) buildLogPanel() fyne.CanvasObject {
	u.logText = widget.NewMultiLineEntry()
	u.logText.Wrapping = fyne.TextWrapWord
	u.logText.SetPlaceHolder("Select a service to view logs...")

	clearBtn := widget.NewButtonWithIcon("Clear", theme.DeleteIcon(), func() {
		u.logText.SetText("")
	})

	return container.NewBorder(
		container.NewHBox(
			widget.NewLabelWithStyle("Logs", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
			layout.NewSpacer(),
			clearBtn,
		),
		nil, nil, nil,
		container.NewScroll(u.logText),
	)
}

// --- Action Handlers ---

func (u *UI) handleDisconnect() {
	if u.executor != nil {
		u.executor.Disconnect()
	}
	u.authenticated = false
	u.isLocalMode = false
	u.window.SetContent(u.buildLoginScreen())
}

// setLogText sets the log text and scrolls to the bottom
func (u *UI) setLogText(text string) {
	u.logText.SetText(text)
	// Move cursor to end to scroll to bottom
	u.logText.CursorRow = len(u.logText.Text)
	u.logText.Refresh()
}

func (u *UI) showContainerLogs(name string) {
	logs, err := u.commands.GetContainerLogs(name, 100)
	if err != nil {
		u.setLogText(fmt.Sprintf("Error getting logs: %v", err))
		return
	}
	u.setLogText(fmt.Sprintf("=== Logs for %s ===\n\n%s", name, logs))
}

func (u *UI) openContainerExec(name string) {
	if u.isLocalMode {
		// Local mode: open a terminal window directly
		err := u.commands.OpenContainerExec(name)
		if err != nil {
			dialog.ShowError(err, u.window)
		}
	} else {
		// SSH mode: open a local terminal that SSHs to the server and runs docker exec
		sshClient, ok := u.executor.(*SSHClient)
		if !ok {
			dialog.ShowError(fmt.Errorf("not connected via SSH"), u.window)
			return
		}
		err := u.openSSHExecTerminal(sshClient.Host, sshClient.Port, sshClient.User, name)
		if err != nil {
			dialog.ShowError(err, u.window)
		}
	}
}

// openSSHExecTerminal opens a local terminal window that SSHs to the server and runs docker exec
func (u *UI) openSSHExecTerminal(host, port, user, containerName string) error {
	// Build SSH command that runs docker exec
	// Use sh instead of bash since many containers (Alpine-based) don't have bash
	sshCmd := fmt.Sprintf("ssh -t -p %s %s@%s docker exec -it %s /bin/sh", port, user, host, containerName)

	// Try Windows Terminal first, fall back to cmd
	// wt = Windows Terminal, cmd = legacy
	cmd := exec.Command("cmd", "/c", "start", "wt", "-p", "Windows PowerShell", "cmd", "/k", sshCmd)
	err := cmd.Start()
	if err != nil {
		// Fallback to regular cmd if Windows Terminal not available
		cmd = exec.Command("cmd", "/c", "start", "cmd", "/k", sshCmd)
		err = cmd.Start()
	}
	return err
}

func (u *UI) showHostServiceLogs(name string) {
	logs, err := u.commands.GetHostServiceLogs(name, 100)
	if err != nil {
		u.setLogText(fmt.Sprintf("Error getting logs: %v", err))
		return
	}
	u.setLogText(fmt.Sprintf("=== Logs for %s ===\n\n%s", name, logs))
}

func (u *UI) restartContainer(name string) {
	dialog.ShowConfirm("Restart Container",
		fmt.Sprintf("Are you sure you want to restart %s?", name),
		func(ok bool) {
			if ok {
				err := u.commands.RestartContainer(name)
				if err != nil {
					dialog.ShowError(err, u.window)
				} else {
					u.refreshStatus()
				}
			}
		}, u.window)
}

func (u *UI) startHostService(name string) {
	u.setLogText(fmt.Sprintf("Starting %s...\n", name))
	go func() {
		appendLog := func(msg string) {
			current := u.logText.Text
			u.logText.SetText(current + msg + "\n")
			u.logText.CursorRow = len(u.logText.Text)
			u.logText.Refresh()
		}

		output, err := u.commands.StartHostServiceWithOutput(name)
		if output != "" {
			appendLog(output)
		}
		if err != nil {
			appendLog(fmt.Sprintf("ERROR: %v", err))
		} else {
			appendLog(fmt.Sprintf("%s started successfully!", name))
		}
		u.refreshStatus()
	}()
}

func (u *UI) stopHostService(name string) {
	dialog.ShowConfirm("Stop Service",
		fmt.Sprintf("Are you sure you want to stop %s?", name),
		func(ok bool) {
			if ok {
				err := u.commands.StopHostService(name)
				if err != nil {
					dialog.ShowError(err, u.window)
				} else {
					u.refreshStatus()
				}
			}
		}, u.window)
}

func (u *UI) createBackup() {
	dialog.ShowConfirm("Create Backup",
		"Create a new database backup?",
		func(ok bool) {
			if ok {
				u.logText.SetText("Creating backup...")
				go func() {
					output, err := u.commands.CreateBackup()
					if err != nil {
						u.logText.SetText(fmt.Sprintf("Backup failed: %v\n%s", err, output))
					} else {
						u.logText.SetText(fmt.Sprintf("Backup completed!\n%s", output))
					}
				}()
			}
		}, u.window)
}

func (u *UI) restoreBackup() {
	// First, get list of backups
	backups, err := u.commands.ListBackups()
	if err != nil {
		dialog.ShowError(err, u.window)
		return
	}

	if len(backups) == 0 {
		dialog.ShowInformation("No Backups", "No backups found in M:\\kpkapp\\backups", u.window)
		return
	}

	// Show selection dialog
	dialog.ShowCustomConfirm("Select Backup", "Restore", "Cancel",
		widget.NewSelect(backups, nil),
		func(ok bool) {
			if ok {
				// TODO: Get selected backup and restore
				dialog.ShowInformation("Restore", "Restore functionality coming soon", u.window)
			}
		}, u.window)
}

func (u *UI) coldStartAll() {
	dialog.ShowConfirm("Cold Start",
		"Start all Docker containers and host services?",
		func(ok bool) {
			if ok {
				u.logText.SetText("Starting cold start sequence...")
				go func() {
					err := u.commands.ColdStart()
					if err != nil {
						u.logText.SetText(fmt.Sprintf("Cold start failed: %v", err))
					} else {
						u.logText.SetText("Cold start completed!")
						u.refreshStatus()
					}
				}()
			}
		}, u.window)
}

func (u *UI) stopAll() {
	dialog.ShowConfirm("Stop All Services",
		"This will stop ALL Docker containers and host services. Are you sure?",
		func(ok bool) {
			if ok {
				u.logText.SetText("Stopping all services...")
				go func() {
					err := u.commands.StopAll()
					if err != nil {
						u.logText.SetText(fmt.Sprintf("Stop all failed: %v", err))
					} else {
						u.logText.SetText("All services stopped.")
						u.refreshStatus()
					}
				}()
			}
		}, u.window)
}

func (u *UI) reloadNginxConfig() {
	dialog.ShowConfirm("Reload Nginx Config",
		"Copy local nginx.conf to container and restart nginx?",
		func(ok bool) {
			if ok {
				u.logText.SetText("Copying nginx.conf and restarting nginx...")
				go func() {
					err := u.commands.ReloadNginxConfig()
					if err != nil {
						u.logText.SetText(fmt.Sprintf("Nginx reload failed: %v", err))
					} else {
						u.logText.SetText("Nginx config reloaded successfully!")
						u.refreshStatus()
					}
				}()
			}
		}, u.window)
}

// startMissingOrRestartAll handles the dynamic button - starts missing services or restarts all
func (u *UI) startMissingOrRestartAll() {
	allRunning := u.isAllServicesRunning()

	if allRunning {
		// All running - offer restart
		dialog.ShowConfirm("Restart All Services",
			"All services are running. Do you want to restart everything?",
			func(ok bool) {
				if ok {
					u.logText.SetText("Restarting all services...")
					go func() {
						// Stop all first
						u.commands.StopAll()
						// Then cold start
						err := u.commands.ColdStart()
						if err != nil {
							u.logText.SetText(fmt.Sprintf("Restart failed: %v", err))
						} else {
							u.logText.SetText("All services restarted!")
							u.refreshStatus()
						}
					}()
				}
			}, u.window)
	} else {
		// Some missing - start them
		dialog.ShowConfirm("Start Missing Services",
			"Start all stopped services?",
			func(ok bool) {
				if ok {
					u.logText.SetText("Starting missing services...\n")
					go func() {
						// Log function that appends to the log window and scrolls to bottom
						logFunc := func(msg string) {
							current := u.logText.Text
							u.logText.SetText(current + msg + "\n")
							u.logText.CursorRow = len(u.logText.Text)
							u.logText.Refresh()
						}
						err := u.commands.StartMissingWithLog(logFunc)
						if err != nil {
							logFunc(fmt.Sprintf("\nERROR: %v", err))
						}
						u.refreshStatus()
					}()
				}
			}, u.window)
	}
}

// isAllServicesRunning checks if all expected services are running
func (u *UI) isAllServicesRunning() bool {
	// Expected containers (7 from docker-compose-PROD.yml: db, app_blue, app_green, nginx, redis, process_excel_completion_listener, ws4kp)
	expectedContainers := 7
	runningContainers := 0
	for _, c := range u.containers {
		if c.State == "running" {
			runningContainers++
		}
	}

	// Expected host services (4)
	expectedHostServices := 4
	runningHostServices := 0
	for _, s := range u.hostServices {
		if s.Running {
			runningHostServices++
		}
	}

	return runningContainers >= expectedContainers && runningHostServices >= expectedHostServices
}

// updateHealthStatus updates the status banner and button based on current state
func (u *UI) updateHealthStatus() {
	if u.statusBanner == nil || u.startRestartBtn == nil {
		return
	}

	// Count running services
	runningContainers := 0
	for _, c := range u.containers {
		if c.State == "running" {
			runningContainers++
		}
	}
	runningHostServices := 0
	for _, s := range u.hostServices {
		if s.Running {
			runningHostServices++
		}
	}

	expectedContainers := 7
	expectedHostServices := 4
	totalExpected := expectedContainers + expectedHostServices
	totalRunning := runningContainers + runningHostServices

	if totalRunning == 0 {
		u.statusBanner.SetText("No services running - Click 'Start Missing' to start the app")
		u.startRestartBtn.SetText("Start All")
		u.startRestartBtn.SetIcon(theme.MediaPlayIcon())
	} else if totalRunning < totalExpected {
		missing := totalExpected - totalRunning
		u.statusBanner.SetText(fmt.Sprintf("%d of %d services running - %d need attention", totalRunning, totalExpected, missing))
		u.startRestartBtn.SetText("Start Missing")
		u.startRestartBtn.SetIcon(theme.MediaPlayIcon())
	} else {
		u.statusBanner.SetText(fmt.Sprintf("All %d services running", totalExpected))
		u.startRestartBtn.SetText("Restart All")
		u.startRestartBtn.SetIcon(theme.ViewRefreshIcon())
	}
}

// --- Status Refresh ---

func (u *UI) refreshStatusLoop() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	// Initial refresh
	u.refreshStatus()

	for range ticker.C {
		if !u.authenticated {
			return
		}
		u.refreshStatus()
	}
}

func (u *UI) refreshStatus() {
	// Get container statuses
	containers, err := u.commands.GetContainerStatuses()
	if err == nil {
		// Track state changes for crash loop detection
		u.trackContainerStateChanges(containers)
		u.containers = containers
	} else {
		// On error (e.g., Docker not running), show empty list
		u.containers = []ContainerStatus{}
	}
	u.containerList.Refresh()
	// Hide loading indicator after first attempt
	if u.containerLoading != nil {
		u.containerLoading.Stop()
		u.containerLoading.Hide()
	}

	// Get host service statuses
	hostServices, err := u.commands.GetHostServiceStatuses()
	if err == nil {
		u.hostServices = hostServices
	} else {
		// On error, show empty list
		u.hostServices = []HostServiceStatus{}
	}
	u.hostServiceList.Refresh()
	// Hide loading indicator after first attempt
	if u.hostServiceLoading != nil {
		u.hostServiceLoading.Stop()
		u.hostServiceLoading.Hide()
	}

	// Update the health status banner and button
	u.updateHealthStatus()
}

// trackContainerStateChanges monitors containers for crash loops
func (u *UI) trackContainerStateChanges(newContainers []ContainerStatus) {
	now := time.Now()
	windowDuration := 5 * time.Minute
	maxStateChanges := 4 // If state changes 4+ times in 5 min, it's a crash loop

	for _, container := range newContainers {
		// Get previous state
		history := u.containerStateHistory[container.Name]

		// Check if state changed from last known state
		if len(history) == 0 || history[len(history)-1].State != container.State {
			// State changed, record it
			u.containerStateHistory[container.Name] = append(history, ContainerStateChange{
				State:     container.State,
				Timestamp: now,
			})
		}

		// Prune old entries outside the window
		var recentChanges []ContainerStateChange
		for _, change := range u.containerStateHistory[container.Name] {
			if now.Sub(change.Timestamp) <= windowDuration {
				recentChanges = append(recentChanges, change)
			}
		}
		u.containerStateHistory[container.Name] = recentChanges

		// Check for crash loop: many state changes in short time
		if len(recentChanges) >= maxStateChanges {
			if !u.crashLoopContainers[container.Name] {
				u.crashLoopContainers[container.Name] = true
				// Log warning
				u.setLogText(fmt.Sprintf("⚠️ CRASH LOOP DETECTED: %s\n\nContainer %s has restarted %d times in the last %v.\n\nThis may indicate:\n- Database might need to be restored from backup\n- Configuration error\n- Missing dependencies\n\nCheck container logs for details.",
					container.Name, container.Name, len(recentChanges), windowDuration))
			}
		} else {
			// Clear crash loop flag if stable
			u.crashLoopContainers[container.Name] = false
		}
	}
}
