import time
import ProdMergetoPostgres as fProdMerge
import TablesConstruction as fTables

for retries in range(100):
    for attempt in range(10):
        try:
            while(True):
                fProdMerge.GetLatestProdMerge()
                fTables.BuildTables()
                print('oh boy here I go again')
        except:
            print("well well well, looks like we need to take a breaky wakey")
            time.sleep(10)
        else:
            break
    else:
        print("we should try taking a longer break, gonna wait for 1 minute then try again")
        time.sleep(60)