import time
# from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
# from app_db_mgmt import horix_sched_to_postgres as horix_pg
# from app_db_mgmt import table_builder as calc_tables_pg
# from app_db_mgmt import table_updates as update_tables_pg
# from app_db_mgmt import xtendo_transactum as long_transactions
# from app_db_mgmt import i_eat_the_specsheet as specsheet_eat


sage_pg.get_all_transactions()

# sage_pg.get_sage_table('CI_Item')
# sage_pg.get_sage_table('IM_ItemTransactionHistory')
# long_transactions.get_sage_table('IM_ItemTransactionHistory')

# sage_pg.get_sage_table('IM_ItemCost')
# table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
# for item in table_list:
#     sage_pg.get_sage_table(item)


# calc_tables_pg.create_bill_of_materials_table()
# prod_sched_pg.get_prod_schedule()
# horix_pg.get_horix_line_blends()
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
# calc_tables_pg.create_adjustment_statistic_table()
# specsheet_eat.get_spec_sheet()
# update_tables_pg.update_lot_number_sage()

# all_functions = {
    # 'create_bill_of_materials_table' : calc_tables_pg.create_bill_of_materials_table,
    # 'get_prod_schedule' : prod_sched_pg.get_prod_schedule,
    # 'get_foam_factor' : prod_sched_pg.get_foam_factor,
    # 'get_starbrite_item_quantities' : prod_sched_pg.get_starbrite_item_quantities,
    # 'create_component_usage_table' : calc_tables_pg.create_component_usage_table,
    # 'create_component_shortages_table' : calc_tables_pg.create_component_shortages_table,
    # 'create_blend_subcomponent_usage_table' : calc_tables_pg.create_blend_subcomponent_usage_table,
    # 'create_blend_subcomponent_shortage_table' : calc_tables_pg.create_blend_subcomponent_shortage_table,
    # 'create_blend_run_data_table' : calc_tables_pg.create_blend_run_data_table,
    # 'create_timetable_run_data_table' : calc_tables_pg.create_timetable_run_data_table,
    # 'create_issuesheet_needed_table' : calc_tables_pg.create_issuesheet_needed_table,
    # 'create_blendthese_table' : calc_tables_pg.create_blendthese_table,
    # 'create_upcoming_blend_count_table' : calc_tables_pg.create_upcoming_blend_count_table,
    # 'create_upcoming_component_count_table' : calc_tables_pg.create_upcoming_component_count_table,
    # 'create_weekly_blend_totals_table' : calc_tables_pg.create_weekly_blend_totals_table,
    # 'create_adjustment_statistic_table' : calc_tables_pg.create_adjustment_statistic_table,
    # 'get_horix_line_blends' : horix_pg.get_horix_line_blends,
    # 'update_lot_number_sage' : update_tables_pg.update_lot_number_sage,
    # 'check_hashes' : sage_pg.check_hashes
# }

# # ### TIME COMPARISON ###
# for func_name, func in all_functions.items():
#     print(f'{func_name} go')
#     start = time.time()
#     func('ci_item')
    # calc_tables_pg.newtt()
    # end = time.time()
    # print('time elapsed: ' + str(end - start))
# print('function2 go')
# start = time.time()
# # calc_tables_pg.create_blend_run_data_table()
# # calc_tables_pg.create_timetable_run_data_table()
# calc_tables_pg.create_issuesheet_needed_table()
# end = time.time()
# print('time elapsed: ' + str(end - start))


