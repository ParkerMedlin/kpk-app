import os
import subprocess
import time
import pystray
from PIL import Image
import tkinter as tk
from tkinter import scrolledtext, font
import queue
import threading
import datetime
import logging
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import ssl # For potential HTTPS, though starting with HTTP for simplicity

# Load environment variables from the kpk-app root .env file
# This path is relative to kpk-app, going up two levels from this script's location
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv(ENV_PATH)

# --- Configuration ---
LOG_DIR_NAME = 'pystray_excel_macro_logs' # Log subdirectory within this script's directory
LOG_FILE_NAME = 'excel_macro_trigger_service.log'
SERVICE_NAME = "Excel Direct Edit Service (PS)" # Updated service name
HTTP_HOST = '127.0.0.1'  # Listen only on loopback for security
HTTP_PORT = 9998         # Port for HTTP server
POWERSHELL_SCRIPT_NAME = "Invoke-DirectExcelEdit.ps1" # New PowerShell script

# --- New Constants for Invoke-DirectExcelEdit.ps1 ---
# PATH_TO_BLEND_SHEET_CSV = r"C:\\Users\\jdavis\\Documents\\kpk-app\\local_machine_scripts\\python_systray_scripts\\pystray_excel_macro_utils\\blendsheetpaths.csv" # Removed
GHS_LABEL_BASE_FOLDER_PATH = r"U:\\qclab\\My Documents\\Blend GHS Tote Label"
GHS_EXCEL_SHEET_NAME = "GHSsheet"
PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE = r"local_machine_scripts\python_systray_scripts\pystray_excel_macro_utils\ghsnonhazardtemplate.xlsx"

# --- Setup Logging ---
# Logs will be in local_machine_scripts/python_systray_scripts/pystray_excel_macro_logs/
log_dir = os.path.join(os.path.dirname(__file__), LOG_DIR_NAME)
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, LOG_FILE_NAME),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Queue for inter-thread communication with Tkinter
log_queue = queue.Queue()

# --- Helper to log and queue messages ---
def log_and_queue(message, level=logging.INFO):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    
    if level == logging.DEBUG:
        logging.debug(message)
    elif level == logging.INFO:
        logging.info(message)
    elif level == logging.WARNING:
        logging.warning(message)
    elif level == logging.ERROR:
        logging.error(message)
    
    log_queue.put(formatted_message)

# --- HTTP Server Handler ---
class MacroTriggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        client_ip = self.client_address[0]
        if self.path == '/run-excel-macro':
            log_and_queue(f"HTTP: Received /run-excel-macro from {client_ip}")
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            response_data = {}
            response_code = 500 # Default to internal server error

            try:
                payload = json.loads(post_data.decode('utf-8'))
                log_and_queue(f"HTTP: Payload received: {payload}") # Log the whole payload now as it's simpler

                macro_to_run = payload.get('macro_to_run')
                data_for_macro = payload.get('data_for_macro') # This is expected to be a list

                if not macro_to_run or data_for_macro is None: # Check if data_for_macro is present (can be empty list for some future macros)
                    log_and_queue("HTTP: 'macro_to_run' or 'data_for_macro' missing from payload.", logging.WARNING)
                    response_data = {'status': 'error', 'message': "'macro_to_run' or 'data_for_macro' missing"}
                    response_code = 400
                elif macro_to_run == "blndSheetGen":
                    if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                        log_and_queue(f"HTTP: 'data_for_macro' for blndSheetGen is not a list or has insufficient length (expected 6, got {len(data_for_macro) if isinstance(data_for_macro, list) else 'not a list'}).", logging.WARNING)
                        response_data = {'status': 'error', 'message': 'Invalid data_for_macro for blndSheetGen'}
                        response_code = 400
                    else:
                        # Extract data for Invoke-DirectExcelEdit.ps1
                        # data_for_macro: [lotQuantity, lotNumber, line, blendDesc, runDate, blendItemCode]
                        lot_quantity = str(data_for_macro[0])
                        lot_number = str(data_for_macro[1])
                        # line = data_for_macro[2] # Unused by new PS script
                        blend_description = str(data_for_macro[3])
                        # runDate = data_for_macro[4] # Unused by new PS script
                        item_code_for_template_lookup = str(data_for_macro[5])

                        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), POWERSHELL_SCRIPT_NAME)
                        
                        log_and_queue(f"DEBUG: ENV_PATH = {ENV_PATH}", logging.DEBUG)
                        app_root_dir = os.path.dirname(ENV_PATH) 
                        log_and_queue(f"DEBUG: app_root_dir = {app_root_dir}", logging.DEBUG)
                        log_and_queue(f"DEBUG: PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE (constant) = {PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE}", logging.DEBUG)
                        
                        calculated_path_before_norm = os.path.join(app_root_dir, PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE)
                        log_and_queue(f"DEBUG: calculated_path_before_norm = {calculated_path_before_norm}", logging.DEBUG)
                        absolute_ghs_template_path = os.path.normpath(calculated_path_before_norm)
                        log_and_queue(f"DEBUG: absolute_ghs_template_path (after normpath) = {absolute_ghs_template_path}", logging.DEBUG)
                        log_and_queue(f"DEBUG: os.path.isabs(absolute_ghs_template_path) = {os.path.isabs(absolute_ghs_template_path)}", logging.DEBUG)
                        log_and_queue(f"DEBUG: os.path.exists(absolute_ghs_template_path) = {os.path.exists(absolute_ghs_template_path)}", logging.DEBUG)

                        if not os.path.exists(script_path):
                            log_and_queue(f"Action: PowerShell script NOT FOUND at {script_path}", logging.ERROR)
                            response_data = {'status': 'error', 'message': f'PowerShell script not found on server at {script_path}'}
                            response_code = 500
                        else:
                            command = [
                                "powershell.exe",
                                "-NoProfile",
                                "-ExecutionPolicy", "Bypass",
                                "-File", script_path,
                                "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                                "-LotQuantity", lot_quantity,
                                "-LotNumber", lot_number,
                                "-BlendDescription", blend_description,
                                "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                                "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                                "-PathToGHSNonHazardExcelTemplate", absolute_ghs_template_path
                            ]
                            
                            # Log the specific argument for GHS template path from the command list
                            ghs_path_in_command = "[NOT FOUND IN COMMAND LIST]"
                            try:
                                ghs_param_index = command.index("-PathToGHSNonHazardExcelTemplate")
                                if ghs_param_index + 1 < len(command):
                                    ghs_path_in_command = command[ghs_param_index + 1]
                            except ValueError:
                                pass # Parameter not found
                            log_and_queue(f"DEBUG: GHS template path in actual command list = {ghs_path_in_command}", logging.DEBUG)

                            log_and_queue(f"Action: Executing PowerShell for blndSheetGen: {' '.join(command)}", logging.INFO)
                            
                            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                            stdout, stderr = process.communicate(timeout=300) # Increased timeout to 5 minutes

                            log_and_queue(f"PS_STDOUT: {stdout}", logging.INFO)
                            if stderr:
                                log_and_queue(f"PS_STDERR: {stderr}", logging.ERROR)

                            if process.returncode == 0:
                                try:
                                    json_output_line = None
                                    # The PowerShell script outputs JSON as its last line.
                                    # Ensure we capture it correctly, even with other Write-Host messages.
                                    all_stdout_lines = stdout.strip().splitlines()
                                    if all_stdout_lines:
                                        potential_json_line = all_stdout_lines[-1].strip()
                                        if potential_json_line.startswith('{') and potential_json_line.endswith('}'):
                                            json_output_line = potential_json_line
                                    
                                    if json_output_line:
                                        ps_response = json.loads(json_output_line)
                                        log_and_queue(f"Action: PowerShell script completed. Parsed Response: {ps_response}", logging.INFO)
                                        response_data = ps_response
                                        response_code = 200 if ps_response.get('status') == 'success' else 500
                                    else:
                                        log_and_queue("Action: PowerShell script finished but no JSON output found in the last line of stdout.", logging.ERROR)
                                        response_data = {'status': 'error', 'message': 'PowerShell script finished but no valid JSON output.', 'stdout': stdout, 'stderr': stderr}
                                        response_code = 500
                                except json.JSONDecodeError as je:
                                    log_and_queue(f"Action: Failed to parse JSON response from PowerShell: {je}. stdout: {stdout}", logging.ERROR)
                                    response_data = {'status': 'error', 'message': 'Failed to parse PowerShell JSON response.', 'stdout': stdout, 'stderr': stderr}
                                    response_code = 500
                            else:
                                log_and_queue(f"Action: PowerShell script failed with return code {process.returncode}. Stderr: {stderr}", logging.ERROR)
                                response_data = {'status': 'error', 'message': f'PowerShell script failed. See service logs.', 'details': stderr, 'stdout': stdout}
                                response_code = 500
                elif macro_to_run == "pickSheetGen":
                    log_and_queue(f"HTTP: Received request for 'pickSheetGen'. This functionality is pending implementation with the new direct Excel editing method.", logging.INFO)
                    response_data = {'status': 'pending_implementation', 'message': 'pickSheetGen is not yet implemented with the direct Excel editing PowerShell script.'}
                    response_code = 501 # Not Implemented
                else:
                    log_and_queue(f"HTTP: Unknown 'macro_to_run' value: {macro_to_run}", logging.WARNING)
                    response_data = {'status': 'error', 'message': f"Unknown macro_to_run type: {macro_to_run}"}
                    response_code = 400

            except json.JSONDecodeError:
                log_and_queue("HTTP: Invalid JSON in POST data", logging.WARNING)
                response_data = {'status': 'error', 'message': 'Invalid JSON payload'}
                response_code = 400
            except subprocess.TimeoutExpired:
                log_and_queue("Action: PowerShell script timed out.", logging.ERROR)
                response_data = {'status': 'error', 'message': 'PowerShell script execution timed out after 300 seconds.'}
                response_code = 500
            except Exception as e:
                log_and_queue(f"HTTP: Error processing /run-excel-macro: {str(e)}", logging.ERROR)
                response_data = {'status': 'error', 'message': f'Internal server error: {str(e)}'}
                response_code = 500
            
            self.send_response(response_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            log_and_queue(f"HTTP: Received {self.path} (404 Not Found)", logging.WARNING)
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def log_message(self, format, *args):
        return # Suppress default BaseHTTPServer logging

def start_http_server():
    # Check if PowerShell script exists at startup of this thread
    ps_script_full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), POWERSHELL_SCRIPT_NAME)
    if not os.path.exists(ps_script_full_path):
        log_and_queue(f"CRITICAL: PowerShell script {POWERSHELL_SCRIPT_NAME} not found at {ps_script_full_path}. HTTP server will start, but requests will fail.", logging.CRITICAL)
    else:
        log_and_queue(f"HTTP Server: PowerShell script {POWERSHELL_SCRIPT_NAME} found at {ps_script_full_path}", logging.INFO)

    try:
        server_address = (HTTP_HOST, HTTP_PORT)
        httpd = HTTPServer(server_address, MacroTriggerHandler)
        log_and_queue(f"HTTP Server: Starting on http://{HTTP_HOST}:{HTTP_PORT} for {SERVICE_NAME}")
        httpd.serve_forever()
    except OSError as e:
        log_and_queue(f"HTTP Server: OS Error for {SERVICE_NAME} (maybe port {HTTP_PORT} is already in use?) - {str(e)}", logging.ERROR)
    except Exception as e:
        log_and_queue(f"HTTP Server: Failed to start {SERVICE_NAME} - {str(e)}", logging.ERROR)

def show_status_window(icon_ref):
    root = tk.Tk()
    root.geometry("450x350")
    root.title(f"{SERVICE_NAME} Status")
    root.configure(bg='#f0f0f0')

    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=10)
    text_font = font.Font(family="Consolas", size=9)

    log_frame = tk.Frame(root, bg='#f0f0f0')
    log_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
    log_label = tk.Label(log_frame, text="Service Activity Log:", font=default_font, bg='#f0f0f0')
    log_label.pack(anchor=tk.W)
    log_text_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=15, bg='#ffffff', fg='#333333', font=text_font, relief=tk.SUNKEN, bd=1)
    log_text_area.pack(fill=tk.BOTH, expand=True)

    button_frame = tk.Frame(root, bg='#f0f0f0')
    button_frame.pack(pady=(0, 10), padx=10, fill=tk.X)
    close_button = tk.Button(button_frame, text="Close Window", command=root.destroy, font=default_font, bg='#d9d9d9', relief=tk.RAISED, bd=1)
    close_button.pack(side=tk.RIGHT)

    def update_log_display():
        try:
            while not log_queue.empty():
                message = log_queue.get_nowait()
                log_text_area.configure(state='normal')
                log_text_area.insert(tk.END, message + '\n')
                log_text_area.configure(state='disabled')
                log_text_area.see(tk.END)
                log_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            # Avoid crashing the GUI update loop
            print(f"Error updating log display: {e}") 
        finally:
            if root.winfo_exists(): # Check if window still exists before scheduling next update
                root.after(150, update_log_display)

    log_text_area.configure(state='normal')
    log_text_area.insert(tk.END, f"Initializing {SERVICE_NAME} Window...\n")
    log_text_area.insert(tk.END, f"Listening for HTTP requests on http://{HTTP_HOST}:{HTTP_PORT}\n")
    log_text_area.insert(tk.END, f"Using PowerShell script: {POWERSHELL_SCRIPT_NAME} (expected in same dir as this script)\n")
    log_text_area.insert(tk.END, "-------------------------------------\n")
    log_text_area.configure(state='disabled')
    
    if root.winfo_exists(): 
        root.after(100, update_log_display)
    
    try:
        root.eval('tk::PlaceWindow . center')
        root.mainloop()
    except tk.TclError as e:
        log_and_queue(f"Tkinter mainloop error (possibly window closed abruptly): {e}", logging.WARNING)

def create_tray_icon():
    try:
        # Icon path is relative to kpk-app root, up two levels from this script's location
        icon_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'core', 'static', 'core'))
        icon_path = os.path.join(icon_base_path, 'excel_icon.png') # Preferred icon
        if not os.path.exists(icon_path):
             log_and_queue(f"Preferred icon excel_icon.png not found at {icon_path}, trying fallback.", logging.DEBUG)
             icon_path = os.path.join(icon_base_path, 'refresh_icon.png') # Fallback
        
        if not os.path.exists(icon_path):
            log_and_queue(f"Fallback icon refresh_icon.png also not found at {icon_path}. Using default image.", logging.WARNING)
            raise FileNotFoundError # Will be caught below
        image = Image.open(icon_path)
    except FileNotFoundError:
        log_and_queue(f"Icon file not found at expected paths. Using default blue image.", logging.WARNING)
        image = Image.new('RGB', (64, 64), color = 'blue') 
    except Exception as e:
        log_and_queue(f"Error loading icon: {e}. Using default red image.", logging.ERROR)
        image = Image.new('RGB', (64, 64), color = 'red')
        
    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: show_status_window(icon), default=True),
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    # Use a unique name for the icon if multiple pystray services might run
    icon_name = SERVICE_NAME.lower().replace(" ", "_").replace("(", "").replace(")", "")
    tray_icon = pystray.Icon(icon_name, image, SERVICE_NAME, menu=pystray.Menu(*menu))
    return tray_icon

# Keep track of the icon globally to manage its state
global_icon_ref = None

def exit_application(icon_ref_param):
    log_and_queue(f"{SERVICE_NAME}: Exit command received. Stopping service.")
    # Use the global reference or the one passed, prefer passed if available
    actual_icon_to_stop = icon_ref_param or global_icon_ref
    if actual_icon_to_stop:
        try:
            actual_icon_to_stop.stop()
        except Exception as e:
            log_and_queue(f"Error stopping icon: {e}", logging.WARNING)
    os._exit(0)

def main():
    global global_icon_ref
    log_and_queue(f"Service: Starting {SERVICE_NAME}...")
    
    # Start the HTTP server thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    try:
        global_icon_ref = create_tray_icon()
        log_and_queue(f"Service: System tray icon created for {SERVICE_NAME}.")
        global_icon_ref.run()
        log_and_queue(f"Service: {SERVICE_NAME} icon run loop finished.")
    except Exception as e:
        log_and_queue(f"Service: Failed to create or run system tray icon for {SERVICE_NAME}: {e}. The service might run without an icon.", logging.ERROR)
        while http_thread.is_alive():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                log_and_queue(f"{SERVICE_NAME} shutting down due to KeyboardInterrupt (headless mode).", logging.INFO)
                break 
    finally:
        log_and_queue(f"Service: {SERVICE_NAME} main function concluded. Initiating exit.")
        exit_application(global_icon_ref) # Ensure cleanup and exit

if __name__ == "__main__":
    # Example env var check. Ensure .env is correctly loaded for your app context.
    test_env_var = os.getenv('DJANGO_SETTINGS_MODULE', '[NOT_SET]') 
    log_and_queue(f"Info: DJANGO_SETTINGS_MODULE env var: {test_env_var}. .env expected at: {ENV_PATH}. File exists: {os.path.exists(ENV_PATH)}", logging.DEBUG)
    main() 