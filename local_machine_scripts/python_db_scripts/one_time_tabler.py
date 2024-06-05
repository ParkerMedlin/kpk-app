from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
from app_db_mgmt import i_eat_the_specsheet as specsheet_eat
from app_db_mgmt import tank_level_reading
import datetime as dt

table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
for item in table_list:
    sage_pg.get_sage_table(item)

functions = [
        tank_level_reading.update_tank_levels_table,
        prod_sched_pg.get_prod_schedule,
        horix_pg.get_horix_line_blends,
        # prod_sched_pg.get_foam_factor, # unused now that /core/foam-factors/ is a thing
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
    ]

for func in functions:
    try:
        func()
    except Exception as e:
        print(f'{dt.datetime.now()}: {str(e)}')
        continue