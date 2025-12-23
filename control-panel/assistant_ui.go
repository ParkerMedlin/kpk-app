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
	chatDisplay   *widget.RichText
	chatScroll    *container.Scroll
	inputEntry    *widget.Entry
	sendButton    *widget.Button
	clearButton   *widget.Button
	loadingBar    *widget.ProgressBarInfinite
	panelVisible  bool
	chatPanel     *fyne.Container
	mu            sync.Mutex

	// Pending action bar
	actionBar        *fyne.Container
	actionLabel      *widget.Label
	actionDescLabel  *widget.Label
	approveBtn       *widget.Button
	denyBtn          *widget.Button
	pendingConfirm   chan bool
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
	// Chat history display using RichText for markdown rendering
	aui.chatDisplay = widget.NewRichTextFromMarkdown("")
	aui.chatDisplay.Wrapping = fyne.TextWrapWord
	aui.chatScroll = container.NewScroll(aui.chatDisplay)

	// Loading indicator
	aui.loadingBar = widget.NewProgressBarInfinite()
	aui.loadingBar.Hide()

	// Build the pending action bar (initially hidden)
	aui.buildActionBar()

	// User input - single line Entry so Enter sends message
	aui.inputEntry = widget.NewEntry()
	aui.inputEntry.SetPlaceHolder("Type your message and press Enter...")
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

	// Bottom area: action bar + input
	bottomArea := container.NewVBox(
		aui.actionBar,
		inputRow,
	)

	// Main chat panel
	aui.chatPanel = container.NewBorder(
		header,
		bottomArea,
		nil, nil,
		aui.chatScroll,
	)

	return aui.chatPanel
}

// buildActionBar creates the pending action confirmation bar
func (aui *AssistantUI) buildActionBar() {
	aui.actionLabel = widget.NewLabelWithStyle("PENDING ACTION", fyne.TextAlignLeading, fyne.TextStyle{Bold: true})
	aui.actionDescLabel = widget.NewLabel("")
	aui.actionDescLabel.Wrapping = fyne.TextWrapWord

	aui.approveBtn = widget.NewButtonWithIcon("Approve", theme.ConfirmIcon(), func() {
		if aui.pendingConfirm != nil {
			aui.pendingConfirm <- true
		}
	})
	aui.approveBtn.Importance = widget.HighImportance

	aui.denyBtn = widget.NewButtonWithIcon("Deny", theme.CancelIcon(), func() {
		if aui.pendingConfirm != nil {
			aui.pendingConfirm <- false
		}
	})
	aui.denyBtn.Importance = widget.DangerImportance

	buttonRow := container.NewHBox(aui.approveBtn, aui.denyBtn)

	aui.actionBar = container.NewVBox(
		widget.NewSeparator(),
		container.NewHBox(
			widget.NewIcon(theme.WarningIcon()),
			aui.actionLabel,
		),
		aui.actionDescLabel,
		buttonRow,
		widget.NewSeparator(),
	)

	// Initially hidden
	aui.actionBar.Hide()
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
				aui.chatDisplay.ParseMarkdown("")
				aui.chatDisplay.Refresh()
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

// refreshChatDisplay updates the chat display with rendered markdown
func (aui *AssistantUI) refreshChatDisplay() {
	aui.mu.Lock()
	defer aui.mu.Unlock()

	var sb strings.Builder
	for i, msg := range aui.messages {
		timestamp := msg.Time.Format("15:04")

		if msg.Role == "user" {
			sb.WriteString(fmt.Sprintf("**You** `%s`\n\n%s", timestamp, msg.Content))
		} else {
			sb.WriteString(fmt.Sprintf("**Claude** `%s`\n\n%s", timestamp, msg.Content))
		}

		// Add separator between messages
		if i < len(aui.messages)-1 {
			sb.WriteString("\n\n---\n\n")
		} else {
			sb.WriteString("\n")
		}
	}

	aui.chatDisplay.ParseMarkdown(sb.String())
	aui.chatDisplay.Refresh()

	// Scroll to bottom after a brief delay to let layout complete
	go func() {
		time.Sleep(50 * time.Millisecond)
		aui.chatScroll.ScrollToBottom()
	}()
}

// showToolConfirmation shows the action bar for tool confirmation
// Blocks until user responds with Approve or Deny
func (aui *AssistantUI) showToolConfirmation(toolName, description string) bool {
	// Create the confirmation channel
	aui.pendingConfirm = make(chan bool, 1)

	// Update action bar content
	aui.actionLabel.SetText(fmt.Sprintf("PENDING: %s", toolName))
	aui.actionDescLabel.SetText(description)

	// Show the action bar
	aui.actionBar.Show()
	aui.chatPanel.Refresh()

	// Wait for user response
	result := <-aui.pendingConfirm

	// Hide the action bar
	aui.actionBar.Hide()
	aui.chatPanel.Refresh()

	// Clean up
	aui.pendingConfirm = nil

	return result
}
