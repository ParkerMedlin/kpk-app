"""
Data Sync Worker
================
Core ETL engine that synchronizes data from Sage 100 ERP, SharePoint schedules,
and builds calculated tables in PostgreSQL.

Replaces: PYSTRAY_data_looper.py
Location: host-services/workers/data_sync.py
"""

import os
import sys
import random
import datetime as dt
import pandas as pd
from multiprocessing import Process
import psycopg2
import pystray
from PIL import Image
from tkinter import messagebox
import tkinter as tk
import logging
import time

# --- Path Configuration ---
KPK_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOST_SERVICES_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# --- Logging Configuration ---
LOG_DIR = os.path.join(HOST_SERVICES_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'data_sync.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add the ETL modules to path
ETL_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'local_machine_scripts', 'python_db_scripts'))
if ETL_PATH not in sys.path:
    sys.path.insert(0, ETL_PATH)

from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
from app_db_mgmt import i_eat_the_specsheet as specsheet_eat
from app_db_mgmt import email_sender
from app_db_mgmt import tank_level_reading
from app_db_mgmt.sharepoint_download import download_to_memory


def sync_production_data():
    """
    Downloads ProductionSchedule once to memory, then runs both
    sync_production_schedule and get_horix_line_blends using the same buffer.
    Eliminates duplicate downloads and file locking issues.
    """
    logger.info("sync_production_data: Downloading ProductionSchedule to memory...")
    file_buffer = download_to_memory("ProductionSchedule")
    logger.info("sync_production_data: Download complete, processing...")
    try:
        prod_sched_pg.sync_production_schedule(file_buffer)
        horix_pg.get_horix_line_blends(file_buffer)
    finally:
        file_buffer.close()
        logger.info("sync_production_data: Buffer closed")

# --- Configuration ---
SERVICE_NAME = "Data Sync Worker"
DB_CONNECTION_STRING = 'postgresql://postgres:blend2021@127.0.0.1:5432/blendversedb'
ICON_PATH = os.path.join(KPK_APP_ROOT, 'app', 'core', 'static', 'core', 'media', 'icons', 'pystray', 'refresh_icon.png')


def update_table_status(function_name, function_result):
    time_now = dt.datetime.now()
    connection_postgres = psycopg2.connect(DB_CONNECTION_STRING)
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


def update_xlsb_tables():
    try:
        logger.info("update_xlsb_tables: Starting...")
        # Aligned with local_machine_scripts/python_db_scripts/data_looper.py
        functions = [
            tank_level_reading.update_tank_levels_table,
            sync_production_data,  # Single download: sync_production_schedule + get_horix_line_blends
            calc_tables_pg.create_bill_of_materials_table,
            calc_tables_pg.create_component_usage_table,
            calc_tables_pg.create_component_shortages_table,
            calc_tables_pg.create_blend_subcomponent_usage_table,
            calc_tables_pg.create_blend_subcomponent_shortage_table,
            calc_tables_pg.create_blend_run_data_table,
            calc_tables_pg.create_timetable_run_data_table,
            # create_upcoming_blend_count_table - unused, work done on page
            # create_upcoming_component_count_table - unused, work done on page
            calc_tables_pg.create_weekly_blend_totals_table,
            specsheet_eat.get_spec_sheet,
            update_tables_pg.update_lot_number_sage,
            update_tables_pg.update_lot_number_desks,
        ]

        exception_list = []
        start_time = dt.datetime.now()
        logger.info("update_xlsb_tables: Entering main loop...")

        while len(exception_list) < 11:
            elapsed_time = dt.datetime.now() - start_time
            if elapsed_time > dt.timedelta(minutes=10):
                start_time = dt.datetime.now()  # Reset the start time after 10 minutes
                exception_list = []
            for func in functions:
                try:
                    func()
                    try:
                        update_table_status(func.__name__, 'Success')
                    except Exception as e:
                        logger.error(f'Status update error: {str(e)}')
                except Exception as e:
                    logger.error(f'Function {func.__name__} failed: {str(e)}')
                    exception_list.append(e)
                    logger.warning(f'Exceptions thrown so far: {len(exception_list)}')
                    try:
                        update_table_status(func.__name__, 'Failure')
                    except Exception as e:
                        logger.error(f'Status update error: {str(e)}')
                    continue
            logger.info('Completed ETL cycle, starting next iteration...')
            number1 = random.randint(1, 1000000)
            number2 = 69420
            if number2 == number1:
                gigachad_file = open(os.path.join(KPK_APP_ROOT, 'local_machine_scripts', 'gigch.txt'), 'r')
                file_contents = gigachad_file.read()
                logger.info(file_contents)

        else:
            logger.error("Too many exceptions. Shutting down the loop now.")
            email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')
    except Exception as e:
        logger.exception(f"update_xlsb_tables CRASHED: {e}")



def clone_sage_tables():
    try:
        logger.info("clone_sage_tables: Starting...")
        table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail', 'SO_SalesOrderDetail', 'PO_PurchaseOrderHeader']
        exception_list = []
        start_time = dt.datetime.now()
        logger.info("clone_sage_tables: Entering main loop...")

        while len(exception_list) < 11:
            elapsed_time = dt.datetime.now() - start_time
            if elapsed_time > dt.timedelta(minutes=10):
                start_time = dt.datetime.now()  # Reset the start time after 10 minutes
                exception_list = []
            for item in table_list:
                try:
                    table_start = dt.datetime.now()
                    logger.info(f'Sage table {item}: Starting sync...')
                    sage_pg.get_sage_table(item)
                    table_elapsed = dt.datetime.now() - table_start
                    logger.info(f'Sage table {item}: Completed in {table_elapsed.total_seconds():.1f}s')
                    try:
                        update_table_status(f'get_sage_table({item})', 'Success')
                    except Exception as e:
                        logger.error(f'Status update error: {str(e)}')
                except Exception as e:
                    logger.error(f'Sage table {item} failed: {str(e)}')
                    exception_list.append(e)
                    logger.warning(f'Exceptions thrown so far: {len(exception_list)}')
                    update_table_status(f'get_sage_table({item})', 'Failure')
                    continue

            # Sync daily transactions and update rolling/deeptime tables
            try:
                table_start = dt.datetime.now()
                logger.info('Daily transactions: Starting sync...')
                sage_pg.get_sage_daily_transactions()
                update_tables_pg.sync_transaction_history_tables()
                table_elapsed = dt.datetime.now() - table_start
                logger.info(f'Daily transactions: Completed in {table_elapsed.total_seconds():.1f}s')
                update_table_status('sync_transaction_history_tables', 'Success')
            except Exception as e:
                logger.error(f'Daily transactions sync failed: {str(e)}')
                exception_list.append(e)
                update_table_status('sync_transaction_history_tables', 'Failure')
        else:
            logger.error("Too many exceptions in Sage sync. Shutting down the loop now.")
            email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')
    except Exception as e:
        logger.exception(f"clone_sage_tables CRASHED: {e}")


def log_tank_levels_table():
    """Continuously log live tank levels into core_tanklevellog."""
    try:
        logger.info("log_tank_levels_table: Starting...")
        exception_list = []
        while len(exception_list) < 11:
            try:
                tank_level_reading.log_tank_levels_table()
                # Sleep 5 minutes between polls to match prior behavior
                time.sleep(300)
            except Exception as e:
                logger.error(f"log_tank_levels_table failed: {str(e)}")
                exception_list.append(e)
                logger.warning(f"log_tank_levels_table exceptions so far: {len(exception_list)}")
                # brief backoff before retrying
                time.sleep(60)
        else:
            logger.error("log_tank_levels_table: Too many exceptions, shutting down loop.")
            email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')
    except Exception as e:
        logger.exception(f"log_tank_levels_table CRASHED: {e}")

def show_info(icon):
    connection_postgres = psycopg2.connect(DB_CONNECTION_STRING)
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute('select * from core_loopstatus')
    loop_status = cursor_postgres.fetchall()

    # Format the loop_status as a DataFrame
    df = pd.DataFrame(loop_status, columns=['id', 'function_name', 'function_result', 'time_stamp'])

    connection_postgres.close()
    cursor_postgres.close()

    window = tk.Tk()
    window.title("Loop Status")

    for c in range(len(df.columns)):
        label = tk.Label(window, text=df.columns[c])
        label.grid(row=0, column=c)

    for r in range(len(df)):
        time_now = dt.datetime.now()
        row_time = df.iat[r, df.columns.get_loc('time_stamp')]
        time_diff = time_now - row_time
        for c in range(len(df.columns)):
            value = df.iat[r, c]
            if 'Success' in str(value) and time_diff <= dt.timedelta(minutes=5):
                color = 'green'
            elif 'Success' in str(value) and time_diff > dt.timedelta(minutes=5):
                color = 'red'  # Success but stale (over 5 min old)
            elif 'Failure' in str(value):
                color = 'red'
            else:
                color = 'SystemButtonFace'
            label = tk.Label(window, text=value, bg=color)
            label.grid(row=r+1, column=c)

    window.mainloop()


def create_icon(image_path):
    try:
        image = Image.open(ICON_PATH)
    except FileNotFoundError:
        logger.warning(f"Icon not found at {ICON_PATH}, using default")
        image = Image.new('RGB', (64, 64), color='green')
    menu = (pystray.MenuItem('Show Info', lambda icon, item: show_info(icon)),
            pystray.MenuItem('Exit', lambda icon, item: exit_application(icon)))
    icon = pystray.Icon("data_sync", image, SERVICE_NAME, menu=pystray.Menu(*menu))
    icon.run()


def exit_application(icon):
    logger.info("Exit command received. Shutting down data_sync service.")
    icon.stop()  # This will stop the system tray icon
    os._exit(0)

def main():
    logger.info(f"Starting {SERVICE_NAME}...")
    logger.info(f"Log file: {LOG_FILE}")
    Process(target=clone_sage_tables).start()
    logger.info("Started clone_sage_tables process")
    Process(target=update_xlsb_tables).start()
    logger.info("Started update_xlsb_tables process")
    Process(target=log_tank_levels_table).start()
    logger.info("Started log_tank_levels_table process")
    # Call this function with the path to your icon image
    create_icon(ICON_PATH)

if __name__ == "__main__":
    main()
