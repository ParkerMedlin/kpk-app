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
                           AND im_itemcost.itemcode = core_lotnumrecord.item_code
                           AND im_itemcost.warehousecode = 'MTG'
                           ''')
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()
    print(f'{dt.datetime.now()} :: table_updates.py :: update_lot_number_sage :: =======Checked Sage for lot number entries.=======')

    # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Calculated_Tables_last_update.txt'), 'w', encoding="utf-8") as f:
    #     f.write('Error: ' + str(dt.datetime.now()))
    # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\Calculated_Tables_error_log.txt'), 'a', encoding="utf-8") as f:
    #     f.write('Checking sage for lot numbers...')
    #     f.write('\n')

def create_daily_blendcounts():
    try:
        today = dt.datetime.now()
        weekday = today.weekday()
        if weekday in (0, 1, 2):  # Monday, Tuesday, Wednesday
            next_day_date = today + dt.timedelta(days=1)
            formatted_nextday = next_day_date.strftime('%Y-%m-%d')
        elif weekday == 3:  # Thursday
            next_day_date = today + dt.timedelta(days=(7 - weekday))
            formatted_nextday = next_day_date.strftime('%Y-%m-%d')
        else:
            return
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(f"""
                SELECT COUNT(*)
                FROM core_countcollectionlink
                WHERE collection_id LIKE '%{next_day_date.strftime('%m-%d-%Y')}';
            """)
        result = cursor_postgres.fetchone()[0]
        if result:
            return

        cursor_postgres.execute('''SELECT component_item_code,
                                        MIN(component_item_description) AS component_item_description,
                                        MIN(start_time) AS start_time,
                                        MIN(component_on_hand_qty) AS component_on_hand_qty
                                    FROM component_usage
                                    WHERE prod_line = 'INLINE' AND component_item_description LIKE 'BLEND%' 
                                    AND start_time < 8
                                    GROUP BY component_item_code
                                    ORDER BY component_item_code
                                    LIMIT 15;''')
        component_usage_rows = cursor_postgres.fetchall()
        cursor_postgres.execute('''SELECT DISTINCT component_item_code, component_item_description,
                                start_time, component_on_hand_qty
                                FROM component_shortage
                                WHERE last_txn_date > last_count_date AND prod_line not like 'Dm'
                                AND prod_line not like 'Hx'
                                AND component_item_code not like '100501K'
                                ORDER BY start_time
                                LIMIT 15;''')
        component_shortage_rows = cursor_postgres.fetchall()
        both_sets = [component_usage_rows, component_shortage_rows]

        # Get the date of two weekdays ago
        if weekday == 0:  # Monday
            two_weekdays_ago = today - dt.timedelta(days=(4))
            formatted_two_weekdays_ago = two_weekdays_ago.strftime('%Y-%m-%d')
        if weekday == 1:  # Tuesday
            two_weekdays_ago = today + dt.timedelta(days=(3))
            formatted_two_weekdays_ago = two_weekdays_ago.strftime('%Y-%m-%d')
        elif weekday in (2, 3):  # Wednesday, Thursday
            two_weekdays_ago = today - dt.timedelta(days=2)
            formatted_two_weekdays_ago = two_weekdays_ago.strftime('%Y-%m-%d')
        else:
            return

        cursor_postgres.execute(f'''SELECT item_code FROM core_blendcountrecord WHERE 
                                    counted = TRUE AND counted_date >= '{formatted_two_weekdays_ago}'
                                ''')
        item_codes = [item[0] for item in cursor_postgres.fetchall()]
        count_list_items = []

        # lol
        for set in both_sets:
            for row in set:
                # filter duplicate component_item_codes
                if not any(item['component_item_code'] == row[0] for item in count_list_items):
                    if row[0] not in item_codes:
                        count_list_items.append(
                            { 
                                'component_item_code' : row[0],
                                'component_item_description' : row[1],
                                'start_time' : row[2],
                                'component_on_hand_qty' : row[3],
                                'counted_date' : formatted_nextday,
                                'counted' : False
                            }
                        )

        for item in count_list_items:
            cursor_postgres.execute(f'''
                INSERT INTO core_blendcountrecord (item_code, item_description, expected_quantity, counted_date, counted, count_type, collection_id)
                VALUES ('{item['component_item_code']}', '{item['component_item_description']}', 
                        '{item['component_on_hand_qty']}', '{item['counted_date']}', 
                        '{item['counted']}','blend','B1A-{formatted_nextday.replace('-','')}')
            ''')
            connection_postgres.commit()

        new_row_ids = []
        number_of_items = len(count_list_items)
        cursor_postgres.execute(f'''
            SELECT id FROM core_blendcountrecord
            ORDER BY id DESC
            LIMIT {number_of_items};
        ''')
        for item in cursor_postgres.fetchall():
            new_row_ids.append(item)
        create_count_collection_link(new_row_ids, next_day_date)

        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        # print(f'{dt.datetime.now()}=======Created countlist=======')
    except Exception as e:
        print(f'{dt.datetime.now()} :: table_updates.py :: create_daily_blendcounts :: {str(e)}')

def create_count_collection_link(id_list, next_day_date):
    try:
        id_list_string = ""
        for item in id_list:
            id_list_string += f"{item[0]},"
        id_list_string = id_list_string[:-1]
        connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        collection_id = f"{next_day_date.strftime('%A').upper()}_blend_count_{next_day_date.strftime('%m-%d-%Y')}"
        id_list_bytestr = id_list_string.encode('UTF-8')
        encoded_id_list = base64.b64encode(id_list_bytestr)
        decoded_id_list = encoded_id_list.decode('utf-8')
        cursor_postgres.execute("SELECT MAX(link_order) FROM core_countcollectionlink")
        max_link_order = cursor_postgres.fetchone()[0]
        if max_link_order is None:
            max_link_order = 0
        else:
            max_link_order += 1
        collection_link = f'/core/count-list/display/{decoded_id_list}?recordType=blend'
        cursor_postgres.execute(f"""INSERT INTO core_countcollectionlink (collection_id, collection_link, link_order)
                                        VALUES ('{collection_id}', '{collection_link}', {max_link_order})
                                    """)
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
    except Exception as e:
        print(f'{dt.datetime.now()} :: table_updates.py :: create_count_collection_link :: {str(e)}')

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