from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
import time

# sage_pg.get_sage_table('IM_ItemCost')
# table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
# for item in table_list:
#     sage_pg.get_sage_table(item)
# prod_sched_pg.get_prod_schedule()
# prod_sched_pg.get_foam_factor()
# prod_sched_pg.get_starbrite_item_quantities()
# calc_tables_pg.create_bill_of_materials_table()
# calc_tables_pg.create_component_usage_table()
# calc_tables_pg.create_component_shortages_table()
# calc_tables_pg.create_blend_subcomponent_usage_table()
# calc_tables_pg.create_blend_subcomponent_shortage_table()
# calc_tables_pg.create_blend_run_data_table()
# calc_tables_pg.create_timetable_run_data_table()
# calc_tables_pg.create_issuesheet_needed_table()
# calc_tables_pg.create_blendthese_table()
# calc_tables_pg.create_upcoming_blend_count_table()
# calc_tables_pg.create_upcoming_component_count_table()
# calc_tables_pg.create_weekly_blend_totals_table()
# horix_pg.get_horix_line_blends()
# update_tables_pg.update_lot_number_sage()

### TIME COMPARISON ###
print('function1 go')
start = time.time()
# calc_tables_pg.create_component_usage_table()
calc_tables_pg.newtt()
end = time.time()
print('time elapsed: ' + str(end - start))
print('function2 go')
start = time.time()
# calc_tables_pg.create_blend_run_data_table()
# calc_tables_pg.create_timetable_run_data_table()
calc_tables_pg.create_issuesheet_needed_table()
end = time.time()
print('time elapsed: ' + str(end - start))


