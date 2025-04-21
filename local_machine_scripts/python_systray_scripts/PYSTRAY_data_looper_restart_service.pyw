import imaplib
import email
import email.header
import os
import subprocess
import time
import pystray
from PIL import Image
import tkinter as tk
import threading
import datetime
import logging
import ssl
from dotenv import load_dotenv

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

def check_email():
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(GMAIL_SERVER, GMAIL_PORT)
        mail.login(os.getenv('NOTIF_EMAIL_ADDRESS'), os.getenv('NOTIF_PW'))
        
        # Select inbox
        mail.select('inbox')
        
        # Search for unread messages
        _, messages = mail.search(None, 'UNSEEN')
        
        for num in messages[0].split():
            try:
                # Fetch message data
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                message = email.message_from_bytes(email_body)
                
                # Get sender's email address
                from_header = message['from']
                # Parse the address to handle names like "John Davis <jdavis@kinpakinc.com>"
                realname, sender_email = email.utils.parseaddr(from_header)
                
                # Check if sender is authorized (case-insensitive)
                if sender_email.lower() in [auth.lower() for auth in AUTHORIZED_SENDERS]:
                    # Get message subject and decode it
                    subject_header = message['subject']
                    decoded_subject = ''
                    for part, encoding in email.header.decode_header(subject_header):
                        if isinstance(part, bytes):
                            # If encoding is None, assume default (e.g., utf-8 or detect)
                            decoded_subject += part.decode(encoding or 'utf-8')
                        else:
                            decoded_subject += part

                    # Get message content (body)
                    content = '' # Initialize content
                    if message.is_multipart():
                        for part in message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            # Check if it's plain text and not an attachment
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    content = part.get_payload(decode=True).decode()
                                    break # Found the plain text body
                                except Exception as decode_err:
                                    logging.warning(f"Could not decode part: {decode_err}")
                    else:
                        # Not multipart, get the payload directly if it's text
                        if message.get_content_type() == "text/plain":
                            try:
                                content = message.get_payload(decode=True).decode()
                            except Exception as decode_err:
                                logging.warning(f"Could not decode payload: {decode_err}")
                    
                    # Check for command phrase in EITHER subject OR body
                    if COMMAND_PHRASE.lower() in content.lower() or \
                       COMMAND_PHRASE.lower() in decoded_subject.lower():
                        logging.info(f"Valid restart command received from {sender_email} (Subject: '{decoded_subject}')")

                        # --- Restart Logic --- 
                        logging.info("Proceeding to attempt restart by executing the batch script...")
                        try:
                            app_dir = os.path.expanduser('~\\Documents\\kpk-app')
                            logging.info(f"Attempting to start batch script: {BAT_SCRIPT_PATH} in directory: {app_dir}")
                            subprocess.Popen([BAT_SCRIPT_PATH],
                                          creationflags=subprocess.CREATE_NEW_CONSOLE,
                                          cwd=app_dir)
                            logging.info(f"Successfully launched Popen for batch script.")
                        except FileNotFoundError:
                             logging.error(f"Could not find batch script at: {BAT_SCRIPT_PATH}")
                        except Exception as e:
                            logging.error(f"Error starting batch script: {str(e)}", exc_info=True)

                        # --- MODIFICATION END ---
                
                # Mark message as read
                mail.store(num, '+FLAGS', '\\Seen')
                
            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")
                continue
                
        mail.close()
        mail.logout()
        
    except Exception as e:
        logging.error(f"Error in email checking: {str(e)}")

def email_monitor_thread():
    while True:
        check_email()
        time.sleep(60)  # Check every minute

def show_status(icon):
    root = tk.Tk()
    root.geometry("300x200")
    root.title("Data Looper Restart Service Status")

    status_label = tk.Label(root, text="Service is running\nMonitoring for restart commands...")
    status_label.pack(pady=20)

    close_button = tk.Button(root, text="Close", command=root.destroy)
    close_button.pack(pady=20)

    root.mainloop()

def create_icon():
    # Use an existing icon from your app
    image = Image.open(os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\refresh_icon.png'))
    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: show_status(icon)),
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    icon = pystray.Icon("data_looper_restart", image, "Data Looper Restart Service", menu=pystray.Menu(*menu))
    return icon

def exit_application(icon):
    icon.stop()
    os._exit(0)

def main():
    # Start the email monitoring thread
    monitor_thread = threading.Thread(target=email_monitor_thread, daemon=True)
    monitor_thread.start()
    
    # Create and run the system tray icon
    icon = create_icon()
    icon.run()

if __name__ == "__main__":
    logging.info("Data Looper Restart Service started")
    main() 