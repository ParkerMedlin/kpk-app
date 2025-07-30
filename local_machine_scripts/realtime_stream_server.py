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

# Configuration
RTSP_URL = "rtsp://admin:Pcm-ki4lfz@192.168.178.9:554/ISAPI/Streaming/channels/1601"
WEBSOCKET_PORT = 8890
FRAME_WIDTH = 1344  # Half resolution for performance
FRAME_HEIGHT = 760
FPS = 15  # Target FPS for low latency

class FrameStreamer:
    """The dark heart of our real-time streaming solution"""
    
    def __init__(self):
        self.clients = set()
        self.ffmpeg_process = None
        self.is_running = False
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        
    def log(self, message):
        """Inscribe our dark deeds"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        # Removed print to prevent console window with pythonw.exe
        # All logging goes to stdout which is captured by the parent process
        
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
        
    def start_ffmpeg(self):
        """Summon the frame extraction daemon"""
        command = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
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
                stderr=subprocess.DEVNULL,
                bufsize=10**8,  # Large buffer for performance
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.is_running = True
            
            # Start frame reading thread
            threading.Thread(target=self._read_frames, daemon=True).start()
            
        except Exception as e:
            self.log(f"Failed to start FFMPEG: {e}")
            self.is_running = False
            
    def _read_frames(self):
        """Extract frames from the RTSP stream"""
        buffer = b''
        
        while self.is_running and self.ffmpeg_process:
            try:
                # Read chunk from ffmpeg
                chunk = self.ffmpeg_process.stdout.read(65536)
                if not chunk:
                    break
                    
                buffer += chunk
                
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
                    
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        fps = self.fps_frame_count / (current_time - self.last_fps_time)
                        self.log(f"FPS: {fps:.1f}, Clients: {len(self.clients)}")
                        self.fps_frame_count = 0
                        self.last_fps_time = current_time
                        
            except Exception as e:
                self.log(f"Frame reading error: {e}")
                break
                
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
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()

async def main():
    """The main summoning ritual"""
    streamer = FrameStreamer()
    
    # Store event loop reference
    streamer.loop = asyncio.get_event_loop()
    
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