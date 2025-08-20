from __future__ import generators
import pyodbc
from pyodbc import Error
import psycopg2
import os
import pandas as pd
import datetime as dt
import hashlib
import json
from dotenv import load_dotenv

def get_all_sage_tables():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '..', '..', '.env')
        load_dotenv(dotenv_path=env_path)

        SAGE_USER = os.getenv('SAGE_USER')
        SAGE_PW = os.getenv('SAGE_PW')

        if not SAGE_USER or not SAGE_PW:
            raise ValueError("Sage credentials not found in environment variables.")
        connection_MAS90 = pyodbc.connect(r"Driver={MAS 90 4.0 ODBC Driver}; " + f"UID={SAGE_USER}; PWD={SAGE_PW}; " +
                                                r"""Directory=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90; 
                                                Prefix=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\SY\, 
                                                \\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\==\; 
                                                ViewDLL=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\HOME; Company=KPK; 
                                                LogFile=\PVXODBC.LOG; CacheSize=8; DirtyReads=1; BurstMode=1; 
                                                StripTrailingSpaces=1;""", autocommit=True)
        cursor_MAS90 = connection_MAS90.cursor()
        
        # Get all table names
        cursor_MAS90.execute("SELECT * FROM INFORMATION_SCHEMA")
        tables = cursor_MAS90.fetchall()
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_all_sage_tables :: {tables}')


        
        # for table in tables:
        #     table_name = table[0]
        #     csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name + '.csv'
        #     columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '.txt'
            
        #     if table_name == "IM_ItemTransactionHistory":
        #         continue
        #     else:
        #         cursor_MAS90.execute("SELECT * FROM " + table_name)
        #     table_contents = list(cursor_MAS90.fetchall())
        #     data_headers = cursor_MAS90.description
            
        #     sql_columns_with_types = '(id serial primary key, '
        #     type_mapping = {
        #         "<class 'str'>": 'text',
        #         "<class 'datetime.date'>": 'date',
        #         "<class 'decimal.Decimal'>": 'decimal'
        #     }
        #     column_definitions = [
        #         f"{column[0]} {type_mapping[str(column[1])]}"
        #         for column in data_headers
        #     ]
        #     sql_columns_with_types += ', '.join(column_definitions) + ')'
        #     column_names_only_string = ''
        #     with open(columns_with_types_path, 'w', encoding="utf-8") as f:
        #         f.write(sql_columns_with_types)
            
        #     column_names_only_string = ', '.join(column[0] for column in data_headers)
        #     column_list = column_names_only_string.split(",")
            
        #     table_dataframe = pd.DataFrame.from_records(table_contents, index=None, exclude=None, columns=column_list, coerce_float=False, nrows=None)
        #     table_dataframe.to_csv(path_or_buf=csv_path, header=column_list, encoding='utf-8')
            
        #     with open(columns_with_types_path, encoding="utf-8") as file:
        #         sql_columns_list = file.readlines()
        #     sql_columns_with_types = sql_columns_list[0]
        
        cursor_MAS90.close()
        connection_MAS90.close()
    except Error as e:
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_all_sage_tables :: Error: {e}')

def get_sage_table(table_name):
    try:
        # print('waiting...')
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Pulling from Sage...')
        csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name+'.csv'
        columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '.txt'
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '..', '..', '.env')
        load_dotenv(dotenv_path=env_path)

        SAGE_USER = os.getenv('SAGE_USER')
        SAGE_PW = os.getenv('SAGE_PW')

        if not SAGE_USER or not SAGE_PW:
            raise ValueError("Sage credentials not found in environment variables.")
        
        connection_MAS90 = pyodbc.connect(r"Driver={MAS 90 4.0 ODBC Driver}; " + f"UID={SAGE_USER}; PWD={SAGE_PW}; " +
                                                r"""Directory=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90; 
                                                Prefix=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\SY\, 
                                                \\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\==\; 
                                                ViewDLL=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\HOME; Company=KPK; 
                                                LogFile=\PVXODBC.LOG; CacheSize=0; DirtyReads=1; BurstMode=1; 
                                                StripTrailingSpaces=1;""", autocommit=True)
        cursor_MAS90 = connection_MAS90.cursor()

        if table_name == "IM_ItemTransactionHistory":
            date_restraint = str(dt.date.today() - dt.timedelta(weeks=52))
            cursor_MAS90.execute("SELECT * FROM " + table_name + " WHERE IM_ItemTransactionHistory.TransactionDate > {d '%s'}" % date_restraint + "ORDER BY TRANSACTIONDATE DESC")
            print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_sage_table :: {dt.date.today()}')
            print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_sage_table :: {date_restraint}')
        else:
            cursor_MAS90.execute("SELECT * FROM " + table_name)
        table_contents = list(cursor_MAS90.fetchall())
        data_headers = cursor_MAS90.description

        sql_columns_with_types = '(id serial primary key, '
        type_mapping = {
            "<class 'str'>": 'text',
            "<class 'datetime.date'>": 'date',
            "<class 'decimal.Decimal'>": 'decimal'
        }
        column_definitions = [
            f"{column[0]} {type_mapping[str(column[1])]}"
            for column in data_headers
        ]
        sql_columns_with_types += ', '.join(column_definitions) + ')'
        column_names_only_string = ''
        with open(columns_with_types_path, 'w', encoding="utf-8") as f:
            f.write(sql_columns_with_types)
        
        column_names_only_string = ', '.join(column[0] for column in data_headers)
        column_list = column_names_only_string.split(",")
        cursor_MAS90.close()
        connection_MAS90.close()

        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Writing to csv...')

        table_dataframe = pd.DataFrame.from_records(table_contents, index=None, exclude=None, columns=column_list, coerce_float=False, nrows=None)
        table_dataframe.to_csv(path_or_buf=csv_path, header=column_list, encoding='utf-8')

        with open(columns_with_types_path, encoding="utf-8") as file:
            sql_columns_list = file.readlines()
        sql_columns_with_types = sql_columns_list[0]

        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Writing to postgres...')
        # print("trying connection")
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        # print("got past that part")
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("drop table if exists " + table_name + "_TEMP")
        cursor_postgres.execute("create table " + table_name + "_TEMP" + sql_columns_with_types)
        copy_sql = "copy " + table_name + "_TEMP from stdin with csv header delimiter as ','"
        with open(csv_path, 'r', encoding='utf-8') as f:
            cursor_postgres.copy_expert(sql=copy_sql, file=f)
        # SET UP INDEXES!
        if table_name == 'CI_Item':
            cursor_postgres.execute("""DROP INDEX if exists ci_item_itemcode_idx;
                                    CREATE INDEX ci_item_itemcode_idx ON ci_item_TEMP (itemcode);""")
        if table_name == 'IM_ItemTransactionHistory':
            cursor_postgres.execute("""DROP INDEX if exists im_itemtxnhist_itemcode_idx;
                                    CREATE INDEX im_itemtxnhist_itemcode_idx ON im_itemtransactionhistory_TEMP (itemcode);
                                    DROP INDEX if exists im_itemtxnhist_transactiondate_idx;
                                    CREATE INDEX im_itemtxnhist_transactiondate_idx ON im_itemtransactionhistory_TEMP (transactiondate);
                                    DROP INDEX if exists im_itemtxnhist_transactioncode_idx;
                                    CREATE INDEX im_itemtxnhist_transactioncode_idx ON im_itemtransactionhistory_TEMP (transactioncode);
                                    DROP INDEX if exists im_itemtxnhist_transactionqty_idx;
                                    CREATE INDEX im_itemtxnhist_transactionqty_idx ON im_itemtransactionhistory_TEMP (transactionqty);""")
        cursor_postgres.execute("drop table if exists " + table_name)
        cursor_postgres.execute("alter table " + table_name + "_TEMP rename to " + table_name)
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        #print(f'{dt.datetime.now()} -- {table_name} table cloned.')

        return table_name
    
    except Exception as e:
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_sage_table :: SAGE ERROR: {table_name} {str(dt.datetime.now())}')
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_sage_table :: {str(e)}')
        

# def create_blends_produced_table():
#     print(f'{dt.datetime.now()} -- starting creation of blends_produced_table.')
#     csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\blends_produced.csv'
#     try:
#         connection_MAS90 = pyodbc.connect("DSN=SOTAMAS90;UID=parker;PWD=Blend2023;",autocommit=True)
#     except Error as this_error:
#         print('SAGE ERROR: Could not connect to Sage. Please verify that internet is connected and Sage is operational.')
#         with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
#             f.write('SAGE ERROR: ' + str(dt.datetime.now()))
#         with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\' + table_name + '_error_log.txt'), 'a', encoding="utf-8") as f:
#             f.write('SAGE ERROR: ' + str(dt.datetime.now()))
#             f.write('\n')
#             f.write(str(this_error))
#         return 'SAGE ERROR: Could not connect to Sage. Please verify that internet is connected and Sage is operational.'
#     cursor_MAS90 = connection_MAS90.cursor()
#     cursor_MAS90.execute("""SELECT itemcode, warehousecode, transactiondate, transactioncode, transactionqty 
#         FROM IM_ItemTransactionHistory
#         WHERE IM_ItemTransactionHistory.transactiondate > {d '2019-01-01'} and 
#         IM_ItemTransactionHistory.transactioncode = 'BR'
#         """)
#     table_contents = list(cursor_MAS90.fetchall())
#     sql_columns_with_types = '''(id serial primary key, 
#         itemcode text, warehousecode text, transactiondate date, transactioncode text, transactionqty numeric
#         )'''
    
#     column_list = ['itemcode', 'warehousecode', 'transactiondate', 'transactioncode', 'transactionqty']

#     table_dataframe = pd.DataFrame.from_records(table_contents, index=None, exclude=None, columns=column_list, coerce_float=False, nrows=None)
#     table_dataframe.to_csv(path_or_buf=csv_path, header=column_list, encoding='utf-8')

#     try:
#         connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
#     except psycopg2.OperationalError as this_error:
#         print('BLENDVERSE DB ERROR: The database is not running. Please start the blendverse and try again.')
#         with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
#             f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
#         with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\' + table_name + '_error_log.txt'), 'a', encoding="utf-8") as f:
#             f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
#             f.write('\n')
#             f.write(str(this_error))
#         return 'BLENDVERSE DB ERROR: The database is not running. Please start the blendverse and try again.'
#     cursor_postgres = connection_postgres.cursor()
#     cursor_postgres.execute("drop table if exists blends_produced_TEMP")
#     cursor_postgres.execute("create table blends_produced_TEMP " + sql_columns_with_types)
#     copy_sql = "copy blends_produced_TEMP from stdin with csv header delimiter as ','"
#     with open(csv_path, 'r', encoding='utf-8') as f:
#         cursor_postgres.copy_expert(sql=copy_sql, file=f)
#     cursor_postgres.execute("drop table if exists blends_produced")
#     cursor_postgres.execute("alter table blends_produced_TEMP rename to blends_produced")
#     connection_postgres.commit()
#     cursor_postgres.close()
#     connection_postgres.close()
#     print(f'{dt.datetime.now()} -- blends_produced table created.')
    

def get_all_transactions():
    try:
        table_name = "IM_ItemTransactionHistory"
        # print('waiting...')
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Pulling from Sage...')
        csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name+'.csv'
        columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '.txt'

        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '..', '..', '.env')
        load_dotenv(dotenv_path=env_path)

        SAGE_USER = os.getenv('SAGE_USER')
        SAGE_PW = os.getenv('SAGE_PW')

        if not SAGE_USER or not SAGE_PW:
            raise ValueError("Sage credentials not found in environment variables.")
        connection_MAS90 = pyodbc.connect(r"Driver={MAS 90 4.0 ODBC Driver}; " + f"UID={SAGE_USER}; PWD={SAGE_PW}; " +
                                                r"""Directory=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90; 
                                                Prefix=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\SY\, 
                                                \\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\==\; 
                                                ViewDLL=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\HOME; Company=KPK; 
                                                LogFile=\PVXODBC.LOG; CacheSize=0; DirtyReads=1; BurstMode=1; 
                                                StripTrailingSpaces=1;""", autocommit=True)
        cursor_MAS90 = connection_MAS90.cursor()
        cursor_MAS90.execute("SELECT * FROM " + table_name)
        table_contents = list(cursor_MAS90.fetchall())
        data_headers = cursor_MAS90.description

        sql_columns_with_types = '(id serial primary key, '
        type_mapping = {
            "<class 'str'>": 'text',
            "<class 'datetime.date'>": 'date',
            "<class 'decimal.Decimal'>": 'decimal'
        }
        column_definitions = [
            f"{column[0]} {type_mapping[str(column[1])]}"
            for column in data_headers
        ]
        sql_columns_with_types += ', '.join(column_definitions) + ')'
        column_names_only_string = ''
        with open(columns_with_types_path, 'w', encoding="utf-8") as f:
            f.write(sql_columns_with_types)

        column_names_only_string = ', '.join(column[0] for column in data_headers)
        column_list = column_names_only_string.split(",")        
        cursor_MAS90.close()
        connection_MAS90.close()

        table_dataframe = pd.DataFrame.from_records(table_contents, index=None, exclude=None, columns=column_list, coerce_float=False, nrows=None)
        table_dataframe.to_csv(path_or_buf=csv_path, header=column_list, encoding='utf-8')

        with open(columns_with_types_path, encoding="utf-8") as file:
            sql_columns_list = file.readlines()
        sql_columns_with_types = sql_columns_list[0]

        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("drop table if exists " + table_name + "_TEMP")
        cursor_postgres.execute("create table " + table_name + "_TEMP" + sql_columns_with_types)
        copy_sql = "copy " + table_name + "_TEMP from stdin with csv header delimiter as ','"
        with open(csv_path, 'r', encoding='utf-8') as f:
            cursor_postgres.copy_expert(sql=copy_sql, file=f)
        # SET UP INDEXES!
        cursor_postgres.execute("""DROP INDEX if exists im_itemtxnhist_itemcode_idx;
                                    CREATE INDEX im_itemtxnhist_itemcode_idx ON im_itemtransactionhistory_TEMP (itemcode);
                                    DROP INDEX if exists im_itemtxnhist_transactiondate_idx;
                                    CREATE INDEX im_itemtxnhist_transactiondate_idx ON im_itemtransactionhistory_TEMP (transactiondate);
                                    DROP INDEX if exists im_itemtxnhist_transactioncode_idx;
                                    CREATE INDEX im_itemtxnhist_transactioncode_idx ON im_itemtransactionhistory_TEMP (transactioncode);
                                    DROP INDEX if exists im_itemtxnhist_transactionqty_idx;
                                    CREATE INDEX im_itemtxnhist_transactionqty_idx ON im_itemtransactionhistory_TEMP (transactionqty);""")
        cursor_postgres.execute("drop table if exists " + table_name)
        cursor_postgres.execute("alter table " + table_name + "_TEMP rename to " + table_name)
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        #print(f'{dt.datetime.now()} -- {table_name} table cloned.')

        return table_name
    
    except Exception as e:
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_all_transactions :: SAGE ERROR: {table_name} {str(dt.datetime.now())}')
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_all_transactions :: {str(e)}')
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        #         f.write('SAGE ERROR: ' + str(dt.datetime.now()))
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\' + table_name + '_error_log.txt'), 'a', encoding="utf-8") as f:
        #     f.write('SAGE ERROR: ' + str(dt.datetime.now()))
        #     f.write('\n')
        #     f.write(str(e))


def sync_im_itemtransactionhistory_incremental(overlap_days=7):
    """
    Incremental sync for IM_ItemTransactionHistory table.
    Only pulls new/recent data and appends to existing table using row_hash deduplication.
    """
    try:
        table_name = "IM_ItemTransactionHistory"
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Starting incremental sync for {table_name}')
        
        csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name + '_incremental.csv'
        columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '_incremental.txt'
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '..', '..', '.env')
        load_dotenv(dotenv_path=env_path)

        SAGE_USER = os.getenv('SAGE_USER')
        SAGE_PW = os.getenv('SAGE_PW')

        if not SAGE_USER or not SAGE_PW:
            raise ValueError("Sage credentials not found in environment variables.")
        
        # First, get the high watermark from PostgreSQL
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        
        # Check if the table exists and has the row_hash column
        cursor_postgres.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'im_itemtransactionhistory' 
            AND column_name = 'row_hash'
        """)
        has_row_hash = cursor_postgres.fetchone() is not None
        
        if not has_row_hash:
            print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Table not ready for incremental sync. Running full sync first.')
            cursor_postgres.close()
            connection_postgres.close()
            return get_sage_table(table_name)
        
        # Get the watermark (latest transaction date in our table)
        cursor_postgres.execute("""
            SELECT COALESCE(MAX(transactiondate), DATE '1900-01-01') 
            FROM im_itemtransactionhistory
        """)
        watermark = cursor_postgres.fetchone()[0]
        cursor_postgres.close()
        connection_postgres.close()
        
        # Calculate the start date for our incremental pull (watermark - overlap)
        start_date = watermark - dt.timedelta(days=overlap_days)
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Watermark: {watermark}, pulling from: {start_date}')
        
        # Connect to Sage and pull incremental data
        connection_MAS90 = pyodbc.connect(r"Driver={MAS 90 4.0 ODBC Driver}; " + f"UID={SAGE_USER}; PWD={SAGE_PW}; " +
                                                r"""Directory=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90; 
                                                Prefix=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\SY\, 
                                                \\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\==\; 
                                                ViewDLL=\\Kinpak-Svr1\Apps\Sage 100 ERP\MAS90\HOME; Company=KPK; 
                                                LogFile=\PVXODBC.LOG; CacheSize=0; DirtyReads=1; BurstMode=1; 
                                                StripTrailingSpaces=1;""", autocommit=True)
        cursor_MAS90 = connection_MAS90.cursor()
        
        # Pull only recent data
        cursor_MAS90.execute(f"SELECT * FROM {table_name} WHERE TransactionDate >= {{d '{start_date}'}} ORDER BY TransactionDate DESC")
        table_contents = list(cursor_MAS90.fetchall())
        data_headers = cursor_MAS90.description
        
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Retrieved {len(table_contents)} rows from Sage')
        
        cursor_MAS90.close()
        connection_MAS90.close()
        
        if not table_contents:
            print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: No new data to sync')
            return table_name
        
        # Prepare column information
        sql_columns_with_types = '(id serial primary key, '
        type_mapping = {
            "<class 'str'>": 'text',
            "<class 'datetime.date'>": 'date',
            "<class 'decimal.Decimal'>": 'decimal'
        }
        column_definitions = [
            f"{column[0]} {type_mapping[str(column[1])]}"
            for column in data_headers
        ]
        sql_columns_with_types += ', '.join(column_definitions) + ', row_hash text)'
        
        with open(columns_with_types_path, 'w', encoding="utf-8") as f:
            f.write(sql_columns_with_types)
        
        column_names_only_string = ', '.join(column[0] for column in data_headers)
        column_list = column_names_only_string.split(",")
        
        # Create DataFrame from Sage data
        table_dataframe = pd.DataFrame.from_records(table_contents, index=None, exclude=None, columns=column_list, coerce_float=False, nrows=None)
        
        # Calculate row hash for each row (excluding id and row_hash columns)
        def calculate_row_hash(row):
            row_dict = row.to_dict()
            # Convert to JSON string and hash it
            row_json = json.dumps(row_dict, sort_keys=True, default=str)
            return hashlib.md5(row_json.encode()).hexdigest()
        
        table_dataframe['row_hash'] = table_dataframe.apply(calculate_row_hash, axis=1)
        
        # Reorder columns to match the expected database schema (Sage columns + row_hash at the end)
        expected_columns = column_list + ['row_hash']
        table_dataframe = table_dataframe[expected_columns]
        
        # Save to CSV with proper column order (no pandas index)
        table_dataframe.to_csv(path_or_buf=csv_path, header=expected_columns, encoding='utf-8', index=False)
        
        # Now perform the incremental merge in PostgreSQL
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        
        # Create staging table
        staging_table = f"{table_name.lower()}_staging"
        cursor_postgres.execute(f"DROP TABLE IF EXISTS {staging_table}")
        cursor_postgres.execute(f"CREATE TABLE {staging_table} {sql_columns_with_types}")
        
        # Copy data to staging table - specify columns explicitly to avoid id column
        sage_columns = column_list  # Original columns from Sage
        copy_columns = sage_columns + ['row_hash']  # Add row_hash at the end
        copy_columns_str = ', '.join(copy_columns)
        
        copy_sql = f"COPY {staging_table} ({copy_columns_str}) FROM STDIN WITH CSV HEADER DELIMITER AS ','"
        with open(csv_path, 'r', encoding='utf-8') as f:
            cursor_postgres.copy_expert(sql=copy_sql, file=f)
        
        # Use the same columns for the insert
        insert_columns_str = copy_columns_str
        
        # Perform the merge - insert only new rows based on row_hash
        merge_sql = f"""
            INSERT INTO im_itemtransactionhistory ({insert_columns_str})
            SELECT {insert_columns_str}
            FROM {staging_table}
            ON CONFLICT (row_hash) DO NOTHING
        """
        cursor_postgres.execute(merge_sql)
        
        # Get count of inserted rows
        inserted_count = cursor_postgres.rowcount
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Inserted {inserted_count} new rows')
        
        # Cleanup staging table
        cursor_postgres.execute(f"DROP TABLE {staging_table}")
        
        # Update indexes (only if we inserted new data)
        if inserted_count > 0:
            cursor_postgres.execute("""
                DROP INDEX IF EXISTS im_itemtxnhist_itemcode_idx;
                CREATE INDEX im_itemtxnhist_itemcode_idx ON im_itemtransactionhistory (itemcode);
                DROP INDEX IF EXISTS im_itemtxnhist_transactiondate_idx;
                CREATE INDEX im_itemtxnhist_transactiondate_idx ON im_itemtransactionhistory (transactiondate);
                DROP INDEX IF EXISTS im_itemtxnhist_transactioncode_idx;
                CREATE INDEX im_itemtxnhist_transactioncode_idx ON im_itemtransactionhistory (transactioncode);
                DROP INDEX IF EXISTS im_itemtxnhist_transactionqty_idx;
                CREATE INDEX im_itemtxnhist_transactionqty_idx ON im_itemtransactionhistory (transactionqty);
            """)
        
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Incremental sync completed successfully')
        return table_name
        
    except Exception as e:
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Error: {str(e)}')
        # Fallback to full sync if incremental fails
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: sync_im_itemtransactionhistory_incremental :: Falling back to full sync')
        return get_sage_table("IM_ItemTransactionHistory")