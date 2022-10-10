import pandas as pd 
import datetime as dt
import os
import psycopg2
import pyexcel as pe
import csv
from sharepoint_download import download_to_temp
import time
import warnings
warnings.filterwarnings("ignore")
import numpy as np

def get_prod_schedule():
    print('GetLatestProdMerge(), I choose you!')
    time_start = time.perf_counter()
    source_file_path = download_to_temp("ProductionSchedule")
    if source_file_path=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return

    header_name_list = ["billno", "po", "description", "blendPN", "case_size", "qty", "bottle", "cap", "runtime", "carton","starttime","line"]
    prodmerge_temp_csv_path = os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\prodmerge1.csv"
    with open(prodmerge_temp_csv_path, 'w', encoding="utf-8") as my_new_csv:
        writer = csv.writer(my_new_csv)
        writer.writerow(header_name_list)
    sheet_name_list = ["BLISTER", "INLINE", "JB LINE", "KITS", "OIL LINE", "PD LINE"]
    for sheet in sheet_name_list:
        print(sheet)
        sheet_df = pd.read_excel(source_file_path, sheet, skiprows = 2, usecols = 'C:L')
        sheet_df = sheet_df.dropna(axis=0, how='any', subset=['Runtime'])
        sheet_df = sheet_df[sheet_df["Runtime"].str.contains(" ", na=False) == False]
        sheet_df = sheet_df[sheet_df["Product"].str.contains("0x2a", na=False) == False]
        sheet_df = sheet_df[sheet_df["Runtime"].str.contains("SchEnd", na=False) == False]
        sheet_df["Starttime"] = sheet_df["Runtime"].cumsum()
        sheet_df = sheet_df.reset_index(drop=True)
        sheet_df["Starttime"] = sheet_df["Starttime"].shift(1, fill_value=0)
        sheet_df["prodline"] = sheet
        sheet_df["ID2"] = np.arange(len(sheet_df))+1
        print(sheet_df)
        print(sheet+" DONE")
        sheet_df.to_csv(prodmerge_temp_csv_path, mode='a', header=False, index=False)

    # The code below removes blank lines. Need two separate files to do this.
    prodmerge_csv_path  = (os.path.expanduser('~\\Documents')
                            +"\\kpk-app\\db_imports\\prodmerge.csv")
    with open(prodmerge_temp_csv_path, newline='', encoding="utf-8") as in_file:
        with open(prodmerge_csv_path, 'w', newline='', encoding="utf-8") as out_file:
            writer = csv.writer(out_file)
            for row in csv.reader(in_file):
                if row:
                    writer.writerow(row)

    os.remove(prodmerge_temp_csv_path)
    os.remove(source_file_path)

    sql_columns_with_types = '''(P_N text,
                PO_Num text, 
                Product text, 
                Blend text, 
                Case_Size text, 
                Qty numeric, 
                Bottle text, 
                Cap text, 
                Runtime numeric, 
                Carton text, 
                Starttime numeric, 
                prodline text, 
                ID2 numeric)'''
    
    ### EXTREMELY SKETCHY AND UNNECESSARY METHOD FOR ###
    ### CONSTRUCTING THE SQL CREATE TABLE STRING ########
    # sql_columns_with_types = '('
    # list_position = 0
    # i = 0
    # for i in range(len(cSdFnewIndex.columns)):
    #     header_name_list[list_position] = (header_name_list[list_position]).replace("/","_")
    #     header_name_list[list_position] = (header_name_list[list_position]).replace(" ","_")
    #     header_name_list[list_position] = (header_name_list[list_position]).replace("#","Num")
    #     sql_columns_with_types += header_name_list[list_position]
    #     if header_name_list[list_position] == "Carton":
    #         sql_columns_with_types += ' text, '
    #         list_position += 1
    #         continue
    #     if header_name_list[list_position] == "P_N":
    #         sql_columns_with_types += ' text, '
    #         list_position += 1
    #         continue
    #     if header_name_list[list_position] == "PO_Num":
    #         sql_columns_with_types += ' text, '
    #         list_position += 1
    #         continue
    #     if str(type(cSdFnewIndex.iat[2,list_position])) == "<class 'str'>":
    #         sql_columns_with_types += ' text, '
    #     elif str(type(cSdFnewIndex.iat[2,list_position])) == "<'datetime.date'>":
    #         sql_columns_with_types += ' date, '
    #     elif str(type(cSdFnewIndex.iat[2,list_position])) == "<class 'numpy.float64'>":
    #         sql_columns_with_types += ' numeric, '
    #     elif str(type(cSdFnewIndex.iat[2,list_position])) == "<class 'int'>":
    #         sql_columns_with_types += ' numeric, '
    #     elif str(type(cSdFnewIndex.iat[2,list_position])) == "<class 'numpy.int32'>":
    #         sql_columns_with_types += ' numeric, '
    #     elif str(type(cSdFnewIndex.iat[2,list_position])) == "<class 'float'>":
    #         sql_columns_with_types += ' numeric, '
    #     list_position += 1
    #     print(sql_columns_with_types)
    # sql_columns_with_types = sql_columns_with_types[:len(sql_columns_with_types)-2] + ')'
    # print(sql_columns_with_types)
    ### EXTREMELY SKETCHY AND UNNECESSARY METHOD FOR ###
    ### CONSTRUCTING THE SQL CREATE TABLE STRING ########


    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("CREATE TABLE prodmerge_run_data_TEMP" + sql_columns_with_types)
    copy_sql = "COPY prodmerge_run_data_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"

    with open(prodmerge_csv_path, 'r', encoding='utf-8') as f:
        cursor_postgres.copy_expert(sql=copy_sql, file=f)
    cursor_postgres.execute("DROP TABLE IF EXISTS prodmerge_run_data")
    cursor_postgres.execute("alter table prodmerge_run_data_TEMP rename to prodmerge_run_data")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    time_checkpoint = time.perf_counter()
    print(f'Complete in {time_checkpoint - time_start:0.4f} seconds','world record prolly')

    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\prod_sched_last_update.txt'), 'a', encoding="utf-8") as f:
        f.write(str(dt.datetime.now()))
        f.write('\n')