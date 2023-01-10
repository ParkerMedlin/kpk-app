import subprocess
import time
import os

batchfile_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\db_backup.bat')

while True:
    subprocess.call([batchfile_path])
    print('Database dumped. Sleeping for 2 hours then taking another dump')
    time.sleep(7200)