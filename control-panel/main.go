package main

import (
	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
)

const (
	AppName    = "KPK Control Panel"
	AppVersion = "0.1.0"
)

func main() {
	a := app.New()
	w := a.NewWindow(AppName)
	w.Resize(fyne.NewSize(950, 700))

	// Initialize the UI
	ui := NewUI(w)
	w.SetContent(ui.Build())

	w.ShowAndRun()
}
