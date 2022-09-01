import pyodbc
import csv
import ctypes
import time

t1 = time.perf_counter()

messageBox = ctypes.windll.user32.MessageBoxW

cnxn = pyodbc.connect("DSN=SOTAMAS90", autocommit=True)

cursor = cnxn.cursor() 

cursor.execute("SELECT * FROM BM_BillDetail")

data = cursor.fetchall()

with open('bom-main.csv','w', newline='') as out:
        csv_out=csv.writer(out)
        for row in data:
            csv_out.writerow(row)

t2 = time.perf_counter()
messageBox(None,f'Complete in {t2 - t1:0.4f} seconds','CSV Bro')