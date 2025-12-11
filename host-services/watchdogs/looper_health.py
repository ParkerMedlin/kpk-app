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
    """Check if data_sync is already running."""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             "Get-WmiObject Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -like '*data_sync*' } | Select-Object ProcessId"],
            capture_output=True,
            text=True,
            timeout=10
        )
        # If we got output with a ProcessId, it's running
        return 'ProcessId' in result.stdout and result.stdout.strip() != ''
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
