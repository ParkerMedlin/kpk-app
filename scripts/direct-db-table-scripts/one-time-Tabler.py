import AllSagetoPostgres as fSage
import ProdMergetoPostgres as fProdMerge
import TablesConstruction as fTables
import ChemLoctoPostgres as fChemLoc
import subprocess

tblList = ['BM_BillHeader', 'BM_BillDetail', 'CI_Item', 'IM_ItemWarehouse', 'IM_ItemCost', 'IM_ItemTransactionHistory', 'PO_PurchaseOrderDetail']
for item in tblList:
    fSage.GetSageTable(item)
fProdMerge.GetLatestProdMerge()
fTables.BuildTables()
fChemLoc.GetChemLocations() 

subprocess.call([r'.\scripts\batch-scripts\importsAnd_d-c-UP.bat'])

subprocess.call([r'.\scripts\batch-scripts\userSetup.bat'])