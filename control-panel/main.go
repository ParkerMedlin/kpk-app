package main

import (
	"os"
	"path/filepath"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
)

const (
	AppName    = "KPK Control Panel"
	AppVersion = "0.1.0"
)

func main() {
	a := app.New()

	// Set the application icon (for taskbar/window)
	if iconPath := findIcon(); iconPath != "" {
		if iconRes, err := fyne.LoadResourceFromPath(iconPath); err == nil {
			a.SetIcon(iconRes)
		}
	}

	w := a.NewWindow(AppName)
	w.Resize(fyne.NewSize(950, 700))

	// Initialize the UI
	ui := NewUI(w)
	w.SetContent(ui.Build())

	w.ShowAndRun()
}

// findIcon looks for icon.png next to the executable or in common locations
func findIcon() string {
	// Try next to executable first
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		iconPath := filepath.Join(exeDir, "icon.png")
		if _, err := os.Stat(iconPath); err == nil {
			return iconPath
		}
		// Also check parent directory (for when exe is in bin/)
		iconPath = filepath.Join(exeDir, "..", "icon.png")
		if _, err := os.Stat(iconPath); err == nil {
			return iconPath
		}
	}
	return ""
}
