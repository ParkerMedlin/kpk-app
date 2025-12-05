from __future__ import generators
import pyodbc
from pyodbc import Error
import psycopg2
import os
import pandas as pd
import datetime as dt
from dotenv import load_dotenv

def get_sage_connection():
    """Get a connection to the Sage database."""

    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, '..', '..', '.env')
    load_dotenv(dotenv_path=env_path)
    SAGE_CONNECTION_STRING = os.getenv('SAGE_CONNECTION_STRING')
    if not SAGE_CONNECTION_STRING:
        raise ValueError("Sage credentials not found in environment variables.")
    connection_MAS90 = pyodbc.connect(SAGE_CONNECTION_STRING, autocommit=True)
    return connection_MAS90

def get_all_sage_tables():
    """Get all table names from the Sage database."""
    try:
        connection_MAS90 = get_sage_connection()
        cursor_MAS90 = connection_MAS90.cursor()

        cursor_MAS90.execute("SELECT * FROM INFORMATION_SCHEMA")
        tables = cursor_MAS90.fetchall()
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_all_sage_tables :: {tables}')

        cursor_MAS90.close()
        connection_MAS90.close()
    except Error as e:
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_all_sage_tables :: Error: {e}')

def get_sage_table(table_name):
    try:
        csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name+'.csv'
        columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '.txt'
        
        connection_MAS90 = get_sage_connection()
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

        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')

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
        if table_name == 'SO_SalesOrderDetail':
            cursor_postgres.execute("""DROP INDEX if exists so_salesorderdetail_salesorderno_idx;
                                    CREATE INDEX so_salesorderdetail_salesorderno_idx ON so_salesorderdetail_TEMP (salesorderno);
                                    DROP INDEX if exists so_salesorderdetail_itemcode_idx;
                                    CREATE INDEX so_salesorderdetail_itemcode_idx ON so_salesorderdetail_TEMP (itemcode);
                                    DROP INDEX if exists so_salesorderdetail_promisedate_idx;
                                    CREATE INDEX so_salesorderdetail_promisedate_idx ON so_salesorderdetail_TEMP (promisedate);""")
        cursor_postgres.execute("drop table if exists " + table_name)
        cursor_postgres.execute("alter table " + table_name + "_TEMP rename to " + table_name)
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()

        return table_name
    
    except Exception as e:
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_sage_table :: SAGE ERROR: {table_name} {str(dt.datetime.now())}')
        print(f'{dt.datetime.now()} :: sage_to_postgres.py :: get_sage_table :: {str(e)}')
        
def get_all_transactions():
    try:
        table_name = "IM_ItemTransactionHistory"
        csv_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\' + table_name+'.csv'
        columns_with_types_path = os.path.expanduser('~\\Documents') + '\\kpk-app\\db_imports\\sql_columns_with_types\\' + table_name + '.txt'
        
        connection_MAS90 = get_sage_connection()
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
