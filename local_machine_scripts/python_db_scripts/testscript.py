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
    while True:
        time.sleep(3)
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)


        stdscr.clear()
        stdscr.addstr(0,0,"|          Process          |     Last Updated      |              Status             |", curses.A_REVERSE)
        stdscr.addstr(1,0,"|---------------------------+-----------------------+---------------------------------|")

        bm_bd_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\BM_BillDetail_last_update.txt')))
        stdscr.addstr(2,0,"| BM_BillDetail             | "
                    + bm_bd_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - bm_bd_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(2,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - bm_bd_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(2,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(2,54, "Running", curses.color_pair(1))
        stdscr.addstr(2,86, "|")


        bm_bh_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\BM_BillHeader_last_update.txt')))
        stdscr.addstr(3,0,"| BM_BillHeader             | "
                    + bm_bh_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - bm_bh_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(3,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - bm_bh_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(3,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(3,54, "Running", curses.color_pair(1))
        stdscr.addstr(3,86, "|")


        ci_i_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\CI_Item_last_update.txt')))
        stdscr.addstr(4,0,"| CI_Item                   | "
                    + ci_i_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - ci_i_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(4,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - ci_i_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(4,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(4,54, "Running", curses.color_pair(1))
        stdscr.addstr(4,86, "|")


        im_ic_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\IM_ItemCost_last_update.txt')))
        stdscr.addstr(5,0,"| IM_ItemCost               | "
                    + im_ic_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - im_ic_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(5,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - im_ic_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(5,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(5,54, "Running", curses.color_pair(1))
        stdscr.addstr(5,86, "|")


        im_it_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\IM_ItemTransactionHistory_last_update.txt')))
        stdscr.addstr(6,0,"| IM_ItemTransactionHistory | "
                    + im_it_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - im_it_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(6,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - im_it_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(6,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(6,54, "Running", curses.color_pair(1))
        stdscr.addstr(6,86, "|")

        im_iw_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\IM_ItemWarehouse_last_update.txt')))
        stdscr.addstr(7,0,"| IM_ItemWarehouse          | "
                    + im_iw_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - im_iw_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(7,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - im_iw_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(7,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(7,54, "Running", curses.color_pair(1))
        stdscr.addstr(7,86, "|")
        
        po_pod_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\PO_PurchaseOrderDetail_last_update.txt')))
        stdscr.addstr(8,0,"| PO_PurchaseOrderDetail    | "
                    + po_pod_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - po_pod_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(8,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - po_pod_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(8,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(8,54, "Running", curses.color_pair(1))
        stdscr.addstr(8,86, "|")
        
        prod_sched_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\prod_sched_last_update.txt')))
        stdscr.addstr(9,0,"| Production Schedule Data  | "
                    + prod_sched_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - prod_sched_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(9,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - prod_sched_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(9,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(9,54, "Running", curses.color_pair(1))
        stdscr.addstr(9,86, "|")

        calculated_tables_mod_time = dt.datetime.fromtimestamp(
                        os.path.getmtime(
                            os.path.expanduser(
                                '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\table_builder_last_update.txt')))
        stdscr.addstr(10,0,"| Calculated Tables         | "
                    + calculated_tables_mod_time.strftime("%m/%d/%Y, %H:%M:%S")
                    + "  |")
        if ((dt.datetime.now() - calculated_tables_mod_time) > dt.timedelta(seconds=200)):
            stdscr.addstr(10,54, "Probably broken.", curses.color_pair(3))
        elif ((dt.datetime.now() - calculated_tables_mod_time) > dt.timedelta(seconds=700)):
            stdscr.addstr(10,54, "Been a sec...",  curses.color_pair(2))
        else:
            stdscr.addstr(10,54, "Running", curses.color_pair(1))
        stdscr.addstr(10,86, "|")
        stdscr.refresh()

wrapper(monitor_activity)