import time
import os
import sys
import random
import datetime as dt
import pytz
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
from app_db_mgmt import i_eat_the_specsheet as specsheet_eat
from app_db_mgmt import email_sender
from app_db_mgmt import tank_level_reading
import datetime as dt
from multiprocessing import Process
import psycopg2
import hashlib

TOGGLE_TABLE = 'core_functiontoggle'


def get_function_toggle_status(function_name):
    """Return 'on' or 'off' for a given function toggle; default to 'on'."""
    connection_postgres = None
    cursor_postgres = None
    try:
        connection_postgres = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(
            f"SELECT status FROM {TOGGLE_TABLE} WHERE function_name = %s",
            (function_name,)
        )
        result = cursor_postgres.fetchone()
        if result and result[0]:
            return result[0].strip().lower()
    except Exception as e:
        print(f"{dt.datetime.now()} :: data_looper.py :: get_function_toggle_status :: Failed to fetch status for {function_name}: {str(e)}")
    finally:
        if cursor_postgres:
            cursor_postgres.close()
        if connection_postgres:
            connection_postgres.close()
    return 'on'


def update_table_status(function_name, function_result):
    time_now = dt.datetime.now()
    connection_postgres = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()

    # Check if a row with the given function_name exists in the table
    cursor_postgres.execute("SELECT * FROM core_loopstatus WHERE function_name = %s", (function_name,))
    row = cursor_postgres.fetchone()

    if row:
        # If a row is found, update the function_result and time_stamp fields
        cursor_postgres.execute("UPDATE core_loopstatus SET function_result = %s, time_stamp = %s WHERE function_name = %s",
                       (function_result, time_now, function_name))
    else:
        # If no row is found, create a new row
        cursor_postgres.execute("INSERT INTO core_loopstatus (function_name, function_result, time_stamp) VALUES (%s, %s, %s)",
                       (function_name, function_result, time_now))

    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()


def _log_toggle_skip(function_name):
    print(
        f"{dt.datetime.now()} :: data_looper.py :: {function_name} :: "
        f"{function_name} has been toggled OFF, skipping for now. "
        "This can be changed on the function-toggles page in the Admin panel."
    )


def can_run_function(function_name, sleep_seconds=None):
    """Return True when the toggle for function_name is on; otherwise log and optionally sleep."""
    status = get_function_toggle_status(function_name)
    if status == 'off':
        _log_toggle_skip(function_name)
        if sleep_seconds:
            time.sleep(sleep_seconds)
        return False
    return True


def update_xlsb_tables():
    functions = [
        tank_level_reading.update_tank_levels_table,
        prod_sched_pg.get_prod_schedule,
        horix_pg.get_horix_line_blends,
        prod_sched_pg.get_starbrite_item_quantities,
        calc_tables_pg.create_bill_of_materials_table,
        calc_tables_pg.create_component_usage_table,
        calc_tables_pg.create_component_shortages_table,
        calc_tables_pg.create_blend_subcomponent_usage_table,
        calc_tables_pg.create_blend_subcomponent_shortage_table,
        calc_tables_pg.create_blend_run_data_table,
        calc_tables_pg.create_timetable_run_data_table,
        # calc_tables_pg.create_upcoming_blend_count_table, # unused now. This work is done on the page
        # calc_tables_pg.create_upcoming_component_count_table, # unused now. This work is done on the page
        calc_tables_pg.create_weekly_blend_totals_table,
        specsheet_eat.get_spec_sheet,
        update_tables_pg.update_lot_number_sage,
        update_tables_pg.update_lot_number_desks
    ]

    exception_list = []
    start_time = dt.datetime.now()

    while len(exception_list) < 11:
        if not can_run_function('update_xlsb_tables', sleep_seconds=60):
            continue
        perf_start_time = dt.datetime.now()
        elapsed_time = dt.datetime.now() - start_time
        if elapsed_time > dt.timedelta(minutes=10):
            start_time = dt.datetime.now()  # Reset the start time after 10 minutes
            exception_list = []
        for func in functions:
            function_name = func.__name__
            if not can_run_function(function_name):
                try:
                    update_table_status(function_name, 'Skipped (Toggled Off)')
                except Exception as e:
                    print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: {function_name} skipped :: {str(e)}')
                continue
            try:
                func()
                try:
                    update_table_status(function_name, 'Success')
                except Exception as e:
                    print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: {function_name} line {e.__traceback__.tb_lineno}: {str(e)}')
            except Exception as e:
                print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: {function_name} line {e.__traceback__.tb_lineno}: {str(e)}')
                exception_list.append(e)
                print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: Exceptions thrown so far: {len(exception_list)}')
                try:
                    update_table_status(function_name, 'Success')
                except Exception as e:
                    print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: {str(e)}')
                continue
        perf_elapsed_time = dt.datetime.now() - perf_start_time
        hours, remainder = divmod(perf_elapsed_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: oh boy here I go again (looped in {int(hours)}:{int(minutes)}:{int(seconds)})')
        number1 = random.randint(1, 1000000)
        number2 = 69420
        if number2 == number1:
            gigachad_file = open(os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\gigch.txt', 'r')
            file_contents = gigachad_file.read()
            print(f'{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: {file_contents}')

    else:
        print(f"{dt.datetime.now()} :: data_looper.py :: update_xlsb_tables :: This isn't working. It's not you, it's me. Shutting down the loop now.")
        email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')

def clone_sage_tables():
    table_list = [
        'BM_BillHeader',
        'BM_BillDetail',
        'CI_Item',
        'IM_ItemWarehouse',
        'IM_ItemCost',
        'IM_ItemTransactionHistory',
        'PO_PurchaseOrderDetail',
        'PO_PurchaseOrderHeader',
        'SO_SalesOrderDetail',
    ]
    exception_list = []
    start_time = dt.datetime.now()

    while len(exception_list) < 11:
        if not can_run_function('clone_sage_tables', sleep_seconds=60):
            continue
        perf_start_time = dt.datetime.now()
        elapsed_time = dt.datetime.now() - start_time
        if elapsed_time > dt.timedelta(minutes=10):
            start_time = dt.datetime.now()  # Reset the start time after 10 minutes
            exception_list = []
        for item in table_list:
            function_name = f'get_sage_table({item})'
            if not can_run_function(function_name):
                try:
                    update_table_status(function_name, 'Skipped (Toggled Off)')
                except Exception as e:
                    print(f'{dt.datetime.now()} :: data_looper.py :: clone_sage_tables :: {function_name} skipped :: {str(e)}')
                continue
            try:
                sage_pg.get_sage_table(item)
                try:
                    update_table_status(function_name, 'Success')
                except Exception as e:
                    print(f'{dt.datetime.now()} :: data_looper.py :: clone_sage_tables :: {str(e)}\nProblem with updating table status after updating {item}')
            except Exception as e:
                print(f'{dt.datetime.now()} :: data_looper.py :: clone_sage_tables :: {str(e)}\nProblem with updating table {item}')
                exception_list.append(e)
                print(f'{dt.datetime.now()} :: data_looper.py :: clone_sage_tables :: Exceptions thrown so far: {len(exception_list)}')
                update_table_status(function_name, 'Failure')
                continue
        perf_elapsed_time = dt.datetime.now() - perf_start_time
        hours, remainder = divmod(perf_elapsed_time.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"{dt.datetime.now()} :: data_looper.py :: clone_sage_tables :: ===OK=== Sage Loop Complete ({int(hours)}:{int(minutes)}:{int(seconds)}), Begin Sage Loop ===OK===")
    else:
        print(f"{dt.datetime.now()} :: data_looper.py :: clone_sage_tables :: This isn't working. It's not you, it's me. Shutting down the loop now.")
        email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')
        os.execv(sys.executable, ['python'] + sys.argv)

def log_tank_levels_table():
    exception_list = []
    function_name = 'log_tank_levels_table'
    while len(exception_list) < 11:
        if not can_run_function(function_name, sleep_seconds=120):
            continue
        try:
            tank_level_reading.log_tank_levels_table()
            time.sleep(300)
        except Exception as e:
            print(f'{dt.datetime.now()} :: data_looper.py :: log_tank_levels_table :: {str(e)}')
            exception_list.append(e)
            print(f'{dt.datetime.now()} :: data_looper.py :: log_tank_levels_table :: Exceptions thrown so far: {len(exception_list)}')
            continue
    else:
        print(f"{dt.datetime.now()} :: data_looper.py :: log_tank_levels_table :: This isn't working. It's not you, it's me. Shutting down the loop now.")
        email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')
        os.execv(sys.executable, ['python'] + sys.argv)

def check_latest_table_updates():
    time.sleep(360)
    strings_to_check_for = [
        'get_sage_table(PO_PurchaseOrderDetail)','get_sage_table(CI_Item)','create_component_usage_table',
        'create_timetable_run_data_table','get_spec_sheet','update_tank_levels_table','get_sage_table(PO_PurchaseOrderHeader)',
        'get_sage_table(IM_ItemWarehouse)','get_horix_line_blends','create_bill_of_materials_table','create_weekly_blend_totals_table',
        'update_lot_number_sage','get_sage_table(IM_ItemCost)','get_sage_table(BM_BillHeader)','get_starbrite_item_quantities',
        'create_blend_subcomponent_usage_table','update_lot_number_desks','get_prod_schedule','get_sage_table(IM_ItemTransactionHistory)',
        'create_component_shortages_table','create_blend_subcomponent_shortage_table','create_blend_run_data_table','get_sage_table(BM_BillDetail)'
    ]

    function_name = 'check_latest_table_updates'

    while True:
        if not can_run_function(function_name, sleep_seconds=120):
            continue
        time_now = dt.datetime.now()
        connection_postgres = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        for check_string in strings_to_check_for:
            try:
                cursor_postgres.execute("""
                    SELECT time_stamp 
                    FROM core_loopstatus 
                    WHERE function_name = %s 
                    ORDER BY time_stamp DESC 
                    LIMIT 1
                """, (check_string,))
                result = cursor_postgres.fetchone()
                if result:
                    time_stamp = result
                    time_diff = time_now - time_stamp[0]
                    if time_diff > dt.timedelta(minutes=5):
                        print(f"{dt.datetime.now()} :: data_looper.py :: check_latest_table_updates :: {check_string}: Last update was {time_diff.total_seconds() / 60:.1f} minutes ago")
                        email_sender.send_email_timeout('pmedlin@kinpakinc.com,jdavis@kinpakinc.com')
                        sys.exit()  # Exit the process when timeout occurs
                else:
                    print(f"{dt.datetime.now()} :: data_looper.py :: check_latest_table_updates :: {check_string}: No updates found")
            except Exception as e:
                print(f"{dt.datetime.now()} :: data_looper.py :: check_latest_table_updates :: Error checking {check_string}: {str(e)}")
        
        cursor_postgres.close()
        connection_postgres.close()
        time.sleep(360) # Sleep for 6 minutes

if __name__ == '__main__':
    Process(target=clone_sage_tables).start()
    Process(target=update_xlsb_tables).start()
    Process(target=log_tank_levels_table).start()
    Process(target=check_latest_table_updates).start()

