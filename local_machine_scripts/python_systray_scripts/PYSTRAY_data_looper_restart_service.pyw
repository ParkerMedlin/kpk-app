import imaplib
import email
import email.header
import os
import subprocess
import time
import pystray
from PIL import Image
import tkinter as tk
# Add scrolledtext and queue
from tkinter import scrolledtext, font
import queue
import threading
import datetime
import logging
import ssl
from dotenv import load_dotenv
# Add HTTP server imports
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

# Load environment variables
load_dotenv(os.path.expanduser('~\\Documents\\kpk-app\\.env'))

# Configure logging
log_dir = os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_systray_scripts\\pystray_logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'data_looper_restart_service.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
GMAIL_SERVER = "imap.gmail.com"
GMAIL_PORT = 993
AUTHORIZED_SENDERS = [
    "pmedlin@kinpakinc.com",
    "jdavis@kinpakinc.com",
    "ddavis@kinpakinc.com"
]
COMMAND_PHRASE = "restart loop"
BAT_SCRIPT_PATH = "C:\\Users\\pmedlin\\Desktop\\4. Update the database.bat"
HTTP_PORT = 9999  # Port for HTTP server

# Queue for inter-thread communication with Tkinter
log_queue = queue.Queue()

# --- Helper to log and queue messages ---
def log_and_queue(message, level=logging.INFO):
    if level == logging.INFO:
        logging.info(message)
    elif level == logging.WARNING:
        logging.warning(message)
    elif level == logging.ERROR:
        logging.error(message)
    # Add timestamp for display
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_queue.put(f"[{timestamp}] {message}")

# HTTP Server Handler
class RestartHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        client_ip = self.client_address[0]
        if self.path == '/trigger-restart':
            log_and_queue(f"HTTP: Received /trigger-restart from {client_ip}")
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Restart initiated")
            
            # Trigger restart in a separate thread to avoid blocking
            restart_thread = threading.Thread(target=execute_restart)
            restart_thread.daemon = True
            restart_thread.start()
        else:
            log_and_queue(f"HTTP: Received {self.path} from {client_ip} (404 Not Found)", logging.WARNING)
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not found")
    
    # Override log messages to use our custom logger (and queue)
    def log_message(self, format, *args):
        # We handle logging within do_GET now, using log_and_queue
        pass 
        # Original behaviour logged basic requests, we want more specific logs.
        # log_and_queue("HTTP: %s" % (format % args))

def execute_restart():
    """Execute the batch script to restart the data looper"""
    try:
        app_dir = os.path.expanduser('~\\Documents\\kpk-app')
        log_and_queue(f"Action: Attempting to start batch script: {BAT_SCRIPT_PATH}")
        subprocess.Popen([BAT_SCRIPT_PATH],
                      creationflags=subprocess.CREATE_NEW_CONSOLE,
                      cwd=app_dir)
        log_and_queue(f"Action: Successfully launched Popen for batch script.")
    except FileNotFoundError:
         log_and_queue(f"Action: Could not find batch script at: {BAT_SCRIPT_PATH}", logging.ERROR)
    except Exception as e:
        log_and_queue(f"Action: Error starting batch script: {str(e)}", logging.error)

def start_http_server():
    """Start HTTP server on localhost"""
    host = '127.0.0.1'
    try:
        server = HTTPServer((host, HTTP_PORT), RestartHandler)
        log_and_queue(f"HTTP Server: Started successfully on {host}:{HTTP_PORT}")
        server.serve_forever()
    except Exception as e:
        log_and_queue(f"HTTP Server: Error starting - {str(e)}", logging.ERROR)

def check_email():
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(GMAIL_SERVER, GMAIL_PORT)
        mail.login(os.getenv('NOTIF_EMAIL_ADDRESS'), os.getenv('NOTIF_PW'))
        log_and_queue("Email: Connected to Gmail", logging.DEBUG) # DEBUG level might be too verbose
        
        # Select inbox
        mail.select('inbox')
        
        # Search for unread messages
        _, messages = mail.search(None, 'UNSEEN')
        
        if not messages[0]:
             log_and_queue("Email: No new unread messages", logging.DEBUG)
        else:
            log_and_queue(f"Email: Found {len(messages[0].split())} unread message(s)")

        for num in messages[0].split():
            try:
                # Fetch message data
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                message = email.message_from_bytes(email_body)
                
                # Get sender's email address
                from_header = message['from']
                realname, sender_email = email.utils.parseaddr(from_header)
                
                # Check if sender is authorized (case-insensitive)
                if sender_email.lower() in [auth.lower() for auth in AUTHORIZED_SENDERS]:
                    # Get message subject and decode it
                    subject_header = message['subject']
                    decoded_subject = ''
                    for part, encoding in email.header.decode_header(subject_header):
                        if isinstance(part, bytes):
                            decoded_subject += part.decode(encoding or 'utf-8')
                        else:
                            decoded_subject += part

                    # Get message content (body)
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
                    
                    # Check for command phrase
                    if COMMAND_PHRASE.lower() in content.lower() or \
                       COMMAND_PHRASE.lower() in decoded_subject.lower():
                        log_and_queue(f"Email: Valid restart command received from {sender_email} (Subject: '{decoded_subject}')")
                        execute_restart()
                    else:
                         log_and_queue(f"Email: Authorized email from {sender_email} received, but no command phrase found.", logging.DEBUG)
                else:
                     log_and_queue(f"Email: Unauthorized email received from {sender_email}. Ignoring.", logging.WARNING)
                
                # Mark message as read
                mail.store(num, '+FLAGS', '\\Seen')
                
            except Exception as e:
                log_and_queue(f"Email: Error processing message {num}: {str(e)}", logging.ERROR)
                continue
                
        mail.close()
        mail.logout()
        log_and_queue("Email: Logged out from Gmail", logging.DEBUG)
        
    except imaplib.IMAP4.abort as e:
        log_and_queue(f"Email: IMAP connection aborted: {str(e)}. Retrying later.", logging.ERROR)
        time.sleep(30) # Wait before retrying after connection abort
    except Exception as e:
        log_and_queue(f"Email: Error in email checking: {str(e)}", logging.ERROR)
        # Avoid rapid retries on persistent errors
        time.sleep(60)

def email_monitor_thread():
    log_and_queue("Service: Email monitor thread started.")
    while True:
        check_email()
        # Consider dynamic sleep based on success/failure?
        time.sleep(60)  # Check every minute

def show_status(icon):
    root = tk.Tk()
    root.geometry("450x350") # Slightly larger window
    root.title("Data Looper Service Status")
    root.configure(bg='#f0f0f0') # Light grey background

    # Use a more readable font
    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=10)
    text_font = font.Font(family="Consolas", size=9) # Monospaced for logs

    # --- Log Display Area ---
    log_frame = tk.Frame(root, bg='#f0f0f0')
    log_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

    log_label = tk.Label(log_frame, text="Service Activity Log:", font=default_font, bg='#f0f0f0')
    log_label.pack(anchor=tk.W)

    log_text = scrolledtext.ScrolledText(
        log_frame, 
        wrap=tk.WORD, 
        state='disabled', # Make read-only
        height=15, 
        bg='#ffffff', # White background for text area
        fg='#333333', # Dark grey text
        font=text_font,
        relief=tk.SUNKEN, 
        bd=1
    )
    log_text.pack(fill=tk.BOTH, expand=True)

    # --- Close Button ---
    button_frame = tk.Frame(root, bg='#f0f0f0')
    button_frame.pack(pady=(0, 10), padx=10, fill=tk.X)

    close_button = tk.Button(
        button_frame, 
        text="Close Window", 
        command=root.destroy, 
        font=default_font,
        bg='#d9d9d9', # Slightly darker grey button
        relief=tk.RAISED,
        bd=1
    )
    close_button.pack(side=tk.RIGHT)

    # --- Function to Update Log Display ---
    def update_log_display():
        try:
            while not log_queue.empty():
                message = log_queue.get_nowait()
                log_text.configure(state='normal') # Enable writing
                log_text.insert(tk.END, message + '\n')
                log_text.configure(state='disabled') # Disable writing
                log_text.see(tk.END) # Scroll to the bottom
                log_queue.task_done()
        except queue.Empty:
            pass # No messages currently
        except Exception as e:
            # Log errors related to GUI updates separately if needed
            print(f"Error updating log display: {e}") 
        finally:
            # Reschedule the check
            root.after(150, update_log_display) # Check queue every 150ms

    # Add initial messages
    log_text.configure(state='normal')
    log_text.insert(tk.END, "Initializing Service Status Window...\n")
    log_text.insert(tk.END, f"Monitoring email: {os.getenv('NOTIF_EMAIL_ADDRESS')}\n")
    log_text.insert(tk.END, f"Listening for HTTP requests on 127.0.0.1:{HTTP_PORT}\n")
    log_text.insert(tk.END, "-------------------------------------\n")
    log_text.configure(state='disabled')
    
    # Start the log updater
    root.after(100, update_log_display)
    
    # Center the window
    root.eval('tk::PlaceWindow . center')
    root.mainloop()

def create_icon():
    # Use an existing icon from your app
    try:
        icon_path = os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\refresh_icon.png')
        image = Image.open(icon_path)
    except FileNotFoundError:
        log_and_queue(f"Icon file not found at {icon_path}. Using default icon.", logging.WARNING)
        # Create a simple default image if icon is missing
        image = Image.new('RGB', (64, 64), color = 'blue') 
        # You might want to draw something on this default image
    except Exception as e:
        log_and_queue(f"Error loading icon: {e}. Using default icon.", logging.ERROR)
        image = Image.new('RGB', (64, 64), color = 'red')
        
    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: show_status(icon), default=True), # Make default action
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    icon = pystray.Icon("data_looper_restart", image, "Data Looper Restart Service", menu=pystray.Menu(*menu))
    return icon

def exit_application(icon):
    log_and_queue("Service: Exit command received. Stopping service.")
    icon.stop()
    os._exit(0)

def main():
    log_and_queue("Service: Starting Data Looper Restart Service...")
    
    # Start the email monitoring thread
    monitor_thread = threading.Thread(target=email_monitor_thread, daemon=True)
    monitor_thread.start()
    
    # Start the HTTP server thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Create and run the system tray icon
    try:
        icon = create_icon()
        log_and_queue("Service: System tray icon created.")
        icon.run()
    except Exception as e:
        log_and_queue(f"Service: Failed to create or run system tray icon: {e}", logging.ERROR)
        # Attempt to keep threads running even if icon fails?
        # For now, we exit if the icon fails critical setup.
        os._exit(1)

if __name__ == "__main__":
    main() 