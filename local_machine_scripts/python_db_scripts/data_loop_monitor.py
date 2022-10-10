import time
import os
import datetime as dt
import curses
from curses import wrapper
from curses import init_pair



def monitor_activity(stdscr):
    # stdscr.clear()
    # stdscr.addstr("")
    # stdscr.refresh()

    col1_left_border = 0
    col2_left_border = 29
    col3_left_border = 57
    col3_right_border = 91
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    process_list = [
        'BM_BillDetail', 'BM_BillHeader', 'CI_Item', 'IM_ItemCost',
        'IM_ItemTransactionHistory', 'IM_ItemWarehouse', 'PO_PurchaseOrderDetail',
        'Production_Schedule', 'Calculated_Tables'
    ]

    def create_lines_and_headers():
        stdscr.addstr(0,0,"|          Process           |        Last Updated       |              Status             |", curses.A_REVERSE)
        stdscr.addstr(1,0,"|----------------------------+---------------------------+---------------------------------|")
        for number in range(len(process_list)):
            stdscr.addstr((number + 2), col1_left_border, '|')
            stdscr.addstr((number + 2), col2_left_border, '|')
            stdscr.addstr((number + 2), col3_left_border, '|')
            stdscr.addstr((number + 2), col3_right_border, '|')

    while True:
        time.sleep(.5)
        stdscr.clear()
        create_lines_and_headers()
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
                this_line = (f.readlines()[0])[0:32]

            if 'ERROR' in this_line:
                stdscr.addstr(current_line, (col3_left_border + 2), this_line,curses.color_pair(3))
            else: 
                stdscr.addstr(current_line, (col3_left_border + 2), this_line)
            stdscr.addstr(current_line, col3_right_border, '|')
        stdscr.refresh()

wrapper(monitor_activity)