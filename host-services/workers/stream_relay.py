"""
Stream Relay Worker
===================
Manages the Hikvision real-time video stream relay server.
Launches and monitors the WebSocket stream server subprocess,
auto-restarting on failures.

Replaces: PYSTRAY_hikvision_stream.pyw
Location: host-services/workers/stream_relay.py
"""

import os
import sys
import subprocess
import threading
from PIL import Image
import pystray
from datetime import datetime
import time
import webbrowser

# --- Path Configuration ---
# Calculate kpk-app root from this file's location (host-services/workers/)
KPK_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOST_SERVICES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# --- Logging Configuration ---
LOG_DIR = os.path.join(HOST_SERVICES_ROOT, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'stream_relay.log')
os.makedirs(LOG_DIR, exist_ok=True)

# --- Service Configuration ---
SERVICE_NAME = "Stream Relay Worker"
ICON_PATH = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'jeff_tray_icon.png')

# The stream server script is still in the old location
STREAM_SERVER_SCRIPT = os.path.join(KPK_APP_ROOT, 'local_machine_scripts', 'realtime_stream_server.pyw')


class StreamManager:
    """Manages the real-time stream server daemon."""

    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.icon = None
        self.log_file = None

    def log(self, message):
        """Write log message to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        if self.log_file:
            self.log_file.write(log_message + "\n")
            self.log_file.flush()

    def get_icon_image(self):
        """Load the system tray icon."""
        try:
            return Image.open(ICON_PATH)
        except FileNotFoundError:
            self.log(f"Icon file not found at {ICON_PATH}. Creating placeholder.")
            return Image.new('RGB', (64, 64), 'darkblue')

    def update_tooltip(self, message):
        """Update the system tray icon tooltip."""
        if self.icon:
            self.icon.title = f"{SERVICE_NAME} ({message})"

    def start_stream(self):
        """Start the streaming server subprocess."""
        if self.is_running:
            return

        self.log(f"=== Starting {SERVICE_NAME} ===")
        self.log_file = open(LOG_FILE, 'a', encoding='utf-8')

        if not os.path.exists(STREAM_SERVER_SCRIPT):
            self.log(f"FATAL ERROR: Cannot find realtime_stream_server.pyw at {STREAM_SERVER_SCRIPT}")
            self.update_tooltip("Script Not Found")
            return

        self.log("Starting REAL-TIME WebSocket server...")

        # Find the correct python executable for windowless subprocess
        python_executable = sys.executable
        if python_executable.lower().endswith("python.exe"):
            pythonw_path = os.path.join(os.path.dirname(python_executable), "pythonw.exe")
            if os.path.exists(pythonw_path):
                self.log(f"Switching to '{pythonw_path}' for silent subprocess.")
                python_executable = pythonw_path

        try:
            self.server_process = subprocess.Popen(
                [python_executable, STREAM_SERVER_SCRIPT],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_running = True
            self.update_tooltip("Streaming Active")
            # Monitor child process and auto-restart if it exits unexpectedly
            threading.Thread(target=self._monitor_server, daemon=True).start()
        except Exception as e:
            self.log(f"Failed to start WebSocket server: {e}")
            self.is_running = False
            self.update_tooltip("Server Failed")

    def stop_stream(self):
        """Stop the streaming server subprocess."""
        if not self.is_running:
            return

        self.log(f"=== Stopping {SERVICE_NAME} ===")
        self.update_tooltip("Stopping...")

        if self.server_process:
            self.log("Terminating Real-Time Server...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            except Exception as e:
                self.log(f"Error terminating server process: {e}")
            self.server_process = None

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        self.is_running = False
        self.update_tooltip("Stopped")

    def _monitor_server(self):
        """Monitor the server process and restart on unexpected exit."""
        while self.is_running:
            proc = self.server_process
            if proc is None:
                break
            ret = proc.poll()
            if ret is not None:
                self.log(f"Real-Time Server exited with code {ret}. Restarting soon...")
                self.update_tooltip("Restarting...")
                self.server_process = None
                self.is_running = False
                time.sleep(2)
                self.start_stream()
                return
            time.sleep(2)

    def toggle_stream(self):
        """Toggle the stream state."""
        if self.is_running:
            self.stop_stream()
        else:
            self.start_stream()

    def open_camera_page(self):
        """Open the camera view in browser."""
        webbrowser.open("http://localhost:8000/prodverse/palletizer-camera/")

    def exit_action(self):
        """Complete shutdown."""
        self.log("Initiating complete shutdown...")
        self.stop_stream()
        if self.icon:
            self.icon.stop()
        os._exit(0)

    def create_menu(self):
        """Create the system tray menu."""
        def get_toggle_text(item):
            return 'Stop Stream' if self.is_running else 'Start Stream'

        return pystray.Menu(
            pystray.MenuItem(get_toggle_text, self.toggle_stream, default=True),
            pystray.MenuItem('Open Camera View', self.open_camera_page),
            pystray.MenuItem('Exit', self.exit_action)
        )

    def run(self):
        """Run the system tray icon."""
        image = self.get_icon_image()
        self.icon = pystray.Icon("stream_relay", image, f"{SERVICE_NAME} (Stopped)")
        self.icon.menu = self.create_menu()

        # Start the stream automatically in a separate thread
        threading.Thread(target=self.start_stream, daemon=True).start()

        self.icon.run()


def main():
    """Main entry point for the Stream Relay Worker."""
    stream_manager = StreamManager()
    stream_manager.run()


if __name__ == "__main__":
    main()
