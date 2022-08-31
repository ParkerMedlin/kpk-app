import sage_to_postgres as fSage
import prod_sched_to_postgres as fProdMerge
import table_builder as fTables
import ChemLoctoPostgres as fChemLoc
import horix_sched_to_postgres as fHxBlend
import subprocess

# table_list = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
# for item in table_list:
#     fSage.get_sage_table(item)

# fProdMerge.get_prod_schedule()
fTables.create_tables()
# fChemLoc.GetChemLocations()
# fHxBlend.get_horix_line_blends()

# subprocess.call([r'.\scripts\batch-scripts\importsAnd_d-c-UP.bat'])

# subprocess.call([r'.\scripts\batch-scripts\userSetup.bat'])