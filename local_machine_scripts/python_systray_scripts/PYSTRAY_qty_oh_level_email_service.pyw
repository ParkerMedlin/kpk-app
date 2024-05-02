import psycopg2
import schedule
import time
from datetime import datetime
import threading
from pystray import Icon, MenuItem, Menu
from PIL import Image
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import json
import logging

# Load .env file for environment variables
from dotenv import load_dotenv
load_dotenv()

# Define the directory and file for logging
log_dir = os.path.join(os.path.dirname(__file__), 'pystray_logs')
log_file = 'inventory_log.txt'
log_path = os.path.join(log_dir, log_file)

# Ensure the directory exists
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Ensure the log file exists
if not os.path.isfile(log_path):
    open(log_path, 'w').close()

# Setup logging to use the new log file path
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Clear log file on start
open(log_path, 'w').close()

# Global variable to store last run time, email status, and item triggers
last_run = {"inventory_check": {"time": None, "email_sent": False}}

# Define the path to the JSON database file
db_file_path = os.path.join(os.path.dirname(__file__), 'pystray_db_files', 'qty_oh_level_db.json')

def load_item_triggers():
    """ Load item triggers from the JSON file. """
    try:
        with open(db_file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return an empty dictionary if the file does not exist or is empty

def save_item_triggers(item_triggers):
    """ Save item triggers to the JSON file. """
    with open(db_file_path, 'w') as file:
        json.dump(item_triggers, file, indent=4)

# Initialize item_triggers from the JSON file
item_triggers = load_item_triggers()

def send_email_error(message, recipients):
    sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
    sender_pass = os.getenv('NOTIF_PW')
    email_message = MIMEMultipart('alternative')
    email_message['From'] = sender_address
    email_message['To'] = ", ".join(recipients)  # Set all recipients at once
    email_message['Subject'] = 'Inventory Alert'
    body = f"<html><body><p>{message}</p></body></html>"
    email_message.attach(MIMEText(body, 'html'))
    email_message.attach(MIMEText(message, 'plain'))

    session = smtplib.SMTP('smtp.gmail.com', 587)
    session.starttls()
    session.login(sender_address, sender_pass)
    session.sendmail(sender_address, recipients, email_message.as_string())  # Send to all recipients at once
    session.quit()
    logging.info("Email sent to:", ", ".join(recipients))

def check_inventory():
    conn = None
    conn_params = "postgresql://postgres:blend2021@localhost:5432/blendversedb"
    for item_code, trigger_level in item_triggers.items():
        query = f"SELECT quantityonhand FROM im_itemwarehouse WHERE itemcode = '{item_code}' AND warehousecode = 'MTG';"
        try:
            conn = psycopg2.connect(conn_params)
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                quantity_on_hand = result[0]
                logging.info(f"Inventory level for {item_code} is {quantity_on_hand}")
                if quantity_on_hand <= trigger_level:
                    current_time = datetime.now()
                    last_email_time = last_run["inventory_check"]["time"] if last_run["inventory_check"]["email_sent"] == True else None
                    if last_email_time and (current_time - last_email_time).total_seconds() < 24 * 60 * 60:
                        logging.info("Skipping email send because an email was sent in the last 24 hours")
                        return
                    message = f"Alert: Quantity on hand for item code {item_code} is low: {quantity_on_hand}"
                    send_email_error(message, ['jdavis@kinpakinc.com', 'pmedlin@kinpakinc.com'])
                    last_run["inventory_check"]["email_sent"] = True
                    last_run["inventory_check"]["time"] = datetime.now()
                    logging.info("Email sent due to low inventory.")
                else:
                    last_run["inventory_check"]["time"] = datetime.now()
                    logging.info(f"Inventory level for {item_code} is sufficient.")
            else:
                logging.info(f"Item {item_code} not found in the database.")
        except Exception as e:
            logging.error(f"Database query failed: {str(e)}")
        finally:
            if conn:
                cursor.close()
                conn.close()

def job():
    check_inventory()

def start_schedule():
    check_inventory()
    schedule.every(0.5).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)

def show_info(icon):
    info = f"Last run: {last_run['inventory_check']['time']}\nEmail sent: {last_run['inventory_check']['email_sent']}\n"
    messagebox.showinfo("Inventory Checker", info)

def manage_items(icon):
    root = tk.Tk()
    root.title("Manage Items")

    def add_item():
        item_code = simpledialog.askstring("Input", "Enter item code:", parent=root)
        trigger_level = simpledialog.askinteger("Input", "Enter trigger level:", parent=root)
        if item_code and trigger_level:
            item_triggers[item_code] = trigger_level
            save_item_triggers(item_triggers)
            update_list()

    def edit_item():
        selected_item = treeview.selection()
        if selected_item:
            item_code = treeview.item(selected_item, 'values')[0]
            new_level = simpledialog.askinteger("Input", f"Enter new trigger level for {item_code}:", parent=root)
            if new_level:
                item_triggers[item_code] = new_level
                save_item_triggers(item_triggers)
                update_list()

    def delete_item():
        selected_item = treeview.selection()
        if selected_item:
            item_code = treeview.item(selected_item, 'values')[0]
            del item_triggers[item_code]
            save_item_triggers(item_triggers)
            update_list()

    def update_list():
        for item in treeview.get_children():
            treeview.delete(item)
        for item_code, level in item_triggers.items():
            treeview.insert('', 'end', values=(item_code, level))

    treeview = ttk.Treeview(root, columns=('Item Code', 'Qty'), show='headings')
    treeview.heading('Item Code', text='Item Code')
    treeview.heading('Qty', text='Qty')
    treeview.column('Qty', anchor='e')  # Right-align the 'Qty' column
    treeview.pack(expand=True, fill=tk.BOTH)

    # Style configuration for the treeview to add borders
    style = ttk.Style()
    style.theme_use('vista')
    style.configure("Treeview", borderwidth=1, relief="solid")
    style.configure("Treeview.Heading", font=('Calibri', 12, 'bold'), borderwidth=1, relief="solid")

    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X)

    add_button = tk.Button(button_frame, text="Add Item", command=add_item)
    add_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

    edit_button = tk.Button(button_frame, text="Edit Item", command=edit_item)
    edit_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

    delete_button = tk.Button(button_frame, text="Delete Item", command=delete_item)
    delete_button.pack(side=tk.LEFT, expand=True, fill=tk.X)

    update_list()

    root.mainloop()

class LogViewer:
    def __init__(self, icon):
        self.icon = icon
        self.running = False
        self.thread = None
        self.log_window = None
        self.text_area = None

    def start(self):
        if self.log_window is not None:
            # Focus the already opened window instead of opening a new one
            self.log_window.focus_force()
            return

        self.log_window = tk.Tk()
        self.log_window.title("Log Viewer")
        self.log_window.configure(bg='white')

        style = ttk.Style()
        style.theme_use('vista')

        self.text_area = tk.Text(self.log_window, wrap='word', height=30, width=100, bd=0, font=('Segoe UI', 10))
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(self.log_window, orient='vertical', command=self.text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)

        self.running = True
        self.thread = threading.Thread(target=self.update_log_content, daemon=True)
        self.thread.start()

        self.log_window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_window.mainloop()

    def update_log_content(self):
        log_path = os.path.join(os.path.dirname(__file__), 'pystray_logs', 'inventory_log.txt')
        while self.running:
            try:
                with open(log_path) as log_file:
                    logs = log_file.read()
                self.text_area.config(state=tk.NORMAL)
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, logs)
                self.text_area.config(state=tk.DISABLED)
            except Exception as e:
                print("Failed to read log file:", e)
            time.sleep(5)

    def on_closing(self):
        self.running = False
        self.log_window.destroy()
        self.log_window = None
        self.text_area = None

def view_logs(icon):
    viewer = LogViewer(icon)
    viewer.start()


def create_icon():
    image = Image.open(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'core', 'static', 'core', 'qty_oh_perv.png'))
    log_viewer = LogViewer(None)
    menu = Menu(
        MenuItem('Show Info', lambda icon, item: threading.Thread(target=show_info, args=(icon,)).start()),
        MenuItem('Manage Items', lambda icon, item: threading.Thread(target=manage_items, args=(icon,)).start()),
        MenuItem('View Logs', lambda icon, item: threading.Thread(target=log_viewer.start).start()),
        MenuItem('Exit', lambda icon, item: icon.stop())
    )
    icon = Icon("InventoryWatcher", image, "Inventory Watcher", menu)
    icon.run()

def main():
    threading.Thread(target=start_schedule).start()
    create_icon()

if __name__ == "__main__":
    main()