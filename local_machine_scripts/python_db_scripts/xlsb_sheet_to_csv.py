import os
from os.path import exists
import subprocess
from sharepoint_download import download_to_temp
import pandas as pd

def lot_numbers_to_csv():
    temp_xlsb_path = download_to_temp('LotNumGenerator')
    temp_csv_path = temp_xlsb_path[:-6] + '.csv'
    if exists(temp_csv_path):
        os.remove(temp_csv_path)
    path_to_vb_script = os.path.expanduser('~\\Documents') + '\\kpk-app\\local_machine_scripts\\vb_scripts\\LotNumsToCsv.vbs'
    subprocess.call("cscript " + path_to_vb_script + " " + temp_xlsb_path + " " + temp_csv_path, shell=False)
    os.remove(temp_xlsb_path)
    lot_number_df = pd.read_csv(temp_csv_path)
    lot_number_df  = lot_number_df.iloc[: , :6]
    lot_number_df = lot_number_df.dropna(axis=0, how='any', subset=['Part_Number'])
    os.remove(temp_csv_path)
    lot_number_df.to_csv(path_or_buf=temp_csv_path, index=False)

def blend_counts_to_csv():
    temp_xlsb_path = download_to_temp('BlendingSchedule')
    temp_csv_path = temp_xlsb_path[:-6] + '.csv'
    if exists(temp_csv_path):
        os.remove(temp_csv_path)
    path_to_vb_script = os.path.expanduser('~\\Documents') + '\\kpk-app\\local_machine_scripts\\vb_scripts\\BlndCountToCsv.vbs'
    subprocess.call("cscript " + path_to_vb_script + " " + temp_xlsb_path + " " + temp_csv_path, shell=False)
    os.remove(temp_xlsb_path)
    blend_counts_df = pd.read_csv(temp_csv_path)
    blend_counts_df  = blend_counts_df.loc[:, ['Blend', 'Desc', 'hr', 'expOH', 'Count', 'CountDate', 'Difference']]
    blend_counts_df = blend_counts_df.dropna(axis=0, how='any', subset=['Blend'])
    blend_counts_df = blend_counts_df.replace('', 0)
    os.remove(temp_csv_path)
    final_csv_path = temp_xlsb_path[:-11] + 'counts.csv'
    blend_counts_df.to_csv(path_or_buf=final_csv_path, index=False)