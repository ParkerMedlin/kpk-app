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
    sheet_df = sheet_df[sheet_df['po_number'] != 'LineEnd']
    sheet_df = sheet_df[sheet_df['po_number'] != 'PailEnd']
    sheet_df = sheet_df[sheet_df['po_number'] != 'SchEnd']
    sheet_df = sheet_df[sheet_df['run_date'] != '???']

    # sheet_df.insert(loc=sheet_df.columns.get_loc('blend') + 1, column='run_time', value=0)
    sheet_df.rename(columns={'dye': 'run_time'}, inplace=True)
    sheet_df['run_time'] = 0

    # set run_time
    sheet_df.loc[sheet_df['Case Size']=='6-1gal','run_time'] = (sheet_df['item_run_qty'] * 6) / 3800
    sheet_df.loc[sheet_df['Case Size']=='55gal drum','run_time'] = (sheet_df['item_run_qty'] * 55) / 1450
    sheet_df.loc[sheet_df['Case Size']=='5 gal pail','run_time'] = (sheet_df['item_run_qty'] * 5) / 40
    sheet_df.loc[sheet_df['Case Size']=='275 gal tote','run_time'] = (sheet_df['item_run_qty'] * 275) / 1450
    sheet_df.loc[sheet_df['Case Size']=='265 gal tote','run_time'] = (sheet_df['item_run_qty'] * 265) / 1450

    # set amt
    sheet_df.loc[sheet_df['Case Size']=='6-1gal','amt'] = (sheet_df['item_run_qty'] * 6)
    sheet_df.loc[sheet_df['Case Size']=='55gal drum','amt'] = (sheet_df['item_run_qty'] * 55)
    sheet_df.loc[sheet_df['Case Size']=='5 gal pail','amt'] = (sheet_df['item_run_qty'] * 5)
    sheet_df.loc[sheet_df['Case Size']=='275 gal tote','amt'] = (sheet_df['item_run_qty'] * 275)
    sheet_df.loc[sheet_df['Case Size']=='265 gal tote','amt'] = (sheet_df['item_run_qty'] * 265)

    # set prod_line
    sheet_df.rename(columns={'Case Size': 'prod_line'}, inplace=True)
    sheet_df.replace('6-1gal', 'Hx', inplace=True)
    sheet_df.replace('55gal drum', 'Dm', inplace=True)
    sheet_df.replace('5 gal pail', 'Pails', inplace=True)
    sheet_df.replace('275 gal tote', 'Totes', inplace=True)
    sheet_df.replace('265 gal tote', 'Totes', inplace=True)

    sheet_df.loc[sheet_df.index[0], 'amt'] = 5600

    for i, row in sheet_df.iterrows():
        if str(row['prod_line'] == 'Hx') and int(row['amt']) > 5040:
            if int(row['amt']) % 5040 == 0:
                blend_count = int(int(row['amt']) / 5040) - 1
                remainder_blend = 0
            else:
                blend_count = -(-int(row['amt']) // 5040)  # This performs ceiling division
                remainder_blend = int(row['amt']) % 5040
            for _ in range(blend_count):
                new_row_df = pd.DataFrame([row])
                sheet_df = pd.concat([sheet_df, new_row_df], ignore_index=True)
            if remainder_blend:
                sheet_df.loc[(sheet_df['amt'] > 5040) & (sheet_df['prod_line'] == 'Hx'), 'amt'] = remainder_blend
                remainder_blend = 0

    sheet_df.loc[(sheet_df['amt'] > 5100) & (sheet_df['prod_line'] == 'Hx'), 'amt'] = 5100
    # sheet_df.loc[(sheet_df['amt'] > 2925) & (sheet_df['prod_line'] == 'Dm'), 'amt'] = 2925
    # sheet_df.loc[(sheet_df['amt'] > 2925) & (sheet_df['prod_line'] == 'Totes'), 'amt'] = 2925
    # sheet_df.loc[(sheet_df['amt'] > 2925) & (sheet_df['prod_line'] == 'Pails'), 'amt'] = 2925
    
    # handle the dates
    sheet_df['run_date'] = sheet_df['run_date'].fillna(0)
    for i, row in sheet_df.iterrows():
        try:
            excel_date = sheet_df.at[i,'run_date']
            py_datetime = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
            sheet_df.at[i,'run_date']= py_datetime
        except ValueError:
            continue

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
            and component_item_description like 'BLEND%'
            limit 1);
        select * from hx_blendthese hb;""")
    cursor_postgres.execute("ALTER TABLE hx_blendthese ADD COLUMN id SERIAL PRIMARY KEY;")
    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()