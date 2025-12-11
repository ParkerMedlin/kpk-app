"""
Excel Worker
=============
HTTP service that triggers PowerShell scripts for Excel-based operations:
- Blend sheet generation
- GHS label creation
- Pick sheet generation
- Combined production package generation

Uses Redis queue for concurrent job processing.

Replaces: PYSTRAY_excel_macro_trigger_service.pyw
Location: host-services/workers/excel_worker.py
"""

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
import ssl
import redis
from concurrent.futures import ThreadPoolExecutor
import requests

# --- Path Configuration ---
# Calculate kpk-app root from this file's location (host-services/workers/)
KPK_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOST_SERVICES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv(os.path.join(KPK_APP_ROOT, '.env'))

# --- Logging Configuration ---
LOG_DIR = os.path.join(HOST_SERVICES_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'excel_worker.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Service Configuration ---
SERVICE_NAME = "Excel Worker"
HTTP_HOST = '127.0.0.1'
HTTP_PORT = 9998

# PowerShell script is in the old location (still in python_systray_scripts)
POWERSHELL_SCRIPT_PATH = os.path.join(KPK_APP_ROOT, 'local_machine_scripts', 'python_systray_scripts', 'Invoke-DirectExcelEdit.ps1')

# --- Excel Macro Configuration ---
GHS_LABEL_BASE_FOLDER_PATH = r"\\KinPak-Svr1\qclab\My Documents\Blend GHS Tote Label"
GHS_EXCEL_SHEET_NAME = "GHSsheet"
PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE = os.path.normpath(
    os.path.join(KPK_APP_ROOT, 'local_machine_scripts', 'python_systray_scripts',
                 'pystray_excel_macro_utils', 'ghsnonhazardtemplate.xlsx')
)

# --- Icon Path ---
ICON_PATH = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'excel_icon.png')
FALLBACK_ICON_PATH = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'refresh_icon.png')

# Queue for inter-thread communication with Tkinter
log_queue = queue.Queue()


def log_and_queue(message, level=logging.INFO):
    """Log message and add to queue for GUI display."""
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
    elif level == logging.CRITICAL:
        logging.critical(message)

    log_queue.put(formatted_message)


class RedisQueueProcessor:
    """Processes Excel macro jobs from Redis queue."""

    def __init__(self):
        self.redis_client = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = True

    def connect_redis(self):
        """Connect to Redis with retry logic."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.Redis(
                    host='host.docker.internal',
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
        """Process a single job from the queue."""
        try:
            job_data = json.loads(job_data_str)
            job_id = job_data['id']

            job_data['status'] = 'processing'
            job_data['started_at'] = datetime.datetime.now().isoformat()
            self.redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))

            log_and_queue(f"Redis: Processing job {job_id} - {job_data['macro_to_run']}", logging.INFO)

            macro_to_run = job_data['macro_to_run']
            data_for_macro = job_data['data_for_macro']
            components_for_pick_sheet = job_data.get('components_for_pick_sheet')

            result = self.execute_macro(job_id, macro_to_run, data_for_macro, components_for_pick_sheet)

            job_data['status'] = 'completed' if result['success'] else 'failed'
            job_data['completed_at'] = datetime.datetime.now().isoformat()
            job_data['result'] = result
            self.redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))

            if result['success']:
                log_and_queue(f"Redis: Job {job_id} completed successfully - {result.get('message', '')}", logging.INFO)
            else:
                log_and_queue(f"Redis: Job {job_id} failed - {result.get('message', 'No message')}", logging.ERROR)

            stdout_text = result.get('stdout')
            if stdout_text:
                log_and_queue(f"Redis: Job {job_id} PowerShell STDOUT:\n{stdout_text}", logging.DEBUG)
            stderr_text = result.get('stderr')
            if stderr_text:
                log_and_queue(f"Redis: Job {job_id} PowerShell STDERR:\n{stderr_text}", logging.ERROR if not result['success'] else logging.WARNING)

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

    def execute_macro(self, job_id, macro_to_run, data_for_macro, components_for_pick_sheet=None):
        """Execute the macro using PowerShell."""
        try:
            log_and_queue(
                f"Redis: Job {job_id} using PowerShell script at {POWERSHELL_SCRIPT_PATH} and GHS template {PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE}",
                logging.DEBUG
            )

            if not os.path.exists(POWERSHELL_SCRIPT_PATH):
                return {
                    'success': False,
                    'message': f'PowerShell script not found at {POWERSHELL_SCRIPT_PATH}',
                    'stdout': '',
                    'stderr': ''
                }

            if macro_to_run == "generateProductionPackage":
                if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                    return {'success': False, 'message': 'Invalid data_for_macro for generateProductionPackage', 'stdout': '', 'stderr': ''}

                lot_quantity = str(data_for_macro[0])
                lot_number = str(data_for_macro[1])
                blend_description = str(data_for_macro[3])
                item_code_for_template_lookup = str(data_for_macro[5])
                components_json_string = json.dumps(components_for_pick_sheet or [])

                command = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", POWERSHELL_SCRIPT_PATH,
                    "-CommandType", "GenerateProductionPackage",
                    "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                    "-LotQuantity", lot_quantity,
                    "-LotNumber", lot_number,
                    "-BlendDescription", blend_description,
                    "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                    "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                    "-PathToGHSNonHazardExcelTemplate", PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE,
                    "-ComponentsForPickSheetJson", components_json_string
                ]
            elif macro_to_run == "blndSheetGen":
                if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                    return {'success': False, 'message': 'Invalid data_for_macro for blndSheetGen'}

                lot_quantity = str(data_for_macro[0])
                lot_number = str(data_for_macro[1])
                blend_description = str(data_for_macro[3])
                item_code_for_template_lookup = str(data_for_macro[5])

                command = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", POWERSHELL_SCRIPT_PATH,
                    "-CommandType", "GenerateBlendSheetOnly",
                    "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
                    "-LotQuantity", lot_quantity,
                    "-LotNumber", lot_number,
                    "-BlendDescription", blend_description,
                    "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
                    "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
                    "-PathToGHSNonHazardExcelTemplate", PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE
                ]
            else:
                return {'success': False, 'message': f'Unknown macro_to_run: {macro_to_run}', 'stdout': '', 'stderr': ''}

            log_and_queue(f"Redis: Job {job_id} launching PowerShell for {macro_to_run}", logging.INFO)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            stdout, stderr = process.communicate(timeout=60)

            if process.returncode == 0:
                try:
                    all_stdout_lines = stdout.strip().splitlines()
                    if all_stdout_lines:
                        potential_json_line = all_stdout_lines[-1].strip()
                        if potential_json_line.startswith('{') and potential_json_line.endswith('}'):
                            ps_response = json.loads(potential_json_line)
                            return {
                                'success': ps_response.get('status') == 'success',
                                'message': ps_response.get('message', ''),
                                'details': ps_response,
                                'stdout': stdout.strip(),
                                'stderr': stderr.strip()
                            }
                    return {'success': False, 'message': 'No JSON output from PowerShell', 'stdout': stdout.strip(), 'stderr': stderr.strip()}
                except json.JSONDecodeError:
                    return {'success': False, 'message': 'Failed to parse PowerShell output', 'stdout': stdout.strip(), 'stderr': stderr.strip()}
            else:
                return {
                    'success': False,
                    'message': f'PowerShell failed with code {process.returncode}',
                    'stdout': stdout.strip(),
                    'stderr': stderr.strip()
                }

        except subprocess.TimeoutExpired:
            log_and_queue(f"Redis: Job {job_id} PowerShell execution timed out after 60 seconds", logging.ERROR)
            process.kill()
            stdout, stderr = process.communicate()
            return {'success': False, 'message': 'PowerShell script timed out', 'stdout': stdout.strip(), 'stderr': stderr.strip()}
        except Exception as e:
            return {'success': False, 'message': f'Error executing macro: {str(e)}', 'stdout': '', 'stderr': ''}

    def run(self):
        """Main queue processing loop."""
        if not self.connect_redis():
            log_and_queue("Redis: Queue processor not starting due to connection failure", logging.ERROR)
            return

        log_and_queue("Redis: Queue processor started", logging.INFO)

        while self.running:
            try:
                result = self.redis_client.brpop('excel_macro_queue', timeout=1)
                if result:
                    _, job_data = result
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
        """Stop the queue processor."""
        self.running = False
        self.executor.shutdown(wait=True)


class MacroTriggerHandler(BaseHTTPRequestHandler):
    """HTTP handler for Excel macro endpoints."""

    def do_POST(self):
        client_ip = self.client_address[0]

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
            response_code = 500

            try:
                payload = json.loads(post_data.decode('utf-8'))
                log_and_queue(f"HTTP: Payload received: {payload}")

                macro_to_run = payload.get('macro_to_run')
                data_for_macro = payload.get('data_for_macro')
                components_for_pick_sheet = payload.get('components_for_pick_sheet')

                if not macro_to_run or data_for_macro is None:
                    log_and_queue("HTTP: 'macro_to_run' or 'data_for_macro' missing from payload.", logging.WARNING)
                    response_data = {'status': 'error', 'message': "'macro_to_run' or 'data_for_macro' missing"}
                    response_code = 400

                elif macro_to_run == "generateProductionPackage":
                    if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                        log_and_queue(f"HTTP: 'data_for_macro' for generateProductionPackage is invalid.", logging.WARNING)
                        response_data = {'status': 'error', 'message': 'Invalid data_for_macro for generateProductionPackage'}
                        response_code = 400
                    elif components_for_pick_sheet is None or not isinstance(components_for_pick_sheet, list):
                        log_and_queue(f"HTTP: 'components_for_pick_sheet' for generateProductionPackage is missing or not a list.", logging.WARNING)
                        response_data = {'status': 'error', 'message': "'components_for_pick_sheet' is required and must be a list"}
                        response_code = 400
                    else:
                        response_data, response_code = self._execute_production_package(data_for_macro, components_for_pick_sheet)

                elif macro_to_run == "blndSheetGen":
                    if not isinstance(data_for_macro, list) or len(data_for_macro) < 6:
                        log_and_queue(f"HTTP: 'data_for_macro' for blndSheetGen is invalid.", logging.WARNING)
                        response_data = {'status': 'error', 'message': 'Invalid data_for_macro for blndSheetGen'}
                        response_code = 400
                    else:
                        response_data, response_code = self._execute_blend_sheet(data_for_macro)

                elif macro_to_run == "pickSheetGen":
                    log_and_queue(f"HTTP: Received request for 'pickSheetGen'. This is deprecated.", logging.INFO)
                    response_data = {'status': 'deprecated', 'message': 'pickSheetGen is now part of generateProductionPackage.', 'original_status_code': 410}
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

    def _execute_production_package(self, data_for_macro, components_for_pick_sheet):
        """Execute generateProductionPackage PowerShell command."""
        lot_quantity = str(data_for_macro[0])
        lot_number = str(data_for_macro[1])
        blend_description = str(data_for_macro[3])
        item_code_for_template_lookup = str(data_for_macro[5])
        components_json_string = json.dumps(components_for_pick_sheet)

        if not os.path.exists(POWERSHELL_SCRIPT_PATH):
            log_and_queue(f"Action: PowerShell script NOT FOUND at {POWERSHELL_SCRIPT_PATH}", logging.ERROR)
            return {'status': 'error', 'message': f'PowerShell script not found'}, 500

        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", POWERSHELL_SCRIPT_PATH,
            "-CommandType", "GenerateProductionPackage",
            "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
            "-LotQuantity", lot_quantity,
            "-LotNumber", lot_number,
            "-BlendDescription", blend_description,
            "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
            "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
            "-PathToGHSNonHazardExcelTemplate", PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE,
            "-ComponentsForPickSheetJson", components_json_string
        ]

        log_and_queue(f"Action: Executing PowerShell for generateProductionPackage", logging.INFO)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        stdout, stderr = process.communicate(timeout=360)

        return self._parse_powershell_response(process, stdout, stderr, "generateProductionPackage")

    def _execute_blend_sheet(self, data_for_macro):
        """Execute blndSheetGen PowerShell command."""
        lot_quantity = str(data_for_macro[0])
        lot_number = str(data_for_macro[1])
        blend_description = str(data_for_macro[3])
        item_code_for_template_lookup = str(data_for_macro[5])

        if not os.path.exists(POWERSHELL_SCRIPT_PATH):
            log_and_queue(f"Action: PowerShell script NOT FOUND at {POWERSHELL_SCRIPT_PATH}", logging.ERROR)
            return {'status': 'error', 'message': f'PowerShell script not found'}, 500

        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", POWERSHELL_SCRIPT_PATH,
            "-CommandType", "GenerateBlendSheetOnly",
            "-ItemCodeForTemplateLookup", item_code_for_template_lookup,
            "-LotQuantity", lot_quantity,
            "-LotNumber", lot_number,
            "-BlendDescription", blend_description,
            "-GHSLabelBaseFolderPath", GHS_LABEL_BASE_FOLDER_PATH,
            "-GHSExcelSheetName", GHS_EXCEL_SHEET_NAME,
            "-PathToGHSNonHazardExcelTemplate", PATH_TO_GHS_NON_HAZARD_EXCEL_TEMPLATE
        ]

        log_and_queue(f"Action: Executing PowerShell for blndSheetGen", logging.INFO)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        stdout, stderr = process.communicate(timeout=360)

        return self._parse_powershell_response(process, stdout, stderr, "blndSheetGen")

    def _parse_powershell_response(self, process, stdout, stderr, operation_name):
        """Parse PowerShell output and return response data and code."""
        log_and_queue(f"PS_STDOUT: {stdout}", logging.INFO)
        if stderr:
            log_and_queue(f"PS_STDERR: {stderr}", logging.ERROR)

        if process.returncode == 0:
            try:
                all_stdout_lines = stdout.strip().splitlines()
                if all_stdout_lines:
                    potential_json_line = all_stdout_lines[-1].strip()
                    if potential_json_line.startswith('{') and potential_json_line.endswith('}'):
                        ps_response = json.loads(potential_json_line)
                        log_and_queue(f"Action: PowerShell script completed ({operation_name}). Response: {ps_response}", logging.INFO)
                        response_code = 200 if ps_response.get('status') == 'success' else 500
                        ps_response['original_status_code'] = response_code
                        return ps_response, response_code

                log_and_queue(f"Action: PowerShell script ({operation_name}) finished but no JSON output found.", logging.ERROR)
                return {'status': 'error', 'message': 'No valid JSON output.', 'stdout': stdout, 'stderr': stderr, 'original_status_code': 500}, 500
            except json.JSONDecodeError as je:
                log_and_queue(f"Action: Failed to parse JSON response ({operation_name}): {je}", logging.ERROR)
                return {'status': 'error', 'message': 'Failed to parse PowerShell JSON response.', 'stdout': stdout, 'stderr': stderr, 'original_status_code': 500}, 500
        else:
            log_and_queue(f"Action: PowerShell script ({operation_name}) failed with return code {process.returncode}", logging.ERROR)
            return {'status': 'error', 'message': 'PowerShell script failed.', 'details': stderr, 'stdout': stdout, 'original_status_code': 500}, 500

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_http_server():
    """Start the HTTP server and Redis queue processor."""
    if not os.path.exists(POWERSHELL_SCRIPT_PATH):
        log_and_queue(f"CRITICAL: PowerShell script not found at {POWERSHELL_SCRIPT_PATH}. HTTP server will start, but requests will fail.", logging.CRITICAL)
    else:
        log_and_queue(f"HTTP Server: PowerShell script found at {POWERSHELL_SCRIPT_PATH}", logging.INFO)

    queue_processor = RedisQueueProcessor()

    try:
        server_address = (HTTP_HOST, HTTP_PORT)
        httpd = HTTPServer(server_address, MacroTriggerHandler)
        httpd.queue_processor = queue_processor

        queue_thread = threading.Thread(target=queue_processor.run, daemon=True)
        queue_thread.start()

        log_and_queue(f"HTTP Server: Starting on http://{HTTP_HOST}:{HTTP_PORT} for {SERVICE_NAME}")
        httpd.serve_forever()
    except OSError as e:
        log_and_queue(f"HTTP Server: OS Error (maybe port {HTTP_PORT} is already in use?) - {str(e)}", logging.ERROR)
    except Exception as e:
        log_and_queue(f"HTTP Server: Failed to start - {str(e)}", logging.ERROR)
    finally:
        queue_processor.stop()


def show_status_window(icon_ref):
    """Display the status window with service activity log."""
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
            print(f"Error updating log display: {e}")
        finally:
            if root.winfo_exists():
                root.after(150, update_log_display)

    log_text_area.configure(state='normal')
    log_text_area.insert(tk.END, f"Initializing {SERVICE_NAME} Window...\n")
    log_text_area.insert(tk.END, f"Listening for HTTP requests on http://{HTTP_HOST}:{HTTP_PORT}\n")
    log_text_area.insert(tk.END, f"Using PowerShell script: {POWERSHELL_SCRIPT_PATH}\n")
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
        log_and_queue(f"Tkinter mainloop error: {e}", logging.WARNING)


def create_tray_icon():
    """Create the system tray icon."""
    try:
        if os.path.exists(ICON_PATH):
            image = Image.open(ICON_PATH)
        elif os.path.exists(FALLBACK_ICON_PATH):
            log_and_queue(f"Preferred icon not found, using fallback.", logging.DEBUG)
            image = Image.open(FALLBACK_ICON_PATH)
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        log_and_queue(f"Icon files not found. Using default blue image.", logging.WARNING)
        image = Image.new('RGB', (64, 64), color='blue')
    except Exception as e:
        log_and_queue(f"Error loading icon: {e}. Using default red image.", logging.ERROR)
        image = Image.new('RGB', (64, 64), color='red')

    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: show_status_window(icon), default=True),
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    icon_name = SERVICE_NAME.lower().replace(" ", "_")
    tray_icon = pystray.Icon(icon_name, image, SERVICE_NAME, menu=pystray.Menu(*menu))
    return tray_icon


global_icon_ref = None


def exit_application(icon_ref_param):
    """Stop the service and exit."""
    log_and_queue(f"{SERVICE_NAME}: Exit command received. Stopping service.")
    actual_icon_to_stop = icon_ref_param or global_icon_ref
    if actual_icon_to_stop:
        try:
            actual_icon_to_stop.stop()
        except Exception as e:
            log_and_queue(f"Error stopping icon: {e}", logging.WARNING)
    os._exit(0)


def main():
    """Main entry point for the Excel Worker."""
    global global_icon_ref
    log_and_queue(f"Service: Starting {SERVICE_NAME}...")

    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    try:
        global_icon_ref = create_tray_icon()
        log_and_queue(f"Service: System tray icon created for {SERVICE_NAME}.")
        global_icon_ref.run()
        log_and_queue(f"Service: {SERVICE_NAME} icon run loop finished.")
    except Exception as e:
        log_and_queue(f"Service: Failed to create or run system tray icon: {e}. Running headless.", logging.ERROR)
        while http_thread.is_alive():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                log_and_queue(f"{SERVICE_NAME} shutting down due to KeyboardInterrupt.", logging.INFO)
                break
    finally:
        log_and_queue(f"Service: {SERVICE_NAME} main function concluded. Initiating exit.")
        exit_application(global_icon_ref)


if __name__ == "__main__":
    main()
