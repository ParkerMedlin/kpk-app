import time
# import pandas as pd
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import tank_level_reading
# from app_db_mgmt import horix_sched_to_postgres_experimental as horix_pg
from app_db_mgmt import table_builder as calc_tables_pg
from app_db_mgmt import table_updates as update_tables_pg
# from app_db_mgmt import xtendo_transactum as long_transactions
from app_db_mgmt import i_eat_the_specsheet as specsheet_eat
from app_db_mgmt import tank_level_reading
# from app_db_mgmt import GHS_file_checker


# GHS_file_checker.check_all_filenames()

# sage_pg.get_all_sage_tables()

# sage_pg.get_sage_table('PO_ReceiptHistoryDetail')
# sage_pg.get_sage_table('IM_ItemTransactionHistory')
# sage_pg.get_sage_table('IM_ItemWarehouse')

# sage_pg.get_sage_table('IM_ItemTransactionHistory')
# table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'PO_PurchaseOrderDetail']
# for item in table_list:
#     sage_pg.get_sage_table(item)

# tank_level_reading.update_tank_levels_table()
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
# calc_tables_pg.create_upcoming_blend_count_table()
# calc_tables_pg.create_upcoming_component_count_table()
# calc_tables_pg.create_weekly_blend_totals_table()
# calc_tables_pg.create_adjustment_statistic_table()
# specsheet_eat.get_spec_sheet()
# update_tables_pg.update_lot_number_sage()

all_functions = [
    # tank_level_reading.update_tank_levels_table,
    # prod_sched_pg.get_prod_schedule,
    horix_pg.get_horix_line_blends,
    # prod_sched_pg.get_foam_factor, # unused now that /core/foam-factors/ is a thing
    # prod_sched_pg.get_starbrite_item_quantities,
    # calc_tables_pg.create_bill_of_materials_table,
    # calc_tables_pg.create_component_usage_table,
    # calc_tables_pg.create_component_shortages_table,
    # calc_tables_pg.create_blend_subcomponent_usage_table,
    # calc_tables_pg.create_blend_subcomponent_shortage_table,
    # calc_tables_pg.create_blend_run_data_table,
    # calc_tables_pg.create_timetable_run_data_table,
    # calc_tables_pg.create_upcoming_blend_count_table, # unused now. This work is done on the page
    # calc_tables_pg.create_upcoming_component_count_table, # unused now. This work is done on the page
    # calc_tables_pg.create_weekly_blend_totals_table,
    # specsheet_eat.get_spec_sheet,
    # update_tables_pg.update_lot_number_sage,
    # update_tables_pg.create_daily_blendcounts,
    # update_tables_pg.update_lot_number_desks
]

### TIME COMPARISON ###
for func in all_functions:
    print(f'{func.__name__} go')
    start = time.time()
    func()
    end = time.time()
    print('time elapsed: ' + str(end - start))
    # Append the results of each function run to the dataframe
    
# print('function2 go')
# start = time.time()
# # calc_tables_pg.create_blend_run_data_table()
# # calc_tables_pg.create_timetable_run_data_table()
# calc_tables_pg.create_issuesheet_needed_table()
# end = time.time()
# print('time elapsed: ' + str(end - start))

# Initialize a list to store function names and execution times
# timing_data = []

# # Iterate over all functions in the all_functions dictionary
# for func_name, func in all_functions.items():
#     start_time = time.time()  # Capture start time
#     func()  # Execute the function
#     end_time = time.time()  # Capture end time
#     execution_time = end_time - start_time  # Calculate execution time
    
#     # Append the function name and its execution time as a dictionary to the list
#     timing_data.append({'Function Name': func_name, 'Execution Time': execution_time})

# # Convert the list of dictionaries to a DataFrame
# timing_df = pd.DataFrame(timing_data)

# # Print the DataFrame to display the function names and their execution times
# print(timing_df)
# # At the end of your script, add the following line:
# timing_df.to_csv('~/Desktop/timing_data.csv', index=False)