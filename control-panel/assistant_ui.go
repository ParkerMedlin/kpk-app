package main

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/theme"
	"fyne.io/fyne/v2/widget"
)

// ChatMessage represents a message in the chat
type ChatMessage struct {
	Role    string // "user" or "assistant"
	Content string
	Time    time.Time
}

// AssistantUI manages the chat panel UI
type AssistantUI struct {
	ui            *UI
	client        *AssistantClient
	messages      []ChatMessage
	chatDisplay   *widget.Entry
	inputEntry    *widget.Entry
	sendButton    *widget.Button
	clearButton   *widget.Button
	loadingBar    *widget.ProgressBarInfinite
	panelVisible  bool
	chatPanel     *fyne.Container
	mu            sync.Mutex
}

// NewAssistantUI creates a new chat UI
func NewAssistantUI(ui *UI) *AssistantUI {
	aui := &AssistantUI{
		ui:       ui,
		messages: []ChatMessage{},
	}
	return aui
}

// Initialize sets up the Claude client (call after UI.commands is available)
func (aui *AssistantUI) Initialize() {
	if aui.ui.commands == nil {
		return
	}

	// Create confirm function that shows dialog
	confirmFunc := func(toolName, description string) bool {
		return aui.showToolConfirmation(toolName, description)
	}

	aui.client = NewAssistantClient(aui.ui.commands, confirmFunc)
}

// BuildChatPanel creates the chat panel UI
func (aui *AssistantUI) BuildChatPanel() *fyne.Container {
	// Chat history display (read-only multi-line entry)
	aui.chatDisplay = widget.NewMultiLineEntry()
	aui.chatDisplay.Wrapping = fyne.TextWrapWord
	aui.chatDisplay.Disable()
	aui.chatDisplay.SetPlaceHolder("Ask Claude about the KPK system status, logs, or request actions...")

	// Loading indicator
	aui.loadingBar = widget.NewProgressBarInfinite()
	aui.loadingBar.Hide()

	// User input
	aui.inputEntry = widget.NewMultiLineEntry()
	aui.inputEntry.SetPlaceHolder("Type your message...")
	aui.inputEntry.Wrapping = fyne.TextWrapWord
	aui.inputEntry.SetMinRowsVisible(2)

	// Handle Enter key to send (Shift+Enter for newline)
	aui.inputEntry.OnSubmitted = func(s string) {
		aui.handleSend()
	}

	// Send button
	aui.sendButton = widget.NewButtonWithIcon("Send", theme.MailSendIcon(), aui.handleSend)
	aui.sendButton.Importance = widget.HighImportance

	// Clear button
	aui.clearButton = widget.NewButtonWithIcon("Clear", theme.DeleteIcon(), aui.handleClear)

	// Input row
	inputRow := container.NewBorder(
		nil, nil, nil,
		container.NewHBox(aui.sendButton, aui.clearButton),
		aui.inputEntry,
	)

	// Header
	header := container.NewVBox(
		widget.NewLabelWithStyle("Claude Assistant", fyne.TextAlignLeading, fyne.TextStyle{Bold: true}),
		aui.loadingBar,
	)

	// Main chat panel
	aui.chatPanel = container.NewBorder(
		header,
		inputRow,
		nil, nil,
		container.NewScroll(aui.chatDisplay),
	)

	return aui.chatPanel
}

// handleSend processes user input
func (aui *AssistantUI) handleSend() {
	message := strings.TrimSpace(aui.inputEntry.Text)
	if message == "" {
		return
	}

	// Clear input
	aui.inputEntry.SetText("")

	// Add user message to display
	aui.addMessage("user", message)

	// Show loading
	aui.loadingBar.Show()
	aui.loadingBar.Start()
	aui.sendButton.Disable()

	// Send to Claude in background
	go func() {
		ctx := context.Background()
		response, err := aui.client.Chat(ctx, message)

		// Update UI on main thread
		aui.loadingBar.Stop()
		aui.loadingBar.Hide()
		aui.sendButton.Enable()

		if err != nil {
			aui.addMessage("assistant", fmt.Sprintf("Error: %v", err))
		} else {
			aui.addMessage("assistant", response)
		}

		// Trigger status refresh in case Claude made changes
		aui.ui.refreshStatus()
	}()
}

// handleClear clears the chat history
func (aui *AssistantUI) handleClear() {
	dialog.ShowConfirm("Clear Chat",
		"Clear the conversation history?",
		func(ok bool) {
			if ok {
				aui.mu.Lock()
				aui.messages = []ChatMessage{}
				aui.mu.Unlock()
				aui.chatDisplay.SetText("")
				if aui.client != nil {
					aui.client.ClearHistory()
				}
			}
		}, aui.ui.window)
}

// addMessage adds a message to the chat display
func (aui *AssistantUI) addMessage(role, content string) {
	aui.mu.Lock()
	aui.messages = append(aui.messages, ChatMessage{
		Role:    role,
		Content: content,
		Time:    time.Now(),
	})
	aui.mu.Unlock()

	aui.refreshChatDisplay()
}

// refreshChatDisplay updates the chat display text
func (aui *AssistantUI) refreshChatDisplay() {
	aui.mu.Lock()
	defer aui.mu.Unlock()

	var sb strings.Builder
	for _, msg := range aui.messages {
		timestamp := msg.Time.Format("15:04")
		if msg.Role == "user" {
			sb.WriteString(fmt.Sprintf("[%s] You:\n%s\n\n", timestamp, msg.Content))
		} else {
			sb.WriteString(fmt.Sprintf("[%s] Claude:\n%s\n\n", timestamp, msg.Content))
		}
	}

	aui.chatDisplay.SetText(sb.String())
	// Scroll to bottom
	aui.chatDisplay.CursorRow = len(strings.Split(aui.chatDisplay.Text, "\n"))
	aui.chatDisplay.Refresh()
}

// showToolConfirmation shows a confirmation dialog for tool execution
// Blocks until user responds
func (aui *AssistantUI) showToolConfirmation(toolName, description string) bool {
	resultChan := make(chan bool, 1)

	// Create a label with the description
	descLabel := widget.NewLabel(description)
	descLabel.Wrapping = fyne.TextWrapWord

	// Must run dialog on main thread
	dialog.ShowCustomConfirm(
		fmt.Sprintf("Confirm: %s", toolName),
		"Execute",
		"Cancel",
		container.NewVBox(
			widget.NewLabel("Claude wants to perform:"),
			widget.NewSeparator(),
			descLabel,
		),
		func(confirmed bool) {
			resultChan <- confirmed
		},
		aui.ui.window,
	)

	return <-resultChan
}
