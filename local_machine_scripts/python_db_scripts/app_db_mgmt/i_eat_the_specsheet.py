import os
import datetime
import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# Connect to PostgreSQL database
conn = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
engine = create_engine("postgresql://", creator=lambda: conn)

# Load the workbook into a pandas dataframe
def get_most_recent_file(path, prefix):
    # Get a list of all files in the directory
    files = os.listdir(path)
    # Filter the list to only include files with the specified prefix
    files = [file for file in files if file.startswith(prefix)]
    # Sort the list of files by the modification time
    files.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
    # Return the most recent file
    return files[0] if files else None

file_path = "U:\qclab\My Documents"
prefix = "Spec Sheet - "

most_recent_specsheet = "U:\qclab\My Documents\\" + get_most_recent_file(file_path, prefix)
print(most_recent_specsheet)

df = pd.read_excel(most_recent_specsheet, sheet_name=None)

# Rename the worksheet_merge_columns to "ItemCode"
worksheet_merge_columns = [("Bill of Materials", "BillNumber"),
("Blend Specs", "Part Number"),
("Lab Info", "BillNumber"),
("Weights", "Product Code"),
("Freeze & UV", "PART #"),
("UPC SCC", "PROD"),
("BOL", "PROD"),
("Item by Blend", "BillNumber"),
("Label Loc", "Part Id"),]

# Delete first row of Freeze & UV
df['Freeze & UV'].rename(columns=df['Freeze & UV'].iloc[0, :], inplace=True)
df['Freeze & UV'].drop(df['Freeze & UV'].index[0], inplace=True)

#Delete Unnecessary Rows of Label Loc
df['Label Loc'].rename(columns=df['Label Loc'].iloc[15], inplace=True)
df['Label Loc'].drop(df['Label Loc'].index[0:18], inplace=True)
df['Label Loc'].reset_index(drop=True, inplace=True)
specsheetlabeldf = df['Label Loc']

# Rename ItemCode-like columns to ItemCode
for worksheet, column in worksheet_merge_columns:
    df[worksheet].rename(columns={column: "ItemCode"}, inplace=True)

# Pre-merge some sheets due to the data relationships in the original file
blend_specs_copy = df['Blend Specs'].copy()
blend_specs_copy.rename(columns={'ItemCode': 'ComponentItemCode'}, inplace=True)
item_by_blend = df['Item by Blend'].merge(blend_specs_copy, on='ComponentItemCode', how='left')
FreezeUV_copy = df['Freeze & UV'].copy()
FreezeUV_copy.rename(columns={'ItemCode': 'ComponentItemCode'}, inplace=True)
item_by_blend = item_by_blend.merge(FreezeUV_copy, on='ComponentItemCode', how='left')

# Replace the original Item by Blend dataframe with the merged dataframe
df['Item by Blend'] = item_by_blend

# Set final_df as new DataFrame for final merge
final_df = pd.DataFrame()

#Define a list of dictionaries, where each dictionary represents a worksheet and the columns to keep
worksheet_cols = [{"Bill of Materials": ["ItemCode"]},
{"Lab Info": ["ItemCode", "Notes", "Current Footprint"]},
{"Weights": ["ItemCode", "Min Weight (N)", "TARGET WEIGHT (N)", "Max Weight (N)"]},
{"UPC SCC": ["ItemCode", "New UPC", "SCC"]},
{"BOL": ["ItemCode", "US - DOT", "Special Notes", "Europe HAZ", "Haz Symbols"]},
{"Item by Blend": ["ItemCode", "ComponentItemCode", "Product Class", "Water Flush", "Solvent Flush", "Soap Flush", "Oil Flush", "Polish Flush", "Package Retain", "UV  Protection", "Freeze Protection"]}]


#Iterate over the list of dictionaries to remove all columns that are not specified in worksheet_cols
for worksheet_col in worksheet_cols:
    worksheet = list(worksheet_col.keys())[0]
    cols = worksheet_col[worksheet]
    df[worksheet].drop(columns=[col for col in df[worksheet].columns if col not in cols], inplace=True)

#Merge all items into final_df
final_df = df["Bill of Materials"].merge(
    df["Item by Blend"], on="ItemCode", how="left").merge(
    df["Weights"], on="ItemCode", how="left").merge(
    df["UPC SCC"], on="ItemCode", how="left").merge(
    df["BOL"], on="ItemCode", how="left").merge(
    df["Lab Info"], on="ItemCode", how="left")

# Remove duplicate columns
final_df = final_df.loc[:, ~final_df.columns.duplicated()]
# Remove duplicate rows
final_df.drop_duplicates(inplace=True)


# Set column types
final_df['New UPC'] = final_df['New UPC'].astype(str)
final_df['SCC'] = final_df['SCC'].astype(str)

# Remove 'nan' results
final_df['New UPC'].replace("nan", "", inplace=True)
final_df['SCC'].replace("nan", "", inplace=True)

# Create the tables in PostgreSQL
final_df.to_sql("specsheet_data", engine, if_exists="replace", index=False)
specsheetlabeldf.to_sql("specsheet_labels", engine, if_exists="replace", index=False)

# Close the connection to the database
conn.close()