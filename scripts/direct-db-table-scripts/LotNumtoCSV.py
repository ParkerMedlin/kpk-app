from SharepointDL import download_to_temp
import subprocess
import os
from os.path import exists
import pandas as pd

def lotNumsToCSV():
    temp_xlsb_path = download_to_temp('LotNumGenerator')
    temp_csv_path = temp_xlsb_path[:-6] + '.csv'
    if exists(temp_csv_path):
        os.remove(temp_csv_path)
    subprocess.call("cscript .\scripts\direct-db-table-scripts\XlsToCsv.vbs "+temp_xlsb_path+" "+temp_csv_path, shell=False)
    os.remove(temp_xlsb_path)
    lotnumDF = pd.read_csv(temp_csv_path)
    lotnumDFfirst5Columns  = lotnumDF.iloc[: , :5]
    lotnumDFnoNA = lotnumDFfirst5Columns.dropna(axis=0, how='any', subset=['Part_Number'])
    os.remove(temp_csv_path)
    lotnumDFnoNA.to_csv(path_or_buf=temp_csv_path, index=False)

lotNumsToCSV


