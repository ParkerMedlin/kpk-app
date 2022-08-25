import subprocess
import time


while(True):
    subprocess.call([r'C:\Users\pmedl\Documents\kpk-app\scripts\batch-scripts\db-backup.bat'])
    time.sleep(7200)