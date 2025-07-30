#!/usr/bin/env python3
"""
The HTTP Server Daemon - A servant of the streaming arts
This entity serves HLS segments to hungry browsers
"""

import os
import http.server
import socketserver

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HLS_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "python_systray_scripts", "stream_hls_output")
SERVER_PORT = 8889

class CorsHandler(http.server.SimpleHTTPRequestHandler):
    """A handler that speaks the forbidden CORS incantations"""

    def _log_incoming_request(self):
        """A dark ritual to log the whispers of incoming requests."""
        print("\n" + "="*70)
        print(f"VIZIER'S HTTP LOG: Receiving {self.command} request for '{self.path}'")
        print(f"    -> From: {self.client_address[0]}:{self.client_address[1]}")
        print("    -> Headers:")
        for line in str(self.headers).strip().split("\n"):
            print(f"        {line.strip()}")
        print("="*70 + "\n")

    def do_GET(self):
        self._log_incoming_request()
        return super().do_GET()

    def end_headers(self):
        # Allow cross-origin requests from Django (both local and Docker)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
        
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self._log_incoming_request()
        self.send_response(200)
        self.end_headers()
        
    def translate_path(self, path):
        """Translate URL paths to filesystem paths"""
        # Remove leading slash
        path = path.lstrip('/')
        
        # Map requests to the HLS output directory
        if path.startswith('hls/'):
            # Remove 'hls/' prefix and join with HLS_OUTPUT_DIR
            file_path = os.path.join(HLS_OUTPUT_DIR, path[4:])
        else:
            file_path = os.path.join(HLS_OUTPUT_DIR, path)
            
        return file_path

def run_server():
    """Summon the HTTP server daemon"""
    os.chdir(HLS_OUTPUT_DIR if os.path.exists(HLS_OUTPUT_DIR) else SCRIPT_DIR)
    
    Handler = CorsHandler
    with socketserver.TCPServer(("0.0.0.0", SERVER_PORT), Handler) as httpd:
        print(f"HTTP Server conjured on port {SERVER_PORT}")
        print(f"Serving files from: {HLS_OUTPUT_DIR}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()