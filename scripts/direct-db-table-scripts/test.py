import pandas as pd
from sqlalchemy import create_engine
import psycopg2


cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
curs1 = cnxnPG.cursor()





curs1.execute('select distinct blendthese.blend_pn from blendthese')
tuplelist = curs1.fetchall()
pnlist = []
inc=0
for thistuple in tuplelist:
    pnlist.append(thistuple[0])
    inc+=1
pndict = dict.fromkeys(pnlist, '') # make a dict whose keys are all the diff part numbers needed
pndictonewk = pndict
pndicttwowk = pndict
pndictthreewk = pndict
alchemyEngine = create_engine('postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb', pool_recycle=3600) 
dbConnection = alchemyEngine.connect()
ttableDF = pd.read_sql('select blend_pn, adjustedrunqty, week_calc from timetable_run_data', dbConnection)
pd.set_option('display.expand_frame_repr', False)
onewkDF = ttableDF[ttableDF.week_calc.isin([2.0,3.0]) == False]
twowkDF = ttableDF[ttableDF.week_calc.isin([3.0]) == False]
threewkDF = ttableDF
for thispn in pnlist:
    filtonewkDF = onewkDF.loc[onewkDF['blend_pn'] == thispn]
    totalblendqty = filtonewkDF['adjustedrunqty'].sum()
    pndictonewk[thispn] = totalblendqty
for thispn in pnlist:
    filttwowkDF = onewkDF.loc[onewkDF['blend_pn'] == thispn]
    totalblendqty = filttwowkDF['adjustedrunqty'].sum()
    pndicttwowk[thispn] = totalblendqty
for thispn in pnlist:
    filtthreewkDF = onewkDF.loc[onewkDF['blend_pn'] == thispn]
    totalblendqty = filtthreewkDF['adjustedrunqty'].sum()
    pndictthreewk[thispn] = totalblendqty

for thisblend_pn in pnlist:
    curs1.execute('update blendthese set one_wk_short=69 where blend_pn="'+thisblend_pn'"')




cnxnPG.commit()
curs1.close()
cnxnPG.close()