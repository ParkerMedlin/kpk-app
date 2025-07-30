import os
import sys
import subprocess
import threading
from PIL import Image
import pystray
from datetime import datetime


# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "stream_logs")
LOG_FILE = os.path.join(LOG_DIR, "hikvision_stream.log")
ICON_PATH = os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\jeff_tray_icon.png')

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

class StreamManager:
    """A purified manager, its sole purpose to control the real-time server daemon."""
    
    def __init__(self):
        self.server_process = None
        self.is_running = False
        self.icon = None
        self.log_file = None
        
    def log(self, message):
        """Inscribe messages into the eternal scrolls."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        if self.log_file:
            self.log_file.write(log_message + "\n")
            self.log_file.flush()
            
    def get_icon_image(self):
        """Summon the sacred icon."""
        try:
            return Image.open(ICON_PATH)
        except FileNotFoundError:
            self.log(f"Icon file not found at {ICON_PATH}. Creating placeholder.")
            return Image.new('RGB', (64, 64), 'darkblue')
            
    def update_tooltip(self, message):
        """Whisper status updates to the icon."""
        if self.icon:
            self.icon.title = f"Hikvision Real-Time Stream ({message})"
            
    def start_stream(self):
        """Begin the streaming ritual by summoning the one true server daemon."""
        if self.is_running:
            return

        self.log("=== Starting Hikvision Real-Time Stream Service ===")
        self.log_file = open(LOG_FILE, 'a', encoding='utf-8')
        
        server_script = os.path.join(os.path.dirname(SCRIPT_DIR), "realtime_stream_server.py")
        
        if not os.path.exists(server_script):
            self.log(f"FATAL ERROR: Cannot find realtime_stream_server.py at {server_script}")
            self.update_tooltip("Script Not Found")
            return

        self.log("Starting REAL-TIME WebSocket server...")
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, server_script],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_running = True
            self.update_tooltip("Streaming Active")
        except Exception as e:
            self.log(f"Failed to start WebSocket server: {e}")
            self.is_running = False
            self.update_tooltip("Server Failed")
            
    def stop_stream(self):
        """Banish the streaming daemon."""
        if not self.is_running:
            return

        self.log("=== Stopping Hikvision Real-Time Stream Service ===")
        self.update_tooltip("Stopping...")
        
        if self.server_process:
            self.log("Terminating Real-Time Server...")
            try:
                # Terminate the process gently first, then kill if necessary
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
        
    def toggle_stream(self):
        """Toggle the stream state."""
        if self.is_running:
            self.stop_stream()
        else:
            self.start_stream()
            
    def open_camera_page(self):
        """Open the camera view in browser."""
        import webbrowser
        webbrowser.open("http://localhost:8000/prodverse/palletizer-camera/")
        
    def exit_action(self):
        """Complete shutdown ritual."""
        self.log("Initiating complete shutdown...")
        self.stop_stream()
        if self.icon:
            self.icon.stop()
        os._exit(0)
        
    def create_menu(self):
        """Craft the menu of dark commands."""
        def get_toggle_text(item):
            return 'Stop Stream' if self.is_running else 'Start Stream'
            
        return pystray.Menu(
            pystray.MenuItem(get_toggle_text, self.toggle_stream, default=True),
            pystray.MenuItem('Open Camera View', self.open_camera_page),
            pystray.MenuItem('Exit', self.exit_action)
        )
        
    def run(self):
        """Begin the eternal vigil."""
        image = self.get_icon_image()
        self.icon = pystray.Icon("hikvision_stream", image, "Hikvision Real-Time Stream (Stopped)")
        self.icon.menu = self.create_menu()
        
        # Start the stream automatically in a separate thread
        threading.Thread(target=self.start_stream, daemon=True).start()
        
        self.icon.run()

if __name__ == "__main__":
    stream_manager = StreamManager()
    stream_manager.run()
