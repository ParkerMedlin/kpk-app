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
import threading
import datetime
import os

os.path.expanduser('~\\Documents\\kpk-app\\.env')

def check_file_for_string(file_path, search_string):
    try:
        with open(file_path, 'r') as file:
            contents = file.read()
            if search_string in contents:
                return True
            else:
                return False
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return False

def replace_string_in_file(file_path, old_string, new_string):
    try:
        with open(file_path, 'r') as file:
            contents = file.read()
        contents = contents.replace(old_string, new_string)
        with open(file_path, 'w') as file:
            file.write(contents)
        print(f"Replaced '{old_string}' with '{new_string}' in the file '{file_path}'.")
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")

def copy_from_container():
    nginx_conf_path = os.path.expanduser('~\\Documents\\kpk-app\\nginx\\temp_copy\\nginx.conf')
    os.system(f"docker cp kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf {nginx_conf_path}")

    if check_file_for_string(nginx_conf_path, "server app_blue:8001;"):
        print(f"The nginx.conf file is pointing to the blue container.\nSwitching to green.")
        replace_string_in_file(nginx_conf_path, "server app_blue:8001;","server app_green:8002;")
        os.system(f"docker cp {nginx_conf_path} kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf")
        os.system("docker exec kpk-app_nginx_1 nginx -s reload")
        # os.remove(nginx_conf_path)
        print(f"Restarting the blue container...")
        os.system("docker restart kpk-app_app_blue_1")

    elif check_file_for_string(nginx_conf_path, "server app_green:8002;"):
        print(f"The nginx.conf file is pointing to the green container.\nSwitching to blue.")
        replace_string_in_file(nginx_conf_path, "server app_green:8002;","server app_blue:8001;")
        os.system(f"docker cp {nginx_conf_path} kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf")
        os.system("docker exec kpk-app_nginx_1 nginx -s reload")
        # os.remove(nginx_conf_path)
        print(f"Restarting the green container...")
        os.system("docker restart kpk-app_app_green_1")

def copy_from_filesystem():
    nginx_conf_path = os.path.expanduser('~\\Documents\\kpk-app\\nginx\\nginx.conf')
    os.system(f"docker cp {nginx_conf_path} kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf")
    os.system("docker exec kpk-app_nginx_1 nginx -s reload")

def close_window(root):
    root.destroy()

def show_reload_options(icon):
    root = tk.Tk()
    root.geometry("300x200")
    root.title("Select source for reload.")

    button1 = tk.Button(root, text="Copy from Container", command=lambda:[copy_from_container(), close_window(root)])
    button1.pack(pady=20)

    button2 = tk.Button(root, text="Copy from Filesystem", command=lambda:[copy_from_filesystem(), close_window(root)])
    button2.pack(pady=20)

    root.mainloop()
    

def create_icon(image_path):
    image = Image.open(os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\nginx_logo.png'))
    menu = (pystray.MenuItem('Reload nginx.conf', lambda icon, item: show_reload_options(icon)),
            pystray.MenuItem('Exit', lambda icon, item: exit_application(icon)))
    icon = pystray.Icon("name", image, "Tank Perv", menu=pystray.Menu(*menu))
    icon.run()


def exit_application(icon):
    icon.stop()  # This will stop the system tray ico
    os._exit(0)

def main():
    # Call this function with the path to your icon image
    create_icon(r'C:\Users\pmedl\Documents\kpk-app\app\static\core\nginx_logo.png')

if __name__ == "__main__":
    main()