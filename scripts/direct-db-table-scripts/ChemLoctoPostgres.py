import pandas as pd # dataframes
import os # for obtaining user path
import psycopg2 # connect w postgres db
import pyexcel as pe # grab the sheet
import csv
from SharepointDL import download_to_temp
import time
import warnings
warnings.filterwarnings("ignore")
import numpy as np

def GetChemLocations():
    print('GetChemLocations(), I choose you!')
    t1 = time.perf_counter()

    srcFilePath = download_to_temp("BlendingSchedule")
    if srcFilePath=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return
        
    sheetDF = pd.read_excel(srcFilePath, 'ChemLocation', usecols = 'A:G') #create dataframe for the sheet we're currently on
    sheetDF.to_csv('init-db-imports\chemloc.csv', header=True, index=False) #write to the csv in our folder
    print(sheetDF)

    os.remove(srcFilePath) #delete the temp sourcefile  

    # put the csv into postgres
    dHeadNameList = list(sheetDF.columns)
    dHeadLwithTypes = '('
    for columnName in dHeadNameList:
        columnName += ' text, '
        dHeadLwithTypes += columnName
    dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'
    print(dHeadLwithTypes)

    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursPG = cnxnPG.cursor()
    cursPG.execute("CREATE TABLE chem_location_TEMP"+dHeadLwithTypes)
    copy_sql = "COPY chem_location_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open('init-db-imports\chemloc.csv', 'r', encoding='utf-8') as f:
        cursPG.copy_expert(sql=copy_sql, file=f)
    cursPG.execute("DROP TABLE IF EXISTS chem_location")
    cursPG.execute("alter table chem_location_TEMP rename to chem_location")
    cnxnPG.commit()
    cursPG.close()
    cnxnPG.close()

    ### show how long it all took
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')