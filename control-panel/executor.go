package main

import (
	"bytes"
	"fmt"
	"net"
	"os/exec"
	"strings"
	"syscall"
)

// hideConsoleWindow sets the process to run without a visible console window on Windows
func hideConsoleWindow(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000, // CREATE_NO_WINDOW
	}
}

// Executor interface for running commands (local or remote)
type Executor interface {
	RunCommand(cmd string) (string, error)
	RunCommandWithOutput(cmd string) (stdout, stderr string, err error)
	IsConnected() bool
	Disconnect()
}

// LocalExecutor runs commands on the local machine
type LocalExecutor struct {
	connected bool
}

// NewLocalExecutor creates a new local executor
func NewLocalExecutor() *LocalExecutor {
	return &LocalExecutor{connected: true}
}

// RunCommand executes a command locally
func (l *LocalExecutor) RunCommand(cmdStr string) (string, error) {
	cmd := exec.Command("powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmdStr)
	hideConsoleWindow(cmd)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()

	// Combine stdout and stderr (matches SSHClient behavior)
	output := stdout.String()
	if stderr.Len() > 0 {
		if output != "" {
			output += "\n"
		}
		output += stderr.String()
	}

	if err != nil {
		return output, fmt.Errorf("command failed: %v", err)
	}
	return output, nil
}

// RunCommandWithOutput executes a command and returns both stdout and stderr
func (l *LocalExecutor) RunCommandWithOutput(cmdStr string) (stdout, stderr string, err error) {
	cmd := exec.Command("powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmdStr)

	// Hide the console window on Windows
	hideConsoleWindow(cmd)

	var stdoutBuf, stderrBuf bytes.Buffer
	cmd.Stdout = &stdoutBuf
	cmd.Stderr = &stderrBuf

	err = cmd.Run()
	return stdoutBuf.String(), stderrBuf.String(), err
}

// IsConnected returns true (always connected locally)
func (l *LocalExecutor) IsConnected() bool {
	return l.connected
}

// Disconnect is a no-op for local executor
func (l *LocalExecutor) Disconnect() {
	l.connected = false
}

// --- Detection ---

// IsLocalHost checks if the target IP is this machine
func IsLocalHost(targetIP string) bool {
	// Check common local addresses
	if targetIP == "localhost" || targetIP == "127.0.0.1" {
		return true
	}

	// Get all local IPs
	localIPs := getLocalIPs()
	for _, ip := range localIPs {
		if ip == targetIP {
			return true
		}
	}

	return false
}

// getLocalIPs returns all IP addresses of this machine
func getLocalIPs() []string {
	var ips []string

	interfaces, err := net.Interfaces()
	if err != nil {
		return ips
	}

	for _, iface := range interfaces {
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}

		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}

			if ip != nil && ip.To4() != nil {
				ips = append(ips, ip.String())
			}
		}
	}

	return ips
}

// GetLocalIPSummary returns a string describing local IPs (for UI display)
func GetLocalIPSummary() string {
	ips := getLocalIPs()
	var filtered []string
	for _, ip := range ips {
		// Skip loopback
		if !strings.HasPrefix(ip, "127.") {
			filtered = append(filtered, ip)
		}
	}
	if len(filtered) == 0 {
		return "unknown"
	}
	return strings.Join(filtered, ", ")
}
