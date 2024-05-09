from __future__ import generators
import psycopg2
import datetime as dt
import os
import base64

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

def create_daily_blendcounts():
    # SELECT component_item_code FROM blendthese where last_txn_date > last_count_date LIMIT 7
    # SELECT component_item_code FROM component_usage WHERE prodline = 'INLINE' AND component_item_description LIKE 'BLEND%' ORDER BY start_time LIMIT 8 
    # JOIN im_itemwarehouse.QuantityOnHand ON im_itemwarehouse.itemcode

    # 

    print("working!")

def create_countlink_list(id_list):
    id_list_bytestr = id_list.encode('UTF-8')
    encoded_id_list = base64.b64encode(id_list_bytestr)