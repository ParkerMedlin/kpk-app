import psycopg2
import time
import curses
from curses import init_pair

col1_left_border = 0
col2_left_border = 35
col2_right_border = 61

table_list = [
    'blend_bill_of_materials', 'blend_run_data', 'blendthese',
    'bm_billdetail', 'bm_billheader', 'chem_location', 'ci_item',
    'core_blendingstep', 'core_blendinstruction',
    'core_checklistlog', 'core_checklistsubmissionrecord',
    'core_countrecord', 'core_deskoneschedule',
    'core_desktwoschedule', 'core_foamfactor',
    'core_forklift', 'core_lotnumrecord', 'hx_blendthese',
    'im_itemcost', 'im_itemtransactionhistory',
    'im_itemwarehouse', 'issue_sheet_needed',
    'po_purchaseorderdetail', 'prod_bill_of_materials',
    'prodmerge_run_data', 'timetable_run_data',
    'upcoming_blend_count'
]

def draw_blendverse_table(stdscr):
    
        stdscr.addstr(14,0,"|              Table               |   Number of Rows   |", curses.A_REVERSE)
        stdscr.addstr(15,0,"|----------------------------------+--------------------|")
        # for row_number, table in enumerate(table_list,14):
        #     stdscr.addstr(row_number, col1_left_border, '|')
        #     stdscr.addstr(row_number, col2_left_border, '|')
        #     stdscr.addstr(row_number, col2_right_border, '|')

# for row_number, process in enumerate(process_list,2):
#     stdscr.addstr(row_number, col1_left_border, '|')
#     stdscr.addstr(row_number, col2_left_border, '|')
#     stdscr.addstr(row_number, col3_left_border, '|')
#     stdscr.addstr(row_number, col3_right_border, '|')

# for row_number, table in enumerate(table_list, 14):
#     print(row_number)
#             (row_number, col2_left_border, '|')
#             stdscr.addstr(row_number, col2_right_border, '|')