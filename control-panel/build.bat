@echo off
echo Building KPK Control Panel...

:: Get dependencies
go mod tidy

:: Build for Windows (portable exe)
set CGO_ENABLED=1
set GOOS=windows
set GOARCH=amd64

go build -ldflags="-s -w -H windowsgui" -o bin\kpk-control-panel.exe .

if %ERRORLEVEL% EQU 0 (
    echo Build successful! Output: bin\kpk-control-panel.exe
) else (
    echo Build failed!
)
