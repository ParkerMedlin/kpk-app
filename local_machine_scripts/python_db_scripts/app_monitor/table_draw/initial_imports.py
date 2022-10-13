import psycopg2
import time
import curses
from curses import init_pair

col1_left_border = 0
col2_left_border = 35
col2_right_border = 47

import_table_list = [
    'core_blendinstruction','core_countrecord',
    'core_foamfactor','core_forklift','core_lotnumrecord'
]

def draw_import_table(stdscr):
    blendverse_window = curses.newwin(17,75,13,0)
    stdscr.refresh()
    blendverse_window.addstr(0,0,"|               Name               | # of Rows |", curses.A_REVERSE)
    blendverse_window.addstr(1,0,"|----------------------------------+-----------|")
    for row_number, table in enumerate(import_table_list,2):
        blendverse_window.addstr(row_number, col1_left_border, '|')
        blendverse_window.addstr(row_number, col2_left_border, '|')
        blendverse_window.addstr(row_number, col2_right_border, '|')
    blendverse_window.refresh()
    return blendverse_window

def populate_import_table(window):
    table_row_counts = {}
    for item in import_table_list:
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("SELECT COUNT(*) FROM " + item)
        cursor_tuple = (cursor_postgres.fetchall())
        row_count = cursor_tuple[0][0]
        table_row_counts[item] = row_count
        cursor_postgres.close()
        connection_postgres.close()
    for current_line, key in enumerate(import_table_list,2):
        window.addstr(current_line, (col1_left_border + 2), key)
        if table_row_counts[key] == 0:
            window.addstr(current_line, (col2_left_border + 3),str(table_row_counts[key]),curses.color_pair(3))
            window.addstr(current_line, (col2_right_border + 1),"  !! IMPORT MISSING !!  ",curses.color_pair(3))
        else:
            window.addstr(current_line, (col2_left_border + 3),str(table_row_counts[key]),curses.color_pair(1))
        window.addstr(current_line, col2_right_border, '|')
        window.refresh()