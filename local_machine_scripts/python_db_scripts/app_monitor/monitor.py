import time
import curses
from curses import wrapper
from curses import init_pair
from table_draw import data_update,initial_imports



def monitor_activity(stdscr):

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    
        
    while True:
        time.sleep(.5)
        data_loop_window = data_update.draw_dataloop_table(stdscr)
        imports_window = initial_imports.draw_import_table(stdscr)
        initial_imports.populate_import_table(imports_window)
        data_update.populate_dataloop_table(data_loop_window)
        stdscr.refresh()

wrapper(monitor_activity)