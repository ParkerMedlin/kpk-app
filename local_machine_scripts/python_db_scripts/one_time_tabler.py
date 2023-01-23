import subprocess
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
import os

table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
for item in table_list:
    sage_pg.get_sage_table(item)

prod_sched_pg.get_prod_schedule()
calc_tables_pg.create_blend_BOM_table()
calc_tables_pg.create_prod_BOM_table()
calc_tables_pg.create_blend_run_data_table()
calc_tables_pg.create_timetable_run_data_table()
calc_tables_pg.create_issuesheet_needed_table()
calc_tables_pg.create_blendthese_table()
calc_tables_pg.create_upcoming_blend_count_table()
horix_pg.get_horix_line_blends()

import_commands_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\import_commands.bat')
subprocess.run(import_commands_path)

user_setup_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\user_setup.bat')
subprocess.run(user_setup_path)

check_imports_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\check_import_tables.bat')
subprocess.run(check_imports_path)