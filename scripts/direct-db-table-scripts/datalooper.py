import time
import ProdMergetoPostgres as fProdMerge
import TablesConstruction as fTables

while(True):
    fProdMerge.GetLatestProdMerge()
    fTables.BuildTables()
    print('oh boy here I go again')