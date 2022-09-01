import pandas as pd 
import os
import psycopg2
from sharepoint_download import download_to_temp
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

def get_horix_line_blends():
    print('get_horix_line_blends(), I choose you!')
    time_start = time.perf_counter()

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
    sheet_df = sheet_df.dropna(axis=0, how='any', subset=['Amt'])
    sheet_df = sheet_df.dropna(axis=0, how='any', subset=['PO #'])
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
    sheet_df['gallonQty']=sheet_df['gal_factor']*sheet_df['Case Qty']
    sheet_df.loc[sheet_df['Line']=="Hx",'num_blends']=sheet_df['gallonQty']/5100
    sheet_df.loc[sheet_df['Line']=="Dm",'num_blends']=sheet_df['gallonQty']/2925
    sheet_df.loc[sheet_df['Line']=="Pails",'num_blends']=sheet_df['gallonQty']/2925
    sheet_df.loc[sheet_df['Line']=="Totes",'num_blends']=sheet_df['gallonQty']/2925
    sheet_df['num_blends'] = sheet_df['num_blends'].apply(np.ceil)
    print(sheet_df)
    
    sheet_df = sheet_df.reset_index(drop=True)

    print(sheet_df)
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
    print(sql_columns_with_types)
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("CREATE TABLE hx_blendthese_TEMP"+sql_columns_with_types)
    copy_sql = "COPY hx_blendthese_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open(horix_csv_path, 'r', encoding='utf-8') as f:
        cursor_postgres.copy_expert(sql=copy_sql, file=f)
    cursor_postgres.execute("DROP TABLE IF EXISTS hx_blendthese")
    cursor_postgres.execute("alter table hx_blendthese_TEMP rename to hx_blendthese")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    time_checkpoint = time.perf_counter()
    print(f'Complete in {time_checkpoint - time_start:0.4f} seconds','world record prolly')