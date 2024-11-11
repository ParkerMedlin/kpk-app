import pandas as pd 
import os
import psycopg2
from .sharepoint_download import download_to_temp
import time
import warnings
import numpy as np
import datetime as dt
from datetime import datetime
warnings.filterwarnings("ignore")
from sqlalchemy import create_engine
import pytz

def floatHourToTime(fh):
    hours, hourSeconds = divmod(fh, 1)
    minutes, seconds = divmod(hourSeconds * 60, 1)
    return (
        int(hours),
        int(minutes),
        int(seconds * 60),
    )

def get_horix_line_blends():
    # try:
    source_file_path = download_to_temp("ProductionSchedule")
    if source_file_path=='Error Encountered':
        print('File not downloaded because of an error in the Sharepoint download function')
        return
    sheet_df = pd.read_excel(source_file_path, 'Horix Line', usecols = 'C:K')
    sheet_df = sheet_df.iloc[2:] # take out first two rows of the table body
    sheet_df.columns = ['item_code','po_number','item_description','amt','blend','dye','Case Size','item_run_qty','run_date']

    # take out non-useful rows
    sheet_df = sheet_df.dropna(axis=0, how='any', subset=['po_number'])
    sheet_df = sheet_df[sheet_df['po_number'] != 'XXXX']
    sheet_df = sheet_df[sheet_df['po_number'] != ' ']
    sheet_df = sheet_df[sheet_df['po_number'] != '0x2a']
    sheet_df = sheet_df[sheet_df['po_number'] != 'LineEnd']
    sheet_df = sheet_df[sheet_df['po_number'] != 'PailEnd']
    sheet_df = sheet_df[sheet_df['po_number'] != 'SchEnd']
    sheet_df = sheet_df[sheet_df['run_date'] != '???']
    sheet_df = sheet_df.drop(columns=['dye'])
    
    # add and set amt column
    sheet_df.loc[sheet_df['Case Size']=='6-1gal','amt'] = (sheet_df['item_run_qty'] * 6)
    sheet_df.loc[sheet_df['Case Size']=='55gal drum','amt'] = (sheet_df['item_run_qty'] * 55)
    sheet_df.loc[sheet_df['Case Size']=='5 gal pail','amt'] = (sheet_df['item_run_qty'] * 5)
    sheet_df.loc[sheet_df['Case Size']=='275 gal tote','amt'] = (sheet_df['item_run_qty'] * 275)
    sheet_df.loc[sheet_df['Case Size']=='265 gal tote','amt'] = (sheet_df['item_run_qty'] * 265)

    # set prod_line
    sheet_df['prod_line'] = ''
    sheet_df.loc[sheet_df['Case Size']=='6-1gal','prod_line'] = 'Hx'
    sheet_df.loc[sheet_df['Case Size']=='55gal drum','prod_line'] = 'Dm'
    sheet_df.loc[sheet_df['Case Size']=='5 gal pail','prod_line'] = 'Pails'
    sheet_df.loc[sheet_df['Case Size']=='265 gal tote','prod_line'] = 'Totes'
    sheet_df.loc[sheet_df['Case Size']=='275 gal tote','prod_line'] = 'Totes'

    run_dicts = []
    for i, row in sheet_df.iterrows():
        row_dict = row.to_dict()
        run_dicts.append(row_dict)

    # Drop rows where 'amt' column contains a string
    sheet_df = sheet_df[pd.to_numeric(sheet_df['amt'], errors='coerce').notnull()]
    
    # Convert 'amt' column to numeric type
    sheet_df['amt'] = pd.to_numeric(sheet_df['amt'])
    
    # Recreate run_dicts with the updated dataframe
    run_dicts = sheet_df.to_dict('records')

    if 'Hx' in sheet_df['prod_line'].values:
        hx_runs = [run for run in run_dicts if run['prod_line'] == 'Hx']
        sheet_df = sheet_df[sheet_df['prod_line'] != 'Hx']
        
        for hx_run in hx_runs:
            if hx_run['amt'] > 5040:
                total_amount = hx_run['amt']
                if total_amount % 5040 == 0:
                    extra_row_count = -(-total_amount // 5040) - 1
                    extra_row_dicts = [hx_run] * extra_row_count
                    for extra_row in extra_row_dicts:
                        extra_row['amt'] = 5100
                        new_row_df = pd.DataFrame([extra_row])
                        sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
                else:
                    remainder_amount = (hx_run['amt'] % 5040) + 60
                    extra_row_count = -(-total_amount // 5040) - 1
                    extra_row_dicts = [hx_run] * extra_row_count
                    for extra_row in extra_row_dicts:
                        extra_row['amt'] = 5100
                        new_row_df = pd.DataFrame([extra_row])
                        sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
                    hx_run['amt'] = remainder_amount
                    print(hx_run['amt'])
            elif hx_run['amt'] == 5040:
                hx_run['amt'] = 5100
            new_row_df = pd.DataFrame([hx_run])
            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
    
    if 'Dm' in sheet_df['prod_line'].values:
        dm_runs = [run for run in run_dicts if run['prod_line'] == 'Dm']
        sheet_df = sheet_df[sheet_df['prod_line'] != 'Dm']
        for dm_run in dm_runs:
            if "XBEE" not in dm_run['item_code']:
                if dm_run['amt'] < 2700:
                    dm_run['amt'] = dm_run['amt'] + 150
                if dm_run['amt'] == 2860:
                    dm_run['amt'] = 2925
                if dm_run['amt'] > 2925:
                    total_amount = dm_run['amt']
                    if total_amount % 2925 == 0:
                        extra_row_count = -(-total_amount // 2925) - 1
                        extra_row_dicts = [dm_run] * extra_row_count
                        for extra_row in extra_row_dicts:
                            extra_row['amt'] = 2925
                            new_row_df = pd.DataFrame([extra_row])
                            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
                    else:
                        remainder_amount = (dm_run['amt'] % 2925) + 60
                        extra_row_count = -(-total_amount // 2925) - 1
                        extra_row_dicts = [dm_run] * extra_row_count
                        for extra_row in extra_row_dicts:
                            extra_row['amt'] = 2925
                            new_row_df = pd.DataFrame([extra_row])
                            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
                        if remainder_amount > 2600:
                            dm_run['amt'] = 2925
                        else:
                            dm_run['amt'] = remainder_amount
            new_row_df = pd.DataFrame([dm_run])
            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
    
    if 'Totes' in sheet_df['prod_line'].values:
        tote_runs = [run for run in run_dicts if run['prod_line'] == 'Totes']
        sheet_df = sheet_df[sheet_df['prod_line'] != 'Totes']
        for tote_run in tote_runs:
            if "XBEE" not in tote_run['item_code']:
                if tote_run['amt'] >= 2750:
                    tote_run['amt'] = 2800
                if tote_run['amt'] > 2925:
                    total_amount = tote_run['amt']
                    if total_amount % 2925 == 0:
                        extra_row_count = -(-total_amount // 2925) - 1
                        extra_row_dicts = [tote_run] * extra_row_count
                        for extra_row in extra_row_dicts:
                            extra_row['amt'] = 2925
                            new_row_df = pd.DataFrame([extra_row])
                            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
                    else:
                        remainder_amount = (tote_run['amt'] % 2925) + 60
                        extra_row_count = -(-total_amount // 2925) - 1
                        extra_row_dicts = [tote_run] * extra_row_count
                        for extra_row in extra_row_dicts:
                            extra_row['amt'] = 2925
                            new_row_df = pd.DataFrame([extra_row])
                            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
                        if remainder_amount > 2600:
                            tote_run['amt'] = 2925
                        else:
                            tote_run['amt'] = remainder_amount
            new_row_df = pd.DataFrame([tote_run])
            sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
    
    # handle the dates
    sheet_df['run_date'] = sheet_df['run_date'].fillna(0)
    for i, row in sheet_df.iterrows():
        try:
            excel_date = sheet_df.at[i,'run_date']
            py_datetime = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
            timezone = pytz.timezone('America/Chicago')
            py_datetime = timezone.localize(py_datetime)
            sheet_df.at[i,'run_date']= py_datetime
        except ValueError:
            continue
    # print(sheet_df)
    
    sheet_df.loc[(sheet_df['prod_line'] == 'Dm') & (sheet_df['item_run_qty'] > 52), 'item_run_qty'] = 52
    sheet_df.loc[(sheet_df['prod_line'] == 'Hx') & (sheet_df['item_run_qty'] > 840), 'item_run_qty'] = 840
    
    sheet_df['run_time'] = 0.0
    # set run_time
    sheet_df.loc[sheet_df['Case Size']=='6-1gal','run_time'] = (sheet_df['item_run_qty'] * 6) / 3800
    sheet_df.loc[sheet_df['Case Size']=='55gal drum','run_time'] = (sheet_df['item_run_qty'] * 55) / 1450
    sheet_df.loc[sheet_df['Case Size']=='5 gal pail','run_time'] = (sheet_df['item_run_qty'] * 5) / 40
    sheet_df.loc[sheet_df['Case Size']=='275 gal tote','run_time'] = (sheet_df['item_run_qty'] * 275) / 1450
    sheet_df.loc[sheet_df['Case Size']=='265 gal tote','run_time'] = (sheet_df['item_run_qty'] * 265) / 1450

    sheet_df['start_time'] = 0.0
    sheet_df['start_time'] = sheet_df['start_time'].astype(float)
    sheet_df['run_time'] = sheet_df['run_time'].astype(float)
    # set start_time based on cumulative run_time
    sheet_df['start_time'] = sheet_df.groupby('prod_line')['run_time'].cumsum().fillna(0)
    sheet_df['start_time'] = sheet_df.groupby('prod_line')['start_time'].shift(1, fill_value=0)

    for index, row in sheet_df.iterrows():
        # calculate the number of weekdays between now and the run date, excluding Fridays
        current_date = dt.date.today()
        weekdays_count = 0
        while current_date < row['run_date'].date():
            if current_date.weekday() < 4:
                weekdays_count += 1
            current_date += dt.timedelta(days=1)
        # set the 'start_time' value equal to the weekdays count
        sheet_df.at[index, 'start_time'] = sheet_df.at[index, 'start_time'] + (weekdays_count  * 10)

    # convert the 'run_date' column to datetime format
    try:
        sheet_df['run_date'] = pd.to_datetime(sheet_df['run_date'])
    except Exception as e:
        print(str(e) + 'unacceptable date value')

    sheet_df = sheet_df.reset_index(drop=True)
    sheet_df['id2'] = sheet_df.groupby('prod_line').cumcount()

    alchemy_engine = create_engine(
            'postgresql+psycopg2://postgres:blend2021@localhost:5432/blendversedb',
            pool_recycle=3600
            )

    # Convert your Pandas DataFrame to a SQL Alchemy table
    sheet_df.to_sql(name='hx_blendthese', con=alchemy_engine, if_exists='replace', index=False)

    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("""update hx_blendthese hb set blend = (
            select component_item_code
            from bill_of_materials bom2 
            where hb.item_code = bom2.item_code
            and component_item_description like 'BLEND%' limit 1);
            ALTER TABLE hx_blendthese RENAME COLUMN blend TO component_item_code;
            ALTER TABLE hx_blendthese ADD COLUMN component_item_description TEXT;
            update hx_blendthese hb set component_item_description= (
            select component_item_description
            from bill_of_materials bom2 
            where hb.item_code = bom2.item_code
            and component_item_description like 'BLEND%' limit 1);
            """)
    # cursor_postgres.execute("ALTER TABLE hx_blendthese ADD COLUMN id SERIAL PRIMARY KEY;")
    cursor_postgres.execute("""INSERT INTO prodmerge_run_data (
                id2, run_time, start_time,
                item_run_qty, item_code, po_number, 
                item_description, prod_line)
            SELECT 
                id2::numeric, run_time::numeric, start_time::numeric,
                item_run_qty::numeric, item_code, po_number,
                item_description, prod_line
            FROM hx_blendthese;""")
    
    # cursor_postgres.execute("""
    #     ALTER TABLE hx_blendthese 
    #     ALTER COLUMN run_date 
    #     TYPE TIMESTAMP WITH TIME ZONE 
    #     USING run_date::TIMESTAMPZ AT TIME ZONE 'UTC-5';
    # """)

    cursor_postgres.execute("ALTER TABLE hx_blendthese ADD COLUMN id SERIAL PRIMARY KEY;")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()