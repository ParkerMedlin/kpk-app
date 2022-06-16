from __future__ import generators
import pyodbc # connect w Sage db
import psycopg2 # connect w postgres db
import ctypes # timer msgbox
import time # time for timer msgbox
#import easygui # user input for which table to grab from Sage db
import pandas as pd # needed for dataframes
import os # for obtaining user path
import datetime # for the date filter on IM_ItemTransactionHistory
from art import *

def GetLatestSage():
    print('GetLatestSage():')
    t1 = time.perf_counter() # creating the time object for insertion into the messageBox at the end
    messageBox = ctypes.windll.user32.MessageBoxW # creating the messageBox object
    cancelBox = ctypes.windll.user32.MessageBoxW # creating the messageBox object

    tblList = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
    inc = 0
    for i in range(len(tblList)):
        ### ODBC CONNECTION TO COLLECT THE DATA ###
        cnxnMAS = pyodbc.connect("DSN=SOTAMAS90;UID=parker;PWD=blend2021;",autocommit=True) 
        cursMAS = cnxnMAS.cursor()
        # tblName = easygui.enterbox('Enter table name:', 'Table Name')
        tblName = tblList[i]
        if type(tblName) == type(None) :
            cancelBox = (None,'Refresh cancelled.','Cancelled')
            exit()
        dateRestr = str(datetime.date.today() - datetime.timedelta(weeks=20))

        if tblName == "IM_ItemTransactionHistory":
            cursMAS.execute("SELECT * FROM "+tblName+" WHERE IM_ItemTransactionHistory.TransactionDate > {d '%s'}" % dateRestr) # grab the whole table contents n everything
        else:
            cursMAS.execute("SELECT * FROM "+tblName)
        t2 = time.perf_counter()
        print('don laod '+tblName+f' {t2 - t1:0.4f} seconds')

        data = list(cursMAS.fetchall()) # store the table, contents ONLY. list of tuples
        t2 = time.perf_counter()
        print('fetchall '+tblName+f" {t2 - t1:0.4f} seconds spent mining bitcoin")
        dataHeaderInfo = cursMAS.description # store the column names and metadata in a list of tuples
        dataHeaders = cursMAS.description

        ### maybe someday look at this one with a critical eye
        dHeadLwithTypes = '(id serial primary key, '
        listPos = 0
        i = 0
        for i in range(len(dataHeaders)):
            dHeadLwithTypes = dHeadLwithTypes+dataHeaders[listPos][0]
            if str(dataHeaders[listPos][1]) == "<class 'str'>":
                dHeadLwithTypes = dHeadLwithTypes+' text, '
            elif str(dataHeaders[listPos][1]) == "<class 'datetime.date'>":
                dHeadLwithTypes = dHeadLwithTypes+' date, '
            elif str(dataHeaders[listPos][1]) == "<class 'decimal.Decimal'>":
                dHeadLwithTypes = dHeadLwithTypes+' decimal, '
            listPos += 1
        dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'

        dataHeadNoParen = ''
        q = 0
        for q in range(len(dataHeaders)):
            dataHeadNoParen = dataHeadNoParen + dataHeaders[q][0]+', '
        dataHeadNoParen = dataHeadNoParen[:len(dataHeadNoParen)-2]
        dataHeaderListString = "("+dataHeadNoParen+")"
        dHeadList = dataHeadNoParen.split(",")

        cursMAS.close()
        cnxnMAS.close()

        ### CURRENT USER DOCUMENTS PATH FOR CSV ###
        csvPathStr = os.path.expanduser('~\Documents')+"\\"+tblName+'.csv'

        # make dataframe
        tblDF = pd.DataFrame.from_records(data, index=None, exclude=None, columns=dHeadList, coerce_float=False, nrows=None)
        tblDF.to_csv(path_or_buf=csvPathStr, header=dHeadList, encoding='utf-8')
        print('csv saved for '+tblName)

        ### PSYCO CONNECTION TO PUSH THE DATA TO POSTGRES TABLE ###
        cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursPG = cnxnPG.cursor()

        cursPG.execute("DROP TABLE IF EXISTS "+tblName)
        cursPG.execute("CREATE TABLE "+tblName+dHeadLwithTypes)
        copy_sql = "COPY "+tblName+" FROM stdin WITH CSV HEADER DELIMITER as ','"

        with open(csvPathStr, 'r', encoding='utf-8') as f:
            cursPG.copy_expert(sql=copy_sql, file=f)

        cnxnPG.commit()
        cursPG.close()
        cnxnPG.close()
        os.remove(csvPathStr)
        

    ### show how long it all took
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')
GetLatestSage()