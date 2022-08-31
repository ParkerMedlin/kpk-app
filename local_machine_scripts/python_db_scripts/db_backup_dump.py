import subprocess
import time

while(True):
    subprocess.call([r'C:\Users\pmedl\Documents\kpk-app\scripts\batch-scripts\db_backup.bat'])
    print('Database dumped. Sleeping for 2 hours then taking another dump')
    time.sleep(7200)