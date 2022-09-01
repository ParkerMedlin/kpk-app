import time
from prod_sched_to_postgres import get_prod_schedule
import table_builder as f_tables
import chem_locations_to_postgres as f_chem_locations
import horix_sched_to_postgres as f_horix_schedule

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