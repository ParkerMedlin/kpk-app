import http.server
import socketserver
import json
import subprocess
import os
import logging

PORT = 8090
# Assuming BlndSheetGen.vbs is in a 'vb_scripts' subdirectory relative to this script
# Adjust this path if your VBScript is located elsewhere.
VBS_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vb_scripts', 'BlndSheetGen.vbs')

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, 'pystray_blendsheet_print_service.log')
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

class PrintServiceHandler(http.server.BaseHTTPRequestHandler):
    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        if self.path == '/print':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))

                item_code = data.get('item_code')
                lot_number = data.get('lot_number')
                lot_quantity = data.get('lot_quantity')

                if not all([item_code, lot_number, lot_quantity]):
                    logging.warning("Missing parameters in request")
                    self._send_response(400, {'status': 'error', 'message': 'Missing parameters'})
                    return

                logging.info(f"Received print request: Item={item_code}, Lot={lot_number}, Qty={lot_quantity}")

                # Call VBScript
                # Ensure CSCRIPT is in your system's PATH or provide the full path to cscript.exe
                # Example: C:\Windows\System32\cscript.exe
                cmd = ['cscript', '//Nologo', VBS_SCRIPT_PATH, 
                       str(item_code), str(lot_number), str(lot_quantity)]
                
                logging.info(f"Executing command: {' '.join(cmd)}")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                stdout, stderr = process.communicate(timeout=60) # 60-second timeout

                if process.returncode == 0:
                    logging.info(f"VBScript executed successfully. Output: {stdout.strip()}")
                    self._send_response(200, {'status': 'success', 'message': stdout.strip() or 'Print command sent to VBScript.'})
                else:
                    error_message = f"VBScript execution failed with code {process.returncode}. Error: {stderr.strip()}"
                    logging.error(error_message)
                    self._send_response(500, {'status': 'error', 'message': error_message})
            
            except json.JSONDecodeError:
                logging.error("Invalid JSON received")
                self._send_response(400, {'status': 'error', 'message': 'Invalid JSON'})
            except subprocess.TimeoutExpired:
                logging.error("VBScript execution timed out")
                self._send_response(500, {'status': 'error', 'message': 'VBScript execution timed out'})
            except FileNotFoundError:
                logging.error(f"VBScript not found at {VBS_SCRIPT_PATH} or cscript not found.")
                self._send_response(500, {'status': 'error', 'message': f'VBScript or cscript not found. Check service configuration.'})
            except Exception as e:
                logging.exception("An unexpected error occurred in do_POST")
                self._send_response(500, {'status': 'error', 'message': f'An server-side error occurred: {str(e)}'})
        else:
            self._send_response(404, {'status': 'error', 'message': 'Not Found'})

if __name__ == '__main__':
    # Check if VBS script exists at startup
    if not os.path.exists(VBS_SCRIPT_PATH):
        logging.error(f"Critical Error: VBScript not found at {VBS_SCRIPT_PATH}. Service cannot start correctly.")
        # In a real .pyw, you might want to show a message box or exit more gracefully
        # For simplicity here, we just log and continue, but the handler will fail.

    try:
        with socketserver.TCPServer(("localhost", PORT), PrintServiceHandler) as httpd:
            logging.info(f"Blend Sheet Print Service started on localhost port {PORT}")
            logging.info(f"Expecting VBScript at: {VBS_SCRIPT_PATH}")
            httpd.serve_forever()
    except OSError as e:
        logging.error(f"Could not start server on port {PORT}: {e}. Is another instance running or port in use?")
    except Exception as e:
        logging.exception("Failed to start the print service.")
