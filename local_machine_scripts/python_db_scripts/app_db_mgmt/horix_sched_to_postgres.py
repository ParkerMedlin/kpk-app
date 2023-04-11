import pandas as pd 
import os
import psycopg2
from .sharepoint_download import download_to_temp
import time
import warnings
import numpy as np
import datetime as dt
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

def get_horix_line_blends():

    source_file_path = download_to_temp("ProductionSchedule")
    if source_file_path=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return
    horix_csv_path  = (os.path.expanduser('~\\Documents')
                            +"\\kpk-app\\db_imports\\hx_sched.csv")
    sheet_df = pd.read_excel(source_file_path, 'Horix Line', usecols = 'A:L')
    sheet_df = sheet_df.iloc[1: , :]
    sheet_df.columns = sheet_df.iloc[0]
    sheet_df = sheet_df[1:]
    sheet_df = sheet_df.drop(sheet_df.columns[0], axis=1)
    sheet_df = sheet_df.dropna(axis=0, how='any', subset=['PO #'])
    sheet_df = sheet_df[sheet_df['PO #'] != 'XXXX']
    sheet_df = sheet_df[sheet_df['PO #'] != 'LineEnd']
    sheet_df = sheet_df[sheet_df['PO #'] != 'PailEnd']
    sheet_df = sheet_df[sheet_df['PO #'] != 'SchEnd']
    #convert excel serial to python date
    for i, row in sheet_df.iterrows():
        excel_date = sheet_df.at[i,'Run Date']
        py_datetime = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
        sheet_df.at[i,'Run Date']= py_datetime
    sheet_df['id']=range(1,len(sheet_df)+1)
    sheet_df.loc[sheet_df['Case Size']=='6-1gal',['gal_factor','Line']]= 6, "Hx"
    sheet_df.loc[sheet_df['Case Size']=='55gal drum',['gal_factor','Line']]= 55, "Dm"
    sheet_df.loc[sheet_df['Case Size']=='5 gal pail',['gal_factor','Line']]= 5, "Pails"
    sheet_df.loc[sheet_df['Case Size']=='275 gal tote',['gal_factor','Line']]= 275, "Totes"
    sheet_df.loc[sheet_df['Case Size']=='265 gal tote',['gal_factor','Line']]= 265, "Totes"
    sheet_df['gallonQty']=sheet_df['gal_factor']*sheet_df['Qty']
    sheet_df.loc[sheet_df['Line']=="Hx",'num_blends']=sheet_df['gallonQty']/5100
    sheet_df.loc[sheet_df['Line']=="Dm",'num_blends']=sheet_df['gallonQty']/2925
    sheet_df.loc[sheet_df['Line']=="Pails",'num_blends']=sheet_df['gallonQty']/2925
    sheet_df.loc[sheet_df['Line']=="Totes",'num_blends']=sheet_df['gallonQty']/2925
    sheet_df['num_blends'] = sheet_df['num_blends'].apply(np.ceil)
    today = dt.datetime.today()
    

    
    sheet_df = sheet_df.reset_index(drop=True)
    sheet_df.to_csv(horix_csv_path, header=True, index=False)
    os.remove(source_file_path)

    header_name_list = list(sheet_df.columns)
    sql_columns_with_types = '('
    for item in header_name_list:
        column_name = str(item)
        column_name = column_name.replace("/","")
        column_name = column_name.replace(" ","_")
        column_name = column_name.replace("#","")
        if "Run_Date" in column_name:
            column_name = column_name +' date, '
        else:
            column_name = column_name +' text, '
        sql_columns_with_types += column_name 
    sql_columns_with_types = sql_columns_with_types[:len(sql_columns_with_types)-2] + ')'
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("CREATE TABLE hx_blendthese_TEMP"+sql_columns_with_types)
    copy_sql = "COPY hx_blendthese_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open(horix_csv_path, 'r', encoding='utf-8') as f:
        cursor_postgres.copy_expert(sql=copy_sql, file=f)
    cursor_postgres.execute('''alter table hx_blendthese_TEMP rename column pn TO item_code;
                               alter table hx_blendthese_TEMP rename column blend TO component_item_code;
                               alter table hx_blendthese_TEMP rename column po_ TO purchase_order_number;
                               ''')
    cursor_postgres.execute("DROP TABLE IF EXISTS hx_blendthese")
    cursor_postgres.execute("alter table hx_blendthese_TEMP rename to hx_blendthese")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    print(f'{dt.datetime.now()}=======Horix line table created.=======')



#def get_lot_numbers():
#    print('get_lot_numbers(), I choose you!')
#    time_start = time.perf_counter()
#
#    source_file_path = download_to_temp("LotNumGenerator")
#    if source_file_path=='Error Encountered':
#        print('File not downloaded because of an error in the Sharepoint download function')
#        return
#    lot_num_csv_path  = (os.path.expanduser('~\\Documents')
#                            +"\\kpk-app\\db_imports\\lot_nums.csv")
#    sheet_df = pd.read_excel(source_file_path, 'LotNumberGenerator', usecols = 'A:X')
#    sheet_df = sheet_df.drop(sheet_df.columns[[22,20,17,16,15,14,13,12,11,10,9,8,7]], axis=1)
#    sheet_df = sheet_df.drop([0])
#    
#    sheet_df['date_created'] = sheet_df['date_created'].apply(lambda this_row: datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(this_row) - 2))
#    sheet_df['run_date'] = sheet_df['run_date'].apply(lambda this_row: None if(this_row=='-') else datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(this_row) - 2))
#    sheet_df['when_entered'] = sheet_df['when_entered'].apply(lambda this_row: None if(this_row=='Not Entered') else datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(this_row) - 2))
#    
#    sheet_df.to_csv(lot_num_csv_path, header=True, index=False)
#    os.remove(source_file_path)
#
#    header_name_list = list(sheet_df.columns)
#    sql_columns_with_types = '('
#    for item in header_name_list:
#        column_name = str(item)
#        if 'date_created' in column_name:
#            column_name = column_name +' date, '
#        elif 'run_date' in column_name:
#            column_name = column_name +' date, '
#        elif 'when_entered' in column_name:
#            column_name = column_name +' date, '
#        else:
#            column_name = column_name +' text, '
#        sql_columns_with_types += column_name
#
#    sql_columns_with_types = sql_columns_with_types[:len(sql_columns_with_types)-2] + ')'
#    print(sql_columns_with_types)
#    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
#    cursor_postgres = connection_postgres.cursor()
#    cursor_postgres.execute("CREATE TABLE lot_num_record_TEMP"+sql_columns_with_types)
#    copy_sql = "COPY lot_num_record_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
#    with open(lot_num_csv_path, 'r', encoding='utf-8') as f:
#        cursor_postgres.copy_expert(sql=copy_sql, file=f)
#    cursor_postgres.execute("DROP TABLE IF EXISTS lot_num_record")
#    cursor_postgres.execute("alter table lot_num_record_TEMP rename to lot_num_record")
#    connection_postgres.commit()
#    cursor_postgres.close()
#    connection_postgres.close()
#
#    time_checkpoint = time.perf_counter()
#    print(f'Complete in {time_checkpoint - time_start:0.4f} seconds','world record prolly')