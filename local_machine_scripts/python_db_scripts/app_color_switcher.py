import os
import shutil

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

nginx_conf_path = os.path.expanduser('~\\Documents\\nginx.conf')
os.system(f"docker cp kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf {nginx_conf_path}")

if check_file_for_string(nginx_conf_path, "server app_blue:8001;"):
    print(f"The nginx.conf file is pointing to the blue container.\nSwitching to green.")
    replace_string_in_file(nginx_conf_path, "server app_blue:8001;","server app_green:8002;")

elif check_file_for_string(nginx_conf_path, "server app_green:8002;"):
    print(f"The nginx.conf file is pointing to the green container.\nSwitching to blue.")
    replace_string_in_file(nginx_conf_path, "server app_green:8002;","server app_blue:8001;")

os.system(f"docker cp {nginx_conf_path} kpk-app_nginx_1:/etc/nginx/conf.d/nginx.conf")
os.remove(nginx_conf_path)