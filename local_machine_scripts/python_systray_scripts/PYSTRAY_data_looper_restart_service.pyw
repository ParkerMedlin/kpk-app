import imaplib
import email
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
    "3344141079@txt.att.net", "3344141079@vtext.com",
    "3344627140@txt.att.net", "3344627140@vtext.com",
    "9806211595@txt.att.net", "9806211595@vtext.com"
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
                
                # Get sender
                sender = message['from']
                
                # Check if sender is authorized
                if any(auth_sender in sender.lower() for auth_sender in AUTHORIZED_SENDERS):
                    # Get message content
                    if message.is_multipart():
                        for part in message.walk():
                            if part.get_content_type() == "text/plain":
                                content = part.get_payload(decode=True).decode()
                                break
                    else:
                        content = message.get_payload(decode=True).decode()
                    
                    # Check for command phrase
                    if COMMAND_PHRASE.lower() in content.lower():
                        logging.info(f"Valid restart command received from {sender}")
                        
                        # Find and kill data_looper process
                        try:
                            # Get process list and find data_looper.py
                            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                                                 capture_output=True, text=True)
                            
                            for line in result.stdout.split('\n'):
                                if 'data_looper.py' in line:
                                    pid = line.split(',')[1].strip('"')
                                    subprocess.run(['taskkill', '/F', '/PID', pid])
                                    logging.info(f"Terminated data_looper.py process with PID {pid}")
                                    break
                            
                            # Start the batch script
                            subprocess.Popen([BAT_SCRIPT_PATH], 
                                          creationflags=subprocess.CREATE_NEW_CONSOLE)
                            logging.info("Started data_looper.py via batch script")
                            
                        except Exception as e:
                            logging.error(f"Error in process management: {str(e)}")
                
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
    image = Image.open(os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\refresh.png'))
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