import pandas as pd
import os
import psycopg2
from sharepoint_download import download_to_temp
import time
import warnings
warnings.filterwarnings("ignore")

def get_chem_locations():
    print('get_chem_locations(), I choose you!')
    time_start = time.perf_counter()

    source_file_path = download_to_temp("BlendingSchedule")
    if source_file_path=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return
        
    sheet_df = pd.read_excel(source_file_path, 'ChemLocation', usecols = 'A:G')
    sheet_df['id']=range(1,len(sheet_df)+1)
    chem_locations_csv_path  = (os.path.expanduser('~\\Documents')
                            +"\\kpk-app\\init_db_imports\\chem_locations.csv")
    sheet_df.to_csv(chem_locations_csv_path, header=True, index=False)

    os.remove(source_file_path)

    header_name_list = list(sheet_df.columns)
    sql_columns_with_types = '('
    for column_name in header_name_list:
        if column_name == 'id':
            column_name += ' serial primary key, '
        else:
            column_name += ' text, '
        sql_columns_with_types += column_name
    sql_columns_with_types = sql_columns_with_types[:len(sql_columns_with_types)-2] + ')'

    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("CREATE TABLE chem_location_TEMP"+sql_columns_with_types)
    copy_sql = "COPY chem_location_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"

    with open(chem_locations_csv_path, 'r', encoding='utf-8') as csv_file:
        cursor_postgres.copy_expert(sql=copy_sql, file=csv_file)
    cursor_postgres.execute("DROP TABLE IF EXISTS chem_location")
    cursor_postgres.execute("alter table chem_location_TEMP rename to chem_location")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    time_checkpoint = time.perf_counter()
    print(f'Complete in {time_checkpoint - time_start:0.4f} seconds','world record prolly')