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
from sqlalchemy import create_engine

def floatHourToTime(fh):
    hours, hourSeconds = divmod(fh, 1)
    minutes, seconds = divmod(hourSeconds * 60, 1)
    return (
        int(hours),
        int(minutes),
        int(seconds * 60),
    )

def get_horix_line_blends():
    try:
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print('File not downloaded because of an error in the Sharepoint download function')
            return
        sheet_df = pd.read_excel(source_file_path, 'Horix Line', usecols = 'C:K')
        sheet_df = sheet_df.iloc[2:] # take out first two rows of the table body
        sheet_df.columns = ['item_code','po_number','item_description','run_time','start_time','dye','prod_line','item_run_qty','run_date']

        # take out non-useful rows
        sheet_df = sheet_df.dropna(axis=0, how='any', subset=['po_number'])
        sheet_df = sheet_df[sheet_df['po_number'] != 'XXXX']
        sheet_df = sheet_df[sheet_df['po_number'] != 'LineEnd']
        sheet_df = sheet_df[sheet_df['po_number'] != 'PailEnd']
        sheet_df = sheet_df[sheet_df['po_number'] != 'SchEnd']
        sheet_df = sheet_df[sheet_df['run_date'] != '???']
        print(sheet_df)
    

        # set run_time
        sheet_df.loc[sheet_df['prod_line']=='6-1gal','run_time'] = (sheet_df['item_run_qty'] * 6) / 3800
        sheet_df.loc[sheet_df['prod_line']=='55gal drum','run_time'] = (sheet_df['item_run_qty'] * 55) / 1450
        sheet_df.loc[sheet_df['prod_line']=='5 gal pail','run_time'] = (sheet_df['item_run_qty'] * 5) / 40
        sheet_df.loc[sheet_df['prod_line']=='275 gal tote','run_time'] = (sheet_df['item_run_qty'] * 275) / 1450
        sheet_df.loc[sheet_df['prod_line']=='265 gal tote','run_time'] = (sheet_df['item_run_qty'] * 265) / 1450

        # set prod_line
        sheet_df.replace('6-1gal', 'Hx', inplace=True)
        sheet_df.replace('55gal drum', 'Dm', inplace=True)
        sheet_df.replace('5 gal pail', 'Pails', inplace=True)
        sheet_df.replace('275 gal tote', 'Totes', inplace=True)
        sheet_df.replace('265 gal tote', 'Totes', inplace=True)

        # set start_time based on cumulative run_time
        sheet_df['start_time'] = sheet_df.groupby('prod_line')['run_time'].cumsum().fillna(0)
        sheet_df['start_time'] = sheet_df.groupby('prod_line')['start_time'].shift(1, fill_value=0)

        # handle the dates
        sheet_df['run_date'] = sheet_df['run_date'].fillna(0)
        for i, row in sheet_df.iterrows():
            try:
                excel_date = sheet_df.at[i,'run_date']
                py_datetime = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
                sheet_df.at[i,'run_date']= py_datetime
            except ValueError:
                continue

        # convert the 'run_date' column to datetime format
        try:
            sheet_df['run_date'] = pd.to_datetime(sheet_df['run_date'])
        except Exception as e:
            print(str(e) + 'unacceptable date value')

        # add 10hrs to the start time for every weekday
        # between now and the run date
        for index, row in sheet_df.iterrows():
            # calculate the number of weekdays between now and the run date, excluding Fridays
            current_date = dt.date.today()
            weekdays_count = 0
            while current_date < row['run_date'].date():
                if current_date.weekday() < 4:
                    weekdays_count += 1
                current_date += dt.timedelta(days=1)
            # set the 'start_time' value equal to the weekdays count
            sheet_df.at[index, 'start_time'] = sheet_df.at[index, 'start_time'] + (weekdays_count  * 10)


        sheet_df.drop(columns=['run_date'], inplace=True)
        sheet_df = sheet_df.reset_index(drop=True)
        sheet_df['id2'] = sheet_df.groupby('prod_line').cumcount()

        alchemy_engine = create_engine(
                'postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb',
                pool_recycle=3600
                )

        # Convert your Pandas DataFrame to a SQL Alchemy table
        sheet_df.to_sql(name='hx_blendthese', con=alchemy_engine, if_exists='replace', index=False)

        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("alter table hx_blendthese drop column dye;")
        cursor_postgres.execute("""update hx_blendthese hb set item_description = (
                select item_description 
                from bill_of_materials bom2 
                where hb.item_code = bom2.item_code
                limit 1);
            select * from hx_blendthese hb;""")
        cursor_postgres.execute("""INSERT INTO prodmerge_run_data (
                id2, run_time, start_time,
                item_run_qty, item_code, po_number, 
                item_description, prod_line)
            SELECT 
                id2::numeric, run_time::numeric, start_time::numeric,
                item_run_qty::numeric, item_code, po_number,
                item_description, prod_line
            FROM hx_blendthese;""")
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()

        print(f'{dt.datetime.now()}=======Horix line table created.=======')
    except Exception as e:
        print(f'{dt.datetime.now()}=======Horix line table NOT created. {str(e)} =======')


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