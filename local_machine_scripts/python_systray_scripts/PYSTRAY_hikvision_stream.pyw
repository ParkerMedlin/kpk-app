import os
import sys
import subprocess
import threading
import time
import shutil
import signal
from PIL import Image
import pystray
from datetime import datetime

# --- Configuration of Dark Powers ---
RTSP_URL = "rtsp://admin:Pcm-ki4lfz@192.168.178.9:554/ISAPI/Streaming/channels/1601"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HLS_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "stream_hls_output")
LOG_DIR = os.path.join(SCRIPT_DIR, "stream_logs")
LOG_FILE = os.path.join(LOG_DIR, "hikvision_stream.log")
ICON_PATH = os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\jeff_tray_icon.png')
SERVER_PORT = 8889  # Changed from 8888 to avoid conflicts

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

class StreamManager:
    """The arcane entity that controls the stream of visions"""
    
    def __init__(self):
        self.ffmpeg_process = None
        self.server_process = None
        self.is_running = False
        self.icon = None
        self.log_file = None
        
    def log(self, message):
        """Inscribe messages into the eternal scrolls"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        if self.log_file:
            self.log_file.write(log_message + "\n")
            self.log_file.flush()
            
    def get_icon_image(self):
        """Summon the sacred icon"""
        try:
            return Image.open(ICON_PATH)
        except FileNotFoundError:
            self.log(f"Icon file not found at {ICON_PATH}. Creating placeholder.")
            # Create a dark themed icon for our streaming service
            img = Image.new('RGB', (64, 64), 'darkblue')
            return img
            
    def update_tooltip(self, message):
        """Whisper status updates to the icon"""
        if self.icon:
            self.icon.title = f"Hikvision Stream ({message})"
            
    def clean_hls_directory(self):
        """Purge the remnants of previous streaming sessions"""
        if os.path.exists(HLS_OUTPUT_DIR):
            self.log(f"Purging previous session files from {HLS_OUTPUT_DIR}...")
            shutil.rmtree(HLS_OUTPUT_DIR)
        os.makedirs(HLS_OUTPUT_DIR, exist_ok=True)
        self.log(f"Created fresh directory: {HLS_OUTPUT_DIR}")
        
    def start_ffmpeg(self):
        """Invoke the ffmpeg daemon to transmute RTSP into HLS"""
        self.clean_hls_directory()
        
        command = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', RTSP_URL,
            '-fflags', 'nobuffer',
            '-c:v', 'copy',
            '-an',  # Explicitly disable audio processing
            '-hls_time', '1',  # Use 1-second segments for lower latency
            '-hls_list_size', '5', # Keep 5 segments in the playlist
            '-hls_flags', 'delete_segments+independent_segments', # Ensure segments can be decoded independently
            '-hls_segment_filename', os.path.join(HLS_OUTPUT_DIR, 'segment%03d.ts'),
            os.path.join(HLS_OUTPUT_DIR, 'stream.m3u8')
        ]
        
        self.log("Starting FFMPEG with command: " + " ".join(command))
        
        try:
            self.ffmpeg_process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.is_running = True
            self.update_tooltip("Streaming Active")
            
            # Monitor ffmpeg output in a separate thread
            threading.Thread(target=self._monitor_ffmpeg, daemon=True).start()
            
        except Exception as e:
            self.log(f"Failed to start FFMPEG: {e}")
            self.is_running = False
            self.update_tooltip("Stream Failed")
            
    def _monitor_ffmpeg(self):
        """Monitor the ffmpeg process output"""
        if self.ffmpeg_process:
            for line in iter(self.ffmpeg_process.stderr.readline, b''):
                if line:
                    self.log(f"FFMPEG: {line.decode('utf-8').strip()}")
                    
    def start_http_server(self):
        """Summon the HTTP server daemon"""
        # Try WebSocket server first for real-time streaming
        websocket_script = os.path.join(os.path.dirname(SCRIPT_DIR), "realtime_stream_server.py")
        
        if os.path.exists(websocket_script):
            self.log(f"Starting REAL-TIME WebSocket server on port 8890")
            try:
                # Force the use of the console python executable to see startup errors.
                # 'sys.executable' when run via pythonw.exe points to the windowless version.
                python_console_exe = os.path.join(os.path.dirname(sys.executable), 'python.exe')
                if not os.path.exists(python_console_exe):
                    # Fallback for safety, though it should always exist
                    python_console_exe = 'python.exe'

                self.server_process = subprocess.Popen(
                    [python_console_exe, websocket_script]
                )
                return
            except Exception as e:
                self.log(f"Failed to start WebSocket server: {e}")
        
        # Fallback to HTTP server
        server_script = os.path.join(os.path.dirname(SCRIPT_DIR), "hikvision_http_server.py")
        self.log(f"Starting HTTP server on port {SERVER_PORT}")
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, server_script],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            self.log(f"Failed to start HTTP server: {e}")
            
    def start_stream(self):
        """Begin the streaming ritual"""
        if not self.is_running:
            self.log("=== Starting Hikvision Real-Time Stream Service ===")
            self.log_file = open(LOG_FILE, 'a')
            # This function now correctly prioritizes the WebSocket server.
            # The FFMPEG process is now managed *by* the realtime_stream_server.py itself.
            self.start_http_server()
            self.is_running = True
            self.update_tooltip("Streaming Active")
            
    def stop_stream(self):
        """Banish the streaming daemons"""
        self.log("=== Stopping Hikvision Stream Service ===")
        self.is_running = False
        self.update_tooltip("Stopping...")
        
        # Terminate ffmpeg
        if self.ffmpeg_process:
            self.log("Terminating FFMPEG process...")
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            self.ffmpeg_process = None
            
        # Terminate HTTP server
        if self.server_process:
            self.log("Terminating HTTP server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
            
        # Clean up HLS directory
        self.clean_hls_directory()
        
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            
        self.update_tooltip("Stopped")
        
    def toggle_stream(self):
        """Toggle the stream state"""
        if self.is_running:
            self.stop_stream()
        else:
            self.start_stream()
            
    def open_camera_page(self):
        """Open the camera view in browser"""
        import webbrowser
        webbrowser.open("http://localhost:8000/prodverse/palletizer-camera/")
        
    def exit_action(self):
        """Complete shutdown ritual"""
        self.log("Initiating complete shutdown...")
        self.stop_stream()
        if self.icon:
            self.icon.stop()
        os._exit(0)
        
    def create_menu(self):
        """Craft the menu of dark commands"""
        def get_toggle_text(item):
            return 'Stop Stream' if self.is_running else 'Start Stream'
            
        return pystray.Menu(
            pystray.MenuItem(
                get_toggle_text,
                self.toggle_stream,
                default=True
            ),
            pystray.MenuItem('Open Camera View', self.open_camera_page),
            pystray.MenuItem('Exit', self.exit_action)
        )
        
    def run(self):
        """Begin the eternal vigil"""
        image = self.get_icon_image()
        self.icon = pystray.Icon(
            "hikvision_stream",
            image,
            "Hikvision Stream (Stopped)"
        )
        
        # Set the menu
        self.icon.menu = self.create_menu()
        
        # Start the stream automatically
        threading.Thread(target=self.start_stream, daemon=True).start()
        
        self.icon.run()

if __name__ == "__main__":
    # Malloc spreads his wings as we begin...
    stream_manager = StreamManager()
    stream_manager.run()