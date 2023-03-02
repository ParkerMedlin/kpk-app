from __future__ import generators
import psycopg2
import pandas as pd
import time
import datetime as dt
import os
from sqlalchemy import create_engine
import sys

def create_bill_of_materials_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''CREATE TABLE bill_of_materials_TEMP as
                                    select distinct Bm_BillDetail.billno AS item_code,
                                    ci_item.itemcode as component_item_code,
                                    ci_item.itemcodedesc as component_item_description,
                                    ci_item.procurementtype as procurementtype,
                                    core_foamfactor.factor AS foam_factor,
                                    ci_item.StandardUnitOfMeasure AS standard_uom,
                                    bm_billdetail.quantityperbill as qtyperbill,
                                    bm_billdetail.commenttext as comment_text,
                                    ci_item.shipweight as weightpergal,
                                    im_itemwarehouse.QuantityOnHand AS qtyonhand
                                FROM ci_item AS ci_item
                                JOIN Bm_BillDetail Bm_BillDetail ON ci_item.itemcode=Bm_BillDetail.componentitemcode
                                left join core_foamfactor core_foamfactor on ci_item.itemcode=core_foamfactor.item_code
                                left join im_itemwarehouse im_itemwarehouse 
                                    on ci_item.itemcode=im_itemwarehouse.itemcode 
                                    and im_itemwarehouse.warehousecode = 'MTG'
                                left join bm_billheader bm_billheader on ci_item.itemcode=bm_billheader.billno
                                order by item_code'''
                                )
        cursor_postgres.execute('alter table bill_of_materials_TEMP add id serial primary key;')
        cursor_postgres.execute('alter table bill_of_materials_TEMP add item_description text;')
        cursor_postgres.execute('''update bill_of_materials_TEMP set item_description=
                                    (select ci_item.itemcodedesc from ci_item 
                                    where bill_of_materials_TEMP.item_code=ci_item.itemcode);''')
        cursor_postgres.execute('''update bill_of_materials_TEMP
                                    set foam_factor=1 where foam_factor IS NULL;''')
        cursor_postgres.execute("update bill_of_materials_TEMP set component_item_description = bill_of_materials_TEMP.comment_text where component_item_code like '/%';")
        cursor_postgres.execute("delete from bill_of_materials_TEMP where component_item_code like '/%' AND component_item_code <> '/C';")
        cursor_postgres.execute('drop table if exists bill_of_materials')
        cursor_postgres.execute('''alter table bill_of_materials_TEMP
                                    rename to bill_of_materials''')
        cursor_postgres.execute('drop table if exists bill_of_materials_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        print(f'{dt.datetime.now()}=======bill_of_materials table created.=======')
        
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\prod_BOM_table_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\prod_BOM_table_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building prod_BOM...')
            f.write('\n')

def create_component_usage_table():
    try:
        connection_postgres = psycopg2.connect(
                    'postgresql://postgres:blend2021@localhost:5432/blendversedb'
                    )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table component_usage_TEMP as 
                    select * from (select prodmerge_run_data.item_run_qty as item_run_qty,
                        prodmerge_run_data.start_time as start_time,
                        prodmerge_run_data.po_number as po_number,
                        prodmerge_run_data.item_code as item_code,
                        prodmerge_run_data.prod_line as prod_line,
                        bill_of_materials.component_item_description,
                        bill_of_materials.component_item_code,
                        bill_of_materials.qtyperbill as qty_per_bill,
                        bill_of_materials.qtyperbill * prodmerge_run_data.item_run_qty * bill_of_materials.foam_factor * 1.1 as run_component_qty,
                        bill_of_materials.qtyonhand as component_on_hand_qty,
                        bill_of_materials.procurementtype as procurement_type,
                        bill_of_materials.foam_factor as foam_factor
                        from prodmerge_run_data
                        left join bill_of_materials on prodmerge_run_data.item_code=bill_of_materials.item_code
                        ) as subquery
                    WHERE component_item_description like 'BLEND%'
                    or component_item_description LIKE 'ADAPTER%'
                    OR component_item_description LIKE 'APPLICATOR%'
                    OR component_item_description LIKE 'BAG%'
                    OR component_item_description LIKE 'BAIL%'
                    OR component_item_description LIKE 'BASE%'
                    OR component_item_description LIKE 'BILGE PAD%'
                    OR component_item_description LIKE 'BOTTLE%'
                    OR component_item_description LIKE 'CABLE TIE%'
                    OR component_item_description LIKE 'CAN%'
                    OR component_item_description LIKE 'CAP%'
                    OR component_item_description LIKE 'CARD%'
                    OR component_item_description LIKE 'CARTON%'
                    OR component_item_description LIKE 'CLAM%'
                    OR component_item_description LIKE 'CLIP%'
                    OR component_item_description LIKE 'COLORANT%'
                    OR component_item_description LIKE 'CUP%'
                    OR component_item_description LIKE 'DISPLAY%'
                    OR component_item_description LIKE 'DIVIDER%'
                    OR component_item_description LIKE 'DRUM%'
                    OR component_item_description LIKE 'ENVELOPE%'
                    OR component_item_description LIKE 'FILLED BOTTLE%'
                    OR component_item_description LIKE 'FILLER%'
                    OR component_item_description LIKE 'FLAG%'
                    OR component_item_description LIKE 'FUNNEL%'
                    OR component_item_description LIKE 'GREASE%'
                    OR component_item_description LIKE 'HANGER%'
                    OR component_item_description LIKE 'HEADER%'
                    OR component_item_description LIKE 'HOLDER%'
                    OR component_item_description LIKE 'HOSE%'
                    OR component_item_description LIKE 'INSERT%'
                    OR component_item_description LIKE 'JAR%'
                    OR component_item_description LIKE 'LABEL%'
                    OR component_item_description LIKE 'LID%'
                    OR component_item_description LIKE 'PAD%'
                    OR component_item_description LIKE 'PAIL%'
                    OR component_item_description LIKE 'PLUG%'
                    OR component_item_description LIKE 'POUCH%'
                    OR component_item_description LIKE 'PUTTY STICK%'
                    OR component_item_description LIKE 'RESIN%'
                    OR component_item_description LIKE 'SCOOT%'
                    OR component_item_description LIKE 'SEAL DISC%'
                    OR component_item_description LIKE 'SLEEVE%'
                    OR component_item_description LIKE 'SPONGE%'
                    OR component_item_description LIKE 'STRIP%'
                    OR component_item_description LIKE 'SUPPORT%'
                    OR component_item_description LIKE 'TOILET PAPER%'
                    OR component_item_description LIKE 'TOOL%'
                    OR component_item_description LIKE 'TOTE%'
                    OR component_item_description LIKE 'TRAY%'
                    OR component_item_description LIKE 'TUB%'
                    OR component_item_description LIKE 'TUBE%'
                    OR component_item_description LIKE 'WINT KIT%'
                    OR component_item_description LIKE 'WRENCH%'
                    ORDER BY start_time, po_number;''')
        cursor_postgres.execute('''alter table component_usage_TEMP add cumulative_component_run_qty numeric;
                    UPDATE component_usage_TEMP AS cu1
                    SET cumulative_component_run_qty = (
                        SELECT SUM(cu2.run_component_qty)
                        FROM component_usage_TEMP AS cu2
                        WHERE cu2.component_item_code = cu1.component_item_code AND cu2.start_time <= cu1.start_time
                    );
                    alter table component_usage_TEMP add component_onhand_after_run numeric;
                    UPDATE component_usage_TEMP set component_onhand_after_run=component_on_hand_qty-cumulative_component_run_qty;''')
        cursor_postgres.execute('alter table component_usage_TEMP add id serial primary key;')
        cursor_postgres.execute('drop table if exists component_usage')
        cursor_postgres.execute('alter table component_usage_TEMP rename to component_usage')
        cursor_postgres.execute('drop table if exists component_usage_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======component_usage table created.=======')
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\component_usage_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        print(f'{dt.datetime.now()} -- {str(e)}')

def create_component_shortages_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists component_shortage_TEMP;')
        cursor_postgres.execute('''create table component_shortage_TEMP as
                                SELECT * FROM (SELECT *,
                                    ROW_NUMBER() OVER (PARTITION BY component_item_code
                                        ORDER BY start_time) AS row_number
                                    FROM component_usage
                                    where component_onhand_after_run < 0
                                ) AS subquery
                                where row_number = 1;
                                ''')
        cursor_postgres.execute('''alter table component_shortage_TEMP
                                add one_wk_short numeric, add two_wk_short numeric,
                                add three_wk_short numeric, add total_shortage numeric,
                                add unscheduled_short numeric, add last_txn_date date,
                                add last_txn_code text, add last_count_quantity numeric, 
                                add last_count_date date;''')
        cursor_postgres.execute('''update component_shortage_TEMP set total_shortage=(
                                SELECT cumulative_component_run_qty from component_usage
                                where component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                order by start_time DESC LIMIT 1)-component_on_hand_qty
                                ''')
        cursor_postgres.execute('''update component_shortage_TEMP set one_wk_short=((select component_usage.cumulative_component_run_qty
                                from component_usage where start_time>=0 and start_time<10 
                                and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                update component_shortage_TEMP set two_wk_short=((select component_usage.cumulative_component_run_qty
                                from component_usage where start_time>=10 and start_time<20 
                                and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                update component_shortage_TEMP set three_wk_short=((select component_usage.cumulative_component_run_qty
                                from component_usage where start_time>=20 and start_time<299
                                and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                update component_shortage_TEMP set unscheduled_short=((select component_usage.cumulative_component_run_qty
                                from component_usage where prod_line like 'UNSCHEDULED%'
                                and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                order by start_time DESC LIMIT 1)-component_on_hand_qty)-three_wk_short;
                                ''')
        cursor_postgres.execute('''update component_shortage_TEMP set one_wk_short=0 where one_wk_short<0;
                                    update component_shortage_TEMP set two_wk_short=0 where two_wk_short<0;
                                    update component_shortage_TEMP set three_wk_short=0 where three_wk_short<0;
                                    update component_shortage_TEMP set unscheduled_short=0 where unscheduled_short<0;
                                    ''')
        cursor_postgres.execute('''update component_shortage_TEMP set last_txn_code=(select transactioncode from im_itemtransactionhistory
                                where im_itemtransactionhistory.itemcode=component_shortage_TEMP.component_item_code order by transactiondate DESC limit 1);
                                update component_shortage_TEMP set last_txn_date=(select transactiondate from im_itemtransactionhistory
                                where im_itemtransactionhistory.itemcode=component_shortage_TEMP.component_item_code order by transactiondate DESC limit 1);
                                update component_shortage_TEMP set last_count_quantity=(select counted_quantity from core_countrecord
                                where core_countrecord.item_code=component_shortage_TEMP.component_item_code and core_countrecord.counted=True order by counted_date DESC limit 1);
                                update component_shortage_TEMP set last_count_date=(select counted_date from core_countrecord
                                where core_countrecord.item_code=component_shortage_TEMP.component_item_code and core_countrecord.counted=True order by counted_date DESC limit 1);''')
                     
        cursor_postgres.execute('drop table if exists component_shortage;')
        cursor_postgres.execute('alter table component_shortage_TEMP rename to component_shortage;')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======component_shortage table created.=======')
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\component_usage_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        print(f'{dt.datetime.now()} -- {str(e)}')

def create_blend_run_data_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table blend_run_data_TEMP as
                                    select distinct prodmerge_run_data.p_n as item_code,
                                    bill_of_materials.component_item_code as component_item_code,
                                    bill_of_materials.component_item_description as component_item_description,
                                    prodmerge_run_data.qty as unadjusted_runqty,
                                    bill_of_materials.foam_factor as foam_factor,
                                    bill_of_materials.qtyperbill as qtyperbill,
                                    bill_of_materials.qtyonhand as qtyonhand,
                                    bill_of_materials.procurementtype as procurementtype,
                                    prodmerge_run_data.runtime as runtime,
                                    prodmerge_run_data.starttime as starttime,
                                    prodmerge_run_data.prodline as prodline,
                                    prodmerge_run_data.id2 as id2
                                from prodmerge_run_data as prodmerge_run_data
                                join bill_of_materials bill_of_materials 
                                    on prodmerge_run_data.p_n=bill_of_materials.item_code 
                                order by starttime'''
                                )
        cursor_postgres.execute('alter table blend_run_data_TEMP add id serial primary key;')
        cursor_postgres.execute('alter table blend_run_data_TEMP add adjustedrunqty numeric;')
        cursor_postgres.execute('''update blend_run_data_TEMP
                                set adjustedrunqty=(unadjusted_runqty*1.1*foam_factor*qtyperbill)''')
        cursor_postgres.execute("delete from blend_run_data_TEMP where component_item_description not like 'BLEND%'")
        cursor_postgres.execute('drop table if exists blend_run_data')
        cursor_postgres.execute('alter table blend_run_data_TEMP rename to blend_run_data')
        cursor_postgres.execute('drop table if exists blend_run_data_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======blend_run_data table created.=======')
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_run_data_table_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\blend_run_data_table_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building blend_run_data...')
            f.write('\n')

def create_timetable_run_data_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Calculated_Tables_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Building timetable...')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table timetable_run_data_TEMP as
                                select id2, item_code, component_item_code, component_item_description, adjustedrunqty, qtyonhand, starttime, prodline, procurementtype,
                                    qtyonhand-sum(adjustedrunqty) over (partition by component_item_code order by starttime) as oh_after_run 
                                from blend_run_data
                                order by starttime''')
        cursor_postgres.execute('alter table timetable_run_data_TEMP add week_calc numeric;')
        cursor_postgres.execute('''update timetable_run_data_TEMP set week_calc=
                                case
                                    when starttime<40 then 1
                                    when starttime>80 then 3
                                    else 2
                                end''')
        cursor_postgres.execute('alter table timetable_run_data_TEMP add id serial primary key')
        cursor_postgres.execute('drop table if exists timetable_run_data')
        cursor_postgres.execute('alter table timetable_run_data_TEMP rename to timetable_run_data')
        cursor_postgres.execute('drop table if exists timetable_run_data_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        print(f'{dt.datetime.now()}=======timetable_run_data table created.=======')
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\timetable_run_data_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\timetable_run_data_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building prod_BOM...')
            f.write('\n')

def create_issuesheet_needed_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists issue_sheet_needed_TEMP')
        cursor_postgres.execute('''create table issue_sheet_needed_TEMP as
                                select * from timetable_run_data where starttime < 20
                                and procurementtype = 'M'
                                order by prodline, starttime'''
                                )
        cursor_postgres.execute('''alter table issue_sheet_needed_TEMP
                                add batchnum1 text, add batchqty1 text,
                                add batchnum2 text, add batchqty2 text,
                                add batchnum3 text, add batchqty3 text,
                                add batchnum4 text, add batchqty4 text,
                                add batchnum5 text, add batchqty5 text,
                                add batchnum6 text, add batchqty6 text,
                                add batchnum7 text, add batchqty7 text,
                                add batchnum8 text, add batchqty8 text,
                                add batchnum9 text, add batchqty9 text,
                                add uniqchek text;'''
                                )
        connection_postgres.commit()
        cursor_postgres.close()
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("select component_item_code from timetable_run_data")
        component_item_code_tuples = cursor_postgres.fetchall()
        cursor_postgres.close()
        component_item_code_list = []
        for blend_tuple in component_item_code_tuples:
            component_item_code_list.append(blend_tuple[0])
        cursor_postgres = connection_postgres.cursor()
        component_item_code_str = ",".join("'" + blend + "'" for blend in component_item_code_list)

        cursor_postgres = connection_postgres.cursor()

        # Get non_standard_lot_total for all component_item_codes in one query
        cursor_postgres.execute(f"select itemcode, sum(quantityonhand) from im_itemcost where itemcode in ({component_item_code_str}) and quantityonhand!=0 and receiptno !~ '^[A-Z].*$' group by itemcode")
        non_standard_lot_total = cursor_postgres.fetchall()

        # Get batch_tuples for all component_item_codes in one query
        cursor_postgres.execute(f"select itemcode, receiptno, quantityonhand from im_itemcost where itemcode in ({component_item_code_str}) and quantityonhand!=0 and receiptno ~ '^[A-Z].*$' order by receiptdate")
        batch_tuples = cursor_postgres.fetchall()

        # create a dictionary for non_standard_lot_total
        non_standard_lot_total_dict = {}
        for item in non_standard_lot_total:
            non_standard_lot_total_dict[item[0]] = item[1]

        # create a dictionary for batch_tuples
        batch_tuples_dict = {}
        for item in batch_tuples:
            if item[0] not in batch_tuples_dict:
                batch_tuples_dict[item[0]] = []
            batch_tuples_dict[item[0]].append((item[1], item[2]))

        for component_item_code in component_item_code_list:
            non_standard_lot_total = non_standard_lot_total_dict.get(component_item_code, 0)
            batch_tuples = batch_tuples_dict.get(component_item_code, [])
            batch_num_list = ['n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a']
            batch_qty_list = [0,'n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a']
            list_pos = 0
            for this_tuple in batch_tuples:
                batch_num_list[list_pos] = this_tuple[0]
                batch_qty_list[list_pos] = str(round(this_tuple[1],0))
                list_pos += 1
            batch_qty_list[0] = str(float(batch_qty_list[0]) + float(non_standard_lot_total))
            item_number = 1
            batch_num = 'batchnum'
            batch_qty = 'batchqty'
            for item_number in range(9):
                batch_num+=str(item_number+1)
                batch_qty+=str(item_number+1)
                cursor_postgres.execute("update issue_sheet_needed_TEMP set "
                                        + batch_num
                                        + "='"
                                        + batch_num_list[item_number]
                                        + "' where component_item_code='"
                                        + component_item_code
                                        + "'")
                cursor_postgres.execute("update issue_sheet_needed_TEMP set "
                                        + batch_qty
                                        + "='"
                                        + batch_qty_list[item_number]
                                        + "' where component_item_code='"
                                        + component_item_code
                                        + "'")
                batch_num = 'batchnum'
                batch_qty = 'batchqty'
        connection_postgres.commit()
        cursor_postgres.close()
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''update issue_sheet_needed_TEMP
                                set uniqchek=concat(prodline, component_item_code)''')
        cursor_postgres.execute('''DELETE FROM issue_sheet_needed_TEMP a USING issue_sheet_needed_TEMP b
                                    WHERE a.id > b.id AND a.uniqchek = b.uniqchek;''')
        cursor_postgres.execute('drop table if exists issue_sheet_needed')
        cursor_postgres.execute('alter table issue_sheet_needed_TEMP rename to issue_sheet_needed')
        cursor_postgres.execute('drop table if exists issue_sheet_needed_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======issue_sheet_needed table created.=======')
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\issue_sheet_needed_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\issue_sheet_needed_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building issue_sheet_needed...')
            f.write('\n')

def create_blendthese_table():
    print(f'{dt.datetime.now()}=======BLEND DEEZ START=======')
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists blendthese_TEMP')
        cursor_postgres.execute('''create table blendthese_TEMP as select *
                                from timetable_run_data trd
                                where oh_after_run < 0''')
        cursor_postgres.execute('''DELETE FROM blendthese_TEMP a USING blendthese_TEMP b
                                WHERE a.id > b.id AND a.component_item_code = b.component_item_code;''') # delete duplicates:
                                # https://stackoverflow.com/questions/17221543/filter-duplicate-rows-based-on-a-field
        cursor_postgres.execute('''alter table blendthese_TEMP
                                add one_wk_short numeric, add two_wk_short numeric,
                                add three_wk_short numeric, add last_txn_date date,
                                add last_txn_code text, add last_count_quantity numeric, 
                                add last_count_date date;''')
        connection_postgres.commit()
        cursor_postgres.close()
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('select distinct blendthese_TEMP.component_item_code from blendthese_TEMP')
        tuple_list = cursor_postgres.fetchall()
        component_item_code_list = []
        for this_tuple in tuple_list:
            component_item_code_list.append(this_tuple[0])
        alchemy_engine = create_engine(
            'postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb',
            pool_recycle=3600
            )
        alchemy_connection = alchemy_engine.connect()
        timetable_df = pd.read_sql('''select component_item_code, adjustedrunqty, oh_after_run, week_calc
                                    from timetable_run_data where oh_after_run<0''', alchemy_connection
                                    )
        pd.set_option('display.expand_frame_repr', False)
        one_week_df = timetable_df[timetable_df.week_calc.isin([2.0,3.0]) == False]
        two_week_df = timetable_df[timetable_df.week_calc.isin([3.0]) == False]
        three_week_df = timetable_df
        for component_item_code in component_item_code_list:
            filtered_one_week_df = one_week_df.loc[one_week_df['component_item_code'] == component_item_code]
            if len(filtered_one_week_df) == 0:
                qty_this_blend_one_week = 0
            else:
                qty_this_blend_one_week =  filtered_one_week_df.iloc[-1,2] * -1
            cursor_postgres.execute("update blendthese_TEMP set one_wk_short="
                                    + "'"
                                    + str(qty_this_blend_one_week)
                                    + "'"
                                    + " where component_item_code="
                                    + "'"
                                    + component_item_code
                                    + "'")

            filtered_two_week_df = two_week_df.loc[two_week_df['component_item_code'] == component_item_code]
            if len(filtered_two_week_df) == 0:
                qty_this_blend_two_weeks = 0
            else:
                qty_this_blend_two_weeks =  filtered_two_week_df.iloc[-1,2] * -1
            cursor_postgres.execute("update blendthese_TEMP set two_wk_short="
                                    + "'"
                                    + str(qty_this_blend_two_weeks)
                                    + "'"
                                    + " where component_item_code="
                                    + "'"
                                    + component_item_code
                                    + "'")

            filtered_three_week_df = three_week_df.loc[three_week_df['component_item_code'] == component_item_code]
            if len(filtered_three_week_df) == 0:
                qty_this_blend_three_weeks = 0
            else:
                qty_this_blend_three_weeks = filtered_three_week_df.iloc[-1,2] * -1
            cursor_postgres.execute("update blendthese_TEMP set three_wk_short="
                                    + "'"
                                    + str(qty_this_blend_three_weeks)+"'"
                                    + " where component_item_code="
                                    + "'"
                                    + component_item_code
                                    + "'")
        cursor_postgres.execute('''update blendthese_TEMP set last_txn_code=(select transactioncode from im_itemtransactionhistory
            where im_itemtransactionhistory.itemcode=blendthese_TEMP.component_item_code order by transactiondate DESC limit 1);
            update blendthese_TEMP set last_txn_date=(select transactiondate from im_itemtransactionhistory
            where im_itemtransactionhistory.itemcode=blendthese_TEMP.component_item_code order by transactiondate DESC limit 1);
            update blendthese_TEMP set last_count_quantity=(select counted_quantity from core_countrecord
            where core_countrecord.item_code=blendthese_TEMP.component_item_code and core_countrecord.counted=True order by counted_date DESC limit 1);
            update blendthese_TEMP set last_count_date=(select counted_date from core_countrecord
            where core_countrecord.item_code=blendthese_TEMP.component_item_code and core_countrecord.counted=True order by counted_date DESC limit 1);''')
        cursor_postgres.execute('drop table if exists blendthese')
        cursor_postgres.execute('alter table blendthese_TEMP rename to blendthese')
        cursor_postgres.execute('drop table if exists blendthese_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======blendthese table created.=======')
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blendthese_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + (f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\blendthese_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Error: ' + (f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
            f.write('\n')

def create_upcoming_blend_count_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists upcoming_blend_count_TEMP')
        cursor_postgres.execute(r'''CREATE TABLE upcoming_blend_count_TEMP AS
                                    SELECT * FROM (
                                    SELECT im_itemtransactionhistory.itemcode AS item_code,
                                            bill_of_materials.component_item_description AS item_description,
                                            bill_of_materials.qtyonhand AS expected_quantity,
                                            im_itemtransactionhistory.transactiondate AS last_transaction_date,
                                            im_itemtransactionhistory.transactioncode AS last_transaction_code,
                                            im_itemtransactionhistory.transactionqty AS last_transaction_quantity,
                                            bill_of_materials.procurementtype AS procurement_type,
                                            timetable_run_data.starttime AS start_time,
                                            timetable_run_data.prodline AS prod_line,
                                            ROW_NUMBER() OVER (PARTITION BY im_itemtransactionhistory.itemcode
                                                    ORDER BY im_itemtransactionhistory.transactiondate DESC) AS row_number
                                    FROM im_itemtransactionhistory
                                    left JOIN bill_of_materials
                                        ON bill_of_materials.component_item_code = im_itemtransactionhistory.itemcode
                                    left JOIN timetable_run_data
                                        ON timetable_run_data.component_item_code = bill_of_materials.component_item_code
                                    WHERE bill_of_materials.component_item_description LIKE 'BLEND%'
                                    and bill_of_materials.component_item_description not like 'BLEND-RVAF%'
                                    and lower(bill_of_materials.component_item_description) not like '%salt citric%'
                                    and lower(bill_of_materials.component_item_description) not like 'blend-splash%'
                                    and lower(bill_of_materials.component_item_description) not like '%supertech%'
                                    and lower(bill_of_materials.component_item_description) not like '%w/w%'
                                    and lower(bill_of_materials.component_item_description) not like '%performacide%'
                                    and lower(bill_of_materials.component_item_description) not like '%lithium%'
                                    and lower(bill_of_materials.component_item_description) not like '%teak sealer%'
                                    and lower(bill_of_materials.component_item_description) not like '%liq elec tape%'
                                    and timetable_run_data.starttime > 4
                                    ) AS subquery
                                    WHERE item_description LIKE 'BLEND%'
                                    AND row_number = 1;
                                    ''')
        cursor_postgres.execute('''alter table upcoming_blend_count_TEMP
                                add column id serial primary key''')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP add last_count_quantity numeric;')
        cursor_postgres.execute('''update upcoming_blend_count_TEMP set last_count_quantity=(
                                    select counted_quantity from core_countrecord
                                    where upcoming_blend_count_TEMP.item_code=core_countrecord.item_code
                                    and core_countrecord.counted=True
                                    order by counted_date DESC limit 1);''')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP add last_count_date date;')
        cursor_postgres.execute('''update upcoming_blend_count_TEMP set last_count_date=(
                                    select counted_date from core_countrecord
                                    where upcoming_blend_count_TEMP.item_code=core_countrecord.item_code
                                    and core_countrecord.counted=True
                                    order by counted_date DESC limit 1);''')
        cursor_postgres.execute('drop table if exists upcoming_blend_count')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP rename to upcoming_blend_count')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======upcoming_blend_count table created.=======')

        connection_postgres.close()

    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\upcoming_blend_count_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\upcoming_blend_count_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Error: ' + (f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
            f.write('\n')

def create_upcoming_component_count_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists upcoming_component_count_TEMP')
        cursor_postgres.execute(r'''CREATE TABLE upcoming_component_count_TEMP AS
                                    SELECT *
                                    FROM (
                                    SELECT im_itemtransactionhistory.itemcode AS item_code,
                                            bill_of_materials.component_item_description AS item_description,
                                            bill_of_materials.qtyonhand AS expected_quantity,
                                            im_itemtransactionhistory.transactiondate AS last_transaction_date,
                                            im_itemtransactionhistory.transactioncode AS last_transaction_code,
                                            im_itemtransactionhistory.transactionqty AS last_transaction_quantity,
                                            ROW_NUMBER() OVER (PARTITION BY im_itemtransactionhistory.itemcode
                                                    ORDER BY im_itemtransactionhistory.transactiondate DESC) AS row_number
                                    FROM im_itemtransactionhistory
                                    left JOIN bill_of_materials
                                        ON bill_of_materials.component_item_code = im_itemtransactionhistory.itemcode
                                    left JOIN timetable_run_data
                                        ON timetable_run_data.component_item_code = bill_of_materials.component_item_code
                                    WHERE bill_of_materials.component_item_description LIKE 'CHEM%'
                                    OR bill_of_materials.component_item_description LIKE 'DYE%'
                                    OR bill_of_materials.component_item_description LIKE 'FRAGRANCE%'
                                    ) AS subquery
                                    WHERE row_number = 1;
                                    ''')
        cursor_postgres.execute('''alter table upcoming_component_count_TEMP
                                add column id serial primary key''')
        cursor_postgres.execute('alter table upcoming_component_count_TEMP add last_count_quantity numeric;')
        cursor_postgres.execute('''update upcoming_component_count_TEMP set last_count_quantity=(
                                    select counted_quantity from core_countrecord
                                    where upcoming_component_count_TEMP.item_code=core_countrecord.item_code
                                    and core_countrecord.counted=True
                                    order by counted_date DESC limit 1);''')
        cursor_postgres.execute('alter table upcoming_component_count_TEMP add last_count_date date;')
        cursor_postgres.execute('''update upcoming_component_count_TEMP set last_count_date=(
                                    select counted_date from core_countrecord
                                    where upcoming_component_count_TEMP.item_code=core_countrecord.item_code
                                    and core_countrecord.counted=True
                                    order by counted_date DESC limit 1);''')
        cursor_postgres.execute('drop table if exists upcoming_component_count')
        cursor_postgres.execute('alter table upcoming_component_count_TEMP rename to upcoming_component_count')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======upcoming_component_count table created.=======')

        connection_postgres.close()

    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\upcoming_component_count_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\upcoming_component_count_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Error: ' + (f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
            f.write('\n')

def create_weekly_blend_totals_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table weekly_blend_totals_TEMP as
                                        select date_trunc('week', core_lotnumrecord.sage_entered_date) as week_starting, 
                                        sum(core_lotnumrecord.lot_quantity) as blend_quantity
                                        FROM core_lotnumrecord WHERE core_lotnumrecord.line like 'Prod'
                                        GROUP BY week_starting ORDER BY week_starting;
                                    alter table weekly_blend_totals_TEMP add column id serial primary key;
                                    drop table if exists weekly_blend_totals;
                                    alter table weekly_blend_totals_TEMP rename to weekly_blend_totals;
                                    ''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======weekly_blend_totals_table created.=======')
        connection_postgres.close()
    except Exception as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\weekly_blend_totals_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\weekly_blend_totals_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Error: ' + (f'{dt.datetime.now()}======= {str(e)} =======') + str(dt.datetime.now()))
            f.write('\n')