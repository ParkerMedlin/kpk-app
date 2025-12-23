package main

import (
	"flag"
	"fmt"
	"os"
	"os/user"
	"strconv"
	"strings"
)

// CLIConfig holds the CLI connection settings
type CLIConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Local    bool
	Lines    int
}

// CLI handles command-line interface operations
type CLI struct {
	config   CLIConfig
	exec     Executor
	commands *Commands
}

// NewCLI creates a new CLI instance
func NewCLI(config CLIConfig) *CLI {
	return &CLI{config: config}
}

// Connect establishes the connection (SSH or local)
func (c *CLI) Connect() error {
	if c.config.Local {
		c.exec = NewLocalExecutor()
		c.commands = NewCommands(c.exec)
		return nil
	}

	// SSH connection
	if c.config.User == "" {
		return fmt.Errorf("username required for SSH connection (use --user or -u)")
	}

	client := NewSSHClient(c.config.Host, c.config.Port, c.config.User)

	var err error
	if c.config.Password != "" {
		err = client.ConnectWithPassword(c.config.Password)
	} else {
		// Try SSH key auth
		err = client.Connect()
	}

	if err != nil {
		return fmt.Errorf("connection failed: %w", err)
	}

	c.exec = client
	c.commands = NewCommands(c.exec)
	return nil
}

// Disconnect closes the connection
func (c *CLI) Disconnect() {
	if c.exec != nil {
		c.exec.Disconnect()
	}
}

// RunCLI parses arguments and executes the appropriate command
// Returns true if CLI mode was detected (arguments present)
func RunCLI() bool {
	if len(os.Args) < 2 {
		// No args = show help
		printUsage()
		os.Exit(0)
		return true
	}

	// Check if first arg looks like a command (not a flag)
	firstArg := os.Args[1]

	// Special case: "gui" command launches GUI mode
	if firstArg == "gui" {
		return false // Let main() continue to GUI
	}

	if strings.HasPrefix(firstArg, "-") && firstArg != "-h" && firstArg != "--help" {
		return false // Flag first = GUI mode (Fyne may have its own flags)
	}

	// Parse global flags
	fs := flag.NewFlagSet("kpk-control-panel", flag.ExitOnError)

	defaultUser := getCurrentUser()

	var config CLIConfig
	fs.StringVar(&config.Host, "host", "192.168.178.169", "SSH host")
	fs.StringVar(&config.Host, "H", "192.168.178.169", "SSH host (shorthand)")
	fs.StringVar(&config.Port, "port", "22", "SSH port")
	fs.StringVar(&config.Port, "p", "22", "SSH port (shorthand)")
	fs.StringVar(&config.User, "user", defaultUser, "SSH username")
	fs.StringVar(&config.User, "u", defaultUser, "SSH username (shorthand)")
	fs.StringVar(&config.Password, "password", "", "SSH password")
	fs.StringVar(&config.Password, "P", "", "SSH password (shorthand)")
	fs.BoolVar(&config.Local, "local", false, "Use local mode instead of SSH")
	fs.IntVar(&config.Lines, "lines", 100, "Number of log lines to show")
	fs.IntVar(&config.Lines, "n", 100, "Number of log lines (shorthand)")

	fs.Usage = func() {
		printUsage()
	}

	// Find the command and its position
	cmdIdx := 1
	for i := 1; i < len(os.Args); i++ {
		arg := os.Args[i]
		if !strings.HasPrefix(arg, "-") {
			cmdIdx = i
			break
		}
		// Skip the value of flags that take values
		if arg == "-H" || arg == "--host" ||
		   arg == "-p" || arg == "--port" ||
		   arg == "-u" || arg == "--user" ||
		   arg == "-P" || arg == "--password" ||
		   arg == "-n" || arg == "--lines" {
			i++ // Skip next arg (the value)
		}
	}

	// Parse flags that come before the command
	if cmdIdx > 1 {
		fs.Parse(os.Args[1:cmdIdx])
	}

	// Also parse flags that come after the command
	command := ""
	subArgs := []string{}
	if cmdIdx < len(os.Args) {
		command = os.Args[cmdIdx]
		if cmdIdx+1 < len(os.Args) {
			subArgs = os.Args[cmdIdx+1:]
		}
	}

	// Parse remaining args for flags
	for i := 0; i < len(subArgs); i++ {
		arg := subArgs[i]
		switch arg {
		case "-H", "--host":
			if i+1 < len(subArgs) {
				config.Host = subArgs[i+1]
				i++
			}
		case "-p", "--port":
			if i+1 < len(subArgs) {
				config.Port = subArgs[i+1]
				i++
			}
		case "-u", "--user":
			if i+1 < len(subArgs) {
				config.User = subArgs[i+1]
				i++
			}
		case "-P", "--password":
			if i+1 < len(subArgs) {
				config.Password = subArgs[i+1]
				i++
			}
		case "-n", "--lines":
			if i+1 < len(subArgs) {
				if n, err := strconv.Atoi(subArgs[i+1]); err == nil {
					config.Lines = n
				}
				i++
			}
		case "--local":
			config.Local = true
		}
	}

	// Handle help
	if command == "" || command == "help" || command == "-h" || command == "--help" {
		printUsage()
		os.Exit(0)
	}

	// Execute the command
	cli := NewCLI(config)
	exitCode := cli.Execute(command, subArgs)
	os.Exit(exitCode)
	return true
}

// Execute runs the specified command
func (c *CLI) Execute(command string, args []string) int {
	// Commands that don't need connection
	switch command {
	case "version":
		fmt.Printf("%s v%s\n", AppName, AppVersion)
		return 0
	}

	// Connect for all other commands
	if err := c.Connect(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}
	defer c.Disconnect()

	// Filter out flag arguments to get positional args
	positional := filterPositionalArgs(args)

	switch command {
	case "status":
		return c.cmdStatus()
	case "start-missing":
		return c.cmdStartMissing()
	case "start-all", "cold-start":
		return c.cmdColdStart()
	case "stop-all":
		return c.cmdStopAll()
	case "container":
		return c.cmdContainer(positional)
	case "service":
		return c.cmdService(positional)
	case "backup":
		return c.cmdBackup(positional)
	case "git":
		return c.cmdGit(positional)
	case "nginx":
		return c.cmdNginx(positional)
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", command)
		fmt.Fprintf(os.Stderr, "Run 'kpk help' for usage\n")
		return 1
	}
}

// getCurrentUser returns the current system username
func getCurrentUser() string {
	if u, err := user.Current(); err == nil {
		username := u.Username
		// On Windows, user.Current() returns DOMAIN\username - strip the domain
		if idx := strings.LastIndex(username, "\\"); idx >= 0 {
			username = username[idx+1:]
		}
		return username
	}
	// Fallback to environment variable
	if username := os.Getenv("USERNAME"); username != "" {
		return username
	}
	if username := os.Getenv("USER"); username != "" {
		return username
	}
	return ""
}

// filterPositionalArgs removes flag arguments from args
func filterPositionalArgs(args []string) []string {
	var result []string
	skipNext := false
	for _, arg := range args {
		if skipNext {
			skipNext = false
			continue
		}
		if strings.HasPrefix(arg, "-") {
			// Check if this flag takes a value
			if arg == "-H" || arg == "--host" ||
			   arg == "-p" || arg == "--port" ||
			   arg == "-u" || arg == "--user" ||
			   arg == "-P" || arg == "--password" ||
			   arg == "-n" || arg == "--lines" {
				skipNext = true
			}
			continue
		}
		result = append(result, arg)
	}
	return result
}

// Command implementations

func (c *CLI) cmdStatus() int {
	fmt.Println("=== Docker Containers ===")
	containers, err := c.commands.GetContainerStatuses()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting containers: %v\n", err)
	} else {
		for _, cont := range containers {
			stateIcon := "[-]"
			if cont.State == "running" {
				stateIcon = "[+]"
			}
			fmt.Printf("%s %-30s %s\n", stateIcon, cont.Name, cont.Status)
		}
	}

	fmt.Println()
	fmt.Println("=== Host Services ===")
	services, err := c.commands.GetHostServiceStatuses()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting services: %v\n", err)
	} else {
		for _, svc := range services {
			stateIcon := "[-]"
			if svc.Running {
				stateIcon = "[+]"
			}
			fmt.Printf("%s %-20s", stateIcon, svc.Name)
			if svc.Running {
				fmt.Printf(" (PID: %s, CPU: %s, Mem: %s)", svc.ProcessID, svc.CPU, svc.Memory)
			}
			fmt.Println()
		}
	}

	return 0
}

func (c *CLI) cmdStartMissing() int {
	fmt.Println("Starting missing services...")

	err := c.commands.StartMissingWithLog(func(msg string) {
		fmt.Println(msg)
	})

	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}

	fmt.Println("Done.")
	return 0
}

func (c *CLI) cmdColdStart() int {
	fmt.Println("Performing cold start...")

	if err := c.commands.ColdStart(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}

	fmt.Println("Cold start complete.")
	return 0
}

func (c *CLI) cmdStopAll() int {
	fmt.Println("Stopping all services...")

	if err := c.commands.StopAll(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		return 1
	}

	fmt.Println("All services stopped.")
	return 0
}

func (c *CLI) cmdContainer(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: container <logs|start|stop|restart> <name>")
		return 1
	}

	subCmd := args[0]

	switch subCmd {
	case "list":
		containers, err := c.commands.GetContainerStatuses()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		for _, cont := range containers {
			fmt.Println(cont.Name)
		}
		return 0

	case "logs":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: container logs <name> [--lines N]")
			return 1
		}
		name := c.resolveContainerName(args[1])
		logs, err := c.commands.GetContainerLogs(name, c.config.Lines)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Print(logs)
		return 0

	case "start":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: container start <name>")
			return 1
		}
		name := c.resolveContainerName(args[1])
		fmt.Printf("Starting container %s...\n", name)
		if err := c.commands.StartContainer(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("Started.")
		return 0

	case "stop":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: container stop <name>")
			return 1
		}
		name := c.resolveContainerName(args[1])
		fmt.Printf("Stopping container %s...\n", name)
		if err := c.commands.StopContainer(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("Stopped.")
		return 0

	case "restart":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: container restart <name>")
			return 1
		}
		name := c.resolveContainerName(args[1])
		fmt.Printf("Restarting container %s...\n", name)
		if err := c.commands.RestartContainer(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("Restarted.")
		return 0

	default:
		fmt.Fprintf(os.Stderr, "Unknown container command: %s\n", subCmd)
		return 1
	}
}

func (c *CLI) cmdService(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: service <list|logs|start|stop> <name>")
		return 1
	}

	subCmd := args[0]

	switch subCmd {
	case "list":
		services, err := c.commands.GetHostServiceStatuses()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		for _, svc := range services {
			fmt.Println(svc.Name)
		}
		return 0

	case "logs":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: service logs <name> [--lines N]")
			return 1
		}
		name := args[1]
		logs, err := c.commands.GetHostServiceLogs(name, c.config.Lines)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Print(logs)
		return 0

	case "start":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: service start <name>")
			return 1
		}
		name := args[1]
		fmt.Printf("Starting service %s...\n", name)
		output, err := c.commands.StartHostServiceWithOutput(name)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println(output)
		return 0

	case "stop":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: service stop <name>")
			return 1
		}
		name := args[1]
		fmt.Printf("Stopping service %s...\n", name)
		if err := c.commands.StopHostService(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("Stopped.")
		return 0

	default:
		fmt.Fprintf(os.Stderr, "Unknown service command: %s\n", subCmd)
		return 1
	}
}

func (c *CLI) cmdBackup(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: backup <create|list|restore> [name]")
		return 1
	}

	subCmd := args[0]

	switch subCmd {
	case "create":
		fmt.Println("Creating database backup...")
		output, err := c.commands.CreateBackup()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		if output != "" {
			fmt.Print(output)
		}
		fmt.Println("Backup created.")
		return 0

	case "list":
		backups, err := c.commands.ListBackups()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		if len(backups) == 0 {
			fmt.Println("No backups found.")
		} else {
			for _, b := range backups {
				fmt.Println(b)
			}
		}
		return 0

	case "restore":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Usage: backup restore <name>")
			fmt.Fprintln(os.Stderr, "Use 'backup list' to see available backups")
			return 1
		}
		name := args[1]
		fmt.Printf("Restoring from backup %s...\n", name)
		if err := c.commands.RestoreBackup(name); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("Backup restored.")
		return 0

	default:
		fmt.Fprintf(os.Stderr, "Unknown backup command: %s\n", subCmd)
		return 1
	}
}

func (c *CLI) cmdGit(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: git <status|fetch|pull|collectstatic>")
		return 1
	}

	subCmd := args[0]

	switch subCmd {
	case "status":
		status, err := c.commands.GetGitStatus()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Printf("Branch: %s\n", status.Branch)
		fmt.Printf("Commit: %s %s\n", status.CommitHash, status.CommitMsg)
		if status.Behind > 0 {
			fmt.Printf("Behind: %d commits\n", status.Behind)
		}
		if status.Ahead > 0 {
			fmt.Printf("Ahead: %d commits\n", status.Ahead)
		}
		if status.HasChanges {
			fmt.Println("Has uncommitted changes")
		}
		return 0

	case "fetch":
		fmt.Println("Fetching from origin...")
		output, err := c.commands.GitFetch()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		if output != "" {
			fmt.Print(output)
		}
		fmt.Println("Fetch complete.")
		return 0

	case "pull":
		fmt.Println("Pulling from origin/main...")
		output, err := c.commands.GitPull()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Print(output)
		return 0

	case "collectstatic":
		fmt.Println("Running collectstatic...")
		output, err := c.commands.RunCollectStatic()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Print(output)
		return 0

	default:
		fmt.Fprintf(os.Stderr, "Unknown git command: %s\n", subCmd)
		return 1
	}
}

func (c *CLI) cmdNginx(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "Usage: nginx <reload>")
		return 1
	}

	subCmd := args[0]

	switch subCmd {
	case "reload":
		fmt.Println("Reloading nginx config...")
		if err := c.commands.ReloadNginxConfig(); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return 1
		}
		fmt.Println("Nginx config reloaded.")
		return 0

	default:
		fmt.Fprintf(os.Stderr, "Unknown nginx command: %s\n", subCmd)
		return 1
	}
}

// resolveContainerName adds kpk-app prefix if needed
func (c *CLI) resolveContainerName(name string) string {
	if strings.HasPrefix(name, "kpk-app") {
		return name
	}
	// Common short names
	switch name {
	case "app_blue", "blue":
		return "kpk-app_app_blue_1"
	case "app_green", "green":
		return "kpk-app_app_green_1"
	case "nginx":
		return "kpk-app_nginx_1"
	case "postgres", "db":
		return "kpk-app_postgres_1"
	case "redis":
		return "kpk-app_redis_1"
	case "celery", "celery_worker":
		return "kpk-app_celery_worker_1"
	case "celery_beat":
		return "kpk-app_celery_beat_1"
	default:
		return "kpk-app_" + name + "_1"
	}
}

func printUsage() {
	fmt.Printf("%s v%s\n", AppName, AppVersion)
	fmt.Println()
	fmt.Println("USAGE:")
	fmt.Println("  kpk [command] [args] [flags]")
	fmt.Println("  kpk                          # Show this help")
	fmt.Println("  kpk gui                      # Launch GUI")
	fmt.Println()
	fmt.Println("CONNECTION FLAGS:")
	fmt.Println("  -H, --host <host>      SSH host (default: 192.168.178.169)")
	fmt.Println("  -p, --port <port>      SSH port (default: 22)")
	fmt.Println("  -u, --user <user>      SSH username (default: current user)")
	fmt.Println("  -P, --password <pass>  SSH password (or use SSH key)")
	fmt.Println("  --local                Use local mode instead of SSH")
	fmt.Println("  -n, --lines <n>        Number of log lines (default: 100)")
	fmt.Println()
	fmt.Println("COMMANDS:")
	fmt.Println("  status                 Show all containers and host services")
	fmt.Println("  start-missing          Start only stopped services")
	fmt.Println("  start-all              Cold start everything (Docker + all services)")
	fmt.Println("  stop-all               Stop all services and containers")
	fmt.Println()
	fmt.Println("  container list                  List all containers")
	fmt.Println("  container logs <name>           Show container logs")
	fmt.Println("  container start <name>          Start a container")
	fmt.Println("  container stop <name>           Stop a container")
	fmt.Println("  container restart <name>        Restart a container")
	fmt.Println()
	fmt.Println("  service list                    List all host services")
	fmt.Println("  service logs <name>             Show service logs")
	fmt.Println("  service start <name>            Start a host service")
	fmt.Println("  service stop <name>             Stop a host service")
	fmt.Println()
	fmt.Println("  backup create                   Create database backup")
	fmt.Println("  backup list                     List available backups")
	fmt.Println("  backup restore <name>           Restore from backup")
	fmt.Println()
	fmt.Println("  git status                      Show git status")
	fmt.Println("  git fetch                       Fetch from origin")
	fmt.Println("  git pull                        Pull from origin/main")
	fmt.Println("  git collectstatic               Run Django collectstatic")
	fmt.Println()
	fmt.Println("  nginx reload                    Hot-reload nginx config")
	fmt.Println()
	fmt.Println("  version                         Show version")
	fmt.Println("  help                            Show this help")
	fmt.Println("  gui                             Launch the GUI")
	fmt.Println()
	fmt.Println("EXAMPLES:")
	fmt.Println("  kpk status                           # Uses current user")
	fmt.Println("  kpk start-missing")
	fmt.Println("  kpk container logs app_blue -n 50")
	fmt.Println("  kpk service start data_sync")
	fmt.Println("  kpk git pull")
	fmt.Println("  kpk status --local                   # Local mode (on server)")
	fmt.Println("  kpk status -u otheruser              # Override username")
	fmt.Println()
	fmt.Println("CONTAINER SHORT NAMES:")
	fmt.Println("  app_blue, blue    -> kpk-app_app_blue_1")
	fmt.Println("  app_green, green  -> kpk-app_app_green_1")
	fmt.Println("  nginx             -> kpk-app_nginx_1")
	fmt.Println("  postgres, db      -> kpk-app_postgres_1")
	fmt.Println("  redis             -> kpk-app_redis_1")
	fmt.Println("  celery            -> kpk-app_celery_worker_1")
	fmt.Println()
	fmt.Println("HOST SERVICES:")
	fmt.Println("  data_sync, excel_worker, stream_relay, looper_health")
}
