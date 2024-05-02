import os
import subprocess
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

def camel_case_convert(name):
    components = name.split('_')
    return ''.join(x.title() for x in components)

def launch_script(script_path):
    subprocess.Popen(['pythonw', script_path], shell=True)

def create_quilt_pattern_image():
    # Create an empty array for the image
    size = 50  # Image size
    array = np.zeros((size, size), dtype=np.uint8)

    # Define the size of each patch in the quilt
    patch_size = 10
    for i in range(0, size, patch_size):
        for j in range(0, size, patch_size):
            # Generate a random shade of grey for each patch
            shade = np.random.randint(0, 256)
            array[i:i+patch_size, j:j+patch_size] = shade

    # Create an image from the array
    return Image.fromarray(array, 'L')

def create_gui(scripts_info):
    root = tk.Tk()
    root.title("Pystray Launcher")

    # Use grid layout for tiles
    row = 0
    col = 0
    for script, details in scripts_info.items():
        frame = tk.Frame(root, borderwidth=1, relief="solid")
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Generate and display the quilt pattern icon
        img = create_quilt_pattern_image()
        img = img.resize((50, 50), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        button = tk.Button(frame, image=photo, command=lambda s=script: launch_script(s))
        button.image = photo  # keep a reference!
        button.pack(pady=10)

        label = tk.Label(frame, text=details['title'])
        label.pack()

        col += 1
        if col > 2:  # Adjust the number of columns per your layout needs
            col = 0
            row += 1

    root.mainloop()

def main():
    directory = r'C:\Users\pmedlin\Documents\kpk-app\local_machine_scripts\python_systray_scripts'
    scripts_info = {}

    # Get the absolute path of the current script
    current_script = os.path.abspath(__file__)

    for filename in os.listdir(directory):
        script_path = os.path.join(directory, filename)
        if filename.endswith('.pyw') and script_path != current_script:
            title = camel_case_convert(filename.replace('.pyw', ''))
            scripts_info[script_path] = {'title': title, 'icon': 'default_icon.png'}

    create_gui(scripts_info)

if __name__ == "__main__":
    main()