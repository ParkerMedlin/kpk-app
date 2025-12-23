package main

import (
	"encoding/json"
	"fmt"

	"github.com/anthropics/anthropic-sdk-go"
)

// Write tools that require user confirmation
var writeTools = map[string]bool{
	"start_container":  true,
	"stop_container":   true,
	"restart_container": true,
	"start_service":    true,
	"stop_service":     true,
	"start_missing":    true,
	"cold_start":       true,
	"stop_all":         true,
	"reload_nginx":     true,
	"create_backup":    true,
	"git_pull":         true,
	"collectstatic":    true,
}

// isWriteTool returns true if the tool requires user confirmation
func isWriteTool(name string) bool {
	return writeTools[name]
}

// buildTools creates all tool definitions for the assistant
func buildTools() []anthropic.ToolUnionParam {
	return []anthropic.ToolUnionParam{
		// Read-only tools (no confirmation required)
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "get_status",
				Description: anthropic.String("Get the current status of all Docker containers and host services. Returns running state, process IDs, and health information. Use this first when diagnosing issues."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "get_container_logs",
				Description: anthropic.String("Get recent logs from a Docker container. Use this to diagnose container issues."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"container_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the Docker container (e.g., kpk-app_app_blue_1, kpk-app_postgres_1)",
						},
						"lines": map[string]interface{}{
							"type":        "integer",
							"description": "Number of log lines to retrieve (default 100)",
						},
					},
					Required: []string{"container_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "get_service_logs",
				Description: anthropic.String("Get recent logs from a host service. Use this to diagnose host service issues."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"service_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the host service (data_sync, excel_worker, stream_relay, or looper_health)",
						},
						"lines": map[string]interface{}{
							"type":        "integer",
							"description": "Number of log lines to retrieve (default 100)",
						},
					},
					Required: []string{"service_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "get_git_status",
				Description: anthropic.String("Get current git repository status including branch, commit hash, and sync status with remote."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "list_backups",
				Description: anthropic.String("List available database backups."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},

		// Write tools (require user confirmation)
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "start_container",
				Description: anthropic.String("Start a stopped Docker container. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"container_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the Docker container to start",
						},
					},
					Required: []string{"container_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "stop_container",
				Description: anthropic.String("Stop a running Docker container. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"container_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the Docker container to stop",
						},
					},
					Required: []string{"container_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "restart_container",
				Description: anthropic.String("Restart a Docker container. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"container_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the Docker container to restart",
						},
					},
					Required: []string{"container_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "start_service",
				Description: anthropic.String("Start a host service. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"service_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the host service to start (data_sync, excel_worker, stream_relay, or looper_health)",
						},
					},
					Required: []string{"service_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "stop_service",
				Description: anthropic.String("Stop a host service. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type: "object",
					Properties: map[string]interface{}{
						"service_name": map[string]interface{}{
							"type":        "string",
							"description": "Name of the host service to stop",
						},
					},
					Required: []string{"service_name"},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "start_missing",
				Description: anthropic.String("Start all stopped containers and host services. Use this when multiple services are down. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "cold_start",
				Description: anthropic.String("Full cold start - start Docker Desktop, all containers, and all host services. Use this after a server reboot. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "stop_all",
				Description: anthropic.String("Stop ALL containers and host services. Use with caution. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "reload_nginx",
				Description: anthropic.String("Copy nginx.conf to container and restart nginx. Use after editing nginx configuration. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "create_backup",
				Description: anthropic.String("Create a new database backup. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "git_pull",
				Description: anthropic.String("Pull latest changes from origin/main. Run collectstatic after if CSS/JS files changed. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
		anthropic.ToolUnionParam{
			OfTool: &anthropic.ToolParam{
				Name:        "collectstatic",
				Description: anthropic.String("Run Django collectstatic command in app_blue container. Use after git pull if static files changed. REQUIRES USER CONFIRMATION."),
				InputSchema: anthropic.ToolInputSchemaParam{
					Type:       "object",
					Properties: map[string]interface{}{},
				},
			},
		},
	}
}

// buildConfirmationMessage creates a human-readable description for the confirmation dialog
func buildConfirmationMessage(tool anthropic.ToolUseBlock) string {
	descriptions := map[string]string{
		"start_container":  "Start Docker container",
		"stop_container":   "Stop Docker container",
		"restart_container": "Restart Docker container",
		"start_service":    "Start host service",
		"stop_service":     "Stop host service",
		"start_missing":    "Start all stopped services",
		"cold_start":       "Perform full cold start (Docker + all services)",
		"stop_all":         "Stop ALL containers and services",
		"reload_nginx":     "Reload nginx configuration",
		"create_backup":    "Create database backup",
		"git_pull":         "Pull latest code from git",
		"collectstatic":    "Run Django collectstatic",
	}

	desc := descriptions[tool.Name]
	if desc == "" {
		desc = tool.Name
	}

	// Add input parameters if present
	if tool.Input != nil {
		inputBytes, _ := json.MarshalIndent(tool.Input, "", "  ")
		inputStr := string(inputBytes)
		if inputStr != "{}" && inputStr != "null" {
			return fmt.Sprintf("%s\n\nParameters:\n%s", desc, inputStr)
		}
	}

	return desc
}
