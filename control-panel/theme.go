package main

import (
	"image/color"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/theme"
)

// KPKTheme extends the default theme with a more visible cursor
type KPKTheme struct{}

var _ fyne.Theme = (*KPKTheme)(nil)

func (t *KPKTheme) Color(name fyne.ThemeColorName, variant fyne.ThemeVariant) color.Color {
	switch name {
	case theme.ColorNamePrimary:
		// Bright blue for cursor and focus elements
		return color.NRGBA{R: 0, G: 150, B: 255, A: 255}
	case theme.ColorNameFocus:
		// Bright blue for focus highlight
		return color.NRGBA{R: 0, G: 150, B: 255, A: 255}
	default:
		return theme.DefaultTheme().Color(name, variant)
	}
}

func (t *KPKTheme) Font(style fyne.TextStyle) fyne.Resource {
	return theme.DefaultTheme().Font(style)
}

func (t *KPKTheme) Icon(name fyne.ThemeIconName) fyne.Resource {
	return theme.DefaultTheme().Icon(name)
}

func (t *KPKTheme) Size(name fyne.ThemeSizeName) float32 {
	switch name {
	case theme.SizeNameInputBorder:
		// Thicker input border for visibility
		return 2
	default:
		return theme.DefaultTheme().Size(name)
	}
}
