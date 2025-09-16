from __future__ import generators
import psycopg2
import datetime as dt
import os
import base64

def update_lot_number_sage():
    connection_postgres = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute('''UPDATE core_lotnumrecord
                           SET sage_qty_on_hand = im_itemcost.quantityonhand,
                               sage_entered_date = im_itemcost.transactiondate + interval '6 hours'
                           FROM im_itemcost
                           WHERE im_itemcost.receiptno = core_lotnumrecord.lot_number
                           AND im_itemcost.itemcode = core_lotnumrecord.item_code
                           AND im_itemcost.warehousecode = 'MTG'
                           ''')

# """
#     If there's a lot number that has been entered into sage prior to the run_date, it's usually a safe bet want to update the run_date to match the sage_entered_date. 
#     HOWEVER, this algorithm is not foolproof. Example: Let's say the blend crew makes a blend ahead of time for the next day. The blend is entered into sage (prior to the run_date). 
#     If we updated the run_date to match the sage_entered_date, the run_date would be wrong, because the run_date is still the next day.
#
#     We must find a way to determine if the lot number has been run on the production line yet. One possible way to do this is to check the im_itemtransactionhistory table. 
# """

    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()
    print(f'{dt.datetime.now()} :: table_updates.py :: update_lot_number_sage :: =======Checked Sage for lot number entries.=======')

def update_lot_number_desks():
    try:
        connection_postgres = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        lot_numbers = []
        cursor_postgres.execute("SELECT lot, blend_area FROM core_deskoneschedule")
        lot_numbers.extend([(row[0], row[1]) for row in cursor_postgres.fetchall()])
        cursor_postgres.execute("SELECT lot, blend_area FROM core_desktwoschedule")
        lot_numbers.extend([(row[0], row[1]) for row in cursor_postgres.fetchall()])
        
        for lot_number, blend_area in lot_numbers:
            cursor_postgres.execute(f"SELECT desk FROM core_lotnumrecord WHERE lot_number = '{lot_number}'")
            current_desk = cursor_postgres.fetchone()[0]
            if current_desk != blend_area:
                cursor_postgres.execute(f"UPDATE core_lotnumrecord SET desk = '{blend_area}' WHERE lot_number = '{lot_number}'")

        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
    except Exception as e:
        print(f'{dt.datetime.now()} :: table_updates.py :: update_lot_number_desks :: {str(e)}')