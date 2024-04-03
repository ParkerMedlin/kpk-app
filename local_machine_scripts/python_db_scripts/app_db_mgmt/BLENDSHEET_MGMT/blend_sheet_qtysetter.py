import pyexcel as pe
import pandas as pd
import os
import csv
from openpyxl import load_workbook

def set_blend_sheet_quantities():
    # Loop through the main folder and then the AF/ww folders, building list of all filepaths.
    file_list = []
    for root, dirs, files in os.walk(os.path.expanduser('~\\Desktop\\testers')):
        for file in files:
            if not file.endswith('.db') and not file.endswith('.tmp'):
                file_list.append(os.path.join(root,file))
    
    # Loop through each Excel file in the list and set cell F3 to 1
    for excel_file in file_list:
        if excel_file.endswith('.xlsx'):  # Ensure it's an Excel file
            try:
                workbook = load_workbook(filename=excel_file)
                sheet = workbook.active  # Assuming you want to modify the active sheet
                sheet['F3'] = 1000  # Set cell F3 to 1
                workbook.save(excel_file)  # Save the changes
            except Exception as e:
                print(str(e))
                continue

set_blend_sheet_quantities()