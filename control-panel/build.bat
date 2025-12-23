@echo off
echo Building KPK Control Panel...

:: Get dependencies
go mod tidy

:: Build for Windows (portable exe)
set CGO_ENABLED=1
set GOOS=windows
set GOARCH=amd64

go build -ldflags="-s -w -H windowsgui" -o bin\kpk.exe .

if %ERRORLEVEL% EQU 0 (
    echo Build successful! Output: bin\kpk.exe

    :: Copy to network share for distribution
    echo Copying to M:\kpkapp\control-panel...
    copy /Y bin\kpk.exe M:\kpkapp\control-panel\kpk.exe
    copy /Y icon.png M:\kpkapp\control-panel\icon.png
    if %ERRORLEVEL% EQU 0 (
        echo Deployed to M:\kpkapp\control-panel\
    ) else (
        echo Warning: Could not copy to M:\kpkapp\control-panel\
    )
) else (
    echo Build failed!
)
