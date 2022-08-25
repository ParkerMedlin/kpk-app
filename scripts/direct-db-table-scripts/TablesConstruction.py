from __future__ import generators
import psycopg2 # connect w postgres db
import pandas as pd # needed for dataframes
from art import *
import time
from sqlalchemy import create_engine

def BuildTables():
    print('BuildTables():')
    t1 = time.perf_counter()

    ### CREATE THE blend_BILL_OF_MATERIALS TABLE ###
    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    bomcursorPG = cnxnPG.cursor()
    bomcursorPG.execute('''CREATE TABLE blend_bill_of_materials_TEMP as
                            select distinct Bm_BillDetail.billno AS bill_pn,
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
                            left join im_itemwarehouse im_itemwarehouse on ci_item.itemcode=im_itemwarehouse.itemcode and im_itemwarehouse.warehousecode = 'MTG'
                            left join bm_billheader bm_billheader on ci_item.itemcode=bm_billheader.billno
                            where ci_item.itemcodedesc like 'CHEM -%' 
                                or ci_item.itemcodedesc like 'BLEND-%' 
                                or ci_item.itemcodedesc like 'FRAGRANCE%' 
                                or ci_item.itemcodedesc like 'DYE%'
                            order by bill_pn'''
                            )
    bomcursorPG.execute('alter table blend_bill_of_materials_TEMP add id serial primary key;')                        
    bomcursorPG.execute('alter table blend_bill_of_materials_TEMP add bill_desc text;')
    bomcursorPG.execute('update blend_bill_of_materials_TEMP set bill_desc=(select ci_item.itemcodedesc from ci_item where blend_bill_of_materials_TEMP.bill_pn=ci_item.itemcode);')
    bomcursorPG.execute("update blend_bill_of_materials_TEMP set foam_factor=1 where foam_factor IS NULL;")
    bomcursorPG.execute('drop table if exists blend_bill_of_materials')
    bomcursorPG.execute('alter table blend_bill_of_materials_TEMP rename to blend_bill_of_materials')
    bomcursorPG.execute('drop table if exists blend_bill_of_materials_TEMP')
    cnxnPG.commit()
    bomcursorPG.close()

     ### CREATE THE prod_BILL_OF_MATERIALS TABLE ###
    cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    prodbomcursorPG = cnxnPG.cursor()
    prodbomcursorPG.execute('''CREATE TABLE prod_bill_of_materials_TEMP as
                            SELECT BM_BillDetail.BillNo, 
                            BM_BillHeader.BillDesc1, 
                            BM_BillDetail.ComponentItemCode, 
                            CI_Item.ItemCodeDesc, 
                            BM_BillDetail.QuantityPerBill, 
                            BM_BillDetail.ScrapPercent, 
                            CI_Item.ProcurementType, 
                            CI_Item.StandardUnitofMeasure, 
                            BM_BillDetail.CommentText 
                            FROM BM_BillDetail BM_BillDetail, BM_BillHeader BM_BillHeader, CI_Item CI_Item
                            WHERE BM_BillDetail.BillNo = BM_BillHeader.BillNo 
                            AND BM_BillDetail.Revision = BM_BillHeader.Revision 
                            AND BM_BillDetail.ComponentItemCode = CI_Item.ItemCode 
                            AND ((CI_Item.ItemCodeDesc Not Like '...%') 
                            AND (BM_BillDetail.ComponentItemCode Not Like '/__%'))'''
                            )
    prodbomcursorPG.execute("update prod_bill_of_materials_TEMP set ItemCodeDesc=CommentText where ItemCodeDesc='Default Item Code /C'")
    prodbomcursorPG.execute('drop table if exists prod_bill_of_materials')
    prodbomcursorPG.execute('alter table prod_bill_of_materials_TEMP rename to prod_bill_of_materials')
    prodbomcursorPG.execute('drop table if exists prod_bill_of_materials_TEMP')
    cnxnPG.commit()
    prodbomcursorPG.close()


    ### CREATE THE BLEND_RUN_DATA TABLE ###
    blenddatacursorPG = cnxnPG.cursor()
    blenddatacursorPG.execute('''create table blend_run_data_TEMP as
                                select distinct prodmerge_run_data.p_n as bill_pn,
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
                            join blend_bill_of_materials blend_bill_of_materials on prodmerge_run_data.p_n=blend_bill_of_materials.bill_pn and procurementtype='M'
                            order by starttime'''
                            )
    blenddatacursorPG.execute('alter table blend_run_data_TEMP add id serial primary key;')
    blenddatacursorPG.execute('alter table blend_run_data_TEMP add adjustedrunqty numeric;')
    blenddatacursorPG.execute('update blend_run_data_TEMP set adjustedrunqty=(unadjusted_runqty*1.1*foam_factor*qtyperbill)')
    blenddatacursorPG.execute('drop table if exists blend_run_data')
    blenddatacursorPG.execute('alter table blend_run_data_TEMP rename to blend_run_data')
    blenddatacursorPG.execute('drop table if exists blend_run_data_TEMP')
    cnxnPG.commit()
    blenddatacursorPG.close()


    ### CREATE THE TIMETABLE_RUN_DATA TABLE ###
    ttablecursorPG = cnxnPG.cursor()
    ttablecursorPG.execute('''create table timetable_run_data_TEMP as
                            select id2, bill_pn, blend_pn, blend_desc, adjustedrunqty, qtyonhand, starttime, prodline,
                                qtyonhand-sum(adjustedrunqty) over (partition by blend_pn order by starttime) as oh_after_run 
                            from blend_run_data
                            order by starttime''')
    ttablecursorPG.execute('alter table timetable_run_data_TEMP add week_calc numeric;')
    ttablecursorPG.execute('''update timetable_run_data_TEMP set week_calc=
                            case
                                when starttime<40 then 1
                                when starttime>80 then 3
                                else 2
                            end''')
    ttablecursorPG.execute('alter table timetable_run_data_TEMP add id serial primary key')
    ttablecursorPG.execute('drop table if exists timetable_run_data')
    ttablecursorPG.execute('alter table timetable_run_data_TEMP rename to timetable_run_data')
    ttablecursorPG.execute('drop table if exists timetable_run_data_TEMP')
    cnxnPG.commit()
    ttablecursorPG.close()




    ### CREATE THE ISSUESHEETNEEDED TABLE ###
    isn_tablecursorPG = cnxnPG.cursor()
    isn_tablecursorPG.execute('drop table if exists issue_sheet_needed_TEMP')
    isn_tablecursorPG.execute('''create table issue_sheet_needed_TEMP as
                            select * from timetable_run_data where starttime < 20
                            order by prodline, starttime'''
                            )
    isn_tablecursorPG.execute('''alter table issue_sheet_needed_TEMP add batchnum1 text, add batchqty1 text, 
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
    cnxnPG.commit()
    isn_tablecursorPG.close()
    ### fill in the batch numbers and batch quantities on issue sheet table ###
    ttableblendscursorPG = cnxnPG.cursor()
    ttableblendscursorPG.execute("select blend_pn from timetable_run_data")
    blendpntuples = ttableblendscursorPG.fetchall()
    ttableblendscursorPG.close()
    blendpnlist = []
    for blendtuple in blendpntuples:
        blendpnlist.append(blendtuple[0])
    print(blendpnlist)
    batchcursorPG = cnxnPG.cursor()
    for blendpn in blendpnlist:
        batchcursorPG.execute("select receiptno, quantityonhand from im_itemcost where itemcode='"+blendpn+"'and quantityonhand!=0 and receiptno ~ '^[A-Z].*$' order by receiptdate")
        cnxnPG.commit()
        batchtuples = batchcursorPG.fetchall()
        batchnumlist = ['n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a']
        batchqtylist = ['n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a','n/a']
        listpos = 0
        for batchtuple in batchtuples:
            batchnumlist[listpos] = batchtuple[0]
            batchqtylist[listpos] = str(round(batchtuple[1],0))
            listpos+=1
        counter = 1
        batchnumstring = 'batchnum'
        batchqtystring = 'batchqty'
        for counter in range(9):
            batchnumstring+=str(counter+1)
            batchqtystring+=str(counter+1)
            batchcursorPG.execute("update issue_sheet_needed_TEMP set "+batchnumstring+"='"+batchnumlist[counter]+"' where blend_pn='"+blendpn+"'")
            batchcursorPG.execute("update issue_sheet_needed_TEMP set "+batchqtystring+"='"+batchqtylist[counter]+"' where blend_pn='"+blendpn+"'")
            batchnumstring = 'batchnum'
            batchqtystring = 'batchqty'
    cnxnPG.commit()
    batchcursorPG.close()
    ### POPULATE THE UNIQCHEK COLUMN ###
    uniqcursorPG = cnxnPG.cursor()
    uniqcursorPG.execute("update issue_sheet_needed_TEMP set uniqchek=concat(prodline, blend_pn)")
    uniqcursorPG.execute('drop table if exists issue_sheet_needed')
    uniqcursorPG.execute('alter table issue_sheet_needed_TEMP rename to issue_sheet_needed')
    uniqcursorPG.execute('drop table if exists issue_sheet_needed_TEMP')
    cnxnPG.commit()
    uniqcursorPG.close()


    ### CREATE THE BLENDTHESE TABLE ###
    blendthesecursor = cnxnPG.cursor()
    blendthesecursor.execute('create table blendthese_TEMP as select * from timetable_run_data trd where oh_after_run < 0')
    blendthesecursor.execute('''DELETE FROM blendthese_TEMP a USING blendthese_TEMP b
                                WHERE a.id > b.id AND a.blend_pn = b.blend_pn;''') # delete the duplicates
    blendthesecursor.execute('alter table blendthese_TEMP add one_wk_short numeric, add two_wk_short numeric, add three_wk_short numeric;')
    cnxnPG.commit()
    blendthesecursor.close()
    ### SET ALL SHORTAGE VALUES FOR THE BLENDTHESE TABLE ###
    blendthesevalscursor = cnxnPG.cursor()
    blendthesevalscursor.execute('select distinct blendthese_TEMP.blend_pn from blendthese_TEMP')
    tuplelist = blendthesevalscursor.fetchall()
    pnlist = [] # list of all part numbers found in blendthese
    inc=0
    for thistuple in tuplelist: # populate the pnlist
        pnlist.append(thistuple[0])
        inc+=1
    alchemyEngine = create_engine('postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb', pool_recycle=3600) 
    dbConnection = alchemyEngine.connect() # connection so we can read the table to a dataframe
    ttableDF = pd.read_sql('select blend_pn, adjustedrunqty, oh_after_run, week_calc from timetable_run_data where oh_after_run<0', dbConnection)
    pd.set_option('display.expand_frame_repr', False)
    onewkDF = ttableDF[ttableDF.week_calc.isin([2.0,3.0]) == False] # dataframe containing all 1week runs that will be short
    twowkDF = ttableDF[ttableDF.week_calc.isin([3.0]) == False] # dataframe containing all 2week runs that will be short
    threewkDF = ttableDF # dataframe containing all 3week runs that will be short
    for thispn in pnlist: # for each week's dataframe, filter by partnumber and then take the oh_after_run of the LAST instance in the dataframe
        filtonewkDF = onewkDF.loc[onewkDF['blend_pn'] == thispn]
        if len(filtonewkDF) == 0:
            totalonewkblendqty = 0
        else: 
            totalonewkblendqty =  filtonewkDF.iloc[-1,2] * -1
        blendthesevalscursor.execute("update blendthese_TEMP set one_wk_short="+"'"+str(totalonewkblendqty)+"'"+" where blend_pn="+"'"+thispn+"'")
        filttwowkDF = twowkDF.loc[twowkDF['blend_pn'] == thispn]
        if len(filttwowkDF) == 0:
            totaltwowkblendqty = 0
        else: 
            totaltwowkblendqty =  filttwowkDF.iloc[-1,2] * -1
        blendthesevalscursor.execute("update blendthese_TEMP set two_wk_short="+"'"+str(totaltwowkblendqty)+"'"+" where blend_pn="+"'"+thispn+"'")
        filtthreewkDF = threewkDF.loc[threewkDF['blend_pn'] == thispn]
        if len(filtthreewkDF) == 0:
            totalthreewkblendqty = 0
        else: 
            totalthreewkblendqty = filtthreewkDF.iloc[-1,2] * -1
        threewkquerystr = "update blendthese_TEMP set three_wk_short="+"'"+str(totalthreewkblendqty)+"'"+" where blend_pn="+"'"+thispn+"'"
        blendthesevalscursor.execute(threewkquerystr)
    blendthesevalscursor.execute('drop table if exists blendthese')
    blendthesevalscursor.execute('alter table blendthese_TEMP rename to blendthese')
    blendthesevalscursor.execute('drop table if exists blendthese_TEMP')
    cnxnPG.commit()
    blendthesevalscursor.close()


    ### BUILD THE BLENDCOUNTS TABLE ###
    upcomingblndctscursor = cnxnPG.cursor()
    upcomingblndctscursor.execute('drop table if exists upcoming_blend_count_TEMP')
    upcomingblndctscursor.execute('''create table upcoming_blend_count_TEMP as 
                                select timetable_run_data.blend_pn as blend_pn,
                                    timetable_run_data.blend_desc as blend_desc, 
                                    timetable_run_data.qtyonhand as expected_on_hand,
                                    timetable_run_data.starttime as starttime,
                                    timetable_run_data.prodline as prodline
                                from timetable_run_data as timetable_run_data 
                                ''')
    upcomingblndctscursor.execute('alter table upcoming_blend_count_TEMP add column id serial primary key') # create id column to track which duplicate gets kept when deleting duplicates 
    upcomingblndctscursor.execute('''DELETE FROM upcoming_blend_count_TEMP a USING upcoming_blend_count_TEMP b
                                WHERE a.id > b.id AND a.blend_pn = b.blend_pn;''') # delete the duplicates
    upcomingblndctscursor.execute('drop table if exists upcoming_blend_count')
    upcomingblndctscursor.execute('alter table upcoming_blend_count_TEMP rename to upcoming_blend_count')
    cnxnPG.commit()
    upcomingblndctscursor.close()


    cnxnPG.close()
    t2 = time.perf_counter()
    print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')