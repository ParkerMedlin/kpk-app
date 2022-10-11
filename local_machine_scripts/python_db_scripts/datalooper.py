import time
from prod_sched_to_postgres import get_prod_schedule
import table_builder as f_tables
import chem_locations_to_postgres as f_chem_locations
import horix_sched_to_postgres as f_horix_schedule
import sage_to_postgres as f_sage
from multiprocessing import Process

def update_xlsb_tables():
    for retries in range(100):
        for attempt in range(10):
            try:
                while True:
                    get_prod_schedule()
                    f_tables.create_tables()
                    f_chem_locations.get_chem_locations()
                    f_horix_schedule.get_horix_line_blends()
                    print('oh boy here I go again')
            except:
                print("well well well, looks like we need to take a breaky wakey")
                time.sleep(10)
            else:
                break
        else:
            print("we should try taking a longer break, gonna wait for 1 minute then try again")
            time.sleep(60)

def get_bmbilldetail():
    while True:
            f_sage.get_sage_table('BM_BillDetail')

def get_bmbillheader():
    while True:
        f_sage.get_sage_table('BM_BillHeader')

def get_ciitem():
    while True:
        f_sage.get_sage_table('CI_Item')

def get_imitemcost():
    while True:
        f_sage.get_sage_table('IM_ItemCost')

def get_imitemtransactionhistory():
    while True:
        f_sage.get_sage_table('IM_ItemTransactionHistory')

def get_imitemwarehouse():
    while True:
        f_sage.get_sage_table('IM_ItemWarehouse')

def get_popurchaseorderdetail():
    while True:
        f_sage.get_sage_table('PO_PurchaseOrderDetail')

if __name__ == '__main__':
    Process(target=update_xlsb_tables).start()
    Process(target=get_bmbilldetail).start()
    Process(target=get_bmbillheader).start()
    Process(target=get_ciitem).start()
    Process(target=get_imitemcost).start()
    Process(target=get_imitemtransactionhistory).start()
    Process(target=get_imitemwarehouse).start()
    Process(target=get_popurchaseorderdetail).start()