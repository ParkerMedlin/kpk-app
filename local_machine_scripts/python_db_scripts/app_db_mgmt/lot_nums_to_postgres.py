import pandas as pd
import os
import psycopg2
from .sharepoint_download import download_to_temp
import time
import warnings
from datetime import datetime
warnings.filterwarnings("ignore")

def get_lot_numbers():
    print('get_lot_numbers(), I choose you!')
    time_start = time.perf_counter()

    source_file_path = download_to_temp("LotNumGenerator")
    if source_file_path=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return
    lot_num_csv_path  = (os.path.expanduser('~\\Documents')
                            +"\\kpk-app\\db_imports\\lot_nums.csv")
    sheet_df = pd.read_excel(source_file_path, 'LotNumberGenerator', usecols = 'A:X')
    sheet_df = sheet_df.drop(sheet_df.columns[[22,20,17,16,15,14,13,12,11,10,9,8,7]], axis=1)
    sheet_df = sheet_df.drop([0])
    
    sheet_df['date_created'] = sheet_df['date_created'].apply(lambda this_row: datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(this_row) - 2))
    sheet_df['run_date'] = sheet_df['run_date'].apply(lambda this_row: None if(this_row=='-') else datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(this_row) - 2))
    sheet_df['date_entered'] = sheet_df['date_entered'].apply(lambda this_row: None if(this_row=='Not Entered') else datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(this_row) - 2))
    
    sheet_df.to_csv(lot_num_csv_path, header=True, index=False)
    os.remove(source_file_path)

    header_name_list = list(sheet_df.columns)
    sql_columns_with_types = '('
    for item in header_name_list:
        column_name = str(item)
        if 'date_created' in column_name:
            column_name = column_name +' date, '
        elif 'run_date' in column_name:
            column_name = column_name +' date, '
        elif 'when_entered' in column_name:
            column_name = column_name +' date, '
        else:
            column_name = column_name +' text, '
        sql_columns_with_types += column_name

    sql_columns_with_types = sql_columns_with_types[:len(sql_columns_with_types)-2] + ')'
    print(sql_columns_with_types)
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("CREATE TABLE lot_num_record_TEMP"+sql_columns_with_types)
    copy_sql = "COPY lot_num_record_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
    with open(lot_num_csv_path, 'r', encoding='utf-8') as f:
        cursor_postgres.copy_expert(sql=copy_sql, file=f)
    cursor_postgres.execute("DROP TABLE IF EXISTS lot_num_record")
    cursor_postgres.execute("alter table lot_num_record_TEMP rename to lot_num_record")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    time_checkpoint = time.perf_counter()
    print(f'Complete in {time_checkpoint - time_start:0.4f} seconds','world record prolly')