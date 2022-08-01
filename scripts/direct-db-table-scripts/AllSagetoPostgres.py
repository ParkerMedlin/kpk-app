from __future__ import generators
import pyodbc # connect w Sage db
import psycopg2 # connect w postgres db
import time # time for timer 
import pandas as pd # needed for dataframes
import os # for obtaining user path
import datetime # for the date filter on IM_ItemTransactionHistory

def GetSageTable(tblName):
    print('GetSageTable(~~'+tblName+'~~)')
    t1 = time.perf_counter() # creating the time object for start time of this function
    cnxnMAS = pyodbc.connect("DSN=SOTAMAS90;UID=parker;PWD=blend2021;",autocommit=True) # odbc connection to get the data
    cursMAS = cnxnMAS.cursor() # cursor from odbc connection
    if tblName == "IM_ItemTransactionHistory":
        dateRestr = str(datetime.date.today() - datetime.timedelta(weeks=24)) # set value of date restraint for query
        cursMAS.execute("SELECT * FROM "+tblName+" WHERE IM_ItemTransactionHistory.TransactionDate > {d '%s'}" % dateRestr) # grab the whole table contents n everything
    else:
        cursMAS.execute("SELECT * FROM "+tblName)
    t2 = time.perf_counter()
    print('don laod '+tblName+f' {t2 - t1:0.4f} seconds')
    tableContents = list(cursMAS.fetchall()) # store the table, contents ONLY. list of tuples
    t2 = time.perf_counter()
    print('fetchall '+tblName+f' {t2 - t1:0.4f} seconds spent mining bitcoin')
    dataHeaders = cursMAS.description # store the column names and metadata in a list of tuples
    ### maybe someday look at this one with a critical eye
    dHeadLwithTypes = '(id serial primary key, '
    listPos = 0 # position holder for the current item being read
    iter = 0
    for iter in range(len(dataHeaders)): # construct the sql table construction string manually
        dHeadLwithTypes = dHeadLwithTypes+dataHeaders[listPos][0]
        if str(dataHeaders[listPos][1]) == "<class 'str'>":
            dHeadLwithTypes = dHeadLwithTypes+' text, '
        elif str(dataHeaders[listPos][1]) == "<class 'datetime.date'>":
            dHeadLwithTypes = dHeadLwithTypes+' date, '
        elif str(dataHeaders[listPos][1]) == "<class 'decimal.Decimal'>":
            dHeadLwithTypes = dHeadLwithTypes+' decimal, '
        listPos += 1
    dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'
    dataHeadNoParen = '' # empty string where dataheaders will be listed
    qiter = 0
    for qiter in range(len(dataHeaders)):
        dataHeadNoParen = dataHeadNoParen + dataHeaders[qiter][0]+', '
    dataHeadNoParen = dataHeadNoParen[:len(dataHeadNoParen)-2]
    dHeadList = dataHeadNoParen.split(",") 
    cursMAS.close() # close the cursor since we have our info
    cnxnMAS.close() # close the connection
    csvPathStr = os.path.expanduser('~\Documents')+'\\'+tblName+'.csv' # establish current user path for csv
    tblDF = pd.DataFrame.from_records(tableContents, index=None, exclude=None, columns=dHeadList, coerce_float=False, nrows=None) # cursor to df
    tblDF.to_csv(path_or_buf=csvPathStr, header=dHeadList, encoding='utf-8') # df to csv
    print('csv saved for '+tblName)
    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb') # connection for dumping info into postgres
    cursPG = cnxnPG.cursor() # cursor for dumping info into postgres
    cursPG.execute("drop table if exists "+tblName+"_TEMP") # make sure temp table is out of there
    cursPG.execute("create table "+tblName+"_TEMP"+dHeadLwithTypes) # make temp table
    copy_sql = "copy "+tblName+"_TEMP from stdin with csv header delimiter as ','" # fill up temp table 
    with open(csvPathStr, 'r', encoding='utf-8') as f:
        cursPG.copy_expert(sql=copy_sql, file=f) # copy the csv into the table we just created
    cursPG.execute("drop table if exists "+tblName) # drop old table
    cursPG.execute("alter table "+tblName+"_TEMP rename to "+tblName) # rename temp table 
    cnxnPG.commit() # tie
    cursPG.close() # up
    cnxnPG.close() # loose 
    os.remove(csvPathStr) # ends
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly') # how long the whole thing took