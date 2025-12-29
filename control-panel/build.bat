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

    :: Copy to network share for distribution
    echo Copying to M:\kpkapp\control-panel...
    copy /Y bin\kpk-control-panel.exe M:\kpkapp\control-panel\kpk-control-panel.exe
    copy /Y icon.png M:\kpkapp\control-panel\icon.png
    copy /Y ps\kpk.ps1 M:\kpkapp\control-panel\kpk.ps1
    copy /Y ps\KPK.psm1 M:\kpkapp\control-panel\KPK.psm1
    if not exist M:\kpkapp\control-panel\cli-setup.bat copy /Y cli-setup.bat M:\kpkapp\control-panel\cli-setup.bat
    if %ERRORLEVEL% EQU 0 (
        echo Deployed to M:\kpkapp\control-panel\
    ) else (
        echo Warning: Could not copy to M:\kpkapp\control-panel\
    )
) else (
    echo Build failed!
)
