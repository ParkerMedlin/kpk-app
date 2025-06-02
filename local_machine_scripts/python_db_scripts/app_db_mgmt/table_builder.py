from __future__ import generators
import psycopg2
import pandas as pd
import time
import datetime as dt
import os
from sqlalchemy import create_engine
import sys

class CustomException(Exception):
    pass

today = dt.datetime.today()
three_days_ago = dt.datetime.strftime(today - dt.timedelta(days = 3), '%Y-%m-%d')

def create_bill_of_materials_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''
                                drop table if exists bill_of_materials_TEMP;
                                CREATE TABLE bill_of_materials_TEMP AS  
                                SELECT DISTINCT
                                    Bm_BillDetail.billno AS item_code,
                                    Bm_BillDetail.scrappercent AS scrap_percent,
                                    ci_item.itemcode AS component_item_code,
                                    ci_item.itemcodedesc AS component_item_description,
                                    ci_item.procurementtype AS procurementtype,
                                    core_foamfactor.factor AS foam_factor,
                                    ci_item.StandardUnitOfMeasure AS standard_uom,
                                    bm_billdetail.commenttext AS comment_text,
                                    bm_billdetail.quantityperbill ::numeric(20,10) as qtyperbill,
                                    ci_item.shipweight AS weightpergal,
                                    im_itemwarehouse.QuantityOnHand AS qtyonhand
                                FROM 
                                    ci_item AS ci_item
                                JOIN Bm_BillDetail Bm_BillDetail ON ci_item.itemcode = Bm_BillDetail.componentitemcode
                                LEFT JOIN core_foamfactor core_foamfactor ON ci_item.itemcode = core_foamfactor.item_code
                                LEFT JOIN im_itemwarehouse im_itemwarehouse ON ci_item.itemcode = im_itemwarehouse.itemcode 
                                    AND im_itemwarehouse.warehousecode = 'MTG'
                                LEFT JOIN bm_billheader bm_billheader ON ci_item.itemcode = bm_billheader.billno
                                ORDER BY item_code;
                                ALTER TABLE bill_of_materials_TEMP ADD id SERIAL PRIMARY KEY;
                                ALTER TABLE bill_of_materials_TEMP ADD item_description TEXT;
                                UPDATE bill_of_materials_TEMP SET item_description = (SELECT ci_item.itemcodedesc FROM ci_item 
                                    WHERE bill_of_materials_TEMP.item_code = ci_item.itemcode);
                                UPDATE bill_of_materials_TEMP SET foam_factor = 1 WHERE foam_factor IS NULL;
                                update bill_of_materials_TEMP set component_item_description = bill_of_materials_TEMP.comment_text
                                    where component_item_code like '/C%';
                                update bill_of_materials_TEMP set component_item_description = concat('_', component_item_description)
                                    where component_item_description like 'DC provide%';
                                UPDATE bill_of_materials_TEMP
                                SET component_item_code = 
                                    CASE 
                                        WHEN component_item_description like '%080100UN%' THEN '080100UN'
                                        WHEN component_item_description like '%080116UN%' THEN '080116UN'
                                        WHEN component_item_description like '%081318UN%' THEN '081318UN'
                                        WHEN component_item_description like '%081816PUN%' THEN '081816PUN'
                                        WHEN component_item_description like '%082314UN%' THEN '082314UN'
                                        WHEN component_item_description like '%082708PUN%' THEN '082708PUN'
                                        WHEN component_item_description like '%083416UN%' THEN '083416UN'
                                        WHEN component_item_description like '%083821UN%' THEN '083821UN'
                                        WHEN component_item_description like '%083823UN%' THEN '083823UN'
                                        WHEN component_item_description like '%085700UN%' THEN '085700UN'
                                        WHEN component_item_description like '%085716PUN%' THEN '085716PUN'
                                        WHEN component_item_description like '%085732UN%' THEN '085732UN'
                                        WHEN component_item_description like '%087208UN%' THEN '087208UN'
                                        WHEN component_item_description like '%087308UN%' THEN '087308UN'
                                        WHEN component_item_description like '%087516UN%' THEN '087516UN'
                                        WHEN component_item_description like '%089600UN%' THEN '089600UN'
                                        WHEN component_item_description like '%089616PUN%' THEN '089616PUN'
                                        WHEN component_item_description like '%089632PUN%' THEN '089632PUN'
                                        ELSE component_item_code
                                    END;
                                 UPDATE bill_of_materials_TEMP bom2
                                    SET qtyperbill = 1,
                                        standard_uom = 'CS',
                                        procurementtype = 'B',
                                        qtyonhand = (select quantity from starbrite_item_quantities siq
                                            where bom2.component_item_code=siq.item_code limit 1)
                                    where component_item_code in ('080100UN','080116UN','081318UN','081816PUN',
                                        '082314UN','082708PUN','083416UN','083821UN','083823UN','085700UN',
                                        '085716PUN','085732UN','087208UN','087308UN','087516UN','089600UN',
                                        '089616PUN','089632PUN');
                                
                                drop table if exists bill_of_materials;
                                alter table bill_of_materials_TEMP rename to bill_of_materials;
                                drop table if exists bill_of_materials_TEMP;
                                ''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======bill_of_materials table created.=======')
        
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\bill_of_materials_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))


def create_component_usage_table():
    try:
        connection_postgres = psycopg2.connect(
                    'postgresql://postgres:blend2021@localhost:5432/blendversedb'
                    )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table component_usage_TEMP as
                    select * from (select prodmerge_run_data.item_run_qty as item_run_qty,
                        prodmerge_run_data.start_time as start_time,
                        prodmerge_run_data.id2 as id2,
                        prodmerge_run_data.po_number as po_number,
                        prodmerge_run_data.item_code as item_code,
                        prodmerge_run_data.prod_line as prod_line,
                        bill_of_materials.component_item_description,
                        bill_of_materials.component_item_code,
                        bill_of_materials.qtyperbill as qty_per_bill,
                        bill_of_materials.qtyperbill * prodmerge_run_data.item_run_qty * bill_of_materials.foam_factor as run_component_qty,
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
                        OR component_item_description LIKE 'BLISTER%'
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
                        OR component_item_description LIKE 'REBATE%'
                        OR component_item_description LIKE 'RUBBERBAND%'
                        OR component_item_code LIKE '080100UN'
                        OR component_item_code LIKE '080116UN'
                        OR component_item_code LIKE '081318UN'
                        OR component_item_code LIKE '081816PUN'
                        OR component_item_code LIKE '082314UN'
                        OR component_item_code LIKE '082708PUN'
                        OR component_item_code LIKE '083416UN'
                        OR component_item_code LIKE '083821UN'
                        OR component_item_code LIKE '083823UN'
                        OR component_item_code LIKE '085700UN'
                        OR component_item_code LIKE '085716PUN'
                        OR component_item_code LIKE '085732UN'
                        OR component_item_code LIKE '087208UN'
                        OR component_item_code LIKE '087308UN'
                        OR component_item_code LIKE '087516UN'
                        OR component_item_code LIKE '089600UN'
                        OR component_item_code LIKE '089616PUN'
                        OR component_item_code LIKE '089632PUN'
                    ORDER BY start_time, po_number;
                    update component_usage_TEMP set run_component_qty = run_component_qty * 1.1 
                        where component_item_description like 'BLEND%' and procurement_type like 'M'
                        and prod_line not like 'Totes' and prod_line not like 'Dm'
                        and prod_line not like 'Hx' and prod_line not like 'Pails'
                        and component_item_code not in ('602025KPK','602026KPK','602027KPK','602028KPK','602034KPK');
                    alter table component_usage_TEMP add cumulative_component_run_qty numeric;
                    UPDATE component_usage_TEMP AS cu1
                    SET cumulative_component_run_qty = (
                        SELECT SUM(cu2.run_component_qty)
                        FROM component_usage_TEMP AS cu2
                        WHERE cu2.component_item_code = cu1.component_item_code AND cu2.start_time <= cu1.start_time);
                    alter table component_usage_TEMP add component_onhand_after_run numeric;
                    UPDATE component_usage_TEMP set component_onhand_after_run=component_on_hand_qty-cumulative_component_run_qty;
                    alter table component_usage_TEMP add id serial primary key;
                    drop table if exists component_usage;
                    alter table component_usage_TEMP rename to component_usage;
                    drop table if exists component_usage_TEMP''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======component_usage table created.=======')
    
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\component_usage_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))


def create_component_shortages_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(f'''drop table if exists component_shortage_TEMP;
                                    create table component_shortage_TEMP as
                                    SELECT * FROM (SELECT *,
                                        ROW_NUMBER() OVER (PARTITION BY component_item_code
                                            ORDER BY start_time) AS component_instance_count
                                        FROM component_usage
                                        where component_onhand_after_run < 0
                                    ) AS subquery;
                                    alter table component_shortage_TEMP
                                        add one_wk_short numeric, add two_wk_short numeric,
                                        add three_wk_short numeric, add total_shortage numeric,
                                        add unscheduled_short numeric, add last_txn_date date,
                                        add last_txn_code text, add last_count_quantity numeric,
                                        add last_count_date date;
                                    update component_shortage_TEMP set total_shortage=((
                                        SELECT cumulative_component_run_qty from component_usage
                                        where component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                        order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_TEMP set one_wk_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where start_time<40
                                            and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_TEMP 
                                        set one_wk_short = COALESCE(one_wk_short, 0)
                                        where one_wk_short is null;
                                    update component_shortage_TEMP set two_wk_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where start_time<80 
                                            and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_TEMP 
                                        set two_wk_short = COALESCE(two_wk_short, 0)
                                        where two_wk_short is null;
                                    update component_shortage_TEMP set three_wk_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where start_time<299
                                            and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_TEMP 
                                        set three_wk_short = COALESCE(three_wk_short, 0)
                                        where three_wk_short is null;
                                    update component_shortage_TEMP set unscheduled_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where prod_line like 'UNSCHEDULED%'
                                            and component_usage.component_item_code=component_shortage_TEMP.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty)-three_wk_short;
                                    update component_shortage_TEMP 
                                        set unscheduled_short = COALESCE(unscheduled_short, 0)
                                        where unscheduled_short is null;
                                    update component_shortage_TEMP set one_wk_short=0 where one_wk_short<0;
                                        update component_shortage_TEMP set two_wk_short=0 where two_wk_short<0;
                                        update component_shortage_TEMP set three_wk_short=0 where three_wk_short<0;
                                        update component_shortage_TEMP set unscheduled_short=0 where unscheduled_short<0;
                                    update component_shortage_TEMP set last_txn_code=(select transactioncode 
                                        from im_itemtransactionhistory
                                        where im_itemtransactionhistory.itemcode=component_shortage_TEMP.component_item_code 
                                        order by transactiondate DESC limit 1);
                                    update component_shortage_TEMP set last_txn_date=(select transactiondate from im_itemtransactionhistory
                                        where im_itemtransactionhistory.itemcode=component_shortage_TEMP.component_item_code 
                                        order by transactiondate DESC limit 1);
                                    update component_shortage_TEMP set last_count_quantity=(select counted_quantity from core_blendcountrecord
                                        where core_blendcountrecord.item_code=component_shortage_TEMP.component_item_code and core_blendcountrecord.counted=True 
                                        order by counted_date DESC limit 1);
                                    update component_shortage_TEMP set last_count_date=(select counted_date from core_blendcountrecord
                                        where core_blendcountrecord.item_code=component_shortage_TEMP.component_item_code and core_blendcountrecord.counted=True 
                                        order by counted_date DESC limit 1);
                                    alter table component_shortage_TEMP add next_order_due date;
                                    update component_shortage_TEMP set next_order_due=(
                                        SELECT requireddate from po_purchaseorderdetail
                                        where requireddate > '{three_days_ago}'
                                        and po_purchaseorderdetail.itemcode = component_shortage_TEMP.component_item_code
                                        and po_purchaseorderdetail.quantityreceived = 0
                                        order by requireddate asc limit 1);
                                    alter table component_shortage_TEMP add run_component_demand numeric;
                                    UPDATE component_shortage_TEMP SET run_component_demand = CASE
                                        WHEN component_instance_count = 1 THEN (component_onhand_after_run * -1)
                                        ELSE run_component_qty
                                        END;
                                    drop table if exists component_shortage;
                                    alter table component_shortage_TEMP rename to component_shortage;''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======component_shortage table created.=======')

    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\component_shortage_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

def create_blend_subcomponent_usage_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''drop table if exists blend_subcomponent_usage_TEMP;
                                    create table blend_subcomponent_usage_TEMP as select * from(
                                        select component_shortage.item_run_qty as item_run_qty,
                                            component_shortage.start_time as start_time,
                                            component_shortage.po_number as po_number,
                                            component_shortage.id2 as id2,
                                            component_shortage.item_code as item_code,
                                            component_shortage.component_item_code as component_item_code,
                                            component_shortage.component_item_description as component_item_description,
                                            component_shortage.run_component_demand as run_component_demand,
                                            component_shortage.prod_line as prod_line,
                                            bill_of_materials.component_item_description as subcomponent_item_description,
                                            bill_of_materials.component_item_code as subcomponent_item_code,
                                            bill_of_materials.qtyperbill as qty_per_bill,
                                            bill_of_materials.qtyonhand as subcomponent_onhand_qty,
                                            bill_of_materials.standard_uom as standard_uom
                                        from component_shortage
                                        join bill_of_materials on component_shortage.component_item_code=bill_of_materials.item_code
                                        where component_shortage.component_item_description like 'BLEND%'
                                            and component_shortage.procurement_type like 'M'
                                            and component_shortage.component_onhand_after_run < 0
                                            and bill_of_materials.component_item_description not like '/C') as subquery
                                    where subcomponent_item_code!='030143' 
                                    and subcomponent_item_code!='965GEL-PREMIX.B';
                                    alter table blend_subcomponent_usage_TEMP add subcomponent_run_qty numeric;
                                    update blend_subcomponent_usage_TEMP 
                                        set subcomponent_run_qty = run_component_demand * qty_per_bill;
                                    alter table blend_subcomponent_usage_TEMP add cumulative_subcomponent_run_qty numeric;
                                    update blend_subcomponent_usage_TEMP as bsu1
                                        set cumulative_subcomponent_run_qty  = (
                                        SELECT SUM(bsu2.subcomponent_run_qty)
                                        FROM blend_subcomponent_usage_TEMP AS bsu2
                                        WHERE bsu2.subcomponent_item_code = bsu1.subcomponent_item_code
                                        AND bsu2.start_time <= bsu1.start_time
                                    );
                                    alter table blend_subcomponent_usage_TEMP 
                                        add subcomponent_onhand_after_run numeric;
                                    update blend_subcomponent_usage_TEMP
                                        set subcomponent_onhand_after_run = (subcomponent_onhand_qty - cumulative_subcomponent_run_qty);
                                    alter table blend_subcomponent_usage_TEMP add id serial primary key;
                                    drop table if exists blend_subcomponent_usage;
                                    alter table blend_subcomponent_usage_TEMP rename to blend_subcomponent_usage;
                                    ''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======subcomponent_usage table created.=======')
    
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_subcomponent_usage_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

def create_blend_subcomponent_shortage_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(f'''
                                drop table if exists blend_subcomponent_shortage_TEMP;
                                create table blend_subcomponent_shortage_TEMP as SELECT * FROM 
                                    (SELECT blend_subcomponent_usage.start_time as start_time,
                                            blend_subcomponent_usage.item_code as item_code,
                                            blend_subcomponent_usage.po_number as po_number,
                                            blend_subcomponent_usage.id2 as id2,
                                            blend_subcomponent_usage.prod_line as prod_line,
                                            blend_subcomponent_usage.component_item_code as component_item_code,
                                            blend_subcomponent_usage.component_item_description as component_item_description,
                                            blend_subcomponent_usage.subcomponent_item_code as subcomponent_item_code,
                                            blend_subcomponent_usage.subcomponent_item_description as subcomponent_item_description,
                                            blend_subcomponent_usage.item_run_qty as item_run_qty,
                                            blend_subcomponent_usage.subcomponent_onhand_qty as subcomponent_onhand_qty,
                                            blend_subcomponent_usage.qty_per_bill as qty_per_bill,
                                            blend_subcomponent_usage.standard_uom as standard_uom,
                                        ROW_NUMBER() OVER (PARTITION BY subcomponent_item_code
                                            ORDER BY start_time) AS subcomponent_instance_count
                                        FROM blend_subcomponent_usage where blend_subcomponent_usage.subcomponent_onhand_after_run < 0
                                    ) AS subquery
                                    where subcomponent_item_code!='030143'
                                    and subcomponent_item_code!='965GEL-PREMIX.B';
                                alter table blend_subcomponent_shortage_TEMP add max_possible_blend numeric;
                                update blend_subcomponent_shortage_TEMP set max_possible_blend=0 
                                    where subcomponent_onhand_qty=0;
                                update blend_subcomponent_shortage_TEMP 
                                    set max_possible_blend=subcomponent_onhand_qty/qty_per_bill
                                    where subcomponent_onhand_qty!=0;
                                alter table blend_subcomponent_shortage_TEMP add next_order_due date;
                                update blend_subcomponent_shortage_TEMP set next_order_due=(
                                    SELECT requireddate from po_purchaseorderdetail
                                    where requireddate > '{three_days_ago}'
                                    and po_purchaseorderdetail.itemcode = blend_subcomponent_shortage_TEMP.subcomponent_item_code
                                    and po_purchaseorderdetail.quantityreceived = 0
                                    order by requireddate asc limit 1);
                                alter table blend_subcomponent_shortage_TEMP
                                    add one_wk_short numeric, add two_wk_short numeric,
                                    add three_wk_short numeric, add total_short numeric,
                                    add unscheduled_short numeric;
                                update blend_subcomponent_shortage_TEMP set total_short=(
                                    SELECT subcomponent_onhand_after_run from blend_subcomponent_usage
                                    where blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_TEMP.subcomponent_item_code
                                    order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_TEMP set one_wk_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where start_time>=0 and start_time<10
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_TEMP.subcomponent_item_code
                                        order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_TEMP set two_wk_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where start_time<20 
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_TEMP.subcomponent_item_code
                                        order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_TEMP set three_wk_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where start_time<299
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_TEMP.subcomponent_item_code
                                        order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_TEMP set one_wk_short = 0 where one_wk_short is null;
                                update blend_subcomponent_shortage_TEMP set one_wk_short = 0 where one_wk_short > 0;
                                update blend_subcomponent_shortage_TEMP set two_wk_short = 0 where two_wk_short is null and one_wk_short = 0;
                                update blend_subcomponent_shortage_TEMP set two_wk_short = one_wk_short where two_wk_short is null and one_wk_short = 0;
                                update blend_subcomponent_shortage_TEMP set two_wk_short = 0 where two_wk_short > 0;
                                update blend_subcomponent_shortage_TEMP set three_wk_short = 0 where three_wk_short is null;
                                update blend_subcomponent_shortage_TEMP set three_wk_short = 0 where three_wk_short > 0;
                                update blend_subcomponent_shortage_TEMP set unscheduled_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where prod_line like 'UNSCHEDULED%'
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_TEMP.subcomponent_item_code
                                        order by start_time DESC LIMIT 1)-three_wk_short;
                                update blend_subcomponent_shortage_TEMP set unscheduled_short = 0 where unscheduled_short is null;
                                alter table blend_subcomponent_shortage_TEMP add id serial primary key;
                                drop table if exists blend_subcomponent_shortage;
                                alter table blend_subcomponent_shortage_TEMP rename to blend_subcomponent_shortage;
                                ''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======subcomponent_shortage table created.====')

    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_subcomponent_shortage_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

def create_blend_run_data_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table blend_run_data_TEMP as
                                    select distinct prodmerge_run_data.item_code as item_code,
                                    bill_of_materials.component_item_code as component_item_code,
                                    bill_of_materials.component_item_description as component_item_description,
                                    prodmerge_run_data.item_run_qty as unadjusted_runqty,
                                    bill_of_materials.foam_factor as foam_factor,
                                    bill_of_materials.qtyperbill as qtyperbill,
                                    bill_of_materials.qtyonhand as qtyonhand,
                                    bill_of_materials.procurementtype as procurementtype,
                                    prodmerge_run_data.run_time as runtime,
                                    prodmerge_run_data.start_time as starttime,
                                    prodmerge_run_data.id2 as id2,
                                    prodmerge_run_data.prod_line as prodline
                                from prodmerge_run_data as prodmerge_run_data
                                join bill_of_materials bill_of_materials 
                                    on prodmerge_run_data.item_code=bill_of_materials.item_code 
                                order by starttime;
                                alter table blend_run_data_TEMP add id serial primary key;
                                alter table blend_run_data_TEMP add adjustedrunqty numeric;
                                update blend_run_data_TEMP
                                    set adjustedrunqty=(unadjusted_runqty*1.1*foam_factor*qtyperbill)
                                    where adjustedrunqty > 0 and blend_run_data_temp.prod_line not like 'Totes' and blend_run_data_temp.prod_line not like 'Dm'
                                    and blend_run_data_temp.prod_line not like 'Hx' and blend_run_data_temp.prod_line not like 'Pails';
                                delete from blend_run_data_TEMP where component_item_description not like 'BLEND%';
                                drop table if exists blend_run_data;
                                alter table blend_run_data_TEMP rename to blend_run_data;
                                drop table if exists blend_run_data_TEMP;''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======blend_run_data table created.=======')
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\blend_run_data_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

def create_timetable_run_data_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table timetable_run_data_TEMP as
                                select id2, item_code, component_item_code, component_item_description, 
                                adjustedrunqty, qtyonhand, starttime, prodline, procurementtype,
                                    qtyonhand-sum(adjustedrunqty) over (partition by component_item_code 
                                    order by starttime) as oh_after_run 
                                from blend_run_data
                                order by starttime;
                                alter table timetable_run_data_TEMP add week_calc numeric;
                                update timetable_run_data_TEMP set week_calc=
                                case
                                    when starttime<40 then 1
                                    when starttime>80 and starttime<250 then 3
                                    when starttime>250 then 4
                                    else 2
                                end;
                                alter table timetable_run_data_TEMP add id serial primary key;
                                delete from timetable_run_data_TEMP where component_item_code = '/C';
                                drop table if exists timetable_run_data;
                                alter table timetable_run_data_TEMP rename to timetable_run_data;
                                drop table if exists timetable_run_data_TEMP''')
        connection_postgres.commit()
        cursor_postgres.close()
        connection_postgres.close()
        #print(f'{dt.datetime.now()}=======timetable_run_data table created.=======')
 
    except CustomException as e:
        # with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\timetable_run_data_last_update.txt'), 'w', encoding="utf-8") as f:
        #     f.write('Error: ' + str(e))
        print(f'{dt.datetime.now()} :: table_builder.py :: create_timetable_run_data_table :: {str(e)}')

def create_upcoming_blend_count_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(r'''drop table if exists upcoming_blend_count_TEMP;
                                     CREATE TABLE upcoming_blend_count_TEMP AS
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
                                    alter table upcoming_blend_count_TEMP
                                        add column id serial primary key;
                                    alter table upcoming_blend_count_TEMP add last_count_quantity numeric;
                                    update upcoming_blend_count_TEMP set last_count_quantity=(
                                        select counted_quantity from core_blendcountrecord
                                        where upcoming_blend_count_TEMP.item_code=core_blendcountrecord.item_code
                                        and core_blendcountrecord.counted=True
                                        order by counted_date DESC limit 1);
                                    alter table upcoming_blend_count_TEMP add last_count_date date;
                                    update upcoming_blend_count_TEMP set last_count_date=(
                                        select counted_date from core_blendcountrecord
                                        where upcoming_blend_count_TEMP.item_code=core_blendcountrecord.item_code
                                        and core_blendcountrecord.counted=True
                                        order by counted_date DESC limit 1);
                                    drop table if exists upcoming_blend_count;
                                    alter table upcoming_blend_count_TEMP rename to upcoming_blend_count;''')
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======upcoming_blend_count table created.=======')
        connection_postgres.close()
    
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\upcoming_blend_count_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

def create_upcoming_component_count_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(r'''drop table if exists upcoming_component_count_TEMP;
                                    CREATE TABLE upcoming_component_count_TEMP AS
                                        SELECT * FROM (
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
                                            WHERE bill_of_materials.component_item_description LIKE 'CHEM%'
                                            OR bill_of_materials.component_item_description LIKE 'DYE%'
                                            OR bill_of_materials.component_item_description LIKE 'FRAGRANCE%'
                                            ) AS subquery
                                                WHERE row_number = 1;
                                    alter table upcoming_component_count_TEMP add column id serial primary key;
                                    alter table upcoming_component_count_TEMP add column importance_rank numeric;
                                    alter table upcoming_component_count_TEMP add column last_count_quantity numeric;
                                    update upcoming_component_count_TEMP set last_count_quantity=(
                                        select counted_quantity from core_blendcomponentcountrecord
                                        where upcoming_component_count_TEMP.item_code=core_blendcomponentcountrecord.item_code
                                        and core_blendcomponentcountrecord.counted=True
                                        order by counted_date DESC limit 1);
                                    alter table upcoming_component_count_TEMP add column last_count_date date;
                                    update upcoming_component_count_TEMP set last_count_date=(
                                    select counted_date from core_blendcomponentcountrecord
                                    where upcoming_component_count_TEMP.item_code=core_blendcomponentcountrecord.item_code
                                    and core_blendcomponentcountrecord.counted=True
                                    order by counted_date DESC limit 1);
                                    drop table if exists upcoming_component_count;
                                    alter table upcoming_component_count_TEMP rename to upcoming_component_count;''')
        
        connection_postgres.commit()
        cursor_postgres.close()
        #print(f'{dt.datetime.now()}=======upcoming_component_count table created.=======')
        connection_postgres.close()
    
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\upcoming_component_count_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

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
        #print(f'{dt.datetime.now()}=======weekly_blend_totals_table created.=======')
        connection_postgres.close()
    
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\weekly_blend_totals_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')

def create_adjustment_statistic_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''drop table if exists adjustment_statistic_TEMP;
                                    create table adjustment_statistic_TEMP as
                                        select distinct on(component_item_code) component_item_code AS item_code, 
                                        component_item_description as item_description,
                                        procurementtype as procurement_type,
                                        standard_uom as standard_uom,
                                        qtyonhand as expected_quantity from bill_of_materials
                                        WHERE component_item_description like 'BLEND%'
                                            or component_item_description LIKE 'CHEM%'
                                            or component_item_description LIKE 'FRAGRANCE%'
                                            or component_item_description LIKE 'DYE%'
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
                                            OR component_item_description LIKE 'REBATE%'
                                            OR component_item_description LIKE 'RUBBERBAND%'
                                            OR component_item_code LIKE '080100UN'
                                            OR component_item_code LIKE '080116UN'
                                            OR component_item_code LIKE '081318UN'
                                            OR component_item_code LIKE '081816PUN'
                                            OR component_item_code LIKE '082314UN'
                                            OR component_item_code LIKE '082708PUN'
                                            OR component_item_code LIKE '083416UN'
                                            OR component_item_code LIKE '083821UN'
                                            OR component_item_code LIKE '083823UN'
                                            OR component_item_code LIKE '085700UN'
                                            OR component_item_code LIKE '085716PUN'
                                            OR component_item_code LIKE '085732UN'
                                            OR component_item_code LIKE '087208UN'
                                            OR component_item_code LIKE '087308UN'
                                            OR component_item_code LIKE '087516UN'
                                            OR component_item_code LIKE '089600UN'
                                            OR component_item_code LIKE '089616PUN'
                                            OR component_item_code LIKE '089632PUN';
                                    alter table adjustment_statistic_TEMP add adjustment_sum numeric;
                                    alter table adjustment_statistic_TEMP add run_sum numeric;
                                    alter table adjustment_statistic_TEMP add max_adjustment numeric;
                                    alter table adjustment_statistic_TEMP add adj_percentage_of_run numeric;
                                    update adjustment_statistic_TEMP ads
                                        set adjustment_sum = (select sum(transactionqty) 
                                            from im_itemtransactionhistory ith
                                            where ads.item_code = ith.itemcode
                                            and ith.transactioncode = 'II');
                                    DELETE FROM adjustment_statistic_TEMP WHERE adjustment_sum IS NULL;
                                    update adjustment_statistic_TEMP ads
                                        set run_sum = (select sum(transactionqty) 
                                            from im_itemtransactionhistory ith
                                            where ads.item_code = ith.itemcode
                                            and ith.transactioncode = 'BI');
                                    DELETE FROM adjustment_statistic_TEMP WHERE run_sum IS NULL;
                                    update adjustment_statistic_TEMP ads
                                        set max_adjustment = (select min(transactionqty) 
                                            from im_itemtransactionhistory ith
                                            where ads.item_code = ith.itemcode
                                            and ith.transactioncode = 'II');
                                    update adjustment_statistic_TEMP ads
                                        set adj_percentage_of_run = ads.adjustment_sum/ads.run_sum;
                                    alter table adjustment_statistic_TEMP add last_count_quantity numeric;
                                    update adjustment_statistic_TEMP set last_count_quantity=(
                                        select counted_quantity from core_blendcountrecord
                                        where adjustment_statistic_TEMP.item_code=core_blendcountrecord.item_code
                                        and core_blendcountrecord.counted=True
                                        order by counted_date DESC limit 1);
                                    alter table adjustment_statistic_TEMP add last_count_date date;
                                    update adjustment_statistic_TEMP set last_count_date=(
                                        select counted_date from core_blendcountrecord
                                        where adjustment_statistic_TEMP.item_code=core_blendcountrecord.item_code
                                        and core_blendcountrecord.counted=True
                                        order by counted_date DESC limit 1);
                                    alter table adjustment_statistic_TEMP add column id serial primary key;
                                    drop table if exists adjustment_statistic;
                                    alter table adjustment_statistic_TEMP rename to adjustment_statistic;
                                    ''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()} :: table_builder.py :: create_adjustment_statistic_table :: ==OK== table_builder.py complete ==OK==')
        connection_postgres.close()
    
    except CustomException as e:
        with open(os.path.expanduser('~\\Documents\\kpk-app\\local_machine_scripts\\python_db_scripts\\last_touch\\weekly_blend_totals_last_update.txt'), 'w', encoding="utf-8") as f:
            f.write('Error: ' + str(e))
        # print(f'{dt.datetime.now()} -- {str(e)}')