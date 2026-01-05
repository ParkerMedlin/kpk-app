from __future__ import generators
import psycopg2
import datetime as dt
import os
import base64

DB_CONNECTION_STRING = 'postgresql://postgres:blend2021@localhost:5432/blendversedb'

def update_lot_number_sage():
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
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
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
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


def _reset_table_sequence(table_name):
    """
    Resets the id sequence for a given table to MAX(id).
    Automatically finds the sequence name using pg_get_serial_sequence.
    """
    connection_postgres = psycopg2.connect(DB_CONNECTION_STRING)
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute(f"""
        SELECT setval(
            pg_get_serial_sequence('{table_name}', 'id'),
            (SELECT COALESCE(MAX(id), 1) FROM {table_name}),
            true
        );
    """)
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

def sync_transaction_history_tables():
    """
    Syncs im_itemtransactionhistory_daily to both im_itemtransactionhistory (rolling 1-year)
    and im_itemtransactionhistory_deeptime (full history).

    Steps:
    1. Find new rows in daily that don't exist in 1-year table (by composite key)
    2. Append those rows to im_itemtransactionhistory
    3. Find new rows in daily that don't exist in deeptime table
    4. Append those rows to im_itemtransactionhistory_deeptime
    5. Delete rows older than 1 year from im_itemtransactionhistory
    """
    try:
        connection_postgres = psycopg2.connect(DB_CONNECTION_STRING)
        cursor_postgres = connection_postgres.cursor()

        # Reset sequences to avoid duplicate key errors
        _reset_table_sequence('im_itemtransactionhistory')
        _reset_table_sequence('im_itemtransactionhistory_deeptime')

        # Get column names from the daily table (excluding 'id')
        cursor_postgres.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'im_itemtransactionhistory_daily'
            AND LOWER(column_name) != 'id'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor_postgres.fetchall()]
        # Double-check id is excluded (case-insensitive)
        columns = [c for c in columns if c.lower() != 'id']
        column_list = ', '.join(columns)
        print(f'{dt.datetime.now()} :: DEBUG :: columns: {columns}')
        print(f'{dt.datetime.now()} :: DEBUG :: column_list: {column_list}')

        # 1. Append new rows to im_itemtransactionhistory (rolling 1-year)
        cursor_postgres.execute(f"""
            INSERT INTO im_itemtransactionhistory ({column_list})
            SELECT {column_list} FROM im_itemtransactionhistory_daily d
            WHERE NOT EXISTS (
                SELECT 1 FROM im_itemtransactionhistory t
                WHERE t.itemcode = d.itemcode
                  AND t.transactiondate = d.transactiondate
                  AND t.transactioncode = d.transactioncode
                  AND t.transactionqty = d.transactionqty
            )
        """)
        rows_inserted_rolling = cursor_postgres.rowcount

        # 2. Append new rows to im_itemtransactionhistory_deeptime (full history)
        cursor_postgres.execute(f"""
            INSERT INTO im_itemtransactionhistory_deeptime ({column_list})
            SELECT {column_list} FROM im_itemtransactionhistory_daily d
            WHERE NOT EXISTS (
                SELECT 1 FROM im_itemtransactionhistory_deeptime t
                WHERE t.itemcode = d.itemcode
                  AND t.transactiondate = d.transactiondate
                  AND t.transactioncode = d.transactioncode
                  AND t.transactionqty = d.transactionqty
            )
        """)
        rows_inserted_deeptime = cursor_postgres.rowcount

        # 3. Prune rows older than 1 year from rolling table
        cursor_postgres.execute("""
            DELETE FROM im_itemtransactionhistory
            WHERE transactiondate < CURRENT_DATE - INTERVAL '52 weeks'
        """)
        rows_pruned = cursor_postgres.rowcount

        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()

        print(f'{dt.datetime.now()} :: table_updates.py :: sync_transaction_history_tables :: '
              f'Inserted {rows_inserted_rolling} rows to rolling table, '
              f'{rows_inserted_deeptime} rows to deeptime table, '
              f'pruned {rows_pruned} old rows')

    except Exception as e:
        print(f'{dt.datetime.now()} :: table_updates.py :: sync_transaction_history_tables :: {str(e)}')

def backfill_deeptime_from_itemtransactionhistory():
    """
    Backfills im_itemtransactionhistory_deeptime with any rows from im_itemtransactionhistory
    that are missing. ONLY used for catching up the deeptime table after initial setup. 
    DO NOT USE THIS FUNCTION FOR REGULAR MAINTENANCE BIOIIITCH. lookin at you, 
    """
    try:
        connection_postgres = psycopg2.connect(DB_CONNECTION_STRING)
        cursor_postgres = connection_postgres.cursor()

        _reset_table_sequence('im_itemtransactionhistory_deeptime')

        # Get column names from the rolling table (excluding 'id')
        cursor_postgres.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'im_itemtransactionhistory'
            AND LOWER(column_name) != 'id'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor_postgres.fetchall()]
        # Double-check id is excluded (case-insensitive)
        columns = [c for c in columns if c.lower() != 'id']
        column_list = ', '.join(columns)

        # Insert rows from rolling table that don't exist in deeptime
        cursor_postgres.execute(f"""
            INSERT INTO im_itemtransactionhistory_deeptime ({column_list})
            SELECT {column_list} FROM im_itemtransactionhistory r
            WHERE NOT EXISTS (
                SELECT 1 FROM im_itemtransactionhistory_deeptime d
                WHERE d.itemcode = r.itemcode
                  AND d.transactiondate = r.transactiondate
                  AND d.transactioncode = r.transactioncode
                  AND d.transactionqty = r.transactionqty
            )
        """)
        rows_inserted = cursor_postgres.rowcount

        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()

        print(f'{dt.datetime.now()} :: table_updates.py :: backfill_deeptime_from_itemtransactionhistory :: '
              f'Inserted {rows_inserted} missing rows into deeptime table')

    except Exception as e:
        print(f'{dt.datetime.now()} :: table_updates.py :: backfill_deeptime_from_itemtransactionhistory :: {str(e)}')