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
import redis
from concurrent.futures import ThreadPoolExecutor
import requests

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

# --- Redis Queue Processor ---
class RedisQueueProcessor:
    def __init__(self):
        self.redis_client = None
        self.executor = ThreadPoolExecutor(max_workers=10)  # Process up to 3 prints concurrently
        self.running = True
        
    def connect_redis(self):
        """Connect to Redis with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.Redis(
                    host='host.docker.internal',  # Docker host from Windows
                    port=6379,
                    decode_responses=True,
                    socket_keepalive=True,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()
                log_and_queue("Redis: Connected successfully to queue", logging.INFO)
                return True
            except Exception as e:
                log_and_queue(f"Redis: Connection attempt {attempt+1} failed: {e}", logging.WARNING)
                time.sleep(2 ** attempt)
        log_and_queue("Redis: Failed to connect after all retries", logging.ERROR)
        return False
    
    def process_job(self, job_data_str):
        """Process a single job from the queue"""
        try:
            job_data = json.loads(job_data_str)
            job_id = job_data['id']
            
            # Update status to processing
            job_data['status'] = 'processing'
            job_data['started_at'] = datetime.datetime.now().isoformat()
            self.redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))
            
            log_and_queue(f"Redis: Processing job {job_id} - {job_data['macro_to_run']}", logging.INFO)
            
            # Call the existing handler logic
            macro_to_run = job_data['macro_to_run']
            data_for_macro = job_data['data_for_macro']
            components_for_pick_sheet = job_data.get('components_for_pick_sheet')
            
            # Execute the macro (reuse existing PowerShell logic)
            result = self.execute_macro(macro_to_run, data_for_macro, components_for_pick_sheet)
            
            # Update job with result
            job_data['status'] = 'completed' if result['success'] else 'failed'
            job_data['completed_at'] = datetime.datetime.now().isoformat()
            job_data['result'] = result
            self.redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))
            
            # If successful and we have lot_num_record_id, publish completion event
            if result['success'] and job_data.get('lot_num_record_id'):
                completion_event = {
                    'job_id': job_id,
                    'lot_num_record_id': job_data['lot_num_record_id'],
                    'lot_number': job_data.get('lot_number'),
                    'item_code': job_data.get('item_code'),
                    'line': job_data.get('line'),
                    'macro_to_run': macro_to_run,
                    'user_id': job_data.get('user_id')
                }
                self.redis_client.publish('excel_macro_completions', json.dumps(completion_event))
                log_and_queue(f"Redis: Published completion event for job {job_id}", logging.DEBUG)
            
        except Exception as e:
            log_and_queue(f"Redis: Error processing job: {e}", logging.ERROR)
            if 'job_id' in locals():
                try:
                    job_data['status'] = 'failed'
                    job_data['error'] = str(e)
                    job_data['completed_at'] = datetime.datetime.now().isoformat()
                    self.redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))
                except:
                    pass
    
    def execute_macro(self, macro_to_run, data_for_macro, components_for_pick_sheet=None):
        """Execute the macro using existing PowerShell logic"""
        try:
            # This is essentially the existing handler logic refactored
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), POWERSHELL_SCRIPT_NAME)
            app_root_dir = os.path.dirname(ENV_PATH)
            absolute_ghs_template_path = os.path.normpath(os.path.join(app_root_dir, PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE))
            
            if not os.path.exists(script_path):
                return {'success': False, 'message': f'PowerShell script not found at {script_path}'}
            
            if macro_to_run == "generateProductionPackage":
                if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                    return {'success': False, 'message': 'Invalid data_for_macro for generateProductionPackage'}
                
                lot_quantity = str(data_for_macro[0])
                lot_number = str(data_for_macro[1])
                blend_description = str(data_for_macro[3])
                item_code_for_template_lookup = str(data_for_macro[5])
                components_json_string = json.dumps(components_for_pick_sheet or [])
                
                # FORENSIC LOGGING - Python side
                log_and_queue(f"FORENSIC PYTHON - Original data_for_macro[0]: {repr(data_for_macro[0])}", logging.INFO)
                log_and_queue(f"FORENSIC PYTHON - Type of data_for_macro[0]: {type(data_for_macro[0])}", logging.INFO)
                log_and_queue(f"FORENSIC PYTHON - After str() conversion: {repr(lot_quantity)}", logging.INFO)
                log_and_queue(f"FORENSIC PYTHON - lot_quantity bytes: {lot_quantity.encode('utf-8')}", logging.INFO)
                
                command = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", script_path,
                    "-CommandType", "GenerateProductionPackage",
                    "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                    "-LotQuantity", lot_quantity,
                    "-LotNumber", lot_number,
                    "-BlendDescription", blend_description,
                    "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                    "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                    "-PathToGHSNonHazardExcelTemplate", absolute_ghs_template_path,
                    "-ComponentsForPickSheetJson", components_json_string
                ]
                
                # Log the exact command being executed
                log_and_queue(f"FORENSIC PYTHON - Full PowerShell command: {' '.join(command)}", logging.INFO)
                
            elif macro_to_run == "blndSheetGen":
                if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                    return {'success': False, 'message': 'Invalid data_for_macro for blndSheetGen'}
                
                lot_quantity = str(data_for_macro[0])
                lot_number = str(data_for_macro[1])
                blend_description = str(data_for_macro[3])
                item_code_for_template_lookup = str(data_for_macro[5])
                
                # FORENSIC LOGGING - Python side
                log_and_queue(f"FORENSIC PYTHON - Original data_for_macro[0]: {repr(data_for_macro[0])}", logging.INFO)
                log_and_queue(f"FORENSIC PYTHON - Type of data_for_macro[0]: {type(data_for_macro[0])}", logging.INFO)
                log_and_queue(f"FORENSIC PYTHON - After str() conversion: {repr(lot_quantity)}", logging.INFO)
                log_and_queue(f"FORENSIC PYTHON - lot_quantity bytes: {lot_quantity.encode('utf-8')}", logging.INFO)
                
                command = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", script_path,
                    "-CommandType", "GenerateBlendSheetOnly",
                    "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                    "-LotQuantity", lot_quantity,
                    "-LotNumber", lot_number,
                    "-BlendDescription", blend_description,
                    "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                    "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                    "-PathToGHSNonHazardExcelTemplate", absolute_ghs_template_path
                ]
                
                # Log the exact command being executed
                log_and_queue(f"FORENSIC PYTHON - Full PowerShell command: {' '.join(command)}", logging.INFO)
                
            else:
                return {'success': False, 'message': f'Unknown macro_to_run: {macro_to_run}'}
            
            # Execute with shorter timeout since we're async now
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout, stderr = process.communicate(timeout=60)  # Much shorter timeout
            
            if process.returncode == 0:
                # Parse PowerShell JSON output
                try:
                    all_stdout_lines = stdout.strip().splitlines()
                    if all_stdout_lines:
                        potential_json_line = all_stdout_lines[-1].strip()
                        if potential_json_line.startswith('{') and potential_json_line.endswith('}'):
                            ps_response = json.loads(potential_json_line)
                            return {
                                'success': ps_response.get('status') == 'success',
                                'message': ps_response.get('message', ''),
                                'details': ps_response
                            }
                    return {'success': False, 'message': 'No JSON output from PowerShell'}
                except json.JSONDecodeError:
                    return {'success': False, 'message': 'Failed to parse PowerShell output', 'stdout': stdout}
            else:
                return {'success': False, 'message': f'PowerShell failed with code {process.returncode}', 'stderr': stderr}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'PowerShell script timed out'}
        except Exception as e:
            return {'success': False, 'message': f'Error executing macro: {str(e)}'}
    
    def run(self):
        """Main queue processing loop"""
        if not self.connect_redis():
            log_and_queue("Redis: Queue processor not starting due to connection failure", logging.ERROR)
            return
        
        log_and_queue("Redis: Queue processor started", logging.INFO)
        
        while self.running:
            try:
                # Blocking pop with 1 second timeout
                result = self.redis_client.brpop('excel_macro_queue', timeout=1)
                if result:
                    _, job_data = result
                    # Submit to thread pool for concurrent processing
                    self.executor.submit(self.process_job, job_data)
            except redis.ConnectionError:
                log_and_queue("Redis: Connection lost, attempting reconnect...", logging.WARNING)
                time.sleep(5)
                self.connect_redis()
            except Exception as e:
                log_and_queue(f"Redis: Queue processor error: {e}", logging.ERROR)
                time.sleep(1)
        
        log_and_queue("Redis: Queue processor stopped", logging.INFO)
    
    def stop(self):
        """Stop the queue processor"""
        self.running = False
        self.executor.shutdown(wait=True)

# --- HTTP Server Handler ---
class MacroTriggerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        client_ip = self.client_address[0]
        
        # Add job status endpoint
        if self.path == '/job-status':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                job_id = payload.get('job_id')
                
                if not job_id:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'error', 'message': 'job_id required'}).encode('utf-8'))
                    return
                
                # Get job status from Redis (access through global queue_processor)
                if hasattr(self.server, 'queue_processor') and self.server.queue_processor.redis_client:
                    job_data = self.server.queue_processor.redis_client.hget('excel_macro_jobs', job_id)
                    if job_data:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(job_data.encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'not_found'}).encode('utf-8'))
                else:
                    self.send_response(503)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'error', 'message': 'Redis not available'}).encode('utf-8'))
                    
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
            return
        
        if self.path == '/run-excel-macro':
            log_and_queue(f"HTTP: Received /run-excel-macro from {client_ip}")
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            response_data = {}
            response_code = 500 # Default to internal server error

            try:
                payload = json.loads(post_data.decode('utf-8'))
                log_and_queue(f"HTTP: Payload received: {payload}")

                macro_to_run = payload.get('macro_to_run')
                data_for_macro = payload.get('data_for_macro') # This is expected to be a list
                components_for_pick_sheet = payload.get('components_for_pick_sheet') # New for generateProductionPackage

                if not macro_to_run or data_for_macro is None:
                    log_and_queue("HTTP: 'macro_to_run' or 'data_for_macro' missing from payload.", logging.WARNING)
                    response_data = {'status': 'error', 'message': "'macro_to_run' or 'data_for_macro' missing"}
                    response_code = 400
                # --- Combined Production Package Logic ---
                elif macro_to_run == "generateProductionPackage":
                    if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                        log_and_queue(f"HTTP: 'data_for_macro' for generateProductionPackage is not a list or has insufficient length (expected 6, got {len(data_for_macro) if isinstance(data_for_macro, list) else 'not a list'}).", logging.WARNING)
                        response_data = {'status': 'error', 'message': 'Invalid data_for_macro for generateProductionPackage'}
                        response_code = 400
                    elif components_for_pick_sheet is None or not isinstance(components_for_pick_sheet, list):
                        log_and_queue(f"HTTP: 'components_for_pick_sheet' for generateProductionPackage is missing or not a list.", logging.WARNING)
                        response_data = {'status': 'error', 'message': "'components_for_pick_sheet' is required and must be a list for generateProductionPackage"}
                        response_code = 400
                    else:
                        lot_quantity = str(data_for_macro[0])
                        lot_number = str(data_for_macro[1])
                        blend_description = str(data_for_macro[3])
                        item_code_for_template_lookup = str(data_for_macro[5])
                        
                        # Serialize components_for_pick_sheet to a JSON string to pass as a single argument
                        components_json_string = json.dumps(components_for_pick_sheet)

                        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), POWERSHELL_SCRIPT_NAME)
                        app_root_dir = os.path.dirname(ENV_PATH)
                        absolute_ghs_template_path = os.path.normpath(os.path.join(app_root_dir, PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE))

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
                                "-CommandType", "GenerateProductionPackage", # New parameter to control PS script logic
                                "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                                "-LotQuantity", lot_quantity,
                                "-LotNumber", lot_number,
                                "-BlendDescription", blend_description,
                                "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                                "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                                "-PathToGHSNonHazardExcelTemplate", absolute_ghs_template_path,
                                "-ComponentsForPickSheetJson", components_json_string # Pass components as JSON string
                            ]
                            log_and_queue(f"Action: Executing PowerShell for generateProductionPackage: {' '.join(command)}", logging.INFO)
                            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                            stdout, stderr = process.communicate(timeout=360) # Increased timeout for combined operation

                            log_and_queue(f"PS_STDOUT: {stdout}", logging.INFO)
                            if stderr:
                                log_and_queue(f"PS_STDERR: {stderr}", logging.ERROR)

                            if process.returncode == 0:
                                try:
                                    json_output_line = None
                                    all_stdout_lines = stdout.strip().splitlines()
                                    if all_stdout_lines:
                                        potential_json_line = all_stdout_lines[-1].strip()
                                        if potential_json_line.startswith('{') and potential_json_line.endswith('}'):
                                            json_output_line = potential_json_line
                                    
                                    if json_output_line:
                                        ps_response = json.loads(json_output_line)
                                        log_and_queue(f"Action: PowerShell script completed (generateProductionPackage). Parsed Response: {ps_response}", logging.INFO)
                                        response_data = ps_response
                                        response_code = 200 if ps_response.get('status') == 'success' else 500
                                        response_data['original_status_code'] = response_code # For Django view to use
                                    else:
                                        log_and_queue("Action: PowerShell script (generateProductionPackage) finished but no JSON output found.", logging.ERROR)
                                        response_data = {'status': 'error', 'message': 'PowerShell script finished but no valid JSON output.', 'stdout': stdout, 'stderr': stderr, 'original_status_code': 500}
                                        response_code = 500
                                except json.JSONDecodeError as je:
                                    log_and_queue(f"Action: Failed to parse JSON response from PowerShell (generateProductionPackage): {je}. stdout: {stdout}", logging.ERROR)
                                    response_data = {'status': 'error', 'message': 'Failed to parse PowerShell JSON response.', 'stdout': stdout, 'stderr': stderr, 'original_status_code': 500}
                                    response_code = 500
                            else:
                                log_and_queue(f"Action: PowerShell script (generateProductionPackage) failed with return code {process.returncode}. Stderr: {stderr}", logging.ERROR)
                                response_data = {'status': 'error', 'message': f'PowerShell script failed. See service logs.', 'details': stderr, 'stdout': stdout, 'original_status_code': 500}
                                response_code = 500
                # --- End Combined Production Package Logic ---
                elif macro_to_run == "blndSheetGen":
                    if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                        log_and_queue(f"HTTP: 'data_for_macro' for blndSheetGen is not a list or has insufficient length (expected 6, got {len(data_for_macro) if isinstance(data_for_macro, list) else 'not a list'}).", logging.WARNING)
                        response_data = {'status': 'error', 'message': 'Invalid data_for_macro for blndSheetGen'}
                        response_code = 400
                    else:
                        lot_quantity = str(data_for_macro[0])
                        lot_number = str(data_for_macro[1])
                        blend_description = str(data_for_macro[3])
                        item_code_for_template_lookup = str(data_for_macro[5])

                        # FORENSIC LOGGING - HTTP Handler
                        log_and_queue(f"FORENSIC HTTP - Original data_for_macro[0]: {repr(data_for_macro[0])}", logging.INFO)
                        log_and_queue(f"FORENSIC HTTP - Type of data_for_macro[0]: {type(data_for_macro[0])}", logging.INFO)
                        log_and_queue(f"FORENSIC HTTP - After str() conversion: {repr(lot_quantity)}", logging.INFO)
                        log_and_queue(f"FORENSIC HTTP - lot_quantity bytes: {lot_quantity.encode('utf-8')}", logging.INFO)

                        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), POWERSHELL_SCRIPT_NAME)
                        app_root_dir = os.path.dirname(ENV_PATH)
                        absolute_ghs_template_path = os.path.normpath(os.path.join(app_root_dir, PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE))

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
                                "-CommandType", "GenerateBlendSheetOnly", # New parameter to control PS script logic
                                "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                                "-LotQuantity", lot_quantity,
                                "-LotNumber", lot_number,
                                "-BlendDescription", blend_description,
                                "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                                "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                                "-PathToGHSNonHazardExcelTemplate", absolute_ghs_template_path
                                # No -ComponentsForPickSheetJson for this command type
                            ]
                            
                            ghs_path_in_command = "[NOT FOUND IN COMMAND LIST]"
                            try:
                                ghs_param_index = command.index("-PathToGHSNonHazardExcelTemplate")
                                if ghs_param_index + 1 < len(command):
                                    ghs_path_in_command = command[ghs_param_index + 1]
                            except ValueError:
                                pass # Parameter not found
                            log_and_queue(f"DEBUG: GHS template path in actual command list = {ghs_path_in_command}", logging.DEBUG)

                            log_and_queue(f"Action: Executing PowerShell for blndSheetGen (via GenerateBlendSheetOnly): {' '.join(command)}", logging.INFO)
                            
                            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                            stdout, stderr = process.communicate(timeout=360) # Increased timeout (was 300)

                            log_and_queue(f"PS_STDOUT: {stdout}", logging.INFO)
                            if stderr:
                                log_and_queue(f"PS_STDERR: {stderr}", logging.ERROR)

                            if process.returncode == 0:
                                try:
                                    json_output_line = None
                                    all_stdout_lines = stdout.strip().splitlines()
                                    if all_stdout_lines:
                                        potential_json_line = all_stdout_lines[-1].strip()
                                        if potential_json_line.startswith('{') and potential_json_line.endswith('}'):
                                            json_output_line = potential_json_line
                                    
                                    if json_output_line:
                                        ps_response = json.loads(json_output_line)
                                        log_and_queue(f"Action: PowerShell script completed (blndSheetGen). Parsed Response: {ps_response}", logging.INFO)
                                        response_data = ps_response
                                        response_code = 200 if ps_response.get('status') == 'success' else 500
                                        response_data['original_status_code'] = response_code # For Django view to use
                                    else:
                                        log_and_queue("Action: PowerShell script (blndSheetGen) finished but no JSON output found in the last line of stdout.", logging.ERROR)
                                        response_data = {'status': 'error', 'message': 'PowerShell script finished but no valid JSON output.', 'stdout': stdout, 'stderr': stderr, 'original_status_code': 500}
                                        response_code = 500
                                except json.JSONDecodeError as je:
                                    log_and_queue(f"Action: Failed to parse JSON response from PowerShell (blndSheetGen): {je}. stdout: {stdout}", logging.ERROR)
                                    response_data = {'status': 'error', 'message': 'Failed to parse PowerShell JSON response.', 'stdout': stdout, 'stderr': stderr, 'original_status_code': 500}
                                    response_code = 500
                            else:
                                log_and_queue(f"Action: PowerShell script (blndSheetGen) failed with return code {process.returncode}. Stderr: {stderr}", logging.ERROR)
                                response_data = {'status': 'error', 'message': f'PowerShell script failed. See service logs.', 'details': stderr, 'stdout': stdout, 'original_status_code': 500}
                                response_code = 500
                elif macro_to_run == "pickSheetGen":
                    log_and_queue(f"HTTP: Received request for 'pickSheetGen'. This is now part of 'generateProductionPackage'. Direct calls are deprecated.", logging.INFO)
                    response_data = {'status': 'deprecated', 'message': 'pickSheetGen is now part of generateProductionPackage. Please use the combined endpoint.', 'original_status_code': 410} # 410 Gone
                    response_code = 410 
                else:
                    log_and_queue(f"HTTP: Unknown 'macro_to_run' value: {macro_to_run}", logging.WARNING)
                    response_data = {'status': 'error', 'message': f"Unknown macro_to_run type: {macro_to_run}", 'original_status_code': 400}
                    response_code = 400

            except json.JSONDecodeError:
                log_and_queue("HTTP: Invalid JSON in POST data", logging.WARNING)
                response_data = {'status': 'error', 'message': 'Invalid JSON payload', 'original_status_code': 400}
                response_code = 400
            except subprocess.TimeoutExpired:
                log_and_queue("Action: PowerShell script timed out.", logging.ERROR)
                response_data = {'status': 'error', 'message': 'PowerShell script execution timed out after 360 seconds.', 'original_status_code': 500}
                response_code = 500
            except Exception as e:
                log_and_queue(f"HTTP: Error processing /run-excel-macro: {str(e)}", logging.ERROR)
                response_data = {'status': 'error', 'message': f'Internal server error: {str(e)}', 'original_status_code': 500}
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

    # Create queue processor
    queue_processor = RedisQueueProcessor()
    
    try:
        server_address = (HTTP_HOST, HTTP_PORT)
        httpd = HTTPServer(server_address, MacroTriggerHandler)
        
        # Attach queue processor to server for access in handler
        httpd.queue_processor = queue_processor
        
        # Start queue processor in separate thread
        queue_thread = threading.Thread(target=queue_processor.run, daemon=True)
        queue_thread.start()
        
        log_and_queue(f"HTTP Server: Starting on http://{HTTP_HOST}:{HTTP_PORT} for {SERVICE_NAME}")
        httpd.serve_forever()
    except OSError as e:
        log_and_queue(f"HTTP Server: OS Error for {SERVICE_NAME} (maybe port {HTTP_PORT} is already in use?) - {str(e)}", logging.ERROR)
    except Exception as e:
        log_and_queue(f"HTTP Server: Failed to start {SERVICE_NAME} - {str(e)}", logging.ERROR)
    finally:
        queue_processor.stop()

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
    log_text_area.insert(tk.END, f"Redis Queue Processor: Enabled (connecting to host.docker.internal:6379)\n")
    log_text_area.insert(tk.END, f"Concurrent Processing: Up to 10 Excel jobs simultaneously\n")
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