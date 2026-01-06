import pandas as pd
import datetime as dt
import os
from io import StringIO
import psycopg2
import pyexcel as pe
import csv
from .sharepoint_download import download_to_temp, download_to_memory
import time
import warnings
warnings.filterwarnings("ignore")
import numpy as np

def get_prod_schedule():
    sheet = None  # Initialize so exception handler can reference it
    try:
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #         f.write('Downloading schedule...')
        time_start = time.perf_counter()
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: File not downloaded because of an error in the Sharepoint download function')
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
            try:
                sheet_df = pd.read_excel(source_file_path, sheet, skiprows = 2, usecols = 'C:L')
                sheet_df["ID2"] = np.arange(len(sheet_df))+4
                sheet_df = sheet_df.dropna(axis=0, how='any', subset=['Runtime'])
                sheet_df = sheet_df[pd.to_numeric(sheet_df["Runtime"], errors='coerce').notna()]
                sheet_df = sheet_df[sheet_df["Product"].astype(str).str.contains("0x2a", na=False) == False]
                sheet_df["Start_time"] = sheet_df["Runtime"].cumsum()
                sheet_df = sheet_df.reset_index(drop=True)
                sheet_df["Start_time"] = sheet_df["Start_time"].shift(1, fill_value=0)
                sheet_df["prod_line"] = sheet
                sheet_df = sheet_df[sheet_df["Qty"] != "."]
                sheet_df.to_csv(prodmerge_temp_csv_path, mode='a', header=False, index=False)
            except Exception as e:
                print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: ERROR processing sheet: {sheet}')
                print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: {str(e)}')
                try:
                    # Attempt to find the problematic row
                    for i, row in sheet_df.iterrows():
                        try:
                            # Simulate the operation that might fail to find the row
                            float(row['Runtime'])
                        except (ValueError, TypeError):
                            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: Problematic row in sheet {sheet} at index {i}:')
                            print(row)
                            break  # Stop after finding the first problematic row
                except NameError:
                    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: sheet_df not defined, error likely during read_excel.')
                # continue to next sheet
                continue

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
                sheet_df = sheet_df[sheet_df["Product"].astype(str).str.contains("0x2a", na=False) == False]
                sheet_df = sheet_df[sheet_df["Runtime"].astype(str).str.contains("SchEnd", na=False) == False]
                sheet_df["start_time"] = sheet_df["Runtime"].cumsum() + starttime_running_total
                sheet_df = sheet_df.reset_index(drop=True)
                sheet_df["start_time"] = sheet_df["start_time"].shift(1, fill_value=starttime_running_total)
                sheet_df["prod_line"] = f'UNSCHEDULED: {sheet}'
                sheet_df = sheet_df[sheet_df["Qty"] != "."]
                if sheet_df.empty:
                    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: Skipping sheet {sheet} because no rows remain after cleaning.')
                    continue
                sheet_df.to_csv(prodmerge_temp_csv_path, mode='a', header=False, index=False)
                last_start_time = sheet_df["start_time"].iloc[-1]
                starttime_running_total = starttime_running_total + last_start_time
            except (ValueError, IndexError) as e:
                print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: Skipping sheet {sheet} due to error: {e}')
                continue
            except Exception as e:
                print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: An unexpected error occurred in sheet {sheet}: {e}')
                try:
                    # Attempt to find the problematic row
                    for i, row in sheet_df.iterrows():
                        try:
                            # Simulate the operation that might fail to find the row
                            float(row['Runtime'])
                        except (ValueError, TypeError):
                            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: Problematic row in sheet {sheet} at index {i}:')
                            print(row)
                            break  # Stop after finding the first problematic row
                except NameError:
                    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: sheet_df not defined, error likely during read_excel.')
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

        #print(f'{dt.datetime.now()}=======Prodmerge table created.=======')

    except Exception as e:
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: PROD SCHEDULE ERROR')
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: sheet: {sheet}')
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_prod_schedule :: {str(e)}')
        # Re-raise so the caller sees the actual error message
        raise

def get_foam_factor():
    try:
        time_start = time.perf_counter()
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_foam_factor :: File not downloaded because of an error in the Sharepoint download function')
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
            #print(f'{dt.datetime.now()}=======Foam Factor table copied.======')
                
        except Exception as this_error:
             print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_foam_factor :: {str(this_error)}')
           
        


    except Exception as e:
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_foam_factor :: {str(e)}')

def get_starbrite_item_quantities():
    try:
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Downloading schedule...')
        time_start = time.perf_counter()
        source_file_path = download_to_temp("ProductionSchedule")
        if source_file_path=='Error Encountered':
            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_starbrite_item_quantities :: File not downloaded because of an error in the Sharepoint download function')
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
        #print(f'{dt.datetime.now()}=======Starbrite Item Quantities table copied.======')
                
    except Exception as e:
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_starbrite_item_quantities :: PROD SCHEDULE ERROR: {str(dt.datetime.now())}')
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: get_starbrite_item_quantities :: {str(e)}')
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Production_Schedule_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('ERROR COPYING FOAMFACTOR: ' + str(dt.datetime.now()))
        #     f.write('\n')
        #     print('BLENDVERSE DB ERROR: ' + str(e))


def sync_production_schedule():
    """
    Unified production schedule sync - downloads once to memory, processes all sheets.
    Replaces: get_prod_schedule() + get_starbrite_item_quantities()
    Zero disk I/O = zero file locking bugs.
    """
    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: Starting...')
    time_start = time.perf_counter()

    # === SINGLE DOWNLOAD TO MEMORY ===
    file_buffer = download_to_memory("ProductionSchedule")
    download_time = time.perf_counter() - time_start
    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: Downloaded in {download_time:.1f}s')

    # === READ ALL SHEETS IN ONE PASS ===
    prod_line_sheets = ["BLISTER", "INLINE", "JB LINE", "KITS", "OIL LINE", "PD LINE"]
    month_sheets = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
                    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
    all_sheets = prod_line_sheets + month_sheets + ["REWORK"]

    sheets = pd.read_excel(file_buffer, sheet_name=all_sheets, engine='pyxlsb')
    read_time = time.perf_counter() - time_start - download_time
    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: Read {len(sheets)} sheets in {read_time:.1f}s')

    # === PROCESS PRODUCTION LINE SHEETS ===
    prodmerge_rows = []
    for sheet_name in prod_line_sheets:
        try:
            df = sheets[sheet_name].iloc[2:]  # skiprows=2
            df.columns = ["Bill#", "PO#", "Product", "Blend", "Case Size", "Qty", "Bottle", "Cap", "Runtime", "Carton"]
            df = df.reset_index(drop=True)
            df["ID2"] = np.arange(len(df)) + 4
            df = df.dropna(subset=['Runtime'])
            df = df[pd.to_numeric(df["Runtime"], errors='coerce').notna()]
            df = df[~df["Product"].astype(str).str.contains("0x2a", na=False)]
            df["Start_time"] = df["Runtime"].cumsum()
            df = df.reset_index(drop=True)
            df["Start_time"] = df["Start_time"].shift(1, fill_value=0)
            df["prod_line"] = sheet_name
            df = df[df["Qty"] != "."]
            prodmerge_rows.append(df)
        except Exception as e:
            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: Error in sheet {sheet_name}: {e}')
            continue

    # === PROCESS MONTH SHEETS (UNSCHEDULED) ===
    now = dt.datetime.now()
    current_month = now.month
    current_year = now.year
    month_dict = {month: i + 1 for i, month in enumerate(month_sheets)}

    sheets_with_dates = []
    for sheet_name in month_sheets:
        month_num = month_dict[sheet_name]
        year = current_year if month_num >= current_month else current_year + 1
        date = dt.datetime(year, month_num, 1)
        sheets_with_dates.append((sheet_name, date))
    sheets_with_dates.sort(key=lambda x: x[1])

    starttime_running_total = 300
    for sheet_name, _ in sheets_with_dates:
        try:
            df = sheets[sheet_name].iloc[3:]  # skiprows=3
            df.columns = ["Bill#", "PO#", "Product", "Blend", "Case Size", "Qty", "Bottle", "Cap", "Runtime", "Carton"]
            df = df.reset_index(drop=True)
            df["ID2"] = np.arange(len(df)) + 5
            df = df.dropna(subset=['Runtime'])
            df = df[~df["Runtime"].astype(str).str.contains(" ", na=False)]
            df = df[~df["Product"].astype(str).str.contains("0x2a", na=False)]
            df = df[~df["Runtime"].astype(str).str.contains("SchEnd", na=False)]
            df["Runtime"] = pd.to_numeric(df["Runtime"], errors='coerce')
            df = df.dropna(subset=['Runtime'])
            if df.empty:
                continue
            df["start_time"] = df["Runtime"].cumsum() + starttime_running_total
            df = df.reset_index(drop=True)
            df["start_time"] = df["start_time"].shift(1, fill_value=starttime_running_total)
            df["prod_line"] = f'UNSCHEDULED: {sheet_name}'
            df = df[df["Qty"] != "."]
            if df.empty:
                continue
            prodmerge_rows.append(df)
            last_start_time = df["start_time"].iloc[-1]
            starttime_running_total = starttime_running_total + last_start_time
        except Exception as e:
            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: Error in month sheet {sheet_name}: {e}')
            continue

    # === BUILD PRODMERGE TABLE ===
    if prodmerge_rows:
        combined = pd.concat(prodmerge_rows, ignore_index=True)
        # Select and rename columns to match DB schema
        prodmerge_df = combined[["Bill#", "PO#", "Qty", "Runtime", "ID2", "Start_time", "prod_line"]].copy()
        prodmerge_df.columns = ["item_code", "po_number", "item_run_qty", "run_time", "id2", "start_time", "prod_line"]

        csv_buffer = StringIO()
        prodmerge_df.to_csv(csv_buffer, index=False, header=True)
        csv_buffer.seek(0)

        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("""CREATE TABLE prodmerge_run_data_TEMP (
            item_code text,
            po_number text,
            item_run_qty numeric,
            run_time numeric,
            id2 numeric,
            start_time numeric,
            prod_line text
        )""")
        cursor_postgres.copy_expert("COPY prodmerge_run_data_TEMP FROM stdin WITH CSV HEADER DELIMITER ','", csv_buffer)
        cursor_postgres.execute("""
            ALTER TABLE prodmerge_run_data_TEMP ADD item_description text;
            UPDATE prodmerge_run_data_TEMP SET item_description = (
                SELECT bill_of_materials.item_description
                FROM bill_of_materials
                WHERE bill_of_materials.item_code = prodmerge_run_data_TEMP.item_code LIMIT 1
            );
            ALTER TABLE prodmerge_run_data_TEMP ADD id serial PRIMARY KEY;
            DROP TABLE IF EXISTS prodmerge_run_data;
            ALTER TABLE prodmerge_run_data_TEMP RENAME TO prodmerge_run_data;
        """)
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: prodmerge_run_data updated ({len(prodmerge_df)} rows)')

    # === PROCESS REWORK SHEET (STARBRITE QUANTITIES) ===
    try:
        df = sheets["REWORK"].iloc[2:52]  # skiprows=2, nrows=50
        df.columns = df.columns[:10].tolist() if len(df.columns) >= 10 else df.columns.tolist()
        # Columns C:D = index 2:4 but after iloc the df has original columns, we need cols C and D
        # Re-read with usecols would be: C=qty, D=item_code
        # Since we read full sheet, select columns by position (C=2, D=3)
        file_buffer.seek(0)  # Reset buffer for re-read
        rework_df = pd.read_excel(file_buffer, sheet_name="REWORK", usecols='C:D', skiprows=2, nrows=50, engine='pyxlsb')
        rework_df.columns = ["quantity", "item_code"]
        rework_df = rework_df.dropna(how='any')
        rework_df = rework_df[~rework_df.apply(lambda row: row.astype(str).str.contains('# CS ON HAND').any(), axis=1)]
        rework_df = rework_df[~rework_df.apply(lambda row: row.astype(str).str.contains('P/N').any(), axis=1)]

        if not rework_df.empty:
            csv_buffer = StringIO()
            rework_df.to_csv(csv_buffer, index=False, header=True)
            csv_buffer.seek(0)

            connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
            cursor_postgres = connection_postgres.cursor()
            cursor_postgres.execute("""CREATE TABLE starbrite_item_quantities_TEMP (
                quantity numeric,
                item_code text,
                id serial PRIMARY KEY
            )""")
            cursor_postgres.copy_expert("COPY starbrite_item_quantities_TEMP(quantity, item_code) FROM stdin WITH CSV HEADER DELIMITER ','", csv_buffer)
            cursor_postgres.execute("DROP TABLE IF EXISTS starbrite_item_quantities")
            cursor_postgres.execute("ALTER TABLE starbrite_item_quantities_TEMP RENAME TO starbrite_item_quantities")
            connection_postgres.commit()
            cursor_postgres.close()
            connection_postgres.close()
            print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: starbrite_item_quantities updated ({len(rework_df)} rows)')
    except Exception as e:
        print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: REWORK sheet error: {e}')

    total_time = time.perf_counter() - time_start
    print(f'{dt.datetime.now()} :: prod_sched_to_postgres.py :: sync_production_schedule :: Complete in {total_time:.1f}s')
