import curses
import datetime as dt
import os
from curses import init_pair
import time

col1_left_border = 0
col2_left_border = 29
col3_left_border = 57
col3_right_border = 91

process_list = [
        'BM_BillDetail', 'BM_BillHeader', 'CI_Item', 'IM_ItemCost',
        'IM_ItemTransactionHistory', 'IM_ItemWarehouse', 'PO_PurchaseOrderDetail',
        'Production_Schedule', 'Calculated_Tables'
    ]

def draw_dataloop_table(stdscr):
        stdscr.addstr(0,0,"|          Process           |        Last Updated       |              Status             |", curses.A_REVERSE)
        stdscr.addstr(1,0,"|----------------------------+---------------------------+---------------------------------|")
        for row_number, process in enumerate(process_list,2):
            stdscr.addstr(row_number, col1_left_border, '|')
            stdscr.addstr(row_number, col2_left_border, '|')
            stdscr.addstr(row_number, col3_left_border, '|')
            stdscr.addstr(row_number, col3_right_border, '|')

def populate_dataloop_table(stdscr):
        for item in process_list:
            current_line = process_list.index(item) + 2
            txtfile_modified_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + item + '_last_update.txt')))
            stdscr.addstr(current_line, (col1_left_border + 2), item)
            if ((dt.datetime.now() - txtfile_modified_time) > dt.timedelta(seconds=200)):
                stdscr.addstr(current_line, (col2_left_border + 3), txtfile_modified_time.strftime("%m/%d/%Y, %I:%M:%S %p"),curses.color_pair(2))
            elif ((dt.datetime.now() - txtfile_modified_time) > dt.timedelta(seconds=700)):
                stdscr.addstr(current_line, (col2_left_border + 3), txtfile_modified_time.strftime("%m/%d/%Y, %I:%M:%S %p"),curses.color_pair(3))
            else:
                stdscr.addstr(current_line, (col2_left_border + 3), txtfile_modified_time.strftime("%m/%d/%Y, %I:%M:%S %p"),curses.color_pair(1))
            with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\' + item + '_last_update.txt'), 'r') as f:
                try:
                    this_line = (f.readlines()[0])[0:32]
                except:
                    time.sleep(1)

            if 'ERROR' in this_line:
                stdscr.addstr(current_line, (col3_left_border + 2), this_line,curses.color_pair(3))
            else:
                stdscr.addstr(current_line, (col3_left_border + 2), this_line)
            stdscr.addstr(current_line, col3_right_border, '|')