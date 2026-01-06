"""
Looper Health Watchdog
======================
Monitors the data looper service health and can trigger restarts via:
- Email commands from authorized senders
- HTTPS endpoint (/trigger-restart)
- Automatic detection of looper status ('down')

Also provides:
- /run-uv-freeze-audit endpoint for spec sheet UV/Freeze scanning
- /service-status endpoint for health checks

Replaces: PYSTRAY_data_looper_restart_service.pyw
Location: host-services/watchdogs/looper_health.py
"""

import imaplib
import email
import email.header
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
import ssl
import sys
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import requests
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod

# --- Path Configuration ---
# Calculate kpk-app root from this file's location (host-services/watchdogs/)
KPK_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOST_SERVICES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv(os.path.join(KPK_APP_ROOT, '.env'))

# Ensure app_db_mgmt is importable for on-demand tasks
APP_DB_PATH = os.path.join(KPK_APP_ROOT, 'local_machine_scripts', 'python_db_scripts')
if APP_DB_PATH not in sys.path:
    sys.path.insert(0, APP_DB_PATH)

# --- Logging Configuration ---
LOG_DIR = os.path.join(HOST_SERVICES_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'looper_health.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Service Configuration ---
SERVICE_NAME = "Looper Health Watchdog"
GMAIL_SERVER = "imap.gmail.com"
GMAIL_PORT = 993
AUTHORIZED_SENDERS = [
    "pmedlin@kinpakinc.com",
    "jdavis@kinpakinc.com",
    "ddavis@kinpakinc.com"
]
COMMAND_PHRASE = "restart loop"
HTTP_PORT = 9999
# Path to the data_sync worker script
DATA_SYNC_SCRIPT = os.path.join(HOST_SERVICES_ROOT, 'workers', 'data_sync.py')
HTTPS_HOST = '127.0.0.1'

# --- Looper Status Check Configuration ---
DEFAULT_KPKAPP_HOST = "kpkapp.lan"
_configured_base = os.environ.get("KPKAPP_BASE_URL")
if _configured_base:
    KPKAPP_BASE_URL = _configured_base.rstrip("/")
else:
    KPKAPP_HOST = os.environ.get("KPKAPP_HOST", DEFAULT_KPKAPP_HOST)
    KPKAPP_BASE_URL = f"https://{KPKAPP_HOST}"

LOOPER_STATUS_URL = f"{KPKAPP_BASE_URL}/core/get-refresh-status/"
STATUS_CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# --- Alert Origin Identification ---
# Use KPKAPP_HOST if set, otherwise fall back to default
ALERT_ORIGIN = os.environ.get("KPKAPP_HOST", DEFAULT_KPKAPP_HOST)

# --- SSL Certificate Paths ---
CERT_BASE_DIR = os.path.join(KPK_APP_ROOT, 'nginx', 'ssl')
CERT_FILE = os.path.normpath(os.path.join(CERT_BASE_DIR, 'kpkapp.lan.pem'))
KEY_FILE = os.path.normpath(os.path.join(CERT_BASE_DIR, 'kpkapp.lan.key'))

# --- Icon Path ---
ICON_PATH = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'refresh_icon.png')

# Queue for inter-thread communication with Tkinter
log_queue = queue.Queue()


def log_and_queue(message, level=logging.INFO):
    """Log message and add to queue for GUI display."""
    if level == logging.INFO:
        logging.info(message)
    elif level == logging.WARNING:
        logging.warning(message)
    elif level == logging.ERROR:
        logging.error(message)
    elif level == logging.DEBUG:
        logging.debug(message)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_queue.put(f"[{timestamp}] {message}")


class RestartHandler(BaseHTTPRequestHandler):
    """HTTPS handler for restart and status endpoints."""

    def do_GET(self):
        client_ip = self.client_address[0]
        if self.path == '/trigger-restart':
            log_and_queue(f"HTTPS: Received /trigger-restart from {client_ip}")
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
            self.end_headers()
            self.wfile.write(b"Restart initiated")

            restart_thread = threading.Thread(target=execute_restart)
            restart_thread.daemon = True
            restart_thread.start()
        elif self.path == '/run-uv-freeze-audit':
            log_and_queue(f"HTTPS: Received /run-uv-freeze-audit from {client_ip}")
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
            self.end_headers()
            self.wfile.write(b"UV/Freeze audit started")

            audit_thread = threading.Thread(target=execute_uv_freeze_audit)
            audit_thread.daemon = True
            audit_thread.start()
        elif self.path == '/service-status':
            log_and_queue(f"HTTPS: Received /service-status from {client_ip}")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
            self.end_headers()
            response = json.dumps({
                'status': 'running',
                'last_check': datetime.datetime.now().isoformat(),
                'version': '1.0'
            })
            self.wfile.write(response.encode())
        elif self.path.startswith('/get-log'):
            # Serve the data_sync log file content with offset support
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            try:
                offset = int(params.get('offset', [0])[0])
            except (ValueError, TypeError):
                offset = 0

            log_file_path = os.path.join(LOG_DIR, 'data_sync.log')
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
            self.end_headers()

            try:
                if not os.path.exists(log_file_path):
                    response = json.dumps({
                        'logs': '[Log file not found - data_sync may not have started yet]\n',
                        'new_offset': 0,
                        'error': True,
                        'status': 'not_found'
                    })
                else:
                    with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(0, 2)  # Seek to end
                        file_size = f.tell()
                        if offset > file_size:
                            offset = 0
                        f.seek(offset)
                        new_content = f.read()
                        new_offset = f.tell()
                    response = json.dumps({
                        'logs': new_content,
                        'new_offset': new_offset,
                        'error': False,
                        'status': 'ok'
                    })
            except Exception as e:
                response = json.dumps({
                    'logs': f'[Error reading log: {str(e)}]\n',
                    'new_offset': offset,
                    'error': True,
                    'status': 'error'
                })
            self.wfile.write(response.encode())
        else:
            log_and_queue(f"HTTPS: Received {self.path} from {client_ip} (404 Not Found)", logging.WARNING)
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Logging handled within do_GET/do_OPTIONS


def execute_restart():
    """Start the data_sync worker if not already running.

    Only starts a new instance if no existing process is found.
    If data_sync is already running, does nothing.
    """
    try:
        # Check if data_sync is already running
        if is_data_sync_running():
            log_and_queue("Action: data_sync is already running. No action needed.")
            return

        log_and_queue("Action: No existing data_sync process found.")

        # Start the data_sync script
        log_and_queue(f"Action: Starting data_sync from: {DATA_SYNC_SCRIPT}")
        if not os.path.exists(DATA_SYNC_SCRIPT):
            log_and_queue(f"Action: Script not found at {DATA_SYNC_SCRIPT}", logging.ERROR)
            return

        # Start hidden using pythonw (no console window)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        process = subprocess.Popen(
            ['pythonw', DATA_SYNC_SCRIPT],
            cwd=KPK_APP_ROOT,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        log_and_queue(f"Action: Successfully launched data_sync process (PID: {process.pid}).")
    except Exception as e:
        log_and_queue(f"Action: Error starting data_sync: {str(e)}", logging.ERROR)


def execute_uv_freeze_audit():
    """Run the spec sheet UV/Freeze scan on the host machine."""
    try:
        from app_db_mgmt import i_eat_the_specsheet as specsheet
        log_and_queue("Action: Starting find_uv_freeze_unmatched_ci_items()")
        result = specsheet.find_uv_freeze_unmatched_ci_items(send_email_on_missing=True)
        log_and_queue(f"Action: UV/Freeze audit completed. Rows: {len(result)}")
    except Exception as e:
        log_and_queue(f"Action: UV/Freeze audit failed: {str(e)}", logging.ERROR)


def start_https_server():
    """Start HTTPS server on localhost using existing certs."""
    log_and_queue(f"HTTPS Server: Attempting to use cert: {CERT_FILE}")
    log_and_queue(f"HTTPS Server: Attempting to use key: {KEY_FILE}")

    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        log_and_queue(f"HTTPS Server: Error - Certificate ({CERT_FILE}) or Key ({KEY_FILE}) not found.", logging.ERROR)
        log_and_queue("HTTPS Server: Ensure nginx/ssl/kpkapp.lan.pem and nginx/ssl/kpkapp.lan.key exist.", logging.ERROR)
        log_and_queue("HTTPS Server: Server startup aborted.", logging.ERROR)
        return

    try:
        server_address = (HTTPS_HOST, HTTP_PORT)
        httpd = HTTPServer(server_address, RestartHandler)

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

        log_and_queue(f"HTTPS Server: Started successfully on https://{HTTPS_HOST}:{HTTP_PORT}")
        httpd.serve_forever()
    except FileNotFoundError:
        log_and_queue(f"HTTPS Server: Error - Cert/Key files disappeared before loading.", logging.ERROR)
    except ssl.SSLError as e:
        log_and_queue(f"HTTPS Server: SSL Error - {str(e)}.", logging.ERROR)
    except OSError as e:
        log_and_queue(f"HTTPS Server: OS Error (maybe port {HTTP_PORT} is already in use?) - {str(e)}", logging.ERROR)
    except Exception as e:
        log_and_queue(f"HTTPS Server: Unexpected error starting - {str(e)}", logging.ERROR)


def check_email():
    """Check Gmail for restart commands from authorized senders."""
    try:
        mail = imaplib.IMAP4_SSL(GMAIL_SERVER, GMAIL_PORT)
        mail.login(os.getenv('NOTIF_EMAIL_ADDRESS'), os.getenv('NOTIF_PW'))
        log_and_queue("Email: Connected to Gmail", logging.DEBUG)

        mail.select('inbox')
        _, messages = mail.search(None, 'UNSEEN')

        if not messages[0]:
            log_and_queue("Email: No new unread messages", logging.DEBUG)
        else:
            log_and_queue(f"Email: Found {len(messages[0].split())} unread message(s)")

        for num in messages[0].split():
            try:
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                message = email.message_from_bytes(email_body)

                from_header = message['from']
                realname, sender_email = email.utils.parseaddr(from_header)

                if sender_email.lower() in [auth.lower() for auth in AUTHORIZED_SENDERS]:
                    subject_header = message['subject']
                    decoded_subject = ''
                    for part, encoding in email.header.decode_header(subject_header):
                        if isinstance(part, bytes):
                            decoded_subject += part.decode(encoding or 'utf-8')
                        else:
                            decoded_subject += part

                    content = ''
                    if message.is_multipart():
                        for part in message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    content = part.get_payload(decode=True).decode()
                                    break
                                except Exception as decode_err:
                                    log_and_queue(f"Email: Could not decode part from {sender_email}: {decode_err}", logging.WARNING)
                    else:
                        if message.get_content_type() == "text/plain":
                            try:
                                content = message.get_payload(decode=True).decode()
                            except Exception as decode_err:
                                log_and_queue(f"Email: Could not decode payload from {sender_email}: {decode_err}", logging.WARNING)

                    if COMMAND_PHRASE.lower() in content.lower() or \
                       COMMAND_PHRASE.lower() in decoded_subject.lower():
                        log_and_queue(f"Email: Valid restart command received from {sender_email} (Subject: '{decoded_subject}')")
                        execute_restart()
                    else:
                        log_and_queue(f"Email: Authorized email from {sender_email} received, but no command phrase found.", logging.DEBUG)
                else:
                    log_and_queue(f"Email: Unauthorized email received from {sender_email}. Ignoring.", logging.WARNING)

                mail.store(num, '+FLAGS', '\\Seen')

            except Exception as e:
                log_and_queue(f"Email: Error processing message {num}: {str(e)}", logging.ERROR)
                continue

        mail.close()
        mail.logout()
        log_and_queue("Email: Logged out from Gmail", logging.DEBUG)

    except imaplib.IMAP4.abort as e:
        log_and_queue(f"Email: IMAP connection aborted: {str(e)}. Retrying later.", logging.ERROR)
        time.sleep(30)
    except Exception as e:
        log_and_queue(f"Email: Error in email checking: {str(e)}", logging.ERROR)
        time.sleep(60)


def email_monitor_thread():
    """Background thread for email monitoring."""
    log_and_queue("Service: Email monitor thread started.")
    while True:
        check_email()
        time.sleep(60)


def looper_status_monitor_thread():
    """Background thread for looper status monitoring."""
    log_and_queue(f"Service: Looper status monitor thread started. Checking {LOOPER_STATUS_URL} every {STATUS_CHECK_INTERVAL_SECONDS} seconds.")
    while True:
        check_looper_status()
        time.sleep(STATUS_CHECK_INTERVAL_SECONDS)


def check_looper_status():
    """Check the status of the data looper via its HTTPS endpoint."""
    log_and_queue(f"Status Check: Querying {LOOPER_STATUS_URL}", logging.DEBUG)
    try:
        response = requests.get(LOOPER_STATUS_URL, timeout=10, verify=False)
        response.raise_for_status()

        try:
            data = response.json()
            status = data.get('status')
            if status == 'down':
                log_and_queue(f"Status Check: Detected looper status is 'down'. Triggering restart.", logging.WARNING)
                execute_restart()
            elif status == 'up':
                log_and_queue(f"Status Check: Looper status is 'up'.", logging.INFO)
            else:
                log_and_queue(f"Status Check: Received unexpected status value: {status}", logging.WARNING)

        except json.JSONDecodeError:
            log_and_queue(f"Status Check: Failed to decode JSON response from {LOOPER_STATUS_URL}", logging.ERROR)
        except Exception as e:
            log_and_queue(f"Status Check: Error processing response data: {str(e)}", logging.ERROR)

    except requests.exceptions.Timeout:
        log_and_queue(f"Status Check: Request timed out connecting to {LOOPER_STATUS_URL}", logging.ERROR)
    except requests.exceptions.ConnectionError:
        log_and_queue(f"Status Check: Could not connect to {LOOPER_STATUS_URL}. Is the server running?", logging.ERROR)
    except requests.exceptions.RequestException as e:
        log_and_queue(f"Status Check: Error during request to {LOOPER_STATUS_URL}: {str(e)}", logging.ERROR)
        if isinstance(e, requests.exceptions.SSLError):
            log_and_queue("Status Check: SSL Error occurred. Note: Certificate verification is disabled (verify=False).", logging.WARNING)


# =============================================================================
# Alert Monitoring System
# =============================================================================

# --- Alert Configuration Paths ---
ALERT_CONFIG_PATH = os.path.join(HOST_SERVICES_ROOT, 'config', 'config_looper_health.json')
ALERT_STATE_PATH = os.path.join(HOST_SERVICES_ROOT, 'config', 'alert_state.json')


@dataclass
class Alert:
    """Represents an alert to be sent."""
    rule_name: str
    description: str
    severity: str
    source: str
    match_count: int
    threshold: int
    window_seconds: int
    origin: str = field(default_factory=lambda: ALERT_ORIGIN)
    sample_matches: list = field(default_factory=list)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    remediation_attempted: Optional[str] = None  # Description of auto-fix action taken
    remediation_success: Optional[bool] = None   # Whether auto-fix succeeded


class AlertConfig:
    """Loads and validates config_looper_health.json configuration."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.rules = []
        self.log_sources = {}
        self.scan_interval = 30
        self.webhook_url = None
        self.default_cooldown = 300
        self.critical_containers = []
        self.container_check_cooldown = 300
        self.critical_host_services = []
        self.host_service_check_cooldown = 300
        self.load()

    def load(self):
        """Load config from JSON file, validate schema."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.scan_interval = config.get('scan_interval_seconds', 30)
            self.default_cooldown = config.get('default_cooldown_seconds', 300)

            # Load webhook URL from environment
            webhook_env_var = config.get('teams_webhook_env_var', 'TEAMS_WEBHOOK_URL')
            self.webhook_url = os.getenv(webhook_env_var)

            # Load log sources with path resolution
            self.log_sources = {}
            for name, source_config in config.get('log_sources', {}).items():
                if source_config.get('type') == 'file':
                    # Resolve relative paths to HOST_SERVICES_ROOT
                    source_config['path'] = os.path.join(
                        HOST_SERVICES_ROOT,
                        source_config['path']
                    )
                self.log_sources[name] = source_config

            # Load rules
            self.rules = config.get('rules', [])

            # Load critical containers for health checks
            self.critical_containers = config.get('critical_containers', [])
            self.container_check_cooldown = config.get('container_check_cooldown_seconds', 300)

            # Load critical host services for health checks
            self.critical_host_services = config.get('critical_host_services', [])
            self.host_service_check_cooldown = config.get('host_service_check_cooldown_seconds', 300)

            log_and_queue(f"Alert Config: Loaded {len(self.rules)} rules, {len(self.log_sources)} sources, {len(self.critical_containers)} containers, {len(self.critical_host_services)} host services")

        except FileNotFoundError:
            log_and_queue(f"Alert Config: Config file not found at {self.config_path}", logging.WARNING)
            raise
        except json.JSONDecodeError as e:
            log_and_queue(f"Alert Config: Invalid JSON in config file: {e}", logging.ERROR)
            raise
        except Exception as e:
            log_and_queue(f"Alert Config: Error loading config: {e}", logging.ERROR)
            raise


class AlertStateManager:
    """Persists and loads scan state to survive restarts."""

    def __init__(self, state_path: str):
        self.state_path = state_path
        self.state = self._load_or_create()
        self._lock = threading.Lock()

    def _load_or_create(self) -> dict:
        """Load state from file or create new."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                log_and_queue(f"Alert State: Could not load state file, creating new: {e}", logging.WARNING)

        return {
            'version': '1.0',
            'last_updated': None,
            'scan_positions': {},
            'alert_history': {}
        }

    def save(self):
        """Persist state to disk (thread-safe)."""
        with self._lock:
            self.state['last_updated'] = datetime.datetime.now().isoformat()
            try:
                # Ensure config directory exists
                os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
                with open(self.state_path, 'w', encoding='utf-8') as f:
                    json.dump(self.state, f, indent=2, default=str)
            except IOError as e:
                log_and_queue(f"Alert State: Failed to save state: {e}", logging.ERROR)

    def get_scan_position(self, source_name: str) -> dict:
        """Get last scan position for a source."""
        return self.state['scan_positions'].get(source_name, {})

    def set_scan_position(self, source_name: str, position: dict):
        """Update scan position for a source."""
        with self._lock:
            self.state['scan_positions'][source_name] = position

    def get_alert_history(self, rule_name: str) -> dict:
        """Get alert history for a rule."""
        return self.state['alert_history'].get(rule_name, {
            'last_alert_sent': None,
            'recent_matches': []
        })

    def update_alert_history(self, rule_name: str, history: dict):
        """Update alert history for a rule."""
        with self._lock:
            self.state['alert_history'][rule_name] = history

    def get_container_alert_time(self, container_name: str) -> Optional[str]:
        """Get last alert time for a container health check."""
        return self.state.get('container_alerts', {}).get(container_name)

    def set_container_alert_time(self, container_name: str, time_str: str):
        """Set last alert time for a container health check."""
        with self._lock:
            if 'container_alerts' not in self.state:
                self.state['container_alerts'] = {}
            self.state['container_alerts'][container_name] = time_str

    def get_host_service_alert_time(self, service_name: str) -> Optional[str]:
        """Get last alert time for a host service health check."""
        return self.state.get('host_service_alerts', {}).get(service_name)

    def set_host_service_alert_time(self, service_name: str, time_str: str):
        """Set last alert time for a host service health check."""
        with self._lock:
            if 'host_service_alerts' not in self.state:
                self.state['host_service_alerts'] = {}
            self.state['host_service_alerts'][service_name] = time_str


class ContainerHealthChecker:
    """Checks if critical containers are running and attempts auto-restart."""

    def __init__(self, config: 'AlertConfig', state_manager: AlertStateManager, notifier: Optional['TeamsNotifier']):
        self.config = config
        self.state_manager = state_manager
        self.notifier = notifier

    def check_containers(self) -> list:
        """Check all critical containers and return alerts for any not running.

        If a container is down, attempts to restart it and reports the outcome.
        Cooldown only affects Teams notification, not the restart attempt.
        """
        alerts = []
        now = datetime.datetime.now()

        for container in self.config.critical_containers:
            # Check if container is running
            is_running, status = self._check_container_status(container)

            if not is_running:
                log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Container '{container}' is NOT running (status: {status})", logging.ERROR)

                # Attempt to restart the container
                restart_success, restart_msg = self._attempt_container_start(container)

                # Determine final severity based on restart outcome
                if restart_success:
                    severity = 'warning'  # Downgrade since we fixed it
                    description = f'Container was down, auto-restarted: {container}'
                    log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Successfully restarted container '{container}'", logging.INFO)
                else:
                    severity = 'critical'
                    description = f'Container down, auto-restart FAILED: {container}'
                    log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Failed to restart container '{container}': {restart_msg}", logging.ERROR)

                # Check cooldown - only affects whether we send Teams notification
                in_cooldown = False
                last_alert = self.state_manager.get_container_alert_time(container)
                if last_alert:
                    last_alert_time = datetime.datetime.fromisoformat(last_alert)
                    if (now - last_alert_time).total_seconds() < self.config.container_check_cooldown:
                        in_cooldown = True
                        log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Suppressing Teams notification for '{container}' (cooldown)", logging.DEBUG)

                if not in_cooldown:
                    alert = Alert(
                        rule_name='container_not_running',
                        description=description,
                        severity=severity,
                        source=container,
                        match_count=1,
                        threshold=1,
                        window_seconds=0,
                        sample_matches=[f"Container status: {status}"],
                        timestamp=now,
                        remediation_attempted=f"docker start {container}",
                        remediation_success=restart_success
                    )
                    alerts.append(alert)

                    # Record alert time only when we actually send
                    self.state_manager.set_container_alert_time(container, now.isoformat())

        return alerts

    def _attempt_container_start(self, container: str) -> tuple:
        """Attempt to start a container. Returns (success: bool, message: str)."""
        try:
            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            result = subprocess.run(
                ['docker', 'start', container],
                capture_output=True,
                text=True,
                timeout=60,  # Give docker more time to start
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                # Verify it actually started
                time.sleep(2)  # Brief wait for container to initialize
                is_running, status = self._check_container_status(container)
                if is_running:
                    return True, f"Container started successfully"
                else:
                    return False, f"docker start succeeded but container status is: {status}"
            else:
                return False, f"docker start failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return False, "docker start command timed out"
        except FileNotFoundError:
            return False, "docker not found in PATH"
        except Exception as e:
            return False, f"error: {str(e)[:100]}"

    def _check_container_status(self, container: str) -> tuple:
        """Check if a container is running. Returns (is_running, status_string)."""
        try:
            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            result = subprocess.run(
                ['docker', 'inspect', '--format', '{{.State.Status}}', container],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode != 0:
                if 'No such object' in result.stderr or 'Error' in result.stderr:
                    return False, 'not found'
                return False, f'error: {result.stderr[:100]}'

            status = result.stdout.strip().lower()
            is_running = status == 'running'
            return is_running, status

        except subprocess.TimeoutExpired:
            return False, 'timeout checking status'
        except FileNotFoundError:
            log_and_queue("Alert Monitor: Docker not found in PATH", logging.ERROR)
            return True, 'docker not available'  # Don't alert if docker CLI isn't available
        except Exception as e:
            return False, f'error: {str(e)[:100]}'


class HostServiceHealthChecker:
    """Checks if critical host services (Python processes) are running and attempts auto-restart.

    Also detects and terminates duplicate process instances ("Looper mode"),
    keeping only the oldest instance of each service.
    """

    def __init__(self, config: 'AlertConfig', state_manager: AlertStateManager, notifier: Optional['TeamsNotifier']):
        self.config = config
        self.state_manager = state_manager
        self.notifier = notifier

    def check_services(self) -> list:
        """Check all critical host services and return alerts for any not running.

        First runs "Looper mode" to detect and kill duplicate instances,
        then checks if services are down and attempts restart if needed.
        Cooldown only affects Teams notification, not the restart attempt.
        """
        alerts = []
        now = datetime.datetime.now()

        # Looper mode: detect and terminate duplicate instances
        for service in self.config.critical_host_services:
            process_pattern = service['process_pattern']
            display_name = service.get('display_name', service['name'])
            looped_count = self._loop_duplicates(process_pattern, display_name)
            if looped_count > 0:
                log_and_queue(f"Looper [{ALERT_ORIGIN}]: Terminated {looped_count} duplicate {display_name} process(es)", logging.WARNING)

        # Now check if services are running (after cleaning up duplicates)
        for service in self.config.critical_host_services:
            service_name = service['name']
            display_name = service.get('display_name', service_name)
            process_pattern = service['process_pattern']
            script_path = os.path.join(KPK_APP_ROOT, service['script'])

            # Check if service is running
            is_running = self._is_service_running(process_pattern)

            if not is_running:
                log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Host service '{display_name}' is NOT running", logging.ERROR)

                # Attempt to restart the service
                restart_success, restart_msg = self._attempt_service_start(script_path, service_name)

                # Determine final severity based on restart outcome
                if restart_success:
                    severity = 'warning'  # Downgrade since we fixed it
                    description = f'Host service was down, auto-restarted: {display_name}'
                    log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Successfully restarted host service '{display_name}'", logging.INFO)
                else:
                    severity = 'critical'
                    description = f'Host service down, auto-restart FAILED: {display_name}'
                    log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Failed to restart host service '{display_name}': {restart_msg}", logging.ERROR)

                # Check cooldown - only affects whether we send Teams notification
                in_cooldown = False
                last_alert = self.state_manager.get_host_service_alert_time(service_name)
                if last_alert:
                    last_alert_time = datetime.datetime.fromisoformat(last_alert)
                    if (now - last_alert_time).total_seconds() < self.config.host_service_check_cooldown:
                        in_cooldown = True
                        log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Suppressing Teams notification for '{display_name}' (cooldown)", logging.DEBUG)

                if not in_cooldown:
                    alert = Alert(
                        rule_name='host_service_not_running',
                        description=description,
                        severity=severity,
                        source=display_name,
                        match_count=1,
                        threshold=1,
                        window_seconds=0,
                        sample_matches=[f"Process pattern: {process_pattern}"],
                        timestamp=now,
                        remediation_attempted=f"pythonw {service['script']}",
                        remediation_success=restart_success
                    )
                    alerts.append(alert)

                    # Record alert time only when we actually send
                    self.state_manager.set_host_service_alert_time(service_name, now.isoformat())

        return alerts

    def _is_service_running(self, process_pattern: str) -> bool:
        """Check if a host service is running by looking for its process pattern."""
        try:
            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            result = subprocess.run(
                ['powershell', '-Command',
                 f"wmic process where \"name like '%python%' and commandline like '%{process_pattern}%'\" get ProcessId /format:csv 2>$null | Select-String '\\d+' | ForEach-Object {{ ($_ -split ',')[-1].Trim() }}"],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # If we got any PIDs, it's running
            pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip().isdigit()]
            return len(pids) > 0
        except Exception:
            return False

    def _get_process_instances(self, process_pattern: str) -> list:
        """Get all process instances matching pattern with their PIDs and creation times.

        Returns list of tuples: [(pid, creation_time_str), ...] sorted by creation time (oldest first).
        """
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            # Get PIDs and CreationDates for matching processes
            result = subprocess.run(
                ['wmic', 'process', 'where',
                 f"name like '%python%' and commandline like '%{process_pattern}%'",
                 'get', 'ProcessId,CreationDate', '/format:csv'],
                capture_output=True,
                text=True,
                timeout=15,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode != 0:
                return []

            instances = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('Node'):
                    continue
                # Format: HOSTNAME,CreationDate,ProcessId
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        creation_date = parts[1].strip()
                        pid = parts[2].strip()
                        if pid.isdigit() and creation_date:
                            instances.append((pid, creation_date))
                    except (IndexError, ValueError):
                        continue

            # Sort by creation date (oldest first) - wmic format: 20260106112122.277742-360
            instances.sort(key=lambda x: x[1])
            return instances

        except subprocess.TimeoutExpired:
            log_and_queue(f"Looper: Timeout getting process instances for {process_pattern}", logging.WARNING)
            return []
        except Exception as e:
            log_and_queue(f"Looper: Error getting process instances: {e}", logging.ERROR)
            return []

    def _loop_duplicates(self, process_pattern: str, display_name: str) -> int:
        """Detect and terminate duplicate process instances (Looper mode).

        Keeps the oldest instance (by CreationDate) and kills all newer duplicates.
        Named after the 2012 film where Bruce Willis terminates his younger self.

        Returns: Number of duplicate processes terminated.
        """
        instances = self._get_process_instances(process_pattern)

        if len(instances) <= 1:
            # No duplicates to loop
            return 0

        # Keep the oldest (first in sorted list), terminate the rest
        keeper_pid, keeper_time = instances[0]
        duplicates = instances[1:]

        killed_count = 0
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        for dup_pid, dup_time in duplicates:
            try:
                log_and_queue(
                    f"Looper [{ALERT_ORIGIN}]: Terminating duplicate {display_name} "
                    f"(PID {dup_pid}, created {dup_time}). Keeping PID {keeper_pid}.",
                    logging.WARNING
                )
                result = subprocess.run(
                    ['taskkill', '/PID', dup_pid, '/F'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    killed_count += 1
                else:
                    log_and_queue(
                        f"Looper [{ALERT_ORIGIN}]: Failed to terminate PID {dup_pid}: {result.stderr[:100]}",
                        logging.ERROR
                    )
            except subprocess.TimeoutExpired:
                log_and_queue(f"Looper [{ALERT_ORIGIN}]: Timeout terminating PID {dup_pid}", logging.ERROR)
            except Exception as e:
                log_and_queue(f"Looper [{ALERT_ORIGIN}]: Error terminating PID {dup_pid}: {e}", logging.ERROR)

        return killed_count

    def _attempt_service_start(self, script_path: str, service_name: str) -> tuple:
        """Attempt to start a host service. Returns (success: bool, message: str)."""
        try:
            if not os.path.exists(script_path):
                return False, f"Script not found: {script_path}"

            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            # Start with pythonw (no console window)
            process = subprocess.Popen(
                ['pythonw', script_path],
                cwd=KPK_APP_ROOT,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Wait briefly and verify it started
            time.sleep(3)

            # Get the process pattern from the script name
            process_pattern = os.path.basename(script_path).replace('.py', '')
            is_running = self._is_service_running(process_pattern)

            if is_running:
                return True, f"Service started successfully (PID: {process.pid})"
            else:
                return False, f"Process started but not found running after 3s"

        except FileNotFoundError:
            return False, "pythonw not found in PATH"
        except Exception as e:
            return False, f"error: {str(e)[:100]}"


class Remediator:
    """Executes remediation actions for log-based alert rules."""

    def __init__(self, config: 'AlertConfig'):
        self.config = config

    def execute(self, remediation_config: dict, alert_context: dict) -> tuple:
        """Execute a remediation action. Returns (success: bool, message: str)."""
        action = remediation_config.get('action')

        if action == 'restart_host_service':
            return self._restart_host_service(remediation_config)
        elif action == 'restart_container':
            return self._restart_container(remediation_config)
        else:
            return False, f"Unknown remediation action: {action}"

    def _restart_host_service(self, remediation_config: dict) -> tuple:
        """Terminate and restart a host service (like data_sync)."""
        service_name = remediation_config.get('service')
        if not service_name:
            return False, "No service specified in remediation config"

        # Find service config
        service_config = None
        for svc in self.config.critical_host_services:
            if svc['name'] == service_name:
                service_config = svc
                break

        # Special handling for data_sync since it may not be in critical_host_services
        if not service_config and service_name == 'data_sync':
            service_config = {
                'name': 'data_sync',
                'display_name': 'Data Sync',
                'script': 'host-services/workers/data_sync.py',
                'process_pattern': 'data_sync'
            }

        if not service_config:
            return False, f"Service '{service_name}' not found in config"

        process_pattern = service_config['process_pattern']
        script_path = os.path.join(KPK_APP_ROOT, service_config['script'])
        display_name = service_config.get('display_name', service_name)

        log_and_queue(f"Remediator: Attempting to restart {display_name}", logging.WARNING)

        # Step 1: Terminate existing process
        try:
            terminate_success = self._terminate_process(process_pattern)
            if terminate_success:
                log_and_queue(f"Remediator: Terminated existing {display_name} process", logging.INFO)
            else:
                log_and_queue(f"Remediator: No existing {display_name} process found to terminate", logging.INFO)
        except Exception as e:
            log_and_queue(f"Remediator: Error terminating {display_name}: {e}", logging.ERROR)

        # Step 2: Wait briefly for cleanup
        time.sleep(2)

        # Step 3: Start new process
        try:
            if not os.path.exists(script_path):
                return False, f"Script not found: {script_path}"

            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            process = subprocess.Popen(
                ['pythonw', script_path],
                cwd=KPK_APP_ROOT,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Wait and verify it started
            time.sleep(3)

            # Check if running
            startupinfo2 = subprocess.STARTUPINFO()
            startupinfo2.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo2.wShowWindow = 0

            result = subprocess.run(
                ['powershell', '-Command',
                 f"wmic process where \"name like '%python%' and commandline like '%{process_pattern}%'\" get ProcessId /format:csv 2>$null | Select-String '\\d+' | ForEach-Object {{ ($_ -split ',')[-1].Trim() }}"],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo2,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip().isdigit()]

            if len(pids) > 0:
                log_and_queue(f"Remediator: Successfully restarted {display_name} (PID: {pids[0]})", logging.INFO)
                return True, f"Restarted {display_name}"
            else:
                return False, f"Process started but not found running after 3s"

        except FileNotFoundError:
            return False, "pythonw not found in PATH"
        except Exception as e:
            return False, f"Error starting service: {str(e)[:100]}"

    def _terminate_process(self, process_pattern: str) -> bool:
        """Terminate processes matching the pattern. Returns True if any were terminated."""
        try:
            # Hide console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            # Find PIDs
            result = subprocess.run(
                ['powershell', '-Command',
                 f"wmic process where \"name like '%python%' and commandline like '%{process_pattern}%'\" get ProcessId /format:csv 2>$null | Select-String '\\d+' | ForEach-Object {{ ($_ -split ',')[-1].Trim() }}"],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip().isdigit()]

            if not pids:
                return False

            # Terminate each PID
            for pid in pids:
                subprocess.run(
                    ['taskkill', '/PID', pid, '/F'],
                    capture_output=True,
                    timeout=10,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

            return True

        except Exception as e:
            log_and_queue(f"Remediator: Error terminating process: {e}", logging.ERROR)
            return False

    def _restart_container(self, remediation_config: dict) -> tuple:
        """Restart a Docker container."""
        container = remediation_config.get('container')
        if not container:
            return False, "No container specified in remediation config"

        try:
            # Hide console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

            # Restart the container
            result = subprocess.run(
                ['docker', 'restart', container],
                capture_output=True,
                text=True,
                timeout=60,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                log_and_queue(f"Remediator: Successfully restarted container {container}", logging.INFO)
                return True, f"Restarted container {container}"
            else:
                return False, f"docker restart failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return False, "docker restart timed out"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"


class LogScanner(ABC):
    """Base class for scanning log sources."""

    def __init__(self, source_name: str, source_config: dict, state_manager: AlertStateManager):
        self.source_name = source_name
        self.config = source_config
        self.state_manager = state_manager

    @abstractmethod
    def get_new_lines(self) -> list:
        """Return new log lines since last scan as list of (timestamp, line) tuples."""
        pass

    def _parse_timestamp(self, line: str) -> Optional[datetime.datetime]:
        """Extract timestamp from log line. Returns None if not found."""
        # Match common log formats:
        # "2025-12-03 13:37:26" or "2025-12-03 13:37:26,149"
        patterns = [
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+',  # With milliseconds
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',       # Without milliseconds
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    return datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
        return None


class FileLogScanner(LogScanner):
    """Scans file-based logs (host services)."""

    def get_new_lines(self) -> list:
        """Read from saved byte offset to current EOF."""
        file_path = self.config['path']
        results = []

        if not os.path.exists(file_path):
            return results

        try:
            saved_state = self.state_manager.get_scan_position(self.source_name)
            saved_offset = saved_state.get('byte_offset', 0)

            # Check for log rotation
            current_size = os.path.getsize(file_path)
            if current_size < saved_offset:
                # File was truncated/rotated, start from beginning
                log_and_queue(f"Alert Scanner: Log rotation detected for {self.source_name}", logging.DEBUG)
                saved_offset = 0

            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(saved_offset)
                new_content = f.read()
                new_offset = f.tell()

            # Parse lines
            for line in new_content.splitlines():
                line = line.strip()
                if line:
                    timestamp = self._parse_timestamp(line)
                    if timestamp is None:
                        timestamp = datetime.datetime.now()
                    results.append((timestamp, line))

            # Update state
            self.state_manager.set_scan_position(self.source_name, {
                'type': 'file',
                'byte_offset': new_offset,
                'last_scan': datetime.datetime.now().isoformat()
            })

        except Exception as e:
            log_and_queue(f"Alert Scanner: Error reading {self.source_name}: {e}", logging.ERROR)

        return results


class DockerLogScanner(LogScanner):
    """Scans Docker container logs via subprocess."""

    def get_new_lines(self) -> list:
        """Run docker logs command and return new lines."""
        container = self.config['container']
        tail_lines = self.config.get('tail_lines', 100)
        results = []

        try:
            saved_state = self.state_manager.get_scan_position(self.source_name)
            last_timestamp = saved_state.get('last_log_timestamp')

            # Build docker command
            cmd = ['docker', 'logs', '--tail', str(tail_lines), '--timestamps', container]

            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode != 0:
                # Container might not exist or Docker not running
                if 'No such container' not in result.stderr:
                    log_and_queue(f"Alert Scanner: Docker error for {self.source_name}: {result.stderr[:200]}", logging.DEBUG)
                return results

            # Parse output (stdout and stderr, as docker logs outputs to both)
            output = result.stdout + result.stderr
            newest_timestamp = last_timestamp

            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Docker log format: "2025-12-03T13:37:26.123456789Z message"
                timestamp = self._parse_docker_timestamp(line)

                if timestamp:
                    ts_str = timestamp.isoformat()
                    # Skip lines we've already seen
                    if last_timestamp and ts_str <= last_timestamp:
                        continue

                    # Track newest timestamp
                    if newest_timestamp is None or ts_str > newest_timestamp:
                        newest_timestamp = ts_str

                    # Remove timestamp prefix from line for pattern matching
                    line_content = re.sub(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s*', '', line)
                    results.append((timestamp, line_content))
                else:
                    results.append((datetime.datetime.utcnow(), line))  # Use UTC to match Docker timestamps

            # Update state
            if newest_timestamp:
                self.state_manager.set_scan_position(self.source_name, {
                    'type': 'docker',
                    'last_log_timestamp': newest_timestamp,
                    'last_scan': datetime.datetime.now().isoformat()
                })

        except subprocess.TimeoutExpired:
            log_and_queue(f"Alert Scanner: Docker command timed out for {self.source_name}", logging.WARNING)
        except FileNotFoundError:
            log_and_queue(f"Alert Scanner: Docker not found in PATH", logging.ERROR)
        except Exception as e:
            log_and_queue(f"Alert Scanner: Error scanning {self.source_name}: {e}", logging.ERROR)

        return results

    def _parse_docker_timestamp(self, line: str) -> Optional[datetime.datetime]:
        """Parse Docker timestamp format."""
        # Docker format: "2025-12-03T13:37:26.123456789Z"
        match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
        if match:
            try:
                return datetime.datetime.fromisoformat(match.group(1))
            except ValueError:
                pass
        return None


class AlertEngine:
    """Pattern matching, threshold tracking, deduplication."""

    def __init__(self, config: AlertConfig, state_manager: AlertStateManager, remediator: Optional[Remediator] = None):
        self.config = config
        self.state_manager = state_manager
        self.remediator = remediator
        self.compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        for rule in self.config.rules:
            try:
                self.compiled_patterns[rule['name']] = re.compile(
                    rule['pattern'],
                    re.IGNORECASE
                )
            except re.error as e:
                log_and_queue(f"Alert Engine: Invalid regex in rule '{rule['name']}': {e}", logging.ERROR)

    def process_lines(self, source_name: str, lines: list) -> list:
        """Match lines against rules for this source. Return alerts to fire."""
        alerts = []
        now = datetime.datetime.utcnow()  # Use UTC to match Docker log timestamps

        for rule in self.config.rules:
            if not rule.get('enabled', True):
                continue
            if source_name not in rule.get('sources', []):
                continue
            if rule['name'] not in self.compiled_patterns:
                continue

            pattern = self.compiled_patterns[rule['name']]
            history = self.state_manager.get_alert_history(rule['name'])
            recent_matches = history.get('recent_matches', [])

            # Find matches in new lines
            for timestamp, line in lines:
                if pattern.search(line):
                    recent_matches.append({
                        'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else timestamp,
                        'line': line[:500]  # Truncate long lines
                    })

            # Prune matches outside the threshold window
            window_seconds = rule.get('threshold_window_seconds', 300)
            cutoff = now - datetime.timedelta(seconds=window_seconds)
            recent_matches = [
                m for m in recent_matches
                if datetime.datetime.fromisoformat(m['timestamp']) > cutoff
            ]

            # Check if threshold exceeded
            threshold_count = rule.get('threshold_count', 1)
            if len(recent_matches) >= threshold_count:
                # Check cooldown
                cooldown_seconds = rule.get('cooldown_seconds', self.config.default_cooldown)
                last_alert = history.get('last_alert_sent')

                in_cooldown = False
                if last_alert:
                    last_alert_time = datetime.datetime.fromisoformat(last_alert)
                    if (now - last_alert_time).total_seconds() < cooldown_seconds:
                        in_cooldown = True

                if not in_cooldown:
                    # Check for remediation config
                    remediation_attempted = None
                    remediation_success = None
                    remediation_config = rule.get('remediation')

                    if remediation_config and self.remediator:
                        # Execute remediation before creating alert
                        action = remediation_config.get('action', 'unknown')
                        service = remediation_config.get('service', remediation_config.get('container', 'unknown'))
                        remediation_attempted = f"{action}: {service}"

                        log_and_queue(f"Alert Engine: Rule '{rule['name']}' triggered remediation: {action}", logging.WARNING)

                        success, message = self.remediator.execute(
                            remediation_config,
                            {'rule_name': rule['name'], 'source': source_name}
                        )
                        remediation_success = success

                        if success:
                            log_and_queue(f"Alert Engine: Remediation succeeded: {message}", logging.INFO)
                        else:
                            log_and_queue(f"Alert Engine: Remediation failed: {message}", logging.ERROR)

                    # Create alert
                    alert = Alert(
                        rule_name=rule['name'],
                        description=rule.get('description', rule['name']),
                        severity=rule.get('severity', 'warning') if not remediation_success else 'warning',
                        source=source_name,
                        match_count=len(recent_matches),
                        threshold=threshold_count,
                        window_seconds=window_seconds,
                        sample_matches=[m['line'] for m in recent_matches[-5:]],
                        timestamp=now,
                        remediation_attempted=remediation_attempted,
                        remediation_success=remediation_success
                    )
                    alerts.append(alert)

                    # Update last alert sent time
                    history['last_alert_sent'] = now.isoformat()

            # Save updated history
            history['recent_matches'] = recent_matches[-100:]  # Keep last 100 matches
            self.state_manager.update_alert_history(rule['name'], history)

        return alerts


class TeamsNotifier:
    """Sends alerts to Microsoft Teams via Workflow webhook."""

    SEVERITY_COLORS = {
        'info': 'Default',
        'warning': 'Warning',
        'error': 'Attention',
        'critical': 'Attention'
    }

    SEVERITY_EMOJI = {
        'info': 'information_source',
        'warning': 'warning',
        'error': 'x',
        'critical': 'rotating_light'
    }

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, alert: Alert) -> bool:
        """Send alert to Teams using Adaptive Card format."""
        card = self._build_adaptive_card(alert)
        try:
            response = requests.post(
                self.webhook_url,
                json=card,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            if response.status_code in (200, 202):
                log_and_queue(f"Alert Notifier: Sent '{alert.rule_name}' alert to Teams")
                return True
            else:
                log_and_queue(f"Alert Notifier: Teams returned status {response.status_code}: {response.text[:200]}", logging.ERROR)
                return False
        except requests.exceptions.Timeout:
            log_and_queue(f"Alert Notifier: Timeout sending to Teams", logging.ERROR)
            return False
        except Exception as e:
            log_and_queue(f"Alert Notifier: Failed to send Teams notification: {e}", logging.ERROR)
            return False

    def _build_adaptive_card(self, alert: Alert) -> dict:
        """Build Microsoft Teams Adaptive Card payload for Workflows."""
        severity_color = self.SEVERITY_COLORS.get(alert.severity, 'Default')

        # Format sample matches for display (500 chars to show full file paths/errors)
        sample_text = "\n".join(f"- {line[:500]}" for line in alert.sample_matches[-3:])
        if not sample_text:
            sample_text = "(no sample lines available)"

        # Build facts list
        facts = [
            {"title": "Origin", "value": alert.origin},
            {"title": "Rule", "value": alert.rule_name},
            {"title": "Source", "value": alert.source},
            {"title": "Matches", "value": f"{alert.match_count} in {alert.window_seconds}s (threshold: {alert.threshold})"},
            {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        ]

        # Add remediation info if attempted
        if alert.remediation_attempted:
            if alert.remediation_success:
                facts.append({"title": "Auto-Fix", "value": f"{alert.remediation_attempted}"})
                facts.append({"title": "Status", "value": "RESOLVED"})
            else:
                facts.append({"title": "Auto-Fix", "value": f"{alert.remediation_attempted}"})
                facts.append({"title": "Status", "value": "FAILED - Manual intervention required"})

        # Determine header text and color based on remediation outcome
        if alert.remediation_attempted and alert.remediation_success:
            header_text = f"RESOLVED: {alert.description}"
            header_color = "Good"  # Green in Teams
        else:
            header_text = f"{alert.severity.upper()}: {alert.description}"
            header_color = severity_color

        body = [
            {
                "type": "TextBlock",
                "text": header_text,
                "weight": "Bolder",
                "size": "Large",
                "color": header_color,
                "wrap": True
            },
            {
                "type": "FactSet",
                "facts": facts
            },
            {
                "type": "TextBlock",
                "text": "Details:",
                "weight": "Bolder",
                "separator": True
            },
            {
                "type": "TextBlock",
                "text": sample_text,
                "wrap": True,
                "fontType": "Monospace",
                "size": "Small"
            }
        ]

        return {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body
                }
            }]
        }


def alert_monitor_thread():
    """Background thread for log monitoring and alerting."""
    # Check if config exists
    if not os.path.exists(ALERT_CONFIG_PATH):
        log_and_queue(f"Alert Monitor: Config not found at {ALERT_CONFIG_PATH}. Alert monitoring disabled.", logging.WARNING)
        return

    try:
        config = AlertConfig(ALERT_CONFIG_PATH)
        state_manager = AlertStateManager(ALERT_STATE_PATH)

        # Check webhook URL
        if not config.webhook_url:
            log_and_queue("Alert Monitor: TEAMS_WEBHOOK_URL not set in .env. Teams notifications disabled.", logging.WARNING)
            notifier = None
        else:
            notifier = TeamsNotifier(config.webhook_url)
            log_and_queue("Alert Monitor: Teams notifications enabled.")

        remediator = Remediator(config)
        alert_engine = AlertEngine(config, state_manager, remediator)

        # Build scanners for each source
        scanners = {}
        for source_name, source_config in config.log_sources.items():
            if source_config.get('type') == 'file':
                scanners[source_name] = FileLogScanner(source_name, source_config, state_manager)
            elif source_config.get('type') == 'docker':
                scanners[source_name] = DockerLogScanner(source_name, source_config, state_manager)

        # Container health checker
        container_checker = ContainerHealthChecker(config, state_manager, notifier)

        # Host service health checker
        host_service_checker = HostServiceHealthChecker(config, state_manager, notifier)

        log_and_queue(f"Alert Monitor: Started on {ALERT_ORIGIN}. Scanning {len(scanners)} sources, monitoring {len(config.critical_containers)} containers, {len(config.critical_host_services)} host services every {config.scan_interval}s")

    except Exception as e:
        log_and_queue(f"Alert Monitor: Failed to initialize: {e}", logging.ERROR)
        return

    while True:
        try:
            # Check critical container health
            container_alerts = container_checker.check_containers()
            for alert in container_alerts:
                if notifier:
                    notifier.send_alert(alert)

            # Check critical host service health
            host_service_alerts = host_service_checker.check_services()
            for alert in host_service_alerts:
                if notifier:
                    notifier.send_alert(alert)

            # Scan log sources for pattern matches
            for source_name, scanner in scanners.items():
                try:
                    new_lines = scanner.get_new_lines()
                    if new_lines:
                        alerts = alert_engine.process_lines(source_name, new_lines)
                        for alert in alerts:
                            log_and_queue(f"Alert Monitor [{ALERT_ORIGIN}]: Firing alert '{alert.rule_name}' from {alert.source}", logging.WARNING)
                            if notifier:
                                notifier.send_alert(alert)
                except Exception as e:
                    log_and_queue(f"Alert Monitor: Error scanning {source_name}: {e}", logging.ERROR)

            # Persist state periodically
            state_manager.save()

        except Exception as e:
            log_and_queue(f"Alert Monitor: Scan cycle error: {e}", logging.ERROR)

        time.sleep(config.scan_interval)


def show_status(icon):
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

    log_text = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        state='disabled',
        height=15,
        bg='#ffffff',
        fg='#333333',
        font=text_font,
        relief=tk.SUNKEN,
        bd=1
    )
    log_text.pack(fill=tk.BOTH, expand=True)

    button_frame = tk.Frame(root, bg='#f0f0f0')
    button_frame.pack(pady=(0, 10), padx=10, fill=tk.X)

    close_button = tk.Button(
        button_frame,
        text="Close Window",
        command=root.destroy,
        font=default_font,
        bg='#d9d9d9',
        relief=tk.RAISED,
        bd=1
    )
    close_button.pack(side=tk.RIGHT)

    def update_log_display():
        try:
            while not log_queue.empty():
                message = log_queue.get_nowait()
                log_text.configure(state='normal')
                log_text.insert(tk.END, message + '\n')
                log_text.configure(state='disabled')
                log_text.see(tk.END)
                log_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error updating log display: {e}")
        finally:
            root.after(150, update_log_display)

    log_text.configure(state='normal')
    log_text.insert(tk.END, f"Initializing {SERVICE_NAME} Window...\n")
    log_text.insert(tk.END, f"Monitoring email: {os.getenv('NOTIF_EMAIL_ADDRESS')}\n")
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        log_text.insert(tk.END, f"Listening for HTTPS restart requests on https://{HTTPS_HOST}:{HTTP_PORT}\n")
        log_text.insert(tk.END, f"Using cert: {CERT_FILE}\n")
        log_text.insert(tk.END, f"Using key: {KEY_FILE}\n")
    else:
        log_text.insert(tk.END, f"ERROR: Cert ({CERT_FILE}) or Key ({KEY_FILE}) not found. HTTPS server not started.\n")
    log_text.insert(tk.END, f"Actively monitoring looper status at: {LOOPER_STATUS_URL}\n")
    log_text.insert(tk.END, f"Status check interval: {STATUS_CHECK_INTERVAL_SECONDS} seconds.\n")
    log_text.insert(tk.END, "-------------------------------------\n")
    log_text.configure(state='disabled')

    root.after(100, update_log_display)
    root.eval('tk::PlaceWindow . center')
    root.mainloop()


def create_icon():
    """Create the system tray icon."""
    try:
        image = Image.open(ICON_PATH)
    except FileNotFoundError:
        log_and_queue(f"Icon file not found at {ICON_PATH}. Using default icon.", logging.WARNING)
        image = Image.new('RGB', (64, 64), color='blue')
    except Exception as e:
        log_and_queue(f"Error loading icon: {e}. Using default icon.", logging.ERROR)
        image = Image.new('RGB', (64, 64), color='red')

    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: show_status(icon), default=True),
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    icon = pystray.Icon("looper_health", image, SERVICE_NAME, menu=pystray.Menu(*menu))
    return icon


def exit_application(icon):
    """Stop the service and exit."""
    log_and_queue("Service: Exit command received. Stopping service.")
    icon.stop()
    os._exit(0)


def is_data_sync_running():
    """Check if data_sync is already running.

    Uses wmic which can see processes across all user sessions,
    unlike Get-WmiObject which may only see the current session.
    """
    try:
        # Hide console window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        result = subprocess.run(
            ['powershell', '-Command',
             "wmic process where \"name like '%python%' and commandline like '%data_sync%'\" get ProcessId /format:csv 2>$null | Select-String '\\d+' | ForEach-Object { ($_ -split ',')[-1].Trim() }"],
            capture_output=True,
            text=True,
            timeout=10,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        # If we got any PIDs, it's running
        pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip().isdigit()]
        return len(pids) > 0
    except Exception:
        return False


def main():
    """Main entry point for the Looper Health Watchdog."""
    log_and_queue(f"Service: Starting {SERVICE_NAME}...")

    # Check if data_sync is running, start it if not
    if not is_data_sync_running():
        log_and_queue("Service: data_sync not detected. Starting it now...")
        execute_restart()
    else:
        log_and_queue("Service: data_sync already running.")

    # Start the email monitoring thread
    monitor_thread = threading.Thread(target=email_monitor_thread, daemon=True)
    monitor_thread.start()

    # Start the HTTPS server thread
    https_thread = threading.Thread(target=start_https_server, daemon=True)
    https_thread.start()

    # Start the looper status monitoring thread
    status_monitor_thread = threading.Thread(target=looper_status_monitor_thread, daemon=True)
    status_monitor_thread.start()

    # Start the alert monitoring thread
    alert_thread = threading.Thread(target=alert_monitor_thread, daemon=True)
    alert_thread.start()

    # Create and run the system tray icon
    try:
        icon = create_icon()
        log_and_queue("Service: System tray icon created.")
        icon.run()
    except Exception as e:
        log_and_queue(f"Service: Failed to create or run system tray icon: {e}", logging.ERROR)
        os._exit(1)


if __name__ == "__main__":
    main()
