import time
import curses
from curses import wrapper
from curses import init_pair
from table_draw import data_loop,blendverse_db

curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_YELLOW)
curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)

def monitor_activity(stdscr):

    while True:
        time.sleep(.5)
        stdscr.clear()
        data_loop.draw_dataloop_table(stdscr)
        data_loop.populate_dataloop_table(stdscr)
        blendverse_db.draw_blendverse_table(stdscr)
        stdscr.refresh()

wrapper(monitor_activity)