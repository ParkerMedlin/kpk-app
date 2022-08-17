import pandas as pd # dataframes
import os # for obtaining user path
import psycopg2 # connect w postgres db
from SharepointDL import download_to_temp
import time
import warnings
import numpy as np
from datetime import datetime
warnings.filterwarnings("ignore")




def floatHourToTime(fh):
    hours, hourSeconds = divmod(fh, 1)
    minutes, seconds = divmod(hourSeconds * 60, 1)
    return (
        int(hours),
        int(minutes),
        int(seconds * 60),
    )


def GetHxBlends():

    print('GetHxBlends(), I choose you!')
    t1 = time.perf_counter()

    srcFilePath = download_to_temp("ProductionSchedule")
    if srcFilePath=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return

    sheetDF = pd.read_excel(srcFilePath, 'Horix Line', usecols = 'A:L') #create dataframe for the Horix line sheet we're currently on

    sheetDFnofirstrow = sheetDF.iloc[1: , :]
    sheetDFnofirstrow.columns = sheetDFnofirstrow.iloc[0]
    sheetDFnofirstrow = sheetDFnofirstrow[1:]
    sheetDFdropColumns = sheetDFnofirstrow.drop(sheetDFnofirstrow.columns[0], axis=1)
    sheetDFnoNA = sheetDFdropColumns.dropna(axis=0, how='any', subset=['Amt'])
    sheetDFnoNA = sheetDFnoNA.dropna(axis=0, how='any', subset=['PO #'])
    #convert excel serial to python date
    for i, row in sheetDFnoNA.iterrows():
        excel_date = sheetDFnoNA.at[i,'Run Date']
        py_datetime = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
        sheetDFnoNA.at[i,'Run Date']= py_datetime
    sheetDFnoNA['id']=range(1,len(sheetDFnoNA)+1)
    sheetDFnoNA.loc[sheetDFnoNA['Case Size']=='6-1gal',['gal_factor','Line']]= 6, "Hx"
    sheetDFnoNA.loc[sheetDFnoNA['Case Size']=='55gal drum',['gal_factor','Line']]= 55, "Dm"
    sheetDFnoNA.loc[sheetDFnoNA['Case Size']=='5 gal pail',['gal_factor','Line']]= 5, "Pails"
    sheetDFnoNA.loc[sheetDFnoNA['Case Size']=='275 gal tote',['gal_factor','Line']]= 275, "Totes"
    sheetDFnoNA.loc[sheetDFnoNA['Case Size']=='265 gal tote',['gal_factor','Line']]= 265, "Totes"
    sheetDFnoNA['gallonQty']=sheetDFnoNA['gal_factor']*sheetDFnoNA['Case Qty']
    sheetDFnoNA.loc[sheetDFnoNA['Line']=="Hx",'num_blends']=sheetDFnoNA['gallonQty']/5100
    sheetDFnoNA.loc[sheetDFnoNA['Line']=="Dm",'num_blends']=sheetDFnoNA['gallonQty']/2925
    sheetDFnoNA.loc[sheetDFnoNA['Line']=="Pails",'num_blends']=sheetDFnoNA['gallonQty']/2925
    sheetDFnoNA.loc[sheetDFnoNA['Line']=="Totes",'num_blends']=sheetDFnoNA['gallonQty']/2925
    sheetDFnoNA['num_blends'] = sheetDFnoNA['num_blends'].apply(np.ceil)
    print(sheetDFnoNA)
    
    sheetDFnewIndex = sheetDFnoNA.reset_index(drop=True)

    print(sheetDFnewIndex)

    sheetDFnewIndex.to_csv('init-db-imports\hxblnd.csv', header=True, index=False) #write to the csv in our folder

    os.remove(srcFilePath) #delete the temp sourcefile  

    # put the csv into postgres
    dHeadNameList = list(sheetDFnewIndex.columns)
    dHeadLwithTypes = '('
    for columnName in dHeadNameList:
        columnNameStr = str(columnName)
        columnNameStr = columnNameStr.replace("/","")
        columnNameStr = columnNameStr.replace(" ","_")
        columnNameStr = columnNameStr.replace("#","")
        if "Run_Date" in columnNameStr:
            columnNameStr = columnNameStr +' date, '
        else:
            columnNameStr = columnNameStr +' text, '
        dHeadLwithTypes += columnNameStr 
    dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'
    print(dHeadLwithTypes)
    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursPG = cnxnPG.cursor()
    cursPG.execute("CREATE TABLE hx_blendthese_TEMP"+dHeadLwithTypes)
    copy_sql = "COPY hx_blendthese_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open('init-db-imports\hxblnd.csv', 'r', encoding='utf-8') as f:
        cursPG.copy_expert(sql=copy_sql, file=f)
    cursPG.execute("DROP TABLE IF EXISTS hx_blendthese")
    cursPG.execute("alter table hx_blendthese_TEMP rename to hx_blendthese")
    cnxnPG.commit()
    cursPG.close()
    cnxnPG.close()

    ### show how long it all took
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')