import time
import os
import random
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
from app_db_mgmt import i_eat_the_specsheet as specsheet_eat
import datetime as dt

from multiprocessing import Process

def update_xlsb_tables():
    for retries in range(100):
        for attempt in range(10):
            try:
                while True:
                    prod_sched_pg.get_prod_schedule()
                    prod_sched_pg.get_foam_factor()
                    prod_sched_pg.get_starbrite_item_quantities()
                    calc_tables_pg.create_bill_of_materials_table()
                    calc_tables_pg.create_component_usage_table()
                    calc_tables_pg.create_component_shortages_table()
                    calc_tables_pg.create_blend_subcomponent_usage_table()
                    calc_tables_pg.create_blend_subcomponent_shortage_table()
                    calc_tables_pg.create_blend_run_data_table()
                    calc_tables_pg.create_timetable_run_data_table()
                    calc_tables_pg.create_issuesheet_needed_table()
                    calc_tables_pg.create_blendthese_table()
                    calc_tables_pg.create_upcoming_blend_count_table()
                    calc_tables_pg.create_upcoming_component_count_table()
                    calc_tables_pg.create_weekly_blend_totals_table()
                    specsheet_eat.get_spec_sheet()
                    horix_pg.get_horix_line_blends()
                    update_tables_pg.update_lot_number_sage()
                    print('oh boy here I go again')
                    number1 = random.randint(1, 1000000)
                    number2 = 69420
                    if number2 == number1:
                        gigachad_file = open(os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\gigch.txt', 'r')
                        file_contents = gigachad_file.read()
                        print(file_contents)
            except Exception as e:
                print(f'{dt.datetime.now()}======= {str(e)} =======')
                time.sleep(10)
            else:
                break
        else:
            print("we should try taking a longer break, gonna wait for 1 minute then try again")
            time.sleep(60)

def clone_sage_tables():
    while True:
        table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
        for item in table_list:
            sage_pg.get_sage_table(item)

if __name__ == '__main__':
    Process(target=clone_sage_tables).start()
    Process(target=update_xlsb_tables).start()