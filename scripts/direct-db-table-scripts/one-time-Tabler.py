import AllSagetoPostgres as fSage
import ProdMergetoPostgres as fProdMerge
import TablesConstruction as fTables
import ChemLoctoPostgres as fChemLoc
import subprocess

fSage.GetLatestSage()
fProdMerge.GetLatestProdMerge()
fTables.BuildTables()
fChemLoc.GetChemLocations()

subprocess.call([r'C:\Users\pmedlin\Desktop\kpk-app\scripts\batch-scripts\importsAnd_d-c-UP.bat'])