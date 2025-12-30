#!/usr/bin/env python3
"""
The Real-Time Streaming Daemon - A creation of dark necessity
This entity transcends HLS, delivering frames with minimal latency
"""

import asyncio
import websockets
import subprocess
import threading
import json
import base64
import time
from datetime import datetime
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Load secrets from .env to avoid plaintext in code
def load_env_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        # No .env file; rely on process environment
        pass

# Resolve and preload environment from common .env locations (path-agnostic)
def _resolve_env_paths():
    paths = []
    # Explicit override via environment
    override = os.environ.get('KPK_ENV_FILE')
    if override:
        paths.append(override)
    # Relative to CWD, script dir, and repo root
    script_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    paths.extend([
        os.path.join(os.getcwd(), '.env'),
        os.path.join(script_dir, '.env'),
        os.path.join(repo_root, '.env'),
        os.path.join(os.path.expanduser('~'), 'Documents', 'kpk-app', '.env'),
    ])
    # Dedupe while keeping order
    seen, unique = set(), []
    for p in paths:
        if p and p not in seen:
            seen.add(p)
            unique.append(p)
    return unique

ENV_LOADED_FROM = None
for _p in _resolve_env_paths():
    if os.path.isfile(_p):
        load_env_file(_p)
        ENV_LOADED_FROM = _p
        break

# Configuration
RTSP_URL = os.environ.get('HIKVISION_RTSP_URL')
WEBSOCKET_PORT = 8890
FRAME_WIDTH = 1344  # Half resolution for performance
FRAME_HEIGHT = 760
FPS = 15  # Target FPS for low latency

# Logging (small rotating file to avoid bloat)
LOG_DIR = os.path.join(os.path.dirname(__file__), 'stream_logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'realtime_stream.log')
logger = logging.getLogger('realtime_stream')
if not logger.handlers:
    logger.setLevel(logging.ERROR)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2, encoding='utf-8')
    fmt = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)

class FrameStreamer:
    """The dark heart of our real-time streaming solution"""
    
    def __init__(self):
        self.clients = set()
        self.ffmpeg_process = None
        self.is_running = False
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        self.last_frame_time = time.time()
        self.restart_lock = threading.Lock()
        self.shutting_down = False
        
    def log(self, message):
        """Inscribe our dark deeds"""
        # Minimal rotating file logging to avoid console windows / bloat
        logger.info(message)
        
    async def register_client(self, websocket):
        """Bind a new soul to our stream"""
        self.clients.add(websocket)
        self.log(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send initial configuration
        await websocket.send(json.dumps({
            "type": "config",
            "width": FRAME_WIDTH,
            "height": FRAME_HEIGHT,
            "fps": FPS
        }))
        
    async def unregister_client(self, websocket):
        """Release a soul from our grasp"""
        self.clients.remove(websocket)
        self.log(f"Client disconnected. Total clients: {len(self.clients)}")

    def _find_ffmpeg(self):
        """Locate ffmpeg executable, checking PATH and common install locations."""
        import shutil
        import glob

        # First, try PATH (works if ffmpeg is properly installed)
        ffmpeg_in_path = shutil.which('ffmpeg')
        if ffmpeg_in_path and os.path.exists(ffmpeg_in_path):
            self.log(f"Found ffmpeg in PATH: {ffmpeg_in_path}")
            return ffmpeg_in_path

        # Check common WinGet installation paths for any user
        winget_patterns = [
            os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe'),
            r'C:\Users\*\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe',
        ]

        for pattern in winget_patterns:
            matches = glob.glob(pattern)
            if matches:
                # Sort to get the latest version (higher version numbers sort later)
                matches.sort(reverse=True)
                self.log(f"Found ffmpeg via WinGet: {matches[0]}")
                return matches[0]

        # Check other common locations
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
        ]

        for path in common_paths:
            if os.path.exists(path):
                self.log(f"Found ffmpeg at: {path}")
                return path

        return None

    def start_ffmpeg(self):
        """Summon the frame extraction daemon"""
        if not RTSP_URL:
            logger.error("HIKVISION_RTSP_URL not set; define it in .env at Documents/kpk-app/.env")
            return

        ffmpeg_path = self._find_ffmpeg()
        if not ffmpeg_path:
            logger.error("FFmpeg not found. Install via 'winget install ffmpeg' or add to PATH.")
            return
        command = [
            ffmpeg_path,
            '-hide_banner',
            '-loglevel', 'error',
            '-rtsp_transport', 'tcp',
            # Favor low latency and faster failure detection
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
            '-analyzeduration', '0',
            '-probesize', '32768',
            '-i', RTSP_URL,
            '-vf', f'scale={FRAME_WIDTH}:{FRAME_HEIGHT}',  # Scale down for performance
            '-r', str(FPS),  # Limit framerate
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            '-q:v', '5',  # JPEG quality (lower = faster)
            '-'
        ]
        
        self.log("Starting FFMPEG with command: " + " ".join(command))
        
        try:
            self.ffmpeg_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8,  # Large buffer for performance
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.is_running = True
            self.last_frame_time = time.time()
            
            # Start frame reading thread
            threading.Thread(target=self._read_frames, daemon=True).start()
            # Start ffmpeg stderr reader
            threading.Thread(target=self._read_stderr, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start FFMPEG: {e}")
            self.is_running = False
    
    def _read_stderr(self):
        """Read and log ffmpeg stderr to aid diagnosis without bloating logs."""
        if not self.ffmpeg_process or not self.ffmpeg_process.stderr:
            return
        try:
            while True:
                line = self.ffmpeg_process.stderr.readline()
                if not line:
                    break
                try:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                except Exception:
                    decoded = str(line)
                if decoded and ('error' in decoded.lower()):
                    logger.error(f"ffmpeg: {decoded}")
        except Exception as e:
            logger.error(f"ffmpeg stderr reader error: {e}")
    
    def _restart_ffmpeg(self, reason):
        """Safely restart ffmpeg when input stalls or exits."""
        if self.shutting_down:
            return
        with self.restart_lock:
            if self.shutting_down:
                return
            logger.warning(f"Restarting ffmpeg due to: {reason}")
            try:
                if self.ffmpeg_process:
                    self.ffmpeg_process.terminate()
                    try:
                        self.ffmpeg_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.ffmpeg_process.kill()
            except Exception as e:
                logger.warning(f"Error terminating ffmpeg during restart: {e}")
            self.ffmpeg_process = None
            time.sleep(1)
            # Keep server alive; only ffmpeg restarts
            self.start_ffmpeg()
        
    def _read_frames(self):
        """Extract frames from the RTSP stream"""
        buffer = b''
        
        while self.is_running and self.ffmpeg_process:
            try:
                # Read chunk from ffmpeg
                chunk = self.ffmpeg_process.stdout.read(65536)
                if not chunk:
                    # EOF is a non-fatal condition; restart silently
                    self._restart_ffmpeg("eof/no data")
                    return
                
                buffer += chunk
                # Bound buffer to avoid runaway growth if markers are missing
                if len(buffer) > 10_000_000 and b'\xff\xd8' not in buffer:
                    # Silent truncate to avoid log spam
                    buffer = buffer[-1_000_000:]
                
                # Look for JPEG markers
                while True:
                    start = buffer.find(b'\xff\xd8')  # JPEG start
                    if start == -1:
                        break
                        
                    end = buffer.find(b'\xff\xd9', start)  # JPEG end
                    if end == -1:
                        break
                        
                    # Extract complete JPEG
                    jpeg_data = buffer[start:end + 2]
                    buffer = buffer[end + 2:]
                    
                    # Send to all clients
                    if self.clients:
                        asyncio.run_coroutine_threadsafe(
                            self._broadcast_frame(jpeg_data),
                            self.loop
                        )
                        
                    self.frame_count += 1
                    self.fps_frame_count += 1
                    self.last_frame_time = time.time()
                    
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        # Suppress periodic FPS logs to keep logs minimal
                        self.fps_frame_count = 0
                        self.last_fps_time = current_time
                
                # Watchdog: if no complete frame parsed for a while, restart ffmpeg
                if time.time() - self.last_frame_time > 10:
                    # Restart silently; treat as transient
                    self._restart_ffmpeg("no frames timeout")
                    return
                        
            except Exception as e:
                logger.error(f"Frame reading error: {e}")
                self._restart_ffmpeg("frame read exception")
                return
                
    async def _broadcast_frame(self, jpeg_data):
        """Transmit frame to all connected souls"""
        if not self.clients:
            return
            
        # Encode frame data
        frame_message = json.dumps({
            "type": "frame",
            "data": base64.b64encode(jpeg_data).decode('ascii'),
            "timestamp": time.time()
        })
        
        # Send to all clients concurrently
        disconnected_clients = set()
        
        async def send_to_client(websocket):
            try:
                await websocket.send(frame_message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(websocket)
                
        await asyncio.gather(
            *[send_to_client(client) for client in self.clients],
            return_exceptions=True
        )
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)
            
    async def handle_client(self, websocket):
        """Handle a WebSocket connection"""
        await self.register_client(websocket)
        
        try:
            # Keep connection alive and handle any client messages
            async for message in websocket:
                # We don't expect messages from client, but process if needed
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
            
    def stop(self):
        """Banish the streaming daemon"""
        self.is_running = False
        self.shutting_down = True
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()

async def main():
    """The main summoning ritual"""
    streamer = FrameStreamer()
    
    # Store event loop reference
    streamer.loop = asyncio.get_event_loop()
    
    # Optional: diagnostics disabled to reduce logs
    
    # Start FFMPEG
    streamer.start_ffmpeg()
    
    # Start WebSocket server
    streamer.log(f"WebSocket server starting on port {WEBSOCKET_PORT}")
    
    async with websockets.serve(
        streamer.handle_client, 
        "0.0.0.0", 
        WEBSOCKET_PORT,
        max_size=10**7,  # 10MB max message size
        compression=None  # Disable compression for lower latency
    ):
        streamer.log(f"Real-time streaming server active on ws://0.0.0.0:{WEBSOCKET_PORT}")
        # No console prompt when running as a service
        
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            streamer.log("Shutting down...")
            streamer.stop()

if __name__ == "__main__":
    asyncio.run(main())
