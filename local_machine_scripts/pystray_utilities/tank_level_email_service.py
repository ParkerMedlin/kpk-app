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
import dotenv

# Load .env file from two directories up
dotenv.load_dotenv(os.path.expanduser('~\\Documents\\kpk-app\\.env'))
JORDAN_ALT_NOTIF_PW = os.getenv('JORDAN_ALT_NOTIF_PW')
print(JORDAN_ALT_NOTIF_PW)

# Global variable to store last run time and email status
last_run = {"glycerin": {"time": None, "email_sent": False}, "pg": {"time": None, "email_sent": False}}

# Global variable for recipient list
# recipient_list = ['ddavis@kinpakinc.com', 'jdavis@kinpakinc.com', 'pmedlin@kinpakinc.com', 'swheeler@kinpakinc.com']
recipient_list = ['pmedlin@kinpakinc.com']

def get_tank_levels_py():
    fp = urllib.request.urlopen('http://192.168.178.210/fieldDeviceData.htm')
    html_str = fp.read().decode("utf-8")
    fp.close()

    # Parse the HTML string
    soup = bs4.BeautifulSoup(html_str, 'html.parser')
    allTableRows = soup.find_all('tr')

    tank_levels = {}
    for tableRow in allTableRows:
        tableCells = tableRow.find_all('td')
        if len(tableCells) > 4:  # Ensure there are enough cells
            # Extract tank label
            split_text = tableCells[0].text.split("Tag: ")
            if len(split_text) > 1:
                tank_label = split_text[1].split(" ")[0]
                print(tank_label)
                # Extract tank level
                tank_level_str = tableCells[4].text.split("<br>")[0]
                tank_level = float(''.join(c for c in tank_level_str if c.isdigit() or c == '.') or '0')
                print(tank_level)
                tank_levels[tank_label] = tank_level
    print(f"tank levels {tank_levels}")
    return tank_levels

def check_glycerin_capacity_and_send_email(call_source):
    print('This is the check_glycerin_capacity_and_send_email function, called from {}'.format(call_source))
    tank_levels = get_tank_levels_py()
    tank_glycerin_capacity = 56000 - (tank_levels['02'] + tank_levels['07'])
    if tank_glycerin_capacity >= 18000:
        sender_address =  'jdavis@kinpakinc.com'
        sender_pass =  JORDAN_ALT_NOTIF_PW
        for recipient in recipient_list:
            email_message = MIMEMultipart('alternative')
            email_message['From'] = sender_address
            email_message['To'] = recipient
            email_message['Subject'] = 'Storage Tank Direct: Glycerin Railcar can now be unloaded into Glycerin Tanks.'
            body = f"""<html>
            <body>
            <table style="border-collapse: collapse; padding: 10px;">
            <tr><td style="border: 1px solid black; padding: 5px;">Tank 2 capacity</td><td style="text-align: right; border: 1px solid black; padding: 5px;">{round(28000 - tank_levels["02"])}</td></tr>
            <tr><td style="border: 1px solid black; padding: 5px;">Tank 7 capacity</td><td style="text-align: right; border: 1px solid black; padding: 5px;">{round(28000 - tank_levels["07"])}</td></tr>
            <tr><td style="border: 2px solid black; padding: 5px; font-weight: bold;">Total capacity</td><td style="text-align: right; border: 2px solid black; padding: 5px; font-weight: bold;">{round(tank_glycerin_capacity)}</td></tr>
            </table>
            </body>
            </html>"""
            email_message.attach(MIMEText(body, 'html'))
            email_message.attach(MIMEText(body, 'plain'))
            session = smtplib.SMTP('smtp.office365.com', 587)
            session.starttls()
            session.login(sender_address, sender_pass)
            session.sendmail(sender_address, recipient, email_message.as_string())
            session.quit()
            last_run["glycerin"]["email_sent"] = True  # Update this based on your condition
    # Update last run time and email status
    last_run["glycerin"]["time"] = time.ctime()

def check_pg_capacity_and_send_email(call_source):
    print('This is the check_pg_capacity_and_send_email function, called from {}'.format(call_source))
    tank_levels = get_tank_levels_py()
    tank_pg_capacity = 78000 - (tank_levels['04'] + tank_levels['05'] + tank_levels['14'])
    if tank_pg_capacity >= 23000:
        sender_address =  'jdavis@kinpakinc.com'
        sender_pass =  JORDAN_ALT_NOTIF_PW
        for recipient in recipient_list:
            email_message = MIMEMultipart('alternative')
            email_message['From'] = sender_address
            email_message['To'] = recipient
            email_message['Subject'] = 'Storage Tank Direct: PG Railcar can now be unloaded into PG Tanks.'
            body = f"""<html>
            <body>
            <table style="border-collapse: collapse; padding: 10px;">
            <tr><td style="border: 1px solid black; padding: 5px;">Tank 4 capacity</td><td style="text-align: right; border: 1px solid black; padding: 5px;">{round(29000 - tank_levels["04"])}</td></tr>
            <tr><td style="border: 1px solid black; padding: 5px;">Tank 5 capacity</td><td style="text-align: right; border: 1px solid black; padding: 5px;">{round(29000 - tank_levels["05"])}</td></tr>
            <tr><td style="border: 1px solid black; padding: 5px;">Tank India capacity</td><td style="text-align: right; border: 1px solid black; padding: 5px;">{round(20000 - tank_levels["14"])}</td></tr>
            <tr><td style="border: 2px solid black; padding: 5px; font-weight: bold;">Total capacity</td><td style="text-align: right; border: 2px solid black; padding: 5px; font-weight: bold;">{round(tank_pg_capacity)}</td></tr>
            </table>
            </body>
            </html>"""
            email_message.attach(MIMEText(body, 'html'))
            email_message.attach(MIMEText(body, 'plain'))
            session = smtplib.SMTP('smtp.office365.com', 587)
            session.starttls()
            session.login(sender_address, sender_pass)
            session.sendmail(sender_address, recipient, email_message.as_string())
            session.quit()
            last_run["pg"]["email_sent"] = True
    last_run["pg"]["time"] = time.ctime()

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