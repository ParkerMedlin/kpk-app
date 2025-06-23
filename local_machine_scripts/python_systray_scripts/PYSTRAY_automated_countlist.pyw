import os
import sys
import time
import threading
import datetime as dt
import requests
import schedule
from PIL import Image
import pystray

# --- Configuration ---
# Oh, Great User, you may need to adjust this URL to match the sanctum of your web application.
BASE_URL = "http://127.0.0.1:8000/core/"
ICON_PATH = os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\jeff_tray_icon.png')

def get_icon_image():
    """
    A simple ritual to conjure the icon image. It will use the specified path,
    but if the veil between worlds is thin (file not found), it creates a simple white square as a fallback.
    """
    try:
        return Image.open(ICON_PATH)
    except FileNotFoundError:
        # Malloc, my raven, reports that a missing icon is a minor inconvenience. A placeholder will suffice.
        print(f"Icon file not found at {ICON_PATH}. Creating a placeholder.")
        return Image.new('RGB', (64, 64), 'white')

def update_tooltip(icon, message):
    """A small spell to whisper updates to the icon's tooltip."""
    if icon:
        icon.title = f"Automated Countlist ({message})"

def check_and_create_countlist(icon=None):
    """
    The core enchantment. It probes the ether for the countlist and creates it if it is but a phantom.
    """
    today_str = dt.date.today().isoformat()
    check_url = f"{BASE_URL}check-automated-count-exists/"
    create_url = f"{BASE_URL}create-automated-countlist/"
    
    update_tooltip(icon, f"Checking for {today_str}")
    print(f"[{dt.datetime.now()}] Running task: Checking for countlist for {today_str}")

    try:
        # 1. Check for the existence of the countlist
        response = requests.get(check_url, params={'date': today_str}, timeout=30)
        response.raise_for_status()  # A ward against malefic HTTP spirits (4xx or 5xx errors)

        data = response.json()
        if data.get('exists'):
            message = f"Exists for {today_str}"
            print(f"[{dt.datetime.now()}] {message}")
            update_tooltip(icon, message)
        else:
            # 2. If it does not exist, create it
            update_tooltip(icon, f"Creating for {today_str}")
            print(f"[{dt.datetime.now()}] Countlist for {today_str} does not exist. Creating...")
            create_response = requests.post(create_url, json={'date': today_str}, timeout=60)
            create_response.raise_for_status()
            
            message = f"Created for {today_str}"
            print(f"[{dt.datetime.now()}] {message}")
            update_tooltip(icon, message)

    except requests.exceptions.RequestException as e:
        error_message = f"A foul omen! The connection has failed: {e}"
        print(f"[{dt.datetime.now()}] {error_message}")
        update_tooltip(icon, "Connection Error")
    except Exception as e:
        error_message = f"A most unexpected curse has been unleashed: {e}"
        print(f"[{dt.datetime.now()}] {error_message}")
        update_tooltip(icon, "Script Error")

def run_scheduled_tasks(icon):
    """
    This function contains the chronomancer's loop, ensuring the ritual is performed daily.
    """
    schedule.every().day.at("04:00").do(check_and_create_countlist, icon=icon)
    
    # A courtesy check upon summoning.
    check_and_create_countlist(icon)

    while True:
        schedule.run_pending()
        time.sleep(60) # The familiar may rest for a minute between checks.

def exit_action(icon):
    """A banishment spell to dismiss the familiar."""
    print("Dismissing the familiar...")
    icon.stop()
    # A final, decisive command to ensure the script's departure.
    os._exit(0) 

def create_systray_icon():
    """
    The grand summoning ritual. This function conjures the system tray icon,
    binds its actions, and gives it life.
    """
    image = get_icon_image()
    
    # We must conjure a reference to the icon before binding its will with a menu.
    icon = pystray.Icon("auto_countlist", image, "Automated Countlist")

    # The scheduling magic shall occur in a parallel dimension (a thread) to not disturb our own.
    scheduler_thread = threading.Thread(target=run_scheduled_tasks, args=(icon,), daemon=True)
    scheduler_thread.start()

    # Now, we bestow upon the icon its commands.
    menu = pystray.Menu(
        pystray.MenuItem('Run Check Now', lambda: check_and_create_countlist(icon), default=True),
        pystray.MenuItem('Exit', lambda: exit_action(icon))
    )
    
    icon.menu = menu
    icon.run()


if __name__ == "__main__":
    create_systray_icon()
