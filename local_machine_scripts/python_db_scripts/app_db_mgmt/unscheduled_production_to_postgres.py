import pandas as pd 
import datetime as dt
import os
import psycopg2
import pyexcel as pe
import csv
from .sharepoint_download import download_to_temp
import time
import warnings
warnings.filterwarnings("ignore")
import numpy as np

def get_unscheduled_production_runs():
    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Downloading schedule...')
    time_start = time.perf_counter()
    source_file_path = download_to_temp("ProductionSchedule")
    if source_file_path=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'a', encoding="utf-8") as f:
            f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            f.write('\n')
        return
    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Writing to csv...')
            f.write('\n')
    header_name_list = ["billno", "po", "description", "blendPN", "case_size", "qty", "bottle", "cap", "runtime", "carton","starttime","line"]
    prodmerge_temp_csv_path = os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\prodmerge1.csv"
    with open(prodmerge_temp_csv_path, 'w', encoding="utf-8") as my_new_csv:
        writer = csv.writer(my_new_csv)
        writer.writerow(header_name_list)
    sheet_name_list = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
    for sheet in sheet_name_list:
        try:
            sheet_df = pd.read_excel(source_file_path, sheet, skiprows = 3, usecols = 'C:L')
            sheet_df = sheet_df.dropna(axis=0, how='any', subset=['Runtime'])
            sheet_df = sheet_df[sheet_df["Runtime"].astype(str).str.contains(" ", na=False) == False]
            sheet_df = sheet_df[sheet_df["Product"].str.contains("0x2a", na=False) == False]
            sheet_df = sheet_df[sheet_df["Runtime"].astype(str).str.contains("SchEnd", na=False) == False]
            sheet_df = sheet_df.reset_index(drop=True)
            sheet_df["po_due"] = sheet
            sheet_df["ID2"] = np.arange(len(sheet_df))+1
            sheet_df.to_csv(prodmerge_temp_csv_path, mode='a', header=False, index=False)
        except ValueError:
            continue

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
                po_due text, 
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

    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Writing to blendverse db...')
    try:
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("CREATE TABLE unscheduled_order_raw_schedule_TEMP" + sql_columns_with_types)
        copy_sql = "COPY unscheduled_order_raw_schedule_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"

        with open(prodmerge_csv_path, 'r', encoding='utf-8') as f:
            cursor_postgres.copy_expert(sql=copy_sql, file=f)
            
        cursor_postgres.execute('''create table unscheduled_orders_TEMP as
                                    select distinct unscheduled_order_raw_schedule_TEMP.p_n as item_code,
                                    bill_of_materials.component_item_code as component_item_code,
                                    bill_of_materials.component_item_description as component_item_description,
                                    unscheduled_order_raw_schedule_TEMP.qty as unadjusted_runqty,
                                    bill_of_materials.foam_factor as foam_factor,
                                    bill_of_materials.qtyperbill as qtyperbill,
                                    bill_of_materials.qtyonhand as qtyonhand,
                                    bill_of_materials.procurementtype as procurementtype,
                                    unscheduled_order_raw_schedule_TEMP.runtime as runtime,
                                    unscheduled_order_raw_schedule_TEMP.po_due as po_due,
                                    unscheduled_order_raw_schedule_TEMP.id2 as id2
                                from unscheduled_order_raw_schedule_TEMP as unscheduled_order_raw_schedule_TEMP
                                join bill_of_materials bill_of_materials 
                                    on unscheduled_order_raw_schedule_TEMP.p_n=bill_of_materials.item_code 
                                '''
                                )
        cursor_postgres.execute('alter table unscheduled_orders_TEMP add id serial primary key;')
        cursor_postgres.execute('alter table unscheduled_orders_TEMP add adjustedrunqty numeric;')
        cursor_postgres.execute('''update unscheduled_orders_TEMP
                                set adjustedrunqty=(unadjusted_runqty*1.1*foam_factor*qtyperbill)''')
        cursor_postgres.execute("delete from unscheduled_orders_TEMP where component_item_description not like 'BLEND%'")

        cursor_postgres.execute("DROP TABLE IF EXISTS unscheduled_orders")
        cursor_postgres.execute("alter table unscheduled_orders_TEMP rename to unscheduled_orders")
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()

        print(f'{dt.datetime.now()}=======unscheduled_orders table created.=======')

    except psycopg2.OperationalError as this_error:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
            f.write('\n')
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\Production_Schedule_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
            f.write('\n')
            f.write(str(this_error))
        print('Check the ')

    except Exception as this_error:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
            f.write('\n')
            print('BLENDVERSE DB ERROR: InvalidTextRepresentation. ' + str(this_error))