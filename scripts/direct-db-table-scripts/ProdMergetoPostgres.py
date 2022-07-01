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

def GetLatestProdMerge():
    print('GetLatestProdMerge(), I choose you!')
    t1 = time.perf_counter()

    srcFilePath = download_to_temp("ProductionSchedule")
    if srcFilePath=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return

    # create the csv and write in the header row
    headers = ["billno", "po", "description", "blendPN", "case_size", "qty", "bottle", "cap", "runtime", "carton","starttime","line"]
    with open('init-db-imports\prodmerge1.csv', 'w') as my_new_csv:
        writer = csv.writer(my_new_csv)
        writer.writerow(headers)
    # for each line's sheet, create a dataframe and append that to the csv
    sheetList = ["BLISTER", "INLINE", "JB LINE", "KITS", "OIL LINE", "PD LINE"]
    for sheet in sheetList:
        print(sheet) #print the name of the current sheet for this iteration
        currentSheetDF = pd.read_excel(srcFilePath, sheet, skiprows = 2, usecols = 'C:L') #create dataframe for the sheet we're currently on
        cSdFnoNaN = currentSheetDF.dropna(axis=0, how='any', subset=['Runtime']) #drop all rows where Runtime is equal to NaN
        cSdFnoSpaces = cSdFnoNaN[cSdFnoNaN["Runtime"].str.contains(" ", na=False) == False] #filter out rows containing spaces
        cSdFno0x2a = cSdFnoSpaces[cSdFnoSpaces["Product"].str.contains("0x2a", na=False) == False] #filter out rows containing 0x2a
        cSdFnoSchEnd = cSdFno0x2a[cSdFno0x2a["Runtime"].str.contains("SchEnd", na=False) == False] #filter out the SchEnd row
        cSdFnoSchEnd["Starttime"] = cSdFnoSchEnd["Runtime"].cumsum() #create Starttime column
        cSdFnewIndex = cSdFnoSchEnd.reset_index(drop=True) #redo the row index so it's actually sequential
        cSdFnewIndex["Starttime"] = cSdFnewIndex["Starttime"].shift(1, fill_value=0) #shift Starttime down by 1 row so it is correct
        cSdFnewIndex["prodline"] = sheet #insert the correct production line for this iteration
        cSdFnewIndex["ID2"] = np.arange(len(cSdFnewIndex))+1
        print(cSdFnewIndex)
        print(sheet+" DONE") #sheet done
        cSdFnewIndex.to_csv('init-db-imports\prodmerge1.csv', mode='a', header=False, index=False) #write to the csv in our folder

    with open('init-db-imports\prodmerge1.csv', newline='') as in_file:
        with open('init-db-imports\prodmerge.csv', 'w', newline='') as out_file:
            writer = csv.writer(out_file)
            for row in csv.reader(in_file):
                if row:
                    writer.writerow(row)

    os.remove('init-db-imports\prodmerge1.csv') #delete the temp csv
    os.remove(srcFilePath) #delete the temp prod schedule 

    # put the csv into postgres
    # dHeadNameList = list(cSdFnewIndex.columns)
    dHeadLwithTypes = '''(P_N text, 
                PO_Num text, 
                Product text, 
                Blend text, 
                Case_Size text, 
                Qty numeric, 
                Bottle text, 
                Cap text, 
                Runtime numeric, 
                Carton text, 
                Starttime numeric, 
                prodline text, 
                ID2 numeric)'''
    # dHeadLwithTypes = '('
    # listPos = 0
    # i = 0
    # for i in range(len(cSdFnewIndex.columns)):
    #     dHeadNameList[listPos] = (dHeadNameList[listPos]).replace("/","_")
    #     dHeadNameList[listPos] = (dHeadNameList[listPos]).replace(" ","_")
    #     dHeadNameList[listPos] = (dHeadNameList[listPos]).replace("#","Num")
    #     dHeadLwithTypes += dHeadNameList[listPos]
    #     if dHeadNameList[listPos] == "Carton":
    #         dHeadLwithTypes += ' text, '
    #         listPos += 1
    #         continue
    #     if dHeadNameList[listPos] == "P_N":
    #         dHeadLwithTypes += ' text, '
    #         listPos += 1
    #         continue
    #     if dHeadNameList[listPos] == "PO_Num":
    #         dHeadLwithTypes += ' text, '
    #         listPos += 1
    #         continue
    #     if str(type(cSdFnewIndex.iat[2,listPos])) == "<class 'str'>":
    #         dHeadLwithTypes += ' text, '
    #     elif str(type(cSdFnewIndex.iat[2,listPos])) == "<'datetime.date'>":
    #         dHeadLwithTypes += ' date, '
    #     elif str(type(cSdFnewIndex.iat[2,listPos])) == "<class 'numpy.float64'>":
    #         dHeadLwithTypes += ' numeric, '
    #     elif str(type(cSdFnewIndex.iat[2,listPos])) == "<class 'int'>":
    #         dHeadLwithTypes += ' numeric, '
    #     elif str(type(cSdFnewIndex.iat[2,listPos])) == "<class 'numpy.int32'>":
    #         dHeadLwithTypes += ' numeric, '
    #     elif str(type(cSdFnewIndex.iat[2,listPos])) == "<class 'float'>":
    #         dHeadLwithTypes += ' numeric, '
    #     listPos += 1
    #     print(dHeadLwithTypes)
    # dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'
    # print(dHeadLwithTypes)

    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursPG = cnxnPG.cursor()
    cursPG.execute("CREATE TABLE prodmerge_run_data_TEMP"+dHeadLwithTypes)
    copy_sql = "COPY prodmerge_run_data_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open('init-db-imports\prodmerge.csv', 'r', encoding='utf-8') as f:
        cursPG.copy_expert(sql=copy_sql, file=f)
    cursPG.execute("DROP TABLE IF EXISTS prodmerge_run_data")
    cursPG.execute("alter table prodmerge_run_data_TEMP rename to prodmerge_run_data")
    cnxnPG.commit()
    cursPG.close()
    cnxnPG.close()

    ### show how long it all took
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')