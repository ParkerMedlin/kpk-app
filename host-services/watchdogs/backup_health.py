"""
Backup Health Watchdog
======================
Monitors daily backup existence in the Apps server folder.
Checks at 5:30 PM daily for a backup folder with today's date.

Backup folders are created by backup_and_copy.bat with format:
    MM-DD-YYYY-HH-MM-SS-backup

Location: host-services/watchdogs/backup_health.py
"""

import os
import sys
import time
import datetime
import logging
import threading
import queue
import json
import requests
import tkinter as tk
from tkinter import scrolledtext, font
from dataclasses import dataclass, field
from typing import Optional

import pystray
from PIL import Image
from dotenv import load_dotenv

# --- Path Configuration ---
KPK_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOST_SERVICES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv(os.path.join(KPK_APP_ROOT, '.env'))

# --- Logging Configuration ---
LOG_DIR = os.path.join(HOST_SERVICES_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'backup_health.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Service Configuration ---
SERVICE_NAME = "Backup Health Watchdog"

# Backup location - UNC path to Apps server
DEFAULT_BACKUP_ROOT = r"\\KinPak-Svr1\apps\kpkapp\backups"
BACKUP_ROOT = os.environ.get("BACKUP_ROOT", DEFAULT_BACKUP_ROOT)

# Check time: 5:30 PM (17:30)
CHECK_HOUR = 17
CHECK_MINUTE = 30

# How long after check time to keep alerting if backup missing (hours)
ALERT_WINDOW_HOURS = 2

# Teams webhook for notifications
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")

# Alert origin identification
DEFAULT_KPKAPP_HOST = "kpkapp.lan"
ALERT_ORIGIN = os.environ.get("KPKAPP_HOST", DEFAULT_KPKAPP_HOST)

# --- Icon Path ---
ICON_PATH = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'backup_icon.png')

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


@dataclass
class BackupAlert:
    """Represents a backup alert."""
    description: str
    severity: str
    backup_path: str
    date_checked: str
    origin: str = field(default_factory=lambda: ALERT_ORIGIN)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


class TeamsNotifier:
    """Sends alerts to Microsoft Teams via Workflow webhook."""

    SEVERITY_COLORS = {
        'info': 'Default',
        'warning': 'Warning',
        'error': 'Attention',
        'critical': 'Attention'
    }

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, alert: BackupAlert) -> bool:
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
                log_and_queue(f"Notifier: Sent backup alert to Teams")
                return True
            else:
                log_and_queue(f"Notifier: Teams returned status {response.status_code}: {response.text[:200]}", logging.ERROR)
                return False
        except requests.exceptions.Timeout:
            log_and_queue(f"Notifier: Timeout sending to Teams", logging.ERROR)
            return False
        except Exception as e:
            log_and_queue(f"Notifier: Failed to send Teams notification: {e}", logging.ERROR)
            return False

    def _build_adaptive_card(self, alert: BackupAlert) -> dict:
        """Build Microsoft Teams Adaptive Card payload."""
        severity_color = self.SEVERITY_COLORS.get(alert.severity, 'Attention')

        facts = [
            {"title": "Origin", "value": alert.origin},
            {"title": "Backup Path", "value": alert.backup_path},
            {"title": "Date Checked", "value": alert.date_checked},
            {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        ]

        body = [
            {
                "type": "TextBlock",
                "text": f"{alert.severity.upper()}: {alert.description}",
                "weight": "Bolder",
                "size": "Large",
                "color": severity_color,
                "wrap": True
            },
            {
                "type": "FactSet",
                "facts": facts
            },
            {
                "type": "TextBlock",
                "text": "Please verify the backup process ran successfully and check the backup server.",
                "wrap": True,
                "separator": True
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


class BackupChecker:
    """Checks for daily backup folder existence."""

    def __init__(self, backup_root: str):
        self.backup_root = backup_root
        self._last_alert_date: Optional[str] = None

    def get_today_date_prefix(self) -> str:
        """Get today's date in the format used by backup_and_copy.bat: MM-DD-YYYY"""
        now = datetime.datetime.now()
        return now.strftime("%m-%d-%Y")

    def check_backup_exists(self) -> tuple:
        """
        Check if a backup folder exists for today.

        Returns: (exists: bool, message: str, folders_found: list)
        """
        date_prefix = self.get_today_date_prefix()

        # Check if backup root is accessible
        if not os.path.exists(self.backup_root):
            return False, f"Backup root not accessible: {self.backup_root}", []

        try:
            # List all folders in backup root
            all_items = os.listdir(self.backup_root)

            # Find folders starting with today's date
            matching_folders = [
                f for f in all_items
                if f.startswith(date_prefix) and os.path.isdir(os.path.join(self.backup_root, f))
            ]

            if matching_folders:
                return True, f"Found {len(matching_folders)} backup(s) for {date_prefix}", matching_folders
            else:
                return False, f"No backup found for {date_prefix}", []

        except PermissionError as e:
            return False, f"Permission denied accessing {self.backup_root}: {e}", []
        except Exception as e:
            return False, f"Error checking backups: {e}", []

    def should_alert(self) -> bool:
        """
        Determine if we should send an alert.
        Only alert once per day for missing backup.
        """
        today = self.get_today_date_prefix()
        if self._last_alert_date == today:
            return False
        return True

    def mark_alerted(self):
        """Mark that we've alerted for today."""
        self._last_alert_date = self.get_today_date_prefix()


def is_check_time() -> bool:
    """Check if current time is within the check window (5:30 PM - 7:30 PM)."""
    now = datetime.datetime.now()
    check_start = now.replace(hour=CHECK_HOUR, minute=CHECK_MINUTE, second=0, microsecond=0)
    check_end = check_start + datetime.timedelta(hours=ALERT_WINDOW_HOURS)
    return check_start <= now <= check_end


def get_seconds_until_check() -> int:
    """Get seconds until next check time (5:30 PM)."""
    now = datetime.datetime.now()
    check_time = now.replace(hour=CHECK_HOUR, minute=CHECK_MINUTE, second=0, microsecond=0)

    # If we're past check time today, schedule for tomorrow
    if now >= check_time:
        check_time += datetime.timedelta(days=1)

    return int((check_time - now).total_seconds())


def backup_monitor_thread():
    """Background thread for backup monitoring."""
    log_and_queue(f"Service: Backup monitor thread started.")
    log_and_queue(f"Service: Backup root: {BACKUP_ROOT}")
    log_and_queue(f"Service: Check time: {CHECK_HOUR}:{CHECK_MINUTE:02d}")

    checker = BackupChecker(BACKUP_ROOT)

    # Set up notifier if webhook is configured
    notifier = None
    if TEAMS_WEBHOOK_URL:
        notifier = TeamsNotifier(TEAMS_WEBHOOK_URL)
        log_and_queue("Service: Teams notifications enabled.")
    else:
        log_and_queue("Service: TEAMS_WEBHOOK_URL not set. Teams notifications disabled.", logging.WARNING)

    while True:
        try:
            if is_check_time():
                log_and_queue(f"Check: Within check window, verifying backup...")

                exists, message, folders = checker.check_backup_exists()

                if exists:
                    log_and_queue(f"Check: {message}")
                    for folder in folders:
                        log_and_queue(f"Check:   - {folder}")
                else:
                    log_and_queue(f"Check: {message}", logging.WARNING)

                    # Send alert if we haven't already today
                    if checker.should_alert():
                        log_and_queue(f"Alert: Sending missing backup alert...", logging.WARNING)

                        if notifier:
                            alert = BackupAlert(
                                description="Daily backup not found",
                                severity="critical",
                                backup_path=BACKUP_ROOT,
                                date_checked=checker.get_today_date_prefix()
                            )
                            notifier.send_alert(alert)

                        checker.mark_alerted()
                    else:
                        log_and_queue(f"Alert: Already alerted for today, skipping.", logging.DEBUG)

                # After checking, sleep until next check window (tomorrow)
                sleep_seconds = get_seconds_until_check()
                log_and_queue(f"Check: Next check in {sleep_seconds // 3600}h {(sleep_seconds % 3600) // 60}m")
                time.sleep(min(sleep_seconds, 3600))  # Sleep at most 1 hour at a time
            else:
                # Not in check window, calculate time until check
                sleep_seconds = get_seconds_until_check()
                hours = sleep_seconds // 3600
                minutes = (sleep_seconds % 3600) // 60

                log_and_queue(f"Service: Next check in {hours}h {minutes}m (at {CHECK_HOUR}:{CHECK_MINUTE:02d})", logging.DEBUG)

                # Sleep for shorter intervals to stay responsive
                time.sleep(min(sleep_seconds, 1800))  # Check every 30 min max

        except Exception as e:
            log_and_queue(f"Monitor: Error in check cycle: {e}", logging.ERROR)
            time.sleep(300)  # Wait 5 minutes on error


def manual_check():
    """Perform a manual backup check (called from tray menu)."""
    log_and_queue("Manual: Running manual backup check...")
    checker = BackupChecker(BACKUP_ROOT)
    exists, message, folders = checker.check_backup_exists()

    if exists:
        log_and_queue(f"Manual: {message}")
        for folder in folders:
            log_and_queue(f"Manual:   - {folder}")
    else:
        log_and_queue(f"Manual: {message}", logging.WARNING)


def show_status(icon):
    """Display the status window with service activity log."""
    root = tk.Tk()
    root.geometry("500x400")
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

    check_button = tk.Button(
        button_frame,
        text="Check Now",
        command=lambda: threading.Thread(target=manual_check, daemon=True).start(),
        font=default_font,
        bg='#4CAF50',
        fg='white',
        relief=tk.RAISED,
        bd=1
    )
    check_button.pack(side=tk.LEFT)

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
    log_text.insert(tk.END, f"Backup root: {BACKUP_ROOT}\n")
    log_text.insert(tk.END, f"Check time: {CHECK_HOUR}:{CHECK_MINUTE:02d} daily\n")
    log_text.insert(tk.END, f"Alert window: {ALERT_WINDOW_HOURS} hours after check time\n")
    if TEAMS_WEBHOOK_URL:
        log_text.insert(tk.END, "Teams notifications: Enabled\n")
    else:
        log_text.insert(tk.END, "Teams notifications: Disabled (TEAMS_WEBHOOK_URL not set)\n")
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
        # Create a simple backup-themed icon (green folder)
        image = Image.new('RGB', (64, 64), color='#4CAF50')
    except Exception as e:
        log_and_queue(f"Error loading icon: {e}. Using default icon.", logging.ERROR)
        image = Image.new('RGB', (64, 64), color='#4CAF50')

    menu = (
        pystray.MenuItem('Show Status', lambda icon, item: show_status(icon), default=True),
        pystray.MenuItem('Check Now', lambda icon, item: threading.Thread(target=manual_check, daemon=True).start()),
        pystray.MenuItem('Exit', lambda icon, item: exit_application(icon))
    )
    icon = pystray.Icon("backup_health", image, SERVICE_NAME, menu=pystray.Menu(*menu))
    return icon


def exit_application(icon):
    """Stop the service and exit."""
    log_and_queue("Service: Exit command received. Stopping service.")
    icon.stop()
    os._exit(0)


def main():
    """Main entry point for the Backup Health Watchdog."""
    log_and_queue(f"Service: Starting {SERVICE_NAME}...")

    # Start the backup monitoring thread
    monitor_thread = threading.Thread(target=backup_monitor_thread, daemon=True)
    monitor_thread.start()

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
