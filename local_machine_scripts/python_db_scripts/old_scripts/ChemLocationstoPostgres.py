#import ctypes # timer msgbox
#import time # time for timer msgbox
import pandas as pd # dataframes
import os # for obtaining user path
import psycopg2 # connect w postgres db
import pyexcel as pe # grab the sheet

#t1 = time.perf_counter() # creating the time object for insertion into the messageBox at the end
#messageBox = ctypes.windll.user32.MessageBoxW # creating the messageBox object

srcFilePath = "C:\OD\Kinpak, Inc\Blending - Documents\\03 Projects\Blending Schedule\Blending-Schedule\BlendingSchedule_2.0.xlsb"
sheetName = 'ChemLocation'
tempPath = os.path.expanduser('~\\Documents')+"\\"+sheetName+'.csv'
pyexcelSheet = pe.get_sheet(file_name=srcFilePath, sheet_name=sheetName)
pyexcelSheet.save_as(tempPath)
sheetDataFrame = pd.read_csv(tempPath)
nan_value = float("NaN")
sheetDataFrame.replace("", nan_value, inplace=True) # ugh
sheetDataFrame.replace(" ", nan_value, inplace=True) # ugh
sheetDataFrame.replace("  ", nan_value, inplace=True) # ugh
sheetDataFrame.dropna(how='all', axis=1, inplace=True) # ugh
sheetDataFrame.columns = sheetDataFrame.columns.str.replace('?','')
os.remove(tempPath)
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
print(dHeadLwithTypes)

cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
cursPG = cnxnPG.cursor()
cursPG.execute("DROP TABLE IF EXISTS "+sheetName)
cursPG.execute("CREATE TABLE "+sheetName+dHeadLwithTypes)
copy_sql = "COPY "+sheetName+" FROM stdin WITH CSV HEADER DELIMITER as ','"
with open(tempPath, 'r', encoding='utf-8') as f:
    cursPG.copy_expert(sql=copy_sql, file=f)
cnxnPG.commit()
cursPG.close()
cnxnPG.close()
os.remove(tempPath)

### show how long it all took
#t2 = time.perf_counter()
#messageBox(None,f'Complete in {t2 - t1:0.4f} seconds','world record prolly')














### AUTHENTICATE WITH SHAREPOINT ### : https://stackoverflow.com/questions/48424045/how-to-read-sharepoint-online-office365-excel-files-in-python-with-work-or-sch

#import io # save spreadsheet to memory
#import office365
#from office365.runtime.auth.authentication_context import AuthenticationContext
#from office365.sharepoint.client_context import ClientContext
#from office365.sharepoint.files.file import File

#url = 'https://adminkinpak.sharepoint.com/sites/PDTN'
#username = 'pmedlin@kinpakinc.com'
#password = 'K2P1K#02'
#relative_url = '/sites/PDTN/Shared%20Documents/Production%20Schedule/Starbrite%20KPK%20production%20schedule.xlsb'
#print(relative_url)
#ctx_auth = AuthenticationContext(url)
#if ctx_auth.acquire_token_for_user(username, password):
#  ctx = ClientContext(url, ctx_auth)
#  web = ctx.web
#  ctx.load(web)
#  ctx.execute_query()
#  print("Web title: {0}".format(web.properties['Title']))
#else:
#  print(ctx_auth.get_last_error())

### SAVE FILE AND READ IT
#response = File.open_binary(ctx, relative_url)
# save data to BytesIO stream
#bytes_file_obj = io.BytesIO()
#bytes_file_obj.write(response.content)
#bytes_file_obj.seek(0) # set file object to start