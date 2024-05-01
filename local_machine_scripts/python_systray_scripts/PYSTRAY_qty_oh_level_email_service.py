import psycopg2
import schedule
import time
from datetime import datetime
import threading
from pystray import Icon, MenuItem, Menu
from PIL import Image
from tkinter import messagebox
import tkinter as tk
import os

# Assuming email_sender has a function send_email_error
from email_sender import send_email_error

# Global variable to store last run time and email status
last_run = {"inventory_check": {"time": None, "email_sent": False}}

def check_inventory():
    conn_params = "postgresql://postgres:blend2021@localhost:5432/blendversedb"
    query = "SELECT quantityonhand FROM im_itemwarehouse WHERE itemcode = '030164';"
    try:
        conn = psycopg2.connect(conn_params)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        print(result)
        if result:
            quantity_on_hand = result[0]
            if quantity_on_hand <= 10:
                current_time = datetime.now()
                if last_run["inventory_check"]["email_sent"]:
                    last_email_time = datetime.strptime(last_run["inventory_check"]["time"], "%Y-%m-%d %H:%M:%S")
                    if (current_time - last_email_time).total_seconds() < 24 * 60 * 60:
                        print("Skipping email send because an email was sent in the last 24 hours")
                        return
                recipients = ['jdavis@kinpakinc.com', 'pmedlin@kinpakinc.com']
                message = f"Alert: Quantity on hand for item code 030164 is low: {quantity_on_hand}"
                send_email_error([message], recipients)
                last_run["inventory_check"]["email_sent"] = True
                last_run["inventory_check"]["time"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                print("Email sent due to low inventory.")
            else:
                print("Inventory level is sufficient.")
        else:
            print("Item not found in the database.")
    except Exception as e:
        print(f"Database query failed: {str(e)}")
    finally:
        if conn:
            cursor.close()
            conn.close()

def job():
    check_inventory()

def start_schedule():
    schedule.every(5).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)

def show_info(icon):
    info = f"Last run: {last_run['inventory_check']['time']}\nEmail sent: {last_run['inventory_check']['email_sent']}\n"
    messagebox.showinfo("Inventory Checker", info)

def create_icon():
    image = Image.open(os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\qty_oh_perv.png'))  # Path to an icon image
    menu = Menu(MenuItem('Show Info', lambda icon, item: threading.Thread(target=show_info, args=(icon,)).start()),
                MenuItem('Exit', lambda icon, item: icon.stop()))
    icon = Icon("InventoryChecker", image, "Inventory Checker", menu)
    icon.run()

def main():
    threading.Thread(target=start_schedule).start()
    create_icon()

if __name__ == "__main__":
    main()