from __future__ import generators
import psycopg2
import pandas as pd
import time
import datetime as dt
import os
from sqlalchemy import create_engine
import sys

def create_blend_BOM_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_BOM_table_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building blend_BOM table...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''CREATE TABLE blend_bill_of_materials_TEMP as
                                select distinct Bm_BillDetail.billno AS bill_no,
                                    ci_item.itemcode as component_itemcode,
                                    ci_item.itemcodedesc as component_desc,
                                    ci_item.procurementtype as procurementtype,
                                    core_foamfactor.factor AS foam_factor,
                                    ci_item.StandardUnitOfMeasure AS standard_uom,
                                    bm_billdetail.quantityperbill as qtyperbill,
                                    ci_item.shipweight as weightpergal,
                                    im_itemwarehouse.QuantityOnHand AS qtyonhand
                                FROM ci_item AS ci_item
                                JOIN Bm_BillDetail Bm_BillDetail ON ci_item.itemcode=Bm_BillDetail.componentitemcode
                                left join core_foamfactor core_foamfactor on ci_item.itemcode=core_foamfactor.blend
                                left join im_itemwarehouse im_itemwarehouse 
                                    on ci_item.itemcode=im_itemwarehouse.itemcode 
                                    and im_itemwarehouse.warehousecode = 'MTG'
                                left join bm_billheader bm_billheader on ci_item.itemcode=bm_billheader.billno
                                where ci_item.itemcodedesc like 'CHEM -%' 
                                    or ci_item.itemcodedesc like 'BLEND-%' 
                                    or ci_item.itemcodedesc like 'FRAGRANCE%' 
                                    or ci_item.itemcodedesc like 'DYE%'
                                order by bill_no'''
                                )
        cursor_postgres.execute('alter table blend_bill_of_materials_TEMP add id serial primary key;')
        cursor_postgres.execute('alter table blend_bill_of_materials_TEMP add bill_desc text;')
        cursor_postgres.execute('''update blend_bill_of_materials_TEMP set bill_desc=
                                    (select ci_item.itemcodedesc from ci_item 
                                    where blend_bill_of_materials_TEMP.bill_no=ci_item.itemcode);''')
        cursor_postgres.execute('''update blend_bill_of_materials_TEMP
                                    set foam_factor=1 where foam_factor IS NULL;''')
        cursor_postgres.execute('drop table if exists blend_bill_of_materials')
        cursor_postgres.execute('''alter table blend_bill_of_materials_TEMP
                                    rename to blend_bill_of_materials''')
        cursor_postgres.execute('drop table if exists blend_bill_of_materials_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        print('blend_bill_of_materials table created')

    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Calculated_Tables_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\Calculated_Tables_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building blend_BOM...')
            f.write('\n')

def create_prod_BOM_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\prod_BOM_table_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building prod_BOM table...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''CREATE TABLE prod_bill_of_materials_TEMP as
                                    select distinct Bm_BillDetail.billno AS bill_no,
                                    ci_item.itemcode as component_itemcode,
                                    ci_item.itemcodedesc as component_desc,
                                    ci_item.procurementtype as procurementtype,
                                    core_foamfactor.factor AS foam_factor,
                                    ci_item.StandardUnitOfMeasure AS standard_uom,
                                    bm_billdetail.quantityperbill as qtyperbill,
                                    ci_item.shipweight as weightpergal,
                                    im_itemwarehouse.QuantityOnHand AS qtyonhand
                                FROM ci_item AS ci_item
                                JOIN Bm_BillDetail Bm_BillDetail ON ci_item.itemcode=Bm_BillDetail.componentitemcode
                                left join core_foamfactor core_foamfactor on ci_item.itemcode=core_foamfactor.blend
                                left join im_itemwarehouse im_itemwarehouse 
                                    on ci_item.itemcode=im_itemwarehouse.itemcode 
                                    and im_itemwarehouse.warehousecode = 'MTG'
                                left join bm_billheader bm_billheader on ci_item.itemcode=bm_billheader.billno
                                order by bill_no'''
                                )
        cursor_postgres.execute('alter table prod_bill_of_materials_TEMP add id serial primary key;')
        cursor_postgres.execute('alter table prod_bill_of_materials_TEMP add bill_desc text;')
        cursor_postgres.execute('''update prod_bill_of_materials_TEMP set bill_desc=
                                    (select ci_item.itemcodedesc from ci_item 
                                    where prod_bill_of_materials_TEMP.bill_no=ci_item.itemcode);''')
        cursor_postgres.execute('''update prod_bill_of_materials_TEMP
                                    set foam_factor=1 where foam_factor IS NULL;''')
        cursor_postgres.execute('drop table if exists prod_bill_of_materials')
        cursor_postgres.execute('''alter table prod_bill_of_materials_TEMP
                                    rename to prod_bill_of_materials''')
        cursor_postgres.execute('drop table if exists prod_bill_of_materials_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        print('prod_bill_of_materials table created')
        
    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\prod_BOM_table_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\prod_BOM_table_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building prod_BOM...')
            f.write('\n')
        
def create_blend_run_data_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_run_data_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building blend_run_data table...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table blend_run_data_TEMP as
                                    select distinct prodmerge_run_data.p_n as bill_no,
                                    blend_bill_of_materials.component_itemcode as blend_pn,
                                    blend_bill_of_materials.component_desc as blend_desc,
                                    prodmerge_run_data.qty as unadjusted_runqty,
                                    blend_bill_of_materials.foam_factor as foam_factor,
                                    blend_bill_of_materials.qtyperbill as qtyperbill,
                                    blend_bill_of_materials.qtyonhand as qtyonhand,
                                    prodmerge_run_data.runtime as runtime,
                                    prodmerge_run_data.starttime as starttime,
                                    prodmerge_run_data.prodline as prodline,
                                    prodmerge_run_data.id2 as id2
                                from prodmerge_run_data as prodmerge_run_data
                                join blend_bill_of_materials blend_bill_of_materials 
                                    on prodmerge_run_data.p_n=blend_bill_of_materials.bill_no 
                                    and procurementtype='M'
                                order by starttime'''
                                )
        cursor_postgres.execute('alter table blend_run_data_TEMP add id serial primary key;')
        cursor_postgres.execute('alter table blend_run_data_TEMP add adjustedrunqty numeric;')
        cursor_postgres.execute('''update blend_run_data_TEMP
                                set adjustedrunqty=(unadjusted_runqty*1.1*foam_factor*qtyperbill)''')
        cursor_postgres.execute('drop table if exists blend_run_data')
        cursor_postgres.execute('alter table blend_run_data_TEMP rename to blend_run_data')
        cursor_postgres.execute('drop table if exists blend_run_data_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print('blend_run_data table created')
    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_run_data_table_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\blend_run_data_table_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building blend_run_data...')
            f.write('\n')

def create_timetable_run_data_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\timetable_run_data_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building timetable_run_data...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\Calculated_Tables_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Building timetable...')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table timetable_run_data_TEMP as
                                select id2, bill_no, blend_pn, blend_desc, adjustedrunqty, qtyonhand, starttime, prodline,
                                    qtyonhand-sum(adjustedrunqty) over (partition by blend_pn order by starttime) as oh_after_run 
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
        print('timetable_run_data table created')
    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\timetable_run_data_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\timetable_run_data_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building prod_BOM...')
            f.write('\n')

def create_issuesheet_needed_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\issuesheet_needed_table_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building issuesheet_needed...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists issue_sheet_needed_TEMP')
        cursor_postgres.execute('''create table issue_sheet_needed_TEMP as
                                select * from timetable_run_data where starttime < 20
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
        cursor_postgres.execute("select blend_pn from timetable_run_data")
        blend_pn_tuples = cursor_postgres.fetchall()
        cursor_postgres.close()
        blend_pn_list = []
        for blend_tuple in blend_pn_tuples:
            blend_pn_list.append(blend_tuple[0])
        cursor_postgres = connection_postgres.cursor()
        for blend_pn in blend_pn_list:
            cursor_postgres.execute("select sum(quantityonhand) from im_itemcost where itemcode='"
                                    + blend_pn
                                    + "' and quantityonhand!=0 and receiptno !~ '^[A-Z].*$'")
            for item in cursor_postgres:
                non_standard_lot_total = item[0]
            if non_standard_lot_total is None:
                non_standard_lot_total = 0
            cursor_postgres.execute("select receiptno, quantityonhand from im_itemcost where itemcode='"
                                    + blend_pn
                                    + "'and quantityonhand!=0 and receiptno ~ '^[A-Z].*$' order by receiptdate")
            connection_postgres.commit()
            batch_tuples = cursor_postgres.fetchall()
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
                                        + "' where blend_pn='"
                                        + blend_pn
                                        + "'")
                cursor_postgres.execute("update issue_sheet_needed_TEMP set "
                                        + batch_qty
                                        + "='"
                                        + batch_qty_list[item_number]
                                        + "' where blend_pn='"
                                        + blend_pn
                                        + "'")
                batch_num = 'batchnum'
                batch_qty = 'batchqty'
        connection_postgres.commit()
        cursor_postgres.close()
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''update issue_sheet_needed_TEMP
                                set uniqchek=concat(prodline, blend_pn)''')
        cursor_postgres.execute('''DELETE FROM issue_sheet_needed_TEMP a USING issue_sheet_needed_TEMP b
                                    WHERE a.id > b.id AND a.uniqchek = b.uniqchek;''')
        cursor_postgres.execute('drop table if exists issue_sheet_needed')
        cursor_postgres.execute('alter table issue_sheet_needed_TEMP rename to issue_sheet_needed')
        cursor_postgres.execute('drop table if exists issue_sheet_needed_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print('issue_sheet_needed table created')
    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\issue_sheet_needed_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\issue_sheet_needed_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building issue_sheet_needed...')
            f.write('\n')

def create_blendthese_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blendthese_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building blendthese...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists blendthese_TEMP')
        cursor_postgres.execute('''create table blendthese_TEMP as select *
                                from timetable_run_data trd
                                where oh_after_run < 0''')
        cursor_postgres.execute('''DELETE FROM blendthese_TEMP a USING blendthese_TEMP b
                                WHERE a.id > b.id AND a.blend_pn = b.blend_pn;''') # delete duplicates:
                                # https://stackoverflow.com/questions/17221543/filter-duplicate-rows-based-on-a-field
        cursor_postgres.execute('''alter table blendthese_TEMP
                                add one_wk_short numeric, add two_wk_short numeric,
                                add three_wk_short numeric, add last_txn_date date,
                                add last_txn_code text, add last_count_quantity numeric, 
                                add last_count_date date;''')
        connection_postgres.commit()
        cursor_postgres.close()
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('select distinct blendthese_TEMP.blend_pn from blendthese_TEMP')
        tuple_list = cursor_postgres.fetchall()
        part_number_list = []
        for this_tuple in tuple_list:
            part_number_list.append(this_tuple[0])
        alchemy_engine = create_engine(
            'postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb',
            pool_recycle=3600
            )
        alchemy_connection = alchemy_engine.connect()
        timetable_df = pd.read_sql('''select blend_pn, adjustedrunqty, oh_after_run, week_calc
                                    from timetable_run_data where oh_after_run<0''', alchemy_connection
                                    )
        pd.set_option('display.expand_frame_repr', False)
        one_week_df = timetable_df[timetable_df.week_calc.isin([2.0,3.0]) == False]
        two_week_df = timetable_df[timetable_df.week_calc.isin([3.0]) == False]
        three_week_df = timetable_df
        for part_number in part_number_list:
            filtered_one_week_df = one_week_df.loc[one_week_df['blend_pn'] == part_number]
            if len(filtered_one_week_df) == 0:
                qty_this_blend_one_week = 0
            else:
                qty_this_blend_one_week =  filtered_one_week_df.iloc[-1,2] * -1
            cursor_postgres.execute("update blendthese_TEMP set one_wk_short="
                                    + "'"
                                    + str(qty_this_blend_one_week)
                                    + "'"
                                    + " where blend_pn="
                                    + "'"
                                    + part_number
                                    + "'")

            filtered_two_week_df = two_week_df.loc[two_week_df['blend_pn'] == part_number]
            if len(filtered_two_week_df) == 0:
                qty_this_blend_two_weeks = 0
            else:
                qty_this_blend_two_weeks =  filtered_two_week_df.iloc[-1,2] * -1
            cursor_postgres.execute("update blendthese_TEMP set two_wk_short="
                                    + "'"
                                    + str(qty_this_blend_two_weeks)
                                    + "'"
                                    + " where blend_pn="
                                    + "'"
                                    + part_number
                                    + "'")

            filtered_three_week_df = three_week_df.loc[three_week_df['blend_pn'] == part_number]
            if len(filtered_three_week_df) == 0:
                qty_this_blend_three_weeks = 0
            else:
                qty_this_blend_three_weeks = filtered_three_week_df.iloc[-1,2] * -1
            cursor_postgres.execute("update blendthese_TEMP set three_wk_short="
                                    + "'"
                                    + str(qty_this_blend_three_weeks)+"'"
                                    + " where blend_pn="
                                    + "'"
                                    + part_number
                                    + "'")
            cursor_postgres.execute('''update blendthese set last_txn_code=(select transactioncode from im_itemtransactionhistory
	                                    where im_itemtransactionhistory.itemcode=blendthese.blend_pn order by transactiondate DESC limit 1);''')
            cursor_postgres.execute('''update blendthese set last_txn_date=(select transactiondate from im_itemtransactionhistory
	                                    where im_itemtransactionhistory.itemcode=blendthese.blend_pn order by transactiondate DESC limit 1);''')
            cursor_postgres.execute('''update blendthese set last_count_quantity=(select counted_quantity from core_countrecord
	                                    where core_countrecord.part_number=blendthese.blend_pn order by counted_date DESC limit 1);''')
            cursor_postgres.execute('''update blendthese set last_count_date=(select counted_date from core_countrecord
	                                    where core_countrecord.part_number=blendthese.blend_pn order by counted_date DESC limit 1);''')                                        
            
        cursor_postgres.execute('drop table if exists blendthese')
        cursor_postgres.execute('alter table blendthese_TEMP rename to blendthese')
        cursor_postgres.execute('drop table if exists blendthese_TEMP')
        connection_postgres.commit()
        cursor_postgres.close()
        print('blendthese table created')
    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blendthese_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\blendthese_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building blendthese...')
            f.write('\n')

def create_upcoming_blend_count_table():
    try:
        with open(os.path.expanduser(
            '~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\upcoming_blend_count_last_update.txt'
            ), 'w', encoding="utf-8") as f:
            f.write('Building upcoming_blend_count...')
        time_start = time.perf_counter()
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('drop table if exists upcoming_blend_count_TEMP')
        cursor_postgres.execute('''create table upcoming_blend_count_TEMP as
                                    select timetable_run_data.blend_pn as itemcode,
                                        timetable_run_data.blend_desc as itemdesc, 
                                        timetable_run_data.qtyonhand as expected_on_hand,
                                        timetable_run_data.starttime as starttime,
                                        timetable_run_data.prodline as prodline
                                    from timetable_run_data as timetable_run_data
                                    ''')
        cursor_postgres.execute('''alter table upcoming_blend_count_TEMP
                                add column id serial primary key''')
        cursor_postgres.execute('''DELETE FROM upcoming_blend_count_TEMP a
                                    USING upcoming_blend_count_TEMP b
                                    WHERE a.id > b.id AND a.itemcode = b.itemcode;''')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP add last_transaction_code text;')
        cursor_postgres.execute('''update upcoming_blend_count_TEMP set last_transaction_code=(
                                    select transactioncode from im_itemtransactionhistory
                                    where upcoming_blend_count_TEMP.itemcode=im_itemtransactionhistory.itemcode
                                    order by transactiondate DESC limit 1);''')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP add last_transaction_date date;')
        cursor_postgres.execute('''update upcoming_blend_count_TEMP set last_transaction_date=
                                    (select transactiondate from im_itemtransactionhistory
                                    where upcoming_blend_count_TEMP.itemcode=im_itemtransactionhistory.itemcode
                                    order by transactiondate DESC limit 1);''')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP add last_count_quantity numeric;')
        cursor_postgres.execute('''update upcoming_blend_count_TEMP set last_count_quantity=(
                                    select counted_quantity from core_countrecord
                                    where upcoming_blend_count_TEMP.itemcode=core_countrecord.part_number
                                    order by counted_date DESC limit 1);''')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP add last_count_date date;')
        cursor_postgres.execute('''update upcoming_blend_count_TEMP set last_count_date=(
                                    select counted_date from core_countrecord
                                    where upcoming_blend_count_TEMP.itemcode=core_countrecord.part_number
                                    order by counted_date DESC limit 1);''')
        cursor_postgres.execute('drop table if exists upcoming_blend_count')
        cursor_postgres.execute('alter table upcoming_blend_count_TEMP rename to upcoming_blend_count')
        connection_postgres.commit()
        cursor_postgres.close()
        print('upcoming_blend_count table created')

        connection_postgres.close()

    except:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\upcoming_blend_count_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(dt.datetime.now()))
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\error_logs\\upcoming_blend_count_error_log.txt'), 'a', encoding="utf-8") as f:
            f.write('Building upcoming_blend_count...')
            f.write('\n')
