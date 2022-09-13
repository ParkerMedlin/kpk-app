import subprocess
import sage_to_postgres as f_sage
import prod_sched_to_postgres as f_prod_merge
import table_builder as f_tables
import chem_locations_to_postgres as f_chem_locations
import horix_sched_to_postgres as f_horix_schedule
import os

table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
for item in table_list:
    f_sage.get_sage_table(item)

f_prod_merge.get_prod_schedule()
f_tables.create_tables()
f_chem_locations.get_chem_locations()
f_horix_schedule.get_horix_line_blends()

import_commands_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\import_commands.bat')
subprocess.run(import_commands_path)

user_setup_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\user_setup.bat')
subprocess.run(user_setup_path)

check_imports_path = (os.path.expanduser('~\\Documents') + r'\kpk-app\local_machine_scripts\batch_scripts\check_import_tables.bat')
subprocess.run(check_imports_path)