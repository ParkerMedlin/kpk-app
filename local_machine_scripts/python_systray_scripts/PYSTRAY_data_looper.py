import os
import random
import datetime as dt
import pandas as pd
from multiprocessing import Process
import psycopg2
import pystray
from PIL import Image
from tkinter import messagebox
import tkinter as tk
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
from app_db_mgmt import i_eat_the_specsheet as specsheet_eat
from app_db_mgmt import email_sender


def update_table_status(function_name, function_result):
    time_now = dt.datetime.now()
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
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
    functions = [
        prod_sched_pg.get_prod_schedule,
        horix_pg.get_horix_line_blends,
        prod_sched_pg.get_foam_factor,
        prod_sched_pg.get_starbrite_item_quantities,
        calc_tables_pg.create_bill_of_materials_table,
        calc_tables_pg.create_component_usage_table,
        calc_tables_pg.create_component_shortages_table,
        calc_tables_pg.create_blend_subcomponent_usage_table,
        calc_tables_pg.create_blend_subcomponent_shortage_table,
        calc_tables_pg.create_blend_run_data_table,
        calc_tables_pg.create_timetable_run_data_table,
        calc_tables_pg.create_issuesheet_needed_table,
        calc_tables_pg.create_upcoming_blend_count_table,
        calc_tables_pg.create_upcoming_component_count_table,
        calc_tables_pg.create_weekly_blend_totals_table,
        specsheet_eat.get_spec_sheet,
        update_tables_pg.update_lot_number_sage,
    ]

    exception_list = []
    start_time = dt.datetime.now()

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
                    print(f'{dt.datetime.now()}: {str(e)}')
            except Exception as e:
                print(f'{dt.datetime.now()}: {str(e)}')
                exception_list.append(e)
                print(f'Exceptions thrown so far: {len(exception_list)}')
                try:
                    update_table_status(func.__name__, 'Success')
                except Exception as e:
                    print(f'{dt.datetime.now()}: {str(e)}')
                continue
        print('oh boy here I go again')
        number1 = random.randint(1, 1000000)
        number2 = 69420
        if number2 == number1:
            gigachad_file = open(os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\gigch.txt', 'r')
            file_contents = gigachad_file.read()
            print(file_contents)

    else:
        print("This isn't working. It's not you, it's me. Shutting down the loop now.")
        email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')



def clone_sage_tables():
    table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
    exception_list = []
    start_time = dt.datetime.now()

    while len(exception_list) < 11:
        elapsed_time = dt.datetime.now() - start_time
        if elapsed_time > dt.timedelta(minutes=10):
            start_time = dt.datetime.now()  # Reset the start time after 10 minutes
            exception_list = []
        for item in table_list:
            try:
                sage_pg.get_sage_table(item)
                try:
                    update_table_status(f'get_sage_table({item})', 'Success')
                except Exception as e:
                    print(f'{dt.datetime.now()}: {str(e)}')
            except Exception as e:
                print(f'{dt.datetime.now()}: {str(e)}')
                exception_list.append(e)
                print(f'Exceptions thrown so far: {len(exception_list)}')
                update_table_status(f'get_sage_table({item})', 'Failure')
                continue
    else:
        print("This isn't working. It's not you, it's me. Shutting down the loop now.")
        email_sender.send_email_error(exception_list, 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com')

def show_info(icon):
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
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
            elif time_diff > dt.timedelta(minutes=5) in str(value):
                color = 'red'
            elif  'Failure' in str(value):
                color = 'red'
            else:
                color = 'SystemButtonFace'
            label = tk.Label(window, text=value, bg=color)
            label.grid(row=r+1, column=c)
    
    window.mainloop()


def create_icon(image_path):
    image = Image.open(os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\refresh_icon.png'))
    menu = (pystray.MenuItem('Show Info', lambda icon, item: show_info(icon)),
            pystray.MenuItem('Exit', lambda icon, item: exit_application(icon)))
    icon = pystray.Icon("name", image, "Tank Perv", menu=pystray.Menu(*menu))
    icon.run()

# clone_sage_tables_process = Process(target=clone_sage_tables)
# update_xlsb_tables_process = Process(target=update_xlsb_tables)

def exit_application(icon):
    icon.stop()  # This will stop the system tray ico
    # clone_sage_tables_process.terminate()
    # update_xlsb_tables_process.terminate()
    os._exit(0)    

def main():
    Process(target=clone_sage_tables).start()
    Process(target=update_xlsb_tables).start()
    # Call this function with the path to your icon image
    create_icon(os.path.expanduser('~\\Documents\\kpk-app\\app\\core\\static\\core\\refresh_icon.png'))

if __name__ == "__main__":
    main()

