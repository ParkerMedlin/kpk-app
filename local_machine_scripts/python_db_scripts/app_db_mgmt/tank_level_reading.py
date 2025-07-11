import pandas as pd
from bs4 import BeautifulSoup
import urllib.request
import psycopg2
import sqlalchemy as sa
import json
import datetime as dt
from sqlalchemy.sql import text

def parse_html_to_dataframe(html_str):
    soup = BeautifulSoup(html_str, 'html.parser')
    tables = soup.find_all('table')  # find all tables in the HTML

    data = []
    for table in tables[1:-1]: # use the middle two tables on the page ONLY.
        rows = table.find_all('tr')  # find all table rows in a table
        for row in rows:
            cols = row.find_all('td')  # find all columns in a row
            cols = [col.text.strip() for col in cols]  # get the text from each column
            data.append(cols)  # add the columns to our data array

    df = pd.DataFrame(data)
    df = df.iloc[:, :-4] # drop the last 4 columns (which are empty)
    df.columns = ['tank_name', 'fill_percentage', 'fill_height_inches', 'height_capacity_inches', 'filled_gallons'] # rename
    df = df.dropna() # drop rows containing None values
    df = df[~df.map(lambda x: 'UKNWN' in str(x)).any(axis=1)]  # remove rows containing the string 'UKNWN'
    df['tank_name'] = df['tank_name'].str.split().str[-1] # extract tank names

    # Remove trailing detritus
    df['fill_percentage'] = df['fill_percentage'].str.replace('PCT', '')
    df['fill_height_inches'] = df['fill_height_inches'].str.replace('IN', '')
    df['height_capacity_inches'] = df['height_capacity_inches'].str.replace('IN', '')
    df['filled_gallons'] = df['filled_gallons'].str.replace('GL', '')
    df = df.map(lambda x: x.split()[0] if isinstance(x, str) else x)

    df['fill_percentage'] = pd.to_numeric(df['fill_percentage'])
    df['fill_height_inches'] = pd.to_numeric(df['fill_height_inches'])
    # print(df)
    df['height_capacity_inches'] = pd.to_numeric(df['height_capacity_inches'])
    df['filled_gallons'] = pd.to_numeric(df['filled_gallons'])

    # Add an id column
    df['id'] = range(1, len(df) + 1)
    
    # Reorder columns to put id first
    df = df[['id', 'tank_name', 'fill_percentage', 'fill_height_inches', 'height_capacity_inches', 'filled_gallons']]

    return df

def get_html_string():
    try:
        req = urllib.request.Request('http://192.168.178.210/fieldDeviceData.htm')
        
        with urllib.request.urlopen(req, timeout=5.0) as fp:
            html_str = fp.read().decode("utf-8")
            
        html_str = urllib.parse.unquote(html_str)
        return html_str
    except Exception as e:
        print(f"Error fetching tank levels: {e}")
        return '<html><body></body></html>'

def update_tank_levels_table():
    this_df = parse_html_to_dataframe(get_html_string())
    engine = sa.create_engine('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    this_df.to_sql('tank_level', engine, if_exists='replace')
    #print("--------Tank levels written to server.--------")

def log_tank_levels_table():
    this_df = parse_html_to_dataframe(get_html_string())
    connection_postgres = psycopg2.connect(
        'postgresql://postgres:blend2021@localhost:5432/blendversedb'
        )
    cursor_postgres = connection_postgres.cursor()

    for index, row in this_df.iterrows():
        timestamp = dt.datetime.now()
        cursor_postgres.execute(f"""
            INSERT INTO core_tanklevellog (tank_name, fill_percentage, fill_height_inches, height_capacity_inches, filled_gallons, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (row['tank_name'], row['fill_percentage'], row['fill_height_inches'], row['height_capacity_inches'], row['filled_gallons'], timestamp))

    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()
    #print("--------Tank levels logged.--------")