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
import argparse
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

# Check time: 5:30 PM (17:30) - can be overridden via command line args
DEFAULT_CHECK_HOUR = 17
DEFAULT_CHECK_MINUTE = 30
DEFAULT_ALERT_WINDOW_HOURS = 2

# These will be set by parse_args() or use defaults
CHECK_HOUR = DEFAULT_CHECK_HOUR
CHECK_MINUTE = DEFAULT_CHECK_MINUTE
ALERT_WINDOW_HOURS = DEFAULT_ALERT_WINDOW_HOURS

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
    print(f"[DEBUG] backup_monitor_thread starting...")
    log_and_queue(f"Service: Backup monitor thread started.")
    log_and_queue(f"Service: Backup root: {BACKUP_ROOT}")
    log_and_queue(f"Service: Check time: {CHECK_HOUR}:{CHECK_MINUTE:02d}")
    log_and_queue(f"Service: Alert window: {ALERT_WINDOW_HOURS} hours")

    checker = BackupChecker(BACKUP_ROOT)

    # Set up notifier if webhook is configured
    notifier = None
    if TEAMS_WEBHOOK_URL:
        notifier = TeamsNotifier(TEAMS_WEBHOOK_URL)
        log_and_queue("Service: Teams notifications enabled.")
    else:
        log_and_queue("Service: TEAMS_WEBHOOK_URL not set. Teams notifications disabled.", logging.WARNING)

    loop_count = 0
    while True:
        loop_count += 1
        now = datetime.datetime.now()
        print(f"[DEBUG] Loop #{loop_count} at {now.strftime('%H:%M:%S')}")

        try:
            in_window = is_check_time()
            print(f"[DEBUG] is_check_time() = {in_window} (window: {CHECK_HOUR}:{CHECK_MINUTE:02d} - {CHECK_HOUR + ALERT_WINDOW_HOURS}:{CHECK_MINUTE:02d})")

            if in_window:
                log_and_queue(f"Check: Within check window, verifying backup...")
                print(f"[DEBUG] IN CHECK WINDOW - running backup check")

                exists, message, folders = checker.check_backup_exists()
                print(f"[DEBUG] check_backup_exists() returned: exists={exists}, message={message}, folders={folders}")

                if exists:
                    log_and_queue(f"Check: {message}")
                    for folder in folders:
                        log_and_queue(f"Check:   - {folder}")
                else:
                    log_and_queue(f"Check: {message}", logging.WARNING)

                    # Send alert if we haven't already today
                    should = checker.should_alert()
                    print(f"[DEBUG] should_alert() = {should}")

                    if should:
                        log_and_queue(f"Alert: Sending missing backup alert...", logging.WARNING)

                        if notifier:
                            alert = BackupAlert(
                                description="Daily backup not found",
                                severity="critical",
                                backup_path=BACKUP_ROOT,
                                date_checked=checker.get_today_date_prefix()
                            )
                            result = notifier.send_alert(alert)
                            print(f"[DEBUG] send_alert() returned: {result}")
                        else:
                            print(f"[DEBUG] No notifier configured, skipping Teams alert")

                        checker.mark_alerted()
                    else:
                        log_and_queue(f"Alert: Already alerted for today, skipping.", logging.DEBUG)

                # After checking, sleep for a bit then check again (in case backup appears)
                sleep_seconds = 60  # Check every minute while in window
                print(f"[DEBUG] In window, sleeping {sleep_seconds}s before next check")
                log_and_queue(f"Check: Will re-check in {sleep_seconds}s")
                time.sleep(sleep_seconds)
            else:
                # Not in check window, calculate time until check
                sleep_seconds = get_seconds_until_check()
                hours = sleep_seconds // 3600
                minutes = (sleep_seconds % 3600) // 60

                print(f"[DEBUG] NOT in check window. Next check in {hours}h {minutes}m ({sleep_seconds}s)")
                log_and_queue(f"Service: Next check in {hours}h {minutes}m (at {CHECK_HOUR}:{CHECK_MINUTE:02d})")

                # Sleep for shorter intervals during testing
                actual_sleep = min(sleep_seconds, 30)  # Check every 30 seconds for responsiveness
                print(f"[DEBUG] Sleeping {actual_sleep}s...")
                time.sleep(actual_sleep)

        except Exception as e:
            print(f"[DEBUG] ERROR in loop: {e}")
            import traceback
            traceback.print_exc()
            log_and_queue(f"Monitor: Error in check cycle: {e}", logging.ERROR)
            time.sleep(60)  # Wait 1 minute on error


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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backup Health Watchdog - monitors daily backup existence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (check at 5:30 PM)
  python backup_health.py

  # Test mode: check at 2:45 PM with 1-hour window
  python backup_health.py --check-time 14:45 --window 1

  # Check in 2 minutes from now (for quick testing)
  python backup_health.py --check-time 14:32
        """
    )
    parser.add_argument(
        '--check-time',
        type=str,
        default=None,
        metavar='HH:MM',
        help=f'Time to check for backup (24-hour format). Default: {DEFAULT_CHECK_HOUR}:{DEFAULT_CHECK_MINUTE:02d}'
    )
    parser.add_argument(
        '--window',
        type=int,
        default=DEFAULT_ALERT_WINDOW_HOURS,
        metavar='HOURS',
        help=f'Hours after check time to keep checking. Default: {DEFAULT_ALERT_WINDOW_HOURS}'
    )
    return parser.parse_args()


def main():
    """Main entry point for the Backup Health Watchdog."""
    global CHECK_HOUR, CHECK_MINUTE, ALERT_WINDOW_HOURS

    args = parse_args()

    # Override check time if provided
    if args.check_time:
        try:
            hour, minute = map(int, args.check_time.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
            CHECK_HOUR = hour
            CHECK_MINUTE = minute
        except ValueError as e:
            print(f"Error: Invalid --check-time format. Use HH:MM (e.g., 17:30). {e}")
            sys.exit(1)

    ALERT_WINDOW_HOURS = args.window

    log_and_queue(f"Service: Starting {SERVICE_NAME}...")
    log_and_queue(f"Service: Check time set to {CHECK_HOUR}:{CHECK_MINUTE:02d} with {ALERT_WINDOW_HOURS}h window")

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
