package main

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"time"

	"golang.org/x/crypto/ssh"
)

// SSHClient wraps an SSH connection to the server
type SSHClient struct {
	Host       string
	Port       string
	User       string
	client     *ssh.Client
	connected  bool
}

// NewSSHClient creates a new SSH client configuration
func NewSSHClient(host, port, user string) *SSHClient {
	return &SSHClient{
		Host: host,
		Port: port,
		User: user,
	}
}

// Connect establishes an SSH connection using key-based auth
func (s *SSHClient) Connect() error {
	keyPath := filepath.Join(os.Getenv("USERPROFILE"), ".ssh", "id_rsa")
	key, err := os.ReadFile(keyPath)
	if err != nil {
		return fmt.Errorf("unable to read private key: %v", err)
	}

	signer, err := ssh.ParsePrivateKey(key)
	if err != nil {
		return fmt.Errorf("unable to parse private key: %v", err)
	}

	config := &ssh.ClientConfig{
		User: s.User,
		Auth: []ssh.AuthMethod{
			ssh.PublicKeys(signer),
		},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // TODO: proper host key verification
		Timeout:         10 * time.Second,
	}

	addr := net.JoinHostPort(s.Host, s.Port)
	client, err := ssh.Dial("tcp", addr, config)
	if err != nil {
		return fmt.Errorf("failed to connect: %v", err)
	}

	s.client = client
	s.connected = true
	return nil
}

// ConnectWithPassword establishes an SSH connection using password auth
func (s *SSHClient) ConnectWithPassword(password string) error {
	config := &ssh.ClientConfig{
		User: s.User,
		Auth: []ssh.AuthMethod{
			ssh.Password(password),
		},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // TODO: proper host key verification
		Timeout:         10 * time.Second,
	}

	addr := net.JoinHostPort(s.Host, s.Port)
	client, err := ssh.Dial("tcp", addr, config)
	if err != nil {
		return fmt.Errorf("failed to connect: %v", err)
	}

	s.client = client
	s.connected = true
	return nil
}

// Disconnect closes the SSH connection (implements Executor interface)
func (s *SSHClient) Disconnect() {
	if s.client != nil {
		s.client.Close()
		s.connected = false
	}
}

// IsConnected returns the connection status (implements Executor interface)
func (s *SSHClient) IsConnected() bool {
	return s.connected
}

// RunCommand executes a command on the remote server via PowerShell
func (s *SSHClient) RunCommand(cmd string) (string, error) {
	if !s.connected {
		return "", fmt.Errorf("not connected")
	}

	session, err := s.client.NewSession()
	if err != nil {
		return "", fmt.Errorf("failed to create session: %v", err)
	}
	defer session.Close()

	var stdout, stderr bytes.Buffer
	session.Stdout = &stdout
	session.Stderr = &stderr

	// Use PowerShell with encoded command to avoid quote escaping issues
	// Base64 encode the command for safe transport
	encoded := base64.StdEncoding.EncodeToString([]byte(utf16LEEncode(cmd)))
	psCmd := fmt.Sprintf(`powershell -NoProfile -EncodedCommand %s`, encoded)
	err = session.Run(psCmd)
	if err != nil {
		return stderr.String(), fmt.Errorf("command failed: %v - %s", err, stderr.String())
	}

	return stdout.String(), nil
}

// utf16LEEncode converts string to UTF-16 LE bytes (required for PowerShell -EncodedCommand)
func utf16LEEncode(s string) []byte {
	var buf bytes.Buffer
	for _, r := range s {
		buf.WriteByte(byte(r))
		buf.WriteByte(byte(r >> 8))
	}
	return buf.Bytes()
}

// RunCommandWithOutput executes a command and returns both stdout and stderr
func (s *SSHClient) RunCommandWithOutput(cmd string) (stdout, stderr string, err error) {
	if !s.connected {
		return "", "", fmt.Errorf("not connected")
	}

	session, err := s.client.NewSession()
	if err != nil {
		return "", "", fmt.Errorf("failed to create session: %v", err)
	}
	defer session.Close()

	var stdoutBuf, stderrBuf bytes.Buffer
	session.Stdout = &stdoutBuf
	session.Stderr = &stderrBuf

	err = session.Run(cmd)
	return stdoutBuf.String(), stderrBuf.String(), err
}
