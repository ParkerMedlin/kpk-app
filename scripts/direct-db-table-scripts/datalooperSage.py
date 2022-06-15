import time
import AllSagetoPostgres as fSage
import ProdMergetoPostgres as fProdMerge
import TablesConstruction as fTables

while(True):
    fSage.GetLatestSage()
    print("Dormammu, I've come to bargain")