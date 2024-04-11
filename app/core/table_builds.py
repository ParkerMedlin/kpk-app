import psycopg2
import datetime as dt


today = dt.datetime.today()
three_days_ago = dt.datetime.strftime(today - dt.timedelta(days = 3), '%Y-%m-%d')

# takes a dictionary containing: item_code, po_number, item_quantity, run_time, start_time, prod_line, item_description
def create_prodmerge_run_data_whatif(new_run):
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(f'''
            drop table if exists prodmerge_run_data_WHATIF;
            CREATE TABLE prodmerge_run_data_WHATIF AS
            SELECT * FROM prodmerge_run_data;
            
            INSERT INTO prodmerge_run_data_WHATIF (item_code, po_number, item_run_qty, run_time, id2, start_time, prod_line, item_description)
                VALUES ({new_run.item_code}, {new_run.po_number}, {new_run.item_quantity}, {new_run.run_time}, 0, {new_run.start_time}, {new_run.prod_line}, {new_run.item_description});
        ''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======prodmerge_run_data_WHATIF table created.=======')
    
    except Exception as e:
        print(str(e))

def create_component_usage_whatif_table():
    try:
        connection_postgres = psycopg2.connect(
                    'postgresql://postgres:blend2021@localhost:5432/blendversedb'
                    )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''create table component_usage_WHATIF as
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
                        or component_item_description LIKE 'BLISTER%'
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
                        OR component_item_code LIKE '089632PUN'
                    ORDER BY start_time, po_number;
                    update component_usage_WHATIF set run_component_qty = run_component_qty * 1.1 
                        where component_item_description like 'BLEND%' and procurement_type like 'M'
                        and prod_line not like 'Totes' and prod_line not like 'Dm'
                        and prod_line not like 'Hx' and prod_line not like 'Pails';
                    alter table component_usage_WHATIF add cumulative_component_run_qty numeric;
                    UPDATE component_usage_WHATIF AS cu1
                    SET cumulative_component_run_qty = (
                        SELECT SUM(cu2.run_component_qty)
                        FROM component_usage_WHATIF AS cu2
                        WHERE cu2.component_item_code = cu1.component_item_code AND cu2.start_time <= cu1.start_time);
                    alter table component_usage_WHATIF add component_onhand_after_run numeric;
                    UPDATE component_usage_WHATIF set component_onhand_after_run=component_on_hand_qty-cumulative_component_run_qty;
                    alter table component_usage_WHATIF add id serial primary key;
                    drop table if exists component_usage_WHATIF;''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======component_usage_WHATIF table created.=======')
    
    except Exception as e:
        print(str(e))

def create_component_shortages_whatif_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(f'''drop table if exists component_shortage_WHATIF;
                                    create table component_shortage_WHATIF as
                                    SELECT * FROM (SELECT *,
                                        ROW_NUMBER() OVER (PARTITION BY component_item_code
                                            ORDER BY start_time) AS component_instance_count
                                        FROM component_usage
                                        where component_onhand_after_run < 0
                                    ) AS subquery;
                                    alter table component_shortage_WHATIF
                                        add one_wk_short numeric, add two_wk_short numeric,
                                        add three_wk_short numeric, add total_shortage numeric,
                                        add unscheduled_short numeric, add last_txn_date date,
                                        add last_txn_code text, add last_count_quantity numeric,
                                        add last_count_date date;
                                    update component_shortage_WHATIF set total_shortage=((
                                        SELECT cumulative_component_run_qty from component_usage
                                        where component_usage.component_item_code=component_shortage_WHATIF.component_item_code
                                        order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_WHATIF set one_wk_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where start_time<40
                                            and component_usage.component_item_code=component_shortage_WHATIF.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_WHATIF 
                                        set one_wk_short = COALESCE(one_wk_short, 0)
                                        where one_wk_short is null;
                                    update component_shortage_WHATIF set two_wk_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where start_time<80 
                                            and component_usage.component_item_code=component_shortage_WHATIF.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_WHATIF 
                                        set two_wk_short = COALESCE(two_wk_short, 0)
                                        where two_wk_short is null;
                                    update component_shortage_WHATIF set three_wk_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where start_time<299
                                            and component_usage.component_item_code=component_shortage_WHATIF.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty);
                                    update component_shortage_WHATIF 
                                        set three_wk_short = COALESCE(three_wk_short, 0)
                                        where three_wk_short is null;
                                    update component_shortage_WHATIF set unscheduled_short=((
                                        select component_usage.cumulative_component_run_qty
                                            from component_usage where prod_line like 'UNSCHEDULED%'
                                            and component_usage.component_item_code=component_shortage_WHATIF.component_item_code
                                            order by start_time DESC LIMIT 1)-component_on_hand_qty)-three_wk_short;
                                    update component_shortage_WHATIF 
                                        set unscheduled_short = COALESCE(unscheduled_short, 0)
                                        where unscheduled_short is null;
                                    update component_shortage_WHATIF set one_wk_short=0 where one_wk_short<0;
                                        update component_shortage_WHATIF set two_wk_short=0 where two_wk_short<0;
                                        update component_shortage_WHATIF set three_wk_short=0 where three_wk_short<0;
                                        update component_shortage_WHATIF set unscheduled_short=0 where unscheduled_short<0;
                                    update component_shortage_WHATIF set last_txn_code=(select transactioncode 
                                        from im_itemtransactionhistory
                                        where im_itemtransactionhistory.itemcode=component_shortage_WHATIF.component_item_code 
                                        order by transactiondate DESC limit 1);
                                    update component_shortage_WHATIF set last_txn_date=(select transactiondate from im_itemtransactionhistory
                                        where im_itemtransactionhistory.itemcode=component_shortage_WHATIF.component_item_code 
                                        order by transactiondate DESC limit 1);
                                    update component_shortage_WHATIF set last_count_quantity=(select counted_quantity from core_blendcountrecord
                                        where core_blendcountrecord.item_code=component_shortage_WHATIF.component_item_code and core_blendcountrecord.counted=True 
                                        order by counted_date DESC limit 1);
                                    update component_shortage_WHATIF set last_count_date=(select counted_date from core_blendcountrecord
                                        where core_blendcountrecord.item_code=component_shortage_WHATIF.component_item_code and core_blendcountrecord.counted=True 
                                        order by counted_date DESC limit 1);
                                    alter table component_shortage_WHATIF add next_order_due date;
                                    update component_shortage_WHATIF set next_order_due=(
                                        SELECT requireddate from po_purchaseorderdetail
                                        where requireddate > '{three_days_ago}'
                                        and po_purchaseorderdetail.itemcode = component_shortage_WHATIF.component_item_code
                                        and po_purchaseorderdetail.quantityreceived = 0
                                        order by requireddate asc limit 1);
                                    alter table component_shortage_WHATIF add run_component_demand numeric;
                                    UPDATE component_shortage_WHATIF SET run_component_demand = CASE
                                        WHEN component_instance_count = 1 THEN (component_onhand_after_run * -1)
                                        ELSE run_component_qty
                                        END;''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======component_shortage table created.=======')

    except Exception as e:
        print(str(e))

def create_blend_subcomponent_usage_whatif_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute('''drop table if exists blend_subcomponent_usage_WHATIF;
                                    create table blend_subcomponent_usage_WHATIF as select * from(
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
                                    alter table blend_subcomponent_usage_WHATIF add subcomponent_run_qty numeric;
                                    update blend_subcomponent_usage_WHATIF 
                                        set subcomponent_run_qty = run_component_demand * qty_per_bill;
                                    alter table blend_subcomponent_usage_WHATIF add cumulative_subcomponent_run_qty numeric;
                                    update blend_subcomponent_usage_WHATIF as bsu1
                                        set cumulative_subcomponent_run_qty  = (
                                        SELECT SUM(bsu2.subcomponent_run_qty)
                                        FROM blend_subcomponent_usage_WHATIF AS bsu2
                                        WHERE bsu2.subcomponent_item_code = bsu1.subcomponent_item_code
                                        AND bsu2.start_time <= bsu1.start_time
                                    );
                                    alter table blend_subcomponent_usage_WHATIF 
                                        add subcomponent_onhand_after_run numeric;
                                    update blend_subcomponent_usage_WHATIF
                                        set subcomponent_onhand_after_run = (subcomponent_onhand_qty - cumulative_subcomponent_run_qty);
                                    alter table blend_subcomponent_usage_WHATIF add id serial primary key;
                                    ''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======subcomponent_usage table created.=======')
    
    except Exception as e:
        print(str(e))

def create_blend_subcomponent_shortage_whatif_table():
    try:
        connection_postgres = psycopg2.connect(
            'postgresql://postgres:blend2021@localhost:5432/blendversedb'
            )
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute(f'''
                                drop table if exists blend_subcomponent_shortage_WHATIF;
                                create table blend_subcomponent_shortage_WHATIF as SELECT * FROM 
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
                                alter table blend_subcomponent_shortage_WHATIF add max_possible_blend numeric;
                                update blend_subcomponent_shortage_WHATIF set max_possible_blend=0 
                                    where subcomponent_onhand_qty=0;
                                update blend_subcomponent_shortage_WHATIF 
                                    set max_possible_blend=subcomponent_onhand_qty/qty_per_bill
                                    where subcomponent_onhand_qty!=0;
                                alter table blend_subcomponent_shortage_WHATIF add next_order_due date;
                                update blend_subcomponent_shortage_WHATIF set next_order_due=(
                                    SELECT requireddate from po_purchaseorderdetail
                                    where requireddate > '{three_days_ago}'
                                    and po_purchaseorderdetail.itemcode = blend_subcomponent_shortage_WHATIF.subcomponent_item_code
                                    and po_purchaseorderdetail.quantityreceived = 0
                                    order by requireddate asc limit 1);
                                alter table blend_subcomponent_shortage_WHATIF
                                    add one_wk_short numeric, add two_wk_short numeric,
                                    add three_wk_short numeric, add total_short numeric,
                                    add unscheduled_short numeric;
                                update blend_subcomponent_shortage_WHATIF set total_short=(
                                    SELECT subcomponent_onhand_after_run from blend_subcomponent_usage
                                    where blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_WHATIF.subcomponent_item_code
                                    order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_WHATIF set one_wk_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where start_time>=0 and start_time<10
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_WHATIF.subcomponent_item_code
                                        order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_WHATIF set two_wk_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where start_time<20 
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_WHATIF.subcomponent_item_code
                                        order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_WHATIF set three_wk_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where start_time<299
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_WHATIF.subcomponent_item_code
                                        order by start_time DESC LIMIT 1);
                                update blend_subcomponent_shortage_WHATIF set one_wk_short = 0 where one_wk_short is null;
                                update blend_subcomponent_shortage_WHATIF set one_wk_short = 0 where one_wk_short > 0;
                                update blend_subcomponent_shortage_WHATIF set two_wk_short = 0 where two_wk_short is null and one_wk_short = 0;
                                update blend_subcomponent_shortage_WHATIF set two_wk_short = one_wk_short where two_wk_short is null and one_wk_short = 0;
                                update blend_subcomponent_shortage_WHATIF set two_wk_short = 0 where two_wk_short > 0;
                                update blend_subcomponent_shortage_WHATIF set three_wk_short = 0 where three_wk_short is null;
                                update blend_subcomponent_shortage_WHATIF set three_wk_short = 0 where three_wk_short > 0;
                                update blend_subcomponent_shortage_WHATIF set unscheduled_short=(
                                    select blend_subcomponent_usage.subcomponent_onhand_after_run
                                        from blend_subcomponent_usage where prod_line like 'UNSCHEDULED%'
                                        and blend_subcomponent_usage.subcomponent_item_code=blend_subcomponent_shortage_WHATIF.subcomponent_item_code
                                        order by start_time DESC LIMIT 1)-three_wk_short;
                                update blend_subcomponent_shortage_WHATIF set unscheduled_short = 0 where unscheduled_short is null;
                                alter table blend_subcomponent_shortage_WHATIF add id serial primary key;
                                ''')
        connection_postgres.commit()
        cursor_postgres.close()
        print(f'{dt.datetime.now()}=======subcomponent_shortage table created.====')

    except Exception as e:
        print(str(e))