import os
import time
import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox

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


def main():
    root = tk.Tk()
    root.geometry("300x200")
    root.title("Choose update type:")

    # Load an image file
    bg_image = Image.open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\gradientImage.png'))
    # Use PhotoImage to create a PhotoImage object
    bg_photo = ImageTk.PhotoImage(bg_image)
    # Create a label with the PhotoImage object as the image
    bg_label = tk.Label(root, image=bg_photo)
    # Position the label to fill the entire window
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    button1 = tk.Button(root, text="Copy nginx.conf from Container", command=copy_from_container)
    button1.pack(pady=20)

    button2 = tk.Button(root, text="Copy nginx.conf from Filesystem", command=copy_from_filesystem)
    button2.pack(pady=20)

    

    root.mainloop()

if __name__ == "__main__":
    main()