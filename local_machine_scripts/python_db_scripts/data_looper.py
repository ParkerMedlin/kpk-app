import time
from app_db_mgmt import prod_sched_to_postgres as prod_sched_pg
from app_db_mgmt import sage_to_postgres as sage_pg
from app_db_mgmt import horix_sched_to_postgres as horix_pg
from app_db_mgmt import chem_locations_to_postgres as chem_loc_pg
from app_db_mgmt import table_builder as calc_tables_pg

from multiprocessing import Process

def update_xlsb_tables():
    for retries in range(100):
        for attempt in range(10):
            try:
                while True:
                    prod_sched_pg.get_prod_schedule()
                    calc_tables_pg.create_tables()
                    chem_loc_pg.get_chem_locations()
                    horix_pg.get_horix_line_blends()
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
        sage_pg.get_sage_table('BM_BillDetail')

def get_bmbillheader():
    while True:
        sage_pg.get_sage_table('BM_BillHeader')

def get_ciitem():
    while True:
        sage_pg.get_sage_table('CI_Item')

def get_imitemcost():
    while True:
        sage_pg.get_sage_table('IM_ItemCost')

def get_imitemtransactionhistory():
    while True:
        sage_pg.get_sage_table('IM_ItemTransactionHistory')

def get_imitemwarehouse():
    while True:
        sage_pg.get_sage_table('IM_ItemWarehouse')

def get_popurchaseorderdetail():
    while True:
        sage_pg.get_sage_table('PO_PurchaseOrderDetail')

if __name__ == '__main__':
    Process(target=update_xlsb_tables).start()
    Process(target=get_bmbilldetail).start()
    Process(target=get_bmbillheader).start()
    Process(target=get_ciitem).start()
    Process(target=get_imitemcost).start()
    Process(target=get_imitemtransactionhistory).start()
    Process(target=get_imitemwarehouse).start()
    Process(target=get_popurchaseorderdetail).start()