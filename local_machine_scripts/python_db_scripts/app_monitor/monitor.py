import time
import curses
from curses import wrapper
from curses import init_pair
from table_draw import data_loop,initial_imports



def monitor_activity(stdscr):

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    imports_window = initial_imports.draw_import_table(stdscr)
    initial_imports.populate_import_table(imports_window)
        
    while True:
        time.sleep(.5)
        
        data_loop_window = data_loop.draw_dataloop_table(stdscr)
        data_loop.populate_dataloop_table(data_loop_window)

        

wrapper(monitor_activity)