from __future__ import generators
import psycopg2 # connect w postgres db
import pandas as pd # needed for dataframes
from art import *
import time

surprise()
t1 = time.perf_counter()

### CREATE THE BILL_OF_MATERIALS TABLE ###
cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
bomcursorPG = cnxnPG.cursor()
bomcursorPG.execute('drop table if exists bill_of_materials')
bomcursorPG.execute('''CREATE TABLE bill_of_materials as
                        select distinct Bm_BillDetail.billno AS bill_pn,
                            ci_item.itemcode as component_itemcode,
                            ci_item.itemcodedesc as component_desc,
                            core_foamfactor.factor AS foam_factor,
                            ci_item.StandardUnitOfMeasure AS standard_uom,
                            bm_billdetail.quantityperbill as qtyperbill,
                            ci_item.shipweight as weightpergal,
                            im_itemwarehouse.QuantityOnHand AS unadjusted_qtyonhand
                        FROM ci_item AS ci_item
                        JOIN Bm_BillDetail Bm_BillDetail ON ci_item.itemcode=Bm_BillDetail.componentitemcode
                        left join core_foamfactor core_foamfactor on ci_item.itemcode=core_foamfactor.blend
                        left join im_itemwarehouse im_itemwarehouse on ci_item.itemcode=im_itemwarehouse.itemcode and im_itemwarehouse.warehousecode = 'MTG'
                        where ci_item.itemcodedesc like 'CHEM -%' 
                            or ci_item.itemcodedesc like 'BLEND-%' 
                            or ci_item.itemcodedesc like 'FRAGRANCE%' 
                            or ci_item.itemcodedesc like 'DYE%'
                        order by bill_pn'''
                        )
bomcursorPG.execute('alter table bill_of_materials add hundred_gx smallint;')
bomcursorPG.execute('alter table bill_of_materials add adjusted_qtyonhand numeric;')
bomcursorPG.execute("update bill_of_materials set hundred_gx=100 where standard_uom='100G';")
bomcursorPG.execute("update bill_of_materials set hundred_gx=1 where standard_uom!='100G';")
bomcursorPG.execute("update bill_of_materials set adjusted_qtyonhand=hundred_gx*unadjusted_qtyonhand;")
bomcursorPG.execute("update bill_of_materials set foam_factor=1 where foam_factor IS NULL;") 
cnxnPG.commit()
bomcursorPG.close()


### CREATE THE BLENDDATA TABLE ###
blenddatacursorPG = cnxnPG.cursor()
blenddatacursorPG.execute('drop table if exists blend_run_data')
blenddatacursorPG.execute('''create table blend_run_data as
                            select distinct prodmerge_run_data.p_n as bill_pn,
                            bill_of_materials.component_itemcode as blend_pn,
                            bill_of_materials.component_desc as blend_desc,
                            prodmerge_run_data.qty as unadjusted_runqty,
                            bill_of_materials.foam_factor as foam_factor,
                            bill_of_materials.hundred_gx as hundred_gx,
                            bill_of_materials.qtyperbill as qtyperbill,
                            bill_of_materials.adjusted_qtyonhand as qtyonhand,
                            prodmerge_run_data.runtime as runtime,
                            prodmerge_run_data.starttime as starttime,
                            prodmerge_run_data.prodline as prodline
                        from prodmerge_run_data as prodmerge_run_data
                        join bill_of_materials bill_of_materials on prodmerge_run_data.p_n=bill_of_materials.bill_pn
                        order by starttime'''
                        )
blenddatacursorPG.execute('alter table blend_run_data add adjustedrunqty numeric;')
blenddatacursorPG.execute('update blend_run_data set adjustedrunqty=(unadjusted_runqty*1.1*foam_factor*hundred_gx*qtyperbill)')
cnxnPG.commit()
blenddatacursorPG.close()


### CREATE THE TIMETABLE TABLE ###
ttablecursorPG = cnxnPG.cursor()
ttablecursorPG.execute('drop table if exists timetable_run_data')
ttablecursorPG.execute('''create table timetable_run_data as
                        select bill_pn, blend_pn, blend_desc, adjustedrunqty, qtyonhand, starttime, prodline,
                            qtyonhand-sum(adjustedrunqty) over (partition by blend_pn order by starttime) as oh_after_run 
                        from blend_run_data
                        order by starttime'''
                        )
cnxnPG.commit()
ttablecursorPG.close()


### CREATE THE ISSUESHEETNEEDED TABLE ###
isn_tablecursorPG = cnxnPG.cursor()
isn_tablecursorPG.execute('drop table if exists issue_sheet_needed')
isn_tablecursorPG.execute('''create table issue_sheet_needed as
                        select * from timetable_run_data where starttime < 20
                        order by prodline, starttime'''
                        )
isn_tablecursorPG.execute('''alter table issue_sheet_needed add batchnum1 text, add batchqty1 text, 
                        add batchnum2 text, add batchqty2 text,
                        add batchnum3 text, add batchqty3 text,
                        add batchnum4 text, add batchqty4 text,
                        add batchnum5 text, add batchqty5 text,
                        add batchnum6 text, add batchqty6 text;'''
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
    batchnumlist = ['n/a','n/a','n/a','n/a','n/a','n/a']
    batchqtylist = ['n/a','n/a','n/a','n/a','n/a','n/a']
    listpos = 0
    for batchtuple in batchtuples:
        batchnumlist[listpos] = batchtuple[0]
        batchqtylist[listpos] = str(batchtuple[1])
        listpos+=1
    counter = 1
    print(batchnumlist)
    print(batchqtylist)
    batchnumstring = 'batchnum'
    batchqtystring = 'batchqty'
    for counter in range(6):
        batchnumstring+=str(counter+1)
        batchqtystring+=str(counter+1)
        batchcursorPG.execute("update issue_sheet_needed set "+batchnumstring+"='"+batchnumlist[counter]+"' where blend_pn='"+blendpn+"'")
        batchcursorPG.execute("update issue_sheet_needed set "+batchqtystring+"='"+batchqtylist[counter]+"' where blend_pn='"+blendpn+"'")
        batchnumstring = 'batchnum'
        batchqtystring = 'batchqty'
batchcursorPG.close()



cnxnPG.close()
t2 = time.perf_counter()
print(f'Complete in {t2 - t1:0.4f} seconds','world record prolly')