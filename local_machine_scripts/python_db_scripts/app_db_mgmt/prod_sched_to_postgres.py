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

def get_prod_schedule():
    try:
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #         f.write('Downloading schedule...')
        time_start = time.perf_counter()
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print('File not downloaded because of an error in the Sharepoint download function')
            # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            #     f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'a', encoding="utf-8") as f:
            #     f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            #     f.write('\n')
            return
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #         f.write('Writing to csv...')
        #         f.write('\n')
        header_name_list = ["billno", "po", "description", "blendPN", "case_size", "qty", "bottle", "cap", "runtime", "carton","starttime","line"]
        prodmerge_temp_csv_path = os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\prodmerge1.csv"
        with open(prodmerge_temp_csv_path, 'w', encoding="utf-8") as my_new_csv:
            writer = csv.writer(my_new_csv)
            writer.writerow(header_name_list)
        sheet_name_list = ["BLISTER", "INLINE", "JB LINE", "KITS", "OIL LINE", "PD LINE"]
        for sheet in sheet_name_list:
            sheet_df = pd.read_excel(source_file_path, sheet, skiprows = 2, usecols = 'C:L')
            sheet_df["ID2"] = np.arange(len(sheet_df))+4
            sheet_df = sheet_df.dropna(axis=0, how='any', subset=['Runtime'])
            sheet_df = sheet_df[sheet_df["Runtime"].str.contains(" ", na=False) == False]
            sheet_df = sheet_df[sheet_df["Product"].str.contains("0x2a", na=False) == False]
            sheet_df = sheet_df[sheet_df["Runtime"].str.contains("SchEnd", na=False) == False]
            sheet_df["Start_time"] = sheet_df["Runtime"].cumsum()
            sheet_df = sheet_df.reset_index(drop=True)
            sheet_df["Start_time"] = sheet_df["Start_time"].shift(1, fill_value=0)
            sheet_df["prod_line"] = sheet
            sheet_df.to_csv(prodmerge_temp_csv_path, mode='a', header=False, index=False)
        unscheduled_sheet_name_list = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
        starttime_running_total = 300
        # Get the current month and year
        now = dt.datetime.now()
        current_month = now.month
        current_year = now.year
        # Create a dictionary to map sheet names to month numbers
        month_dict = {month: i+1 for i, month in enumerate(unscheduled_sheet_name_list)}
        # Create a list of tuples, each containing a sheet name and a datetime object
        sheets_with_dates = []
        for sheet in unscheduled_sheet_name_list:
            month_num = month_dict[sheet]
            year = current_year if month_num >= current_month else current_year + 1
            date = dt.datetime(year, month_num, 1)
            sheets_with_dates.append((sheet, date))

        # Sort the list based on the datetime objects
        sheets_with_dates.sort(key=lambda x: x[1])

        # Now you can loop over the sorted list of sheets
        for sheet, _ in sheets_with_dates:
        #for sheet in unscheduled_sheet_name_list:
            try:
                sheet_df = pd.read_excel(source_file_path, sheet, skiprows = 3, usecols = 'C:L')
                sheet_df["ID2"] = np.arange(len(sheet_df))+5
                sheet_df = sheet_df.dropna(axis=0, how='any', subset=['Runtime'])
                sheet_df = sheet_df[sheet_df["Runtime"].astype(str).str.contains(" ", na=False) == False]
                sheet_df = sheet_df[sheet_df["Product"].str.contains("0x2a", na=False) == False]
                sheet_df = sheet_df[sheet_df["Runtime"].astype(str).str.contains("SchEnd", na=False) == False]
                sheet_df["start_time"] = sheet_df["Runtime"].cumsum() + starttime_running_total
                sheet_df = sheet_df.reset_index(drop=True)
                sheet_df["start_time"] = sheet_df["start_time"].shift(1, fill_value=starttime_running_total)
                sheet_df["prod_line"] = f'UNSCHEDULED: {sheet}'
                sheet_df.to_csv(prodmerge_temp_csv_path, mode='a', header=False, index=False)
                starttime_running_total = starttime_running_total + sheet_df.loc[sheet_df.index[-1], 'start_time']
            except ValueError:
                continue
            except IndexError:
                continue

        # This code removes blank lines. Need two separate files to do this.########
        prodmerge_csv_path  = (os.path.expanduser('~\\Documents')
                                +"\\kpk-app\\db_imports\\prodmerge.csv")
        with open(prodmerge_temp_csv_path, newline='', encoding="utf-8") as in_file:
            with open(prodmerge_csv_path, 'w', newline='', encoding="utf-8") as out_file:
                writer = csv.writer(out_file)
                for row in csv.reader(in_file):
                    if row:
                        writer.writerow(row)
        # Ick. ######################################################################

        os.remove(prodmerge_temp_csv_path)
        os.remove(source_file_path)

        sql_columns_with_types = '''(
                    item_code text,
                    po_number text,
                    Product text,
                    Blend text,
                    Case_Size text,
                    item_run_qty numeric,
                    Bottle text,
                    Cap text,
                    run_time numeric,
                    Carton text,
                    ID2 numeric,
                    start_time numeric,
                    prod_line text
                    )'''
        
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

        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #         f.write('Writing to blendverse db...')

        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("CREATE TABLE prodmerge_run_data_TEMP" + sql_columns_with_types)
        copy_sql = "COPY prodmerge_run_data_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"

        with open(prodmerge_csv_path, 'r', encoding='utf-8') as f:
            cursor_postgres.copy_expert(sql=copy_sql, file=f)
        cursor_postgres.execute("""alter table prodmerge_run_data_TEMP drop column Product;
                                    alter table prodmerge_run_data_TEMP drop column Blend;
                                    alter table prodmerge_run_data_TEMP drop column Case_Size;
                                    alter table prodmerge_run_data_TEMP drop column Bottle;
                                    alter table prodmerge_run_data_TEMP drop column Cap;
                                    alter table prodmerge_run_data_TEMP drop column Carton;
                                    alter table prodmerge_run_data_TEMP add item_description text;
                                    update prodmerge_run_data_TEMP set item_description=(
                                        select bill_of_materials.item_description 
                                        from bill_of_materials
                                        where bill_of_materials.item_code=prodmerge_run_data_TEMP.item_code limit 1);
                                    alter table prodmerge_run_data_TEMP add id serial primary key;
                                    """)
        cursor_postgres.execute("DROP TABLE IF EXISTS prodmerge_run_data")
        cursor_postgres.execute("alter table prodmerge_run_data_TEMP rename to prodmerge_run_data")
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()

        print(f'{dt.datetime.now()}=======Prodmerge table created.=======')

    except Exception as e:
        print('PROD SCHEDULE ERROR: ' + str(dt.datetime.now()))
        print(str(e))
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
        #     f.write('\n')
        #     print('BLENDVERSE DB ERROR: InvalidTextRepresentation. ' + str(e))

def get_foam_factor():
    try:
        time_start = time.perf_counter()
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print('File not downloaded because of an error in the Sharepoint download function')
            # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            #     f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'a', encoding="utf-8") as f:
            #     f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            #     f.write('\n')
            return
        
        
        header_name_list = ["item_code", "factor", "item_description"]
        foamfactor_temp_csv_path = os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\foamfactor1.csv"
        with open(foamfactor_temp_csv_path, 'w', encoding="utf-8") as my_new_csv:
            writer = csv.writer(my_new_csv)
            writer.writerow(header_name_list)
        sheet_name = "foamFactorList"
        sheet_df = pd.read_excel(source_file_path, sheet_name, usecols = 'A:C')
        sheet_df["id"] = np.arange(len(sheet_df))
        sheet_df.to_csv(foamfactor_temp_csv_path, mode='a', header=False, index=False)
        foamfactor_csv_path  = (os.path.expanduser('~\\Documents')
                            +"\\kpk-app\\db_imports\\foamfactor.csv")
        with open(foamfactor_temp_csv_path, newline='', encoding="utf-8") as in_file:
            with open(foamfactor_csv_path, 'w', newline='', encoding="utf-8") as out_file:
                writer = csv.writer(out_file)
                for row in csv.reader(in_file):
                    if row:
                        writer.writerow(row)
        
        os.remove(foamfactor_temp_csv_path)
        os.remove(source_file_path)

        sql_columns_with_types = '''(item_code text,
                    factor numeric,
                    item_description text,
                    id serial primary key)'''
   
        try:
            connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
            cursor_postgres = connection_postgres.cursor()
            cursor_postgres.execute("CREATE TABLE core_foamfactor_TEMP" + sql_columns_with_types)
            copy_sql = "COPY core_foamfactor_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
            with open(foamfactor_csv_path, 'r', encoding='utf-8') as f:
                cursor_postgres.copy_expert(sql=copy_sql, file=f)
            cursor_postgres.execute("DROP TABLE IF EXISTS core_foamfactor")
            cursor_postgres.execute("alter table core_foamfactor_TEMP rename to core_foamfactor")
            connection_postgres.commit()
            cursor_postgres.close()
            connection_postgres.close()
            print(f'{dt.datetime.now()}=======Foam Factor table copied.======')
                
        except Exception as this_error:
             print(str(this_error))
           
        


    except Exception as e:
        print(str(e))


def get_starbrite_item_quantities():
    try:
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Downloading schedule...')
        time_start = time.perf_counter()
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print('File not downloaded because of an error in the Sharepoint download function')
            # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
            #     f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'a', encoding="utf-8") as f:
            #     f.write('SHAREPOINT ERROR: ' + str(dt.datetime.now()))
            #     f.write('\n')
            return
        
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #         f.write('Writing to csv...')
        #         f.write('\n')
        header_name_list = ["quantity", "item_code"]
        starbrite_item_quantities_temp_csv_path = os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\starbrite_item_quantities1.csv"
        with open(starbrite_item_quantities_temp_csv_path, 'w', encoding="utf-8") as my_new_csv:
            writer = csv.writer(my_new_csv)
            writer.writerow(header_name_list)
        sheet_name = "REWORK"
        sheet_df = pd.read_excel(source_file_path, sheet_name, usecols = 'C:D', skiprows = 2, nrows = 50)
        sheet_df = sheet_df.dropna(how='any', axis=0) #get rid of all rows that don't have anything in them
        sheet_df = sheet_df[~sheet_df.apply(lambda row: row.astype(str).str.contains('# CS ON HAND').any(), axis=1)]
        sheet_df = sheet_df[~sheet_df.apply(lambda row: row.astype(str).str.contains('P/N').any(), axis=1)]

        sheet_df["id"] = np.arange(len(sheet_df))
        sheet_df.to_csv(starbrite_item_quantities_temp_csv_path, mode='a', header=False, index=False)
        starbrite_item_quantities_csv_path  = (os.path.expanduser('~\\Documents')
                            +"\\kpk-app\\db_imports\\starbrite_item_quantities.csv")
        with open(starbrite_item_quantities_temp_csv_path, newline='', encoding="utf-8") as in_file:
            with open(starbrite_item_quantities_csv_path, 'w', newline='', encoding="utf-8") as out_file:
                writer = csv.writer(out_file)
                for row in csv.reader(in_file):
                    if row:
                        writer.writerow(row)
        
        os.remove(starbrite_item_quantities_temp_csv_path)
        os.remove(source_file_path)

        sql_columns_with_types = '''(quantity numeric,
                    item_code text,
                    id serial primary key)'''
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Writing to blendverse db...')
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("CREATE TABLE starbrite_item_quantities_TEMP" + sql_columns_with_types)
        copy_sql = "COPY starbrite_item_quantities_TEMP FROM stdin WITH CSV HEADER DELIMITER as ','"
        with open(starbrite_item_quantities_csv_path, 'r', encoding='utf-8') as f:
            cursor_postgres.copy_expert(sql=copy_sql, file=f)
        cursor_postgres.execute("DROP TABLE IF EXISTS starbrite_item_quantities")
        cursor_postgres.execute("alter table starbrite_item_quantities_TEMP rename to starbrite_item_quantities")
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        print(f'{dt.datetime.now()}=======Starbrite Item Quantities table copied.======')
                
    except Exception as e:
        print('PROD SCHEDULE ERROR: ' + str(dt.datetime.now()))
        print(str(e))
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('ERROR COPYING FOAMFACTOR: ' + str(dt.datetime.now()))
        #     f.write('\n')
        #     print('BLENDVERSE DB ERROR: ' + str(e))