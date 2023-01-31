import psycopg2

#connect to the database
cnxnPG = psycopg2.connect(
            host = "localhost",
            database = "blendversedb",
            user = "postgres",
            password = "blend2021")

#cursor
cursPG = cnxnPG.cursor()

cursPG.execute("create table if not exists blending_procedures (id serial unique, item_code varchar(40) not null, status text, step_no int, step_desc text, component_code text, component_item_desc text)")
with open('C:\Users\pmedlin\Documents\Programming-Experiments\Blendverse-App\BlendverseApp\\blendverseApp\\actualData\\blendInstructions.csv', 'r') as f:
    next(f) # Skip the header row.
    #f , <database name>, Comma-Seperated
    cursPG.copy_from(f, 'blendInstructions', sep=',')
    #Commit Changes
    cnxnPG.commit()
    #Close connections
    f.close()
    cursPG.close()
    cnxnPG.close()