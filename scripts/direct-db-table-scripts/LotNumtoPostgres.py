import pandas as pd # dataframes
import os # for obtaining user path
import psycopg2 # connect w postgres db
from SharepointDL import download_to_temp
import time
import warnings
import datetime as dt
from datetime import datetime

warnings.filterwarnings("ignore")

def GetLotNumbers():
    print('GetLotNumbers(), I choose you!')
    t1 = time.perf_counter()

    srcFilePath = download_to_temp("LotNumGenerator")
    if srcFilePath=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return
    sheetDFpre = pd.read_excel(srcFilePath, 'LotNumberGenerator', usecols = 'A:F') #create dataframe for the Chem Locations sheet
    sheetDFnoNaN = sheetDFpre.dropna(axis=0, how='any', subset=['date_created'])
    sheetDF = sheetDFnoNaN.iloc[1:, :]
    sheetDF['id']=range(1,len(sheetDF)+1)
    sheetDF.date_created = pd.TimedeltaIndex(sheetDF.date_created.astype(int), unit='d') + datetime(1900, 1, 1)
    # sheetDF["date_created"] = sheetDF["date_created"].apply(convertTheDate)

    sheetDF.to_csv('init-db-imports\lotnum.csv', header=True, index=False) #write to the csv in our folder
    os.remove(srcFilePath) #delete the temp sourcefile  

    # put the csv into postgres
    dHeadNameList = list(sheetDF.columns)
    dHeadLwithTypes = '('
    for columnName in dHeadNameList:
        if columnName == 'lot_number':
            columnName += ' primary key, '
        else:
            columnName += ' text, '
        dHeadLwithTypes += columnName
    dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'
    print(dHeadLwithTypes)

    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursPG = cnxnPG.cursor()
    cursPG.execute("CREATE TABLE lotnumrecord_TEMP"+dHeadLwithTypes)
    copy_sql = "COPY lotnumrecord_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open('init-db-imports\lotnum.csv', 'r', encoding='utf-8') as f:
        cursPG.copy_expert(sql=copy_sql, file=f)
    cursPG.execute("DROP TABLE IF EXISTS lotnumrecord")
    cursPG.execute("alter table lotnumrecord_TEMP rename to lotnumrecord")
    cnxnPG.commit()
    cursPG.close()
    cnxnPG.close()

    ### show how long it all took
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')