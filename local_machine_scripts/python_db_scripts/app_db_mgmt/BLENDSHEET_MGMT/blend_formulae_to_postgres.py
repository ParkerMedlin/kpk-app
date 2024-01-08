import os
import shutil
import pandas as pd
import datetime as dt
from datetime import datetime
from sqlalchemy import create_engine
import psycopg2

def copy_formula_file():
    formula_file = "U:/qclab/Formulation/Quality Master.xlsm"
    destination = os.getcwd()  # get current working directory
    shutil.copy(formula_file, destination)  # copy the file

    copied_file_path = os.path.join(destination, os.path.basename(formula_file))
    return copied_file_path

def copy_formulae_to_postgres():
    source_file_path = copy_formula_file()
    sheet_df = pd.read_excel(source_file_path, 'Log - Formula', usecols = 'A:I')
    sheet_df['Date'] = sheet_df['Date'].fillna(0)
    sheet_df['Date'] = pd.to_datetime(sheet_df['Date'], errors='coerce')

    alchemy_engine = create_engine(
            'postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb',
            pool_recycle=3600
            )
    
    # Write the DataFrame to a CSV file on your desktop
    # sheet_df.to_csv(os.path.expanduser('~/Desktop/sheet_df.csv'), index=False)
    
    sheet_df.rename(columns={'Product Density (lb/gal)': 'product_density'}, inplace=True)
    sheet_df.rename(columns={'w/w': 'percent_weight_of_total'}, inplace=True)
    sheet_df.rename(columns={'Item': 'component_item_code'}, inplace=True)
    sheet_df.columns = sheet_df.columns.str.lower().str.replace(' ', '_')
    sheet_df.to_sql(name='blend_formula_component_temp', con=alchemy_engine, if_exists='replace', index=False)

    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("""drop table if exists blend_formula_component;
                                alter table blend_formula_component_temp rename to blend_formula_component;  
                                drop table if exists blend_formula_component_temp;
                                alter table blend_formula_component add column id serial primary key;
                            """)
    
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    os.remove(source_file_path)

# copy_formulae_to_postgres()
def write_unmatched_rows_to_csv():
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()

    cursor_postgres.execute("SELECT itemcode FROM ci_item")
    itemcodes = [item[0] for item in cursor_postgres.fetchall()]

    # Convert itemcodes to a tuple to use in the SQL query
    itemcodes_tuple = tuple(itemcodes)
    
    # Select rows from core_blendinstruction where component_item_code is not in itemcodes
    # and component_item_code is not "WATER" or an empty string
    query = f"""
    SELECT * FROM core_blendinstruction 
    WHERE component_item_code NOT IN {itemcodes_tuple} 
    AND component_item_code != 'WATER' 
    AND component_item_code != ''
    """
    unmatched_rows_df = pd.read_sql_query(query, connection_postgres)

    # Print unique blend_item_code values
    unique_blend_item_codes = unmatched_rows_df['blend_item_code'].unique()
    print(unique_blend_item_codes)

    # Write the DataFrame to a CSV file
    unmatched_rows_df.to_csv(os.path.expanduser('~\\Documents\\unmatched_rows.csv'), index=False)

    cursor_postgres.close()
    connection_postgres.close()

# write_unmatched_rows_to_csv()

def write_unmatched_from_csv():
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()

    cursor_postgres.execute("SELECT itemcode FROM ci_item")
    itemcodes = [item[0] for item in cursor_postgres.fetchall()]

    column_names = ['step_description', 'nothin', 'component_item_code', 'step_number', 'blend_item_code', 'trimm']
    # Read the CSV file
    df = pd.read_csv(os.path.expanduser('~/Desktop/blendinstructions.csv'), header=None, names=column_names)
    # print(df)
    # Drop NA in column 'component_item_code'
    df = df.dropna(subset=['component_item_code'])
    list_of_approved_values = ['WATER', '100507TANKO', '030146P', 'Q601013PA', '030008CN', '100421G2', '100507TANKB', '100507TANKD', '100428M6', '050000G', '100433CONS']
    for index, row in df.iterrows():
        if not row['component_item_code'] in list_of_approved_values and len(str(row['component_item_code'])) != 6:
            print(row['component_item_code'] + ' ' + row['blend_item_code'])

    # Convert column 'D' to a list

    # # Print unique blend_item_code values
    # unique_blend_item_codes = unmatched_rows_df['blend_item_code'].unique()
    # print(unique_blend_item_codes)

    # # Write the DataFrame to a CSV file
    # unmatched_rows_df.to_csv(os.path.expanduser('~\\Documents\\unmatched_rows.csv'), index=False)

    cursor_postgres.close()
    connection_postgres.close()
# write_unmatched_from_csv()


def get_item_codes_of_interest():
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()

    cursor_postgres.execute("""SELECT component_item_code FROM core_blendinstruction 
                            where length(component_item_code) > 6 
                            and component_item_code not in ('WATER', '100507TANKO', '030146P', 'Q601013PA', '030008CN', '100421G2', '100507TANKB', '100507TANKD', '100428M6', '050000G', '100433CONS')""")
    itemcodes = [item[0] for item in cursor_postgres.fetchall()]
    for item in itemcodes:
        print(item)

    cursor_postgres.close()
    connection_postgres.close()
get_item_codes_of_interest()

