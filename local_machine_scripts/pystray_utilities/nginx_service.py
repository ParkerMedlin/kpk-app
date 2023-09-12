import urllib.request
import bs4
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import schedule
import time
import pystray
from PIL import Image
import tkinter as tk
from tkinter import messagebox
import threading
import datetime
import os

os.path.expanduser('~\\Documents\\kpk-app\\.env')


# this is all the stuff that we want executed at a certain interval
def job():
    # Get the current time
    current_time = datetime.datetime.now()

    # Check if an email has been sent in the last 24 hours
    for task, data in last_run.items():
        if data["email_sent"]:
            last_email_time = datetime.datetime.strptime(data["time"], "%a %b %d %H:%M:%S %Y")
            if (current_time - last_email_time).total_seconds() < 24 * 60 * 60:
                print(f"Skipping {task} check because an email was sent in the last 24 hours")
                continue

        # Reset email_sent status after 24 hours
        data["email_sent"] = False

        if task == "glycerin":
            check_glycerin_capacity_and_send_email('Tank Perv')
        elif task == "pg":
            check_pg_capacity_and_send_email('Tank Perv')

 
def start_schedule():
    job()
    schedule.every(5).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
        

def show_info(icon):
    info = ""
    current_time = datetime.datetime.now()
    for task, data in last_run.items():
        info += f"Task: {task}\nLast run: {data['time']}\nEmail sent: {data['email_sent']}\n"
        if data["email_sent"]:
            last_email_time = datetime.datetime.strptime(data["time"], "%a %b %d %H:%M:%S %Y")
            if (current_time - last_email_time).total_seconds() < 24 * 60 * 60:
                info += "Email sending is paused for 24 hours\n\n"
            else:
                info += "Email sending is not paused\n\n"
        else:
            info += "Email sending is not paused\n\n"
    messagebox.showinfo("Tank Perv reporting for duty!", info)

def create_icon(image_path):
    image = Image.open(r"C:\Users\blend\Downloads\mkgSpiralSticker1LESSANGLED.png")
    menu = (pystray.MenuItem('Show Info', lambda icon, item: threading.Thread(target=show_info, args=(icon,)).start()),
            pystray.MenuItem('Exit', lambda icon, item: exit_application(icon)))
    icon = pystray.Icon("name", image, "Tank Perv", menu=pystray.Menu(*menu))
    icon.run()

def exit_application(icon):
    schedule.clear()  # This will stop all scheduled jobs
    icon.stop()  # This will stop the system tray ico
    os._exit(0)

def main():
    # Start the schedule in a separate thread
    threading.Thread(target=start_schedule).start()

    # Call this function with the path to your icon image
    create_icon(r'C:\Users\pmedl\Documents\kpk-app\app\static\core\kpk_192x192.png')

if __name__ == "__main__":
    main()