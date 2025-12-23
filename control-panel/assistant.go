package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
)

// AssistantClient manages Claude API interactions
type AssistantClient struct {
	client       anthropic.Client
	commands     *Commands
	confirmFunc  func(toolName, description string) bool
	messages     []anthropic.MessageParam
	tools        []anthropic.ToolUnionParam
	systemPrompt []anthropic.TextBlockParam
}

// NewAssistantClient creates a new Claude assistant client
func NewAssistantClient(commands *Commands, confirmFunc func(string, string) bool) *AssistantClient {
	client := anthropic.NewClient(
		option.WithAPIKey(AnthropicAPIKey),
	)

	ac := &AssistantClient{
		client:      client,
		commands:    commands,
		confirmFunc: confirmFunc,
		messages:    []anthropic.MessageParam{},
	}

	ac.systemPrompt = []anthropic.TextBlockParam{
		{Text: buildSystemPrompt()},
	}
	ac.tools = buildTools()

	return ac
}

// Chat sends a user message and processes the response with tool use
func (ac *AssistantClient) Chat(ctx context.Context, userMessage string) (string, error) {
	// Add user message
	ac.messages = append(ac.messages, anthropic.NewUserMessage(
		anthropic.NewTextBlock(userMessage),
	))

	return ac.runAgentLoop(ctx)
}

// runAgentLoop processes messages until Claude stops calling tools
func (ac *AssistantClient) runAgentLoop(ctx context.Context) (string, error) {
	var finalResponse string

	for {
		message, err := ac.client.Messages.New(ctx, anthropic.MessageNewParams{
			Model:     "claude-sonnet-4-20250514",
			MaxTokens: 4096,
			System:    ac.systemPrompt,
			Messages:  ac.messages,
			Tools:     ac.tools,
		})
		if err != nil {
			return "", fmt.Errorf("API error: %w", err)
		}

		// Collect text response and tool calls
		var textParts []string
		var toolCalls []anthropic.ToolUseBlock

		for _, block := range message.Content {
			switch b := block.AsAny().(type) {
			case anthropic.TextBlock:
				textParts = append(textParts, b.Text)
			case anthropic.ToolUseBlock:
				toolCalls = append(toolCalls, b)
			}
		}

		finalResponse = strings.Join(textParts, "\n")

		// Convert content blocks to params for assistant message
		var contentParams []anthropic.ContentBlockParamUnion
		for _, block := range message.Content {
			switch b := block.AsAny().(type) {
			case anthropic.TextBlock:
				contentParams = append(contentParams, anthropic.NewTextBlock(b.Text))
			case anthropic.ToolUseBlock:
				contentParams = append(contentParams, anthropic.ContentBlockParamUnion{
					OfToolUse: &anthropic.ToolUseBlockParam{
						ID:    b.ID,
						Name:  b.Name,
						Input: b.Input,
					},
				})
			}
		}
		ac.messages = append(ac.messages, anthropic.NewAssistantMessage(contentParams...))

		// If no tool calls or stop reason is end_turn, we're done
		if len(toolCalls) == 0 || message.StopReason == "end_turn" {
			break
		}

		// Process tool calls
		var toolResults []anthropic.ContentBlockParamUnion
		for _, tool := range toolCalls {
			result, isError := ac.executeTool(ctx, tool)
			toolResults = append(toolResults,
				anthropic.NewToolResultBlock(tool.ID, result, isError))
		}

		// Add tool results to messages
		ac.messages = append(ac.messages, anthropic.NewUserMessage(toolResults...))
	}

	return finalResponse, nil
}

// executeTool runs a tool and returns the result
func (ac *AssistantClient) executeTool(ctx context.Context, tool anthropic.ToolUseBlock) (string, bool) {
	// Check if this is a write tool requiring confirmation
	if isWriteTool(tool.Name) {
		return ac.executeWriteToolWithConfirmation(ctx, tool)
	}
	return ac.executeReadTool(tool)
}

// executeReadTool executes a read-only tool
func (ac *AssistantClient) executeReadTool(tool anthropic.ToolUseBlock) (string, bool) {
	var result interface{}
	var err error
	var strResult string

	// Parse input JSON
	inputBytes, _ := json.Marshal(tool.Input)

	switch tool.Name {
	case "get_status":
		containers, cErr := ac.commands.GetContainerStatuses()
		services, sErr := ac.commands.GetHostServiceStatuses()
		if cErr != nil && sErr != nil {
			return fmt.Sprintf("Error getting status: containers: %v, services: %v", cErr, sErr), true
		}
		result = map[string]interface{}{
			"containers":    containers,
			"host_services": services,
		}

	case "get_container_logs":
		var input struct {
			ContainerName string `json:"container_name"`
			Lines         int    `json:"lines"`
		}
		json.Unmarshal(inputBytes, &input)
		if input.Lines == 0 {
			input.Lines = 100
		}
		strResult, err = ac.commands.GetContainerLogs(input.ContainerName, input.Lines)
		if err != nil {
			return fmt.Sprintf("Error: %v", err), true
		}
		return strResult, false

	case "get_service_logs":
		var input struct {
			ServiceName string `json:"service_name"`
			Lines       int    `json:"lines"`
		}
		json.Unmarshal(inputBytes, &input)
		if input.Lines == 0 {
			input.Lines = 100
		}
		strResult, err = ac.commands.GetHostServiceLogs(input.ServiceName, input.Lines)
		if err != nil {
			return fmt.Sprintf("Error: %v", err), true
		}
		return strResult, false

	case "get_git_status":
		gitStatus, err := ac.commands.GetGitStatus()
		if err != nil {
			return fmt.Sprintf("Error: %v", err), true
		}
		result = gitStatus

	case "list_backups":
		backups, err := ac.commands.ListBackups()
		if err != nil {
			return fmt.Sprintf("Error: %v", err), true
		}
		result = backups

	default:
		return fmt.Sprintf("Unknown tool: %s", tool.Name), true
	}

	// Convert result to JSON string
	jsonResult, _ := json.MarshalIndent(result, "", "  ")
	return string(jsonResult), false
}

// executeWriteToolWithConfirmation handles write tools with user confirmation
func (ac *AssistantClient) executeWriteToolWithConfirmation(ctx context.Context, tool anthropic.ToolUseBlock) (string, bool) {
	description := buildConfirmationMessage(tool)

	// Show confirmation dialog and wait for response
	if ac.confirmFunc == nil {
		return "No confirmation handler available", true
	}

	confirmed := ac.confirmFunc(tool.Name, description)
	if !confirmed {
		return "User declined to execute this operation", false
	}

	return ac.executeWriteTool(tool)
}

// executeWriteTool executes a write tool after confirmation
func (ac *AssistantClient) executeWriteTool(tool anthropic.ToolUseBlock) (string, bool) {
	var err error
	var output string

	inputBytes, _ := json.Marshal(tool.Input)

	switch tool.Name {
	case "start_container":
		var input struct {
			ContainerName string `json:"container_name"`
		}
		json.Unmarshal(inputBytes, &input)
		err = ac.commands.StartContainer(input.ContainerName)
		output = fmt.Sprintf("Started container %s", input.ContainerName)

	case "stop_container":
		var input struct {
			ContainerName string `json:"container_name"`
		}
		json.Unmarshal(inputBytes, &input)
		err = ac.commands.StopContainer(input.ContainerName)
		output = fmt.Sprintf("Stopped container %s", input.ContainerName)

	case "restart_container":
		var input struct {
			ContainerName string `json:"container_name"`
		}
		json.Unmarshal(inputBytes, &input)
		err = ac.commands.RestartContainer(input.ContainerName)
		output = fmt.Sprintf("Restarted container %s", input.ContainerName)

	case "start_service":
		var input struct {
			ServiceName string `json:"service_name"`
		}
		json.Unmarshal(inputBytes, &input)
		output, err = ac.commands.StartHostServiceWithOutput(input.ServiceName)

	case "stop_service":
		var input struct {
			ServiceName string `json:"service_name"`
		}
		json.Unmarshal(inputBytes, &input)
		err = ac.commands.StopHostService(input.ServiceName)
		output = fmt.Sprintf("Stopped service %s", input.ServiceName)

	case "start_missing":
		err = ac.commands.StartMissing()
		output = "Started all missing services"

	case "cold_start":
		err = ac.commands.ColdStart()
		output = "Cold start completed"

	case "stop_all":
		err = ac.commands.StopAll()
		output = "Stopped all services"

	case "reload_nginx":
		err = ac.commands.ReloadNginxConfig()
		output = "Nginx config reloaded"

	case "create_backup":
		output, err = ac.commands.CreateBackup()

	case "git_pull":
		output, err = ac.commands.GitPull()

	case "collectstatic":
		output, err = ac.commands.RunCollectStatic()

	default:
		return fmt.Sprintf("Unknown write tool: %s", tool.Name), true
	}

	if err != nil {
		return fmt.Sprintf("Error: %v\nOutput: %s", err, output), true
	}
	return output, false
}

// ClearHistory clears the conversation history
func (ac *AssistantClient) ClearHistory() {
	ac.messages = []anthropic.MessageParam{}
}

// buildSystemPrompt returns the system prompt for the assistant
func buildSystemPrompt() string {
	return `You are an AI assistant integrated into the KPK Control Panel, helping manage the KPK App infrastructure.

## System Overview

KPK App is a Django-based production management application running on a Windows Server with:

### Docker Containers (7 expected)
- kpk-app_postgres_1: PostgreSQL database
- kpk-app_app_blue_1: Django app (blue deployment, primary)
- kpk-app_app_green_1: Django app (green deployment, standby)
- kpk-app_nginx_1: Nginx reverse proxy
- kpk-app_redis_1: Redis cache/message broker
- kpk-app_process_excel_completion_listener_1: Excel processing listener
- kpk-app_ws4kp_1: WebSocket service

### Host Services (4 expected)
- data_sync: Synchronizes data from Sage/Excel to PostgreSQL
- excel_worker: Processes Excel file operations
- stream_relay: Handles RTSP stream relay
- looper_health: Health monitoring watchdog with restart endpoints

## Common Issues and Fixes

1. **Container not starting**: Check logs for errors. May need database restore if data corrupted.
2. **Crash loop detected**: Container restarting repeatedly - check logs for root cause. Often indicates database issues.
3. **Host service not starting**: Check if Python environment is correct, verify log files for errors.
4. **Git behind origin**: Pull latest changes, then run collectstatic if CSS/JS changed.
5. **Nginx config issues**: After editing nginx.conf, use reload_nginx to apply changes.
6. **Redis connection errors**: Redis container may need restart. Check app logs for connection refused errors.
7. **Database connection errors**: Check postgres container status and logs.

## Important Notes

- All paths on the server are under C:/Users/pmedlin/Documents/kpk-app
- Database backups are stored at M:\kpkapp\backups
- When diagnosing issues, ALWAYS check status first, then logs
- Write operations (start/stop/restart) require user confirmation
- If multiple services are down, use start_missing to start all at once
- The app_blue container is the primary Django instance
- Celery worker runs inside app_blue container

## Your Role

1. Help diagnose issues by checking statuses and logs
2. Suggest appropriate fixes based on error patterns
3. Execute fixes when the user confirms
4. Explain what actions you're taking and why
5. Be concise but thorough in your analysis
6. If you're unsure, suggest checking specific logs before taking action`
}
