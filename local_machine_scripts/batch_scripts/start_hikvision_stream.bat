@echo off
REM ===================================================
REM Hikvision Stream Service Launcher
REM A dark ritual to summon the streaming daemon
REM ===================================================

echo.
echo [*] Summoning the Hikvision Stream Service...
echo [*] The camera's gaze shall pierce the veil...
echo.

REM Navigate to the script directory
cd /d "%~dp0\..\python_systray_scripts"

REM Launch the streaming service with pythonw (no console window)
start "Hikvision Stream Service" pythonw PYSTRAY_hikvision_stream.pyw

echo [*] The streaming service has been awakened!
echo [*] Look for the icon in your system tray.
echo [*] Access the camera at: http://localhost:8000/prodverse/palletizer-camera/
echo.
echo [*] Press any key to close this window...
pause > nul