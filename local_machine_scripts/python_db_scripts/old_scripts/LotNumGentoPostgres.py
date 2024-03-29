#import ctypes # timer msgbox
#import time # time for timer msgbox
import pandas as pd # dataframes
import os # for obtaining user path
import psycopg2 # connect w postgres db
import pyexcel as pe # grab the sheet

#t1 = time.perf_counter() # creating the time object for insertion into the messageBox at the end
#messageBox = ctypes.windll.user32.MessageBoxW # creating the messageBox object
srcFilePath = "C:\OD\Kinpak, Inc\Blending - Documents\\01 Spreadsheet Tools\Blending Lot Number Generator\Blending Lot Number Generator.xlsb"
sheetName = 'LotNumberGenerator'
tempPath = os.path.expanduser('~\\Documents')+"\\"+sheetName+'.csv'
pyexcelSheet = pe.get_sheet(file_name=srcFilePath, sheet_name=sheetName, column_limit=5)
pyexcelSheet.save_as(tempPath)
sheetDataFrame = pd.read_csv(tempPath)
os.remove(tempPath)
nan_value = float("NaN")
sheetDataFrame.replace("", nan_value, inplace=True) # ugh
sheetDataFrame.replace(" ", nan_value, inplace=True) # ugh
sheetDataFrame.replace("  ", nan_value, inplace=True) # ugh
sheetDataFrame.dropna(how='all', axis=1, inplace=True) # ugh
sheetDataFrame.columns = sheetDataFrame.columns.str.replace(' ','_')
sheetDataFrame.columns = sheetDataFrame.columns.str.replace('.','_')
sheetDataFrame.columns = sheetDataFrame.columns.str.replace(':','_')
sheetDataFrame['Date'] = pd.to_datetime(sheetDataFrame['Date'], unit='D', origin='1899-12-30').dt.strftime("%m-%d-%Y")
dHeadNameList = list(sheetDataFrame.columns)
sheetDataFrame.to_csv(path_or_buf=tempPath, header=dHeadNameList, encoding='utf-8')
print('csv saved for sheet '+sheetName)

dHeadLwithTypes = '(id serial primary key, '
listPos = 0
i = 0
for i in range(len(sheetDataFrame.columns)):
    dHeadLwithTypes += dHeadNameList[listPos]
    if str(type(sheetDataFrame.iat[2,listPos])) == "<class 'str'>":
        dHeadLwithTypes += ' text, '
    elif str(type(sheetDataFrame.iat[2,listPos])) == "<'datetime.date'>":
        dHeadLwithTypes += ' date, '
    elif str(type(sheetDataFrame.iat[2,listPos])) == "<class 'numpy.float64'>":
        dHeadLwithTypes += ' numeric, '
    elif str(type(sheetDataFrame.iat[2,listPos])) == "<class 'int'>":
        dHeadLwithTypes += ' numeric, '
    listPos += 1
dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'

cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
cursPG = cnxnPG.cursor()
cursPG.execute("DROP TABLE IF EXISTS lotnumexcel")
cursPG.execute("CREATE TABLE lotnumexcel"+dHeadLwithTypes)
copy_sql = "COPY lotnumexcel FROM stdin WITH CSV HEADER DELIMITER as ','"
with open(tempPath, 'r', encoding='utf-8') as f:
    cursPG.copy_expert(sql=copy_sql, file=f)
cursPG.execute("DELETE FROM lotnumexcel WHERE description IS NULL")
cnxnPG.commit()
cursPG.close()
cnxnPG.close()
os.remove(tempPath)

### show how long it all took
#t2 = time.perf_counter()
#messageBox(None,f'Complete in {t2 - t1:0.4f} seconds','world record prolly')