import psycopg2
import csv

csvPathStr = r'C:\Users\pmedlin\Documents\Programming-Experiments\Blendverse-App\BlendverseApp\blendverseApp\actualData\blendInstructions.csv'
tblName = 'blendInstructions'

with open(csvPathStr) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter = ',')
    list = []
    for row in csv_reader:
        list.append(row)
        break

list_of_column_names = list[0]    

dHeadLwithTypes = '('
for i in range(len(list_of_column_names)):
    if list_of_column_names[i] == 'id':
        dHeadLwithTypes += list_of_column_names[i]+' serial primary key, '
    else:
        dHeadLwithTypes += list_of_column_names[i]+' text, '
dHeadLwithTypes = dHeadLwithTypes[:len(dHeadLwithTypes)-2] + ')'

### PSYCO CONNECTION TO PUSH THE DATA TO POSTGRES TABLE ###
cnxnPG = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
cursPG = cnxnPG.cursor()

cursPG.execute("DROP TABLE IF EXISTS "+tblName)
cursPG.execute("CREATE TABLE "+tblName+dHeadLwithTypes)
copy_sql = "COPY "+tblName+" FROM stdin WITH CSV HEADER DELIMITER as ','"

with open(csvPathStr, 'r', encoding='utf-8') as f:
    cursPG.copy_expert(sql=copy_sql, file=f)

cnxnPG.commit()
cursPG.close()
cnxnPG.close()