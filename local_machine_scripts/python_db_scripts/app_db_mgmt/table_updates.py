from __future__ import generators
import psycopg2
import datetime as dt
import os

def update_lot_number_sage():
    # with open(os.path.expanduser(
    #     '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_BOM_table_last_update.txt'
    #     ), 'w', encoding="utf-8") as f:
    #     f.write('Checking sage for lot numbers...')
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute('''UPDATE core_lotnumrecord
                           SET sage_qty_on_hand = im_itemcost.quantityonhand, 
                               sage_entered_date = im_itemcost.transactiondate
                           FROM im_itemcost 
                           WHERE im_itemcost.receiptno = core_lotnumrecord.lot_number
                           ''')
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()
    print(f'{dt.datetime.now()}=======Checked Sage for lot number entries.=======')

    # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Calculated_Tables_last_update.txt'), 'w', encoding="utf-8") as f:
    #     f.write('Error: ' + str(dt.datetime.now()))
    # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\Calculated_Tables_error_log.txt'), 'a', encoding="utf-8") as f:
    #     f.write('Checking sage for lot numbers...')
    #     f.write('\n')