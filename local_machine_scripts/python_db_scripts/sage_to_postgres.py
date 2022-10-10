from __future__ import generators
import pyodbc
from pyodbc import Error
import psycopg2
import time
import os
import pandas as pd
import datetime as dt

def get_sage_table(table_name):
    print('Executing get_sage_table(' + table_name + ')...')
    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        f.write('Pulling from Sage...')
    time_start = time.perf_counter()
    csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name+'.csv'
    columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '.txt'
    try:
        connection_MAS90 = pyodbc.connect("DSN=SOTAMAS90;UID=parker;PWD=blend2021;",autocommit=True)
    except Error as this_error:
        print('SAGE ERROR: Could not connect to Sage. Please verify that internet is connected and Sage is operational.')
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('SAGE ERROR: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\' + table_name + '_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('SAGE ERROR: ' + str(dt.datetime.now()))
            f.write('\n')
            f.write(str(this_error))
        return 'SAGE ERROR: Could not connect to Sage. Please verify that internet is connected and Sage is operational.'
    cursor_MAS90 = connection_MAS90.cursor()
    if table_name == "IM_ItemTransactionHistory":
        date_restraint = str(dt.date.today() - dt.timedelta(weeks=24))
        cursor_MAS90.execute("SELECT * FROM " + table_name + " WHERE IM_ItemTransactionHistory.TransactionDate > {d '%s'}" % date_restraint)
    else:
        cursor_MAS90.execute("SELECT * FROM " + table_name)
    time_checkpoint = time.perf_counter()
    print('don laod cursor for ' + table_name + f': {time_checkpoint - time_start:0.4f} seconds.')
    table_contents = list(cursor_MAS90.fetchall())
    data_headers = cursor_MAS90.description

    ### maybe someday look at this one with a critical eye
    sql_columns_with_types = '(id serial primary key, '
    listPos = 0
    iter = 0
    for iter in range(len(data_headers)):
        sql_columns_with_types = sql_columns_with_types + data_headers[listPos][0]
        if str(data_headers[listPos][1]) == "<class 'str'>":
            sql_columns_with_types = sql_columns_with_types + ' text, '
        elif str(data_headers[listPos][1]) == "<class 'datetime.date'>":
            sql_columns_with_types = sql_columns_with_types + ' date, '
        elif str(data_headers[listPos][1]) == "<class 'decimal.Decimal'>":
            sql_columns_with_types = sql_columns_with_types + ' decimal, '
        listPos += 1
    sql_columns_with_types = sql_columns_with_types[:len(sql_columns_with_types)-2] + ')'
    column_names_only_string = ''

    with open(columns_with_types_path, 'w', encoding="utf-8") as f:
        f.write(sql_columns_with_types)

    qiter = 0
    for qiter in range(len(data_headers)):
        column_names_only_string = column_names_only_string + data_headers[qiter][0] + ', '
    column_names_only_string = column_names_only_string[:len(column_names_only_string)-2]
    column_list = column_names_only_string.split(",")
    cursor_MAS90.close()
    connection_MAS90.close()

    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        f.write('Writing to csv...')

    table_dataframe = pd.DataFrame.from_records(table_contents, index=None, exclude=None, columns=column_list, coerce_float=False, nrows=None)
    table_dataframe.to_csv(path_or_buf=csv_path, header=column_list, encoding='utf-8')
    print('csv saved for ' + table_name +'. Now attempting to write to blendverse db...')

    with open(columns_with_types_path, encoding="utf-8") as file:
        sql_columns_list = file.readlines()
    sql_columns_with_types = sql_columns_list[0]

    with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
        f.write('Writing to postgres...')
    
    try:
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    except psycopg2.OperationalError as this_error:
        print('BLENDVERSE DB ERROR: The database is not running. Please start the blendverse and try again.')
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + table_name + '_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\' + table_name + '_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('BLENDVERSE DB ERROR: ' + str(dt.datetime.now()))
            f.write('\n')
            f.write(str(this_error))
        return 'BLENDVERSE DB ERROR: The database is not running. Please start the blendverse and try again.'
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("drop table if exists " + table_name + "_TEMP")
    cursor_postgres.execute("create table " + table_name + "_TEMP" + sql_columns_with_types)
    copy_sql = "copy " + table_name + "_TEMP from stdin with csv header delimiter as ','"
    with open(csv_path, 'r', encoding='utf-8') as f:
        cursor_postgres.copy_expert(sql=copy_sql, file=f)
    cursor_postgres.execute("drop table if exists " + table_name)
    cursor_postgres.execute("alter table " + table_name + "_TEMP rename to " + table_name)
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()
    time_checkpoint = time.perf_counter()
    print(f'Complete in {time_checkpoint - time_start:0.4f} seconds','world record prolly')