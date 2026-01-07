import pandas as pd
import os
import psycopg2
from .sharepoint_download import download_to_temp, download_to_memory
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

def get_horix_line_blends(file_buffer=None, use_dev=False):
    """
    Args:
        file_buffer: Optional BytesIO buffer containing ProductionSchedule.xlsb.
                     If None, downloads fresh from SharePoint.
        use_dev: If True and file_buffer is None, downloads DEV version.
    """
    try:
        if file_buffer is None:
            source = download_to_memory("ProductionSchedule" if not use_dev else "ProductionScheduleDEV")
            print(f'{dt.datetime.now()} :: horix_sched_to_postgres.py :: get_horix_line_blends :: Downloaded to memory')
        else:
            source = file_buffer
            source.seek(0)  # Reset buffer position
            print(f'{dt.datetime.now()} :: horix_sched_to_postgres.py :: get_horix_line_blends :: Using provided buffer')
        sheet_df = pd.read_excel(source, 'Horix Line', usecols = 'C:K')
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
        pail_mask = sheet_df['Case Size'].str.contains('gal pail', case=False, na=False)
        pail_sizes = (
            sheet_df.loc[pail_mask, 'Case Size']
            .str.extract(r'(\d+(?:\.\d+)?)')[0]
            .astype(float)
        )
        sheet_df.loc[pail_mask, 'amt'] = (sheet_df.loc[pail_mask, 'item_run_qty'] * pail_sizes)
        tote_mask = sheet_df['Case Size'].str.contains(' gal tote', na=False)
        sheet_df.loc[tote_mask, 'amt'] = (
            sheet_df.loc[tote_mask, 'item_run_qty'] * 
            sheet_df.loc[tote_mask, 'Case Size'].str.extract(r'(\d+)').astype(int).iloc[:, 0]
        )

        # set prod_line
        sheet_df['prod_line'] = ''
        sheet_df.loc[sheet_df['Case Size']=='6-1gal','prod_line'] = 'Hx'
        sheet_df.loc[sheet_df['Case Size']=='55gal drum','prod_line'] = 'Dm'
        sheet_df.loc[pail_mask, 'prod_line'] = 'Pails'
        sheet_df.loc[tote_mask, 'prod_line'] = 'Totes'

        run_dicts = []
        for i, row in sheet_df.iterrows():
            row_dict = row.to_dict()
            run_dicts.append(row_dict)

        # Drop rows where 'amt' column contains a string
        sheet_df = sheet_df[pd.to_numeric(sheet_df['amt'], errors='coerce').notnull()]
        
               # Convert 'amt' column to numeric type
        sheet_df['amt'] = pd.to_numeric(sheet_df['amt'])
        
        processed_runs = []
        for _, row in sheet_df.iterrows():
            run = row.to_dict()
            prod_line = run.get('prod_line')
            amt = run.get('amt', 0)
            item_code = run.get('item_code', '')

            if prod_line == 'Hx':
                if amt > 5040:
                    num_full_batches = int(amt // 5040)
                    remainder = amt % 5040
                    for _ in range(num_full_batches):
                        new_run = run.copy()
                        new_run['amt'] = 5100
                        processed_runs.append(new_run)
                    if remainder > 0:
                        remainder_run = run.copy()
                        remainder_run['amt'] = remainder + 60
                        processed_runs.append(remainder_run)
                elif amt == 5040:
                    run['amt'] = 5100
                    processed_runs.append(run)
                else:
                    processed_runs.append(run)
            
            elif prod_line == 'Dm':
                if "XBEE" in item_code:
                    processed_runs.append(run)
                    continue
                if amt == 2860:
                    run['amt'] = 2925
                    processed_runs.append(run)
                elif amt > 2925:
                    num_full_batches = int(amt // 2925)
                    remainder = amt % 2925
                    for _ in range(num_full_batches):
                        new_run = run.copy()
                        new_run['amt'] = 2925
                        processed_runs.append(new_run)
                    if remainder > 0:
                        remainder_run = run.copy()
                        remainder_amt = remainder + 60
                        if remainder_amt > 2700:
                            remainder_run['amt'] = 2925
                        else:
                            remainder_run['amt'] = remainder_amt
                        processed_runs.append(remainder_run)
                else:
                    processed_runs.append(run)

            elif prod_line == 'Totes':
                if "XBEE" in item_code:
                    processed_runs.append(run)
                    continue
                
                BLEND_CAPACITY = 2925
                num_full_totes = int(amt // BLEND_CAPACITY)
                remainder = amt % BLEND_CAPACITY
                
                if num_full_totes > 0:
                    full_tote_run = run.copy()
                    full_tote_run['amt'] = BLEND_CAPACITY
                    for _ in range(num_full_totes):
                        processed_runs.append(full_tote_run.copy())
                
                if remainder > 0:
                    remainder_run = run.copy()
                    remainder_run['amt'] = remainder
                    processed_runs.append(remainder_run)
            
            else:
                processed_runs.append(run)

        sheet_df = pd.DataFrame(processed_runs)
        
        target_timezone = pytz.timezone('America/Chicago')
        today_datetime_localized = datetime.now(target_timezone).replace(hour=0, minute=0, second=0, microsecond=0)

        # This loop processes 'run_date' to handle various input types and ensure valid, localized datetimes
        for i in sheet_df.index: 
            current_run_date_val = sheet_df.at[i, 'run_date']
            # Default to today; will be overwritten if a valid date is parsed or if it's explicitly NaN/empty
            processed_date = today_datetime_localized 

            if pd.isna(current_run_date_val) or (isinstance(current_run_date_val, str) and str(current_run_date_val).strip() == ''):
                # Handles NaN (null) and empty strings. Processed_date remains today.
                pass 
            elif isinstance(current_run_date_val, (datetime, pd.Timestamp)):
                # Handles if it's already a datetime object (e.g., from Excel direct parsing)
                dt_obj = pd.to_datetime(current_run_date_val) 
                if dt_obj.tzinfo is None:
                    localized_dt = target_timezone.localize(dt_obj)
                else:
                    localized_dt = dt_obj.astimezone(target_timezone)
                processed_date = localized_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                # Attempt to parse as Excel ordinal date or other convertible numerics/strings
                try:
                    # Convert to string first to handle numbers, then to float, then to int
                    excel_date_ordinal = int(float(str(current_run_date_val))) 
                    
                    # Excel dates 0, 1, etc., result in pre-1900 dates with the formula used.
                    # Treat such small ordinals as "not a date". Processed_date remains today.
                    if excel_date_ordinal < 2: 
                        processed_date = today_datetime_localized # Ensure processed_date is explicitly today
                    else:
                        dt_obj = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + excel_date_ordinal - 2)
                        localized_dt = target_timezone.localize(dt_obj)
                        processed_date = localized_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                except (ValueError, TypeError, OverflowError):
                    # Catches: non-numeric strings, float/int conversion issues, out of range for ordinal.
                    # Processed_date remains today.
                    pass 
                except Exception: 
                    # A broad catch for any other unexpected errors. Processed_date remains today.
                    pass 
            
            sheet_df.at[i, 'run_date'] = processed_date
        
     
        sheet_df.loc[(sheet_df['prod_line'] == 'Dm') & (sheet_df['item_run_qty'] > 52), 'item_run_qty'] = 52
        sheet_df.loc[(sheet_df['prod_line'] == 'Hx') & (sheet_df['item_run_qty'] > 840), 'item_run_qty'] = 840
        
        sheet_df['run_time'] = 0.0
        # set run_time
        sheet_df.loc[sheet_df['Case Size']=='6-1gal','run_time'] = (sheet_df['item_run_qty'] * 6) / 3800
        sheet_df.loc[sheet_df['Case Size']=='55gal drum','run_time'] = (sheet_df['item_run_qty'] * 55) / 2500
        sheet_df.loc[sheet_df['Case Size']=='5 gal pail','run_time'] = (sheet_df['item_run_qty'] * 5) / 40
        sheet_df.loc[sheet_df['Case Size']=='275 gal tote','run_time'] = (sheet_df['item_run_qty'] * 275) / 2500
        sheet_df.loc[sheet_df['Case Size']=='265 gal tote','run_time'] = (sheet_df['item_run_qty'] * 265) / 2500

        sheet_df['start_time'] = 0.0
        sheet_df['start_time'] = sheet_df['start_time'].astype(float)
        sheet_df['run_time'] = sheet_df['run_time'].astype(float)

        # set start_time based on cumulative run_time
        sheet_df = sheet_df.sort_values(['prod_line', 'run_date']).reset_index(drop=True)
        sheet_df['id2'] = sheet_df.groupby('prod_line').cumcount()

        
        sheet_df = ensure_daily_runtime_minimum(sheet_df, 'Dm')

        sheet_df['start_time'] = sheet_df.groupby('prod_line')['run_time'].cumsum().fillna(0)
        sheet_df['start_time'] = sheet_df.groupby('prod_line')['start_time'].shift(1, fill_value=0)

        # sheet_df['start_time'] = sheet_df.groupby('prod_line')['start_time'].cumsum().fillna(0)

        # for index, row in sheet_df.iterrows():
        #     # calculate the number of weekdays between now and the run date, excluding Fridays
        #     current_date = dt.date.today()
        #     weekdays_count = 0
        #     try:
        #         while current_date < row['run_date'].date():
        #             if current_date.weekday() < 4:
        #                 weekdays_count += 1
        #             current_date += dt.timedelta(days=1)
        #         # set the 'start_time' value equal to the weekdays count
        #         sheet_df.at[index, 'start_time'] = sheet_df.at[index, 'start_time'] + (weekdays_count  * 10)
        #     except Exception as e:
        #         print(f'{dt.datetime.now()} :: horix_sched_to_postgres.py :: get_horix_line_blends :: line {e.__traceback__.tb_lineno}: {str(e)}')
        #         print(f'{dt.datetime.now()} :: horix_sched_to_postgres.py :: get_horix_line_blends :: continuing anyway lol')
        #         continue

        alchemy_engine = create_engine(
                'postgresql+psycopg2://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb',
                pool_recycle=3600
                )

        # Convert your Pandas DataFrame to a SQL Alchemy table
        sheet_df.to_sql(name='hx_blendthese', con=alchemy_engine, if_exists='replace', index=False)

        connection_postgres = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
        cursor_postgres = connection_postgres.cursor()
        cursor_postgres.execute("""update hx_blendthese hb set blend = (
                select component_item_code
                from bill_of_materials bom2 
                where hb.item_code = bom2.item_code
                and component_item_description like 'BLEND%' limit 1);
                ALTER TABLE hx_blendthese RENAME COLUMN blend TO component_item_code;
                ALTER TABLE hx_blendthese ADD COLUMN component_item_description TEXT;
                ALTER TABLE hx_blendthese ALTER COLUMN run_date TYPE TIMESTAMP WITH TIME ZONE
                USING run_date::TIMESTAMP AT TIME ZONE 'UTC-5';
                UPDATE hx_blendthese
                SET run_date = run_date + interval '5 hours';
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
    except Exception as e:
        print(f'{dt.datetime.now()} :: horix_sched_to_postgres.py :: get_horix_line_blends :: line {e.__traceback__.tb_lineno}: {str(e)}')

def ensure_daily_runtime_minimum(df, prod_line, target_hours=10):
    filtered_df = df[df['prod_line'] == prod_line]
    distinct_dates = filtered_df['run_date'].unique().tolist()

    date_remainders = {}
    for distinct_date in distinct_dates:
        daily_runtime_sum = filtered_df[filtered_df['run_date'] == distinct_date]['run_time'].sum()
        date_remainders[distinct_date] = target_hours - daily_runtime_sum

    date_id2s = {}
    for distinct_date in distinct_dates:
        date_mask = filtered_df['run_date'] == distinct_date
        matching_indices = filtered_df[date_mask].index
        if len(matching_indices) > 0:
            date_id2s[distinct_date] = matching_indices[-1]
 
    for date, remainder in date_remainders.items():
        if remainder > 0:
            id2 = date_id2s[date]
            df.loc[df['id2'] == df.at[id2, 'id2'], 'run_time'] += remainder

    return df
