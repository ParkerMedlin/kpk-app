import os
import datetime as dt
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import logging
import cProfile
import pstats

SPEC_SHEET_DIR = r"U:\qclab\My Documents"
SPEC_SHEET_PREFIX = "Spec Sheet - "
DEBUG_LOG_PATH = os.path.expanduser(r'~\Documents\kpk-app\local_machine_scripts\python_systray_scripts\pystray_logs\uv_freeze_audit.log')


def _normalize_item_code(series):
    """Normalize item code strings for consistent joins."""
    return (
        series.astype(str)
        .str.replace(r"\.0$", "", regex=True)      # drop Excel-added .0
        .str.replace(r"^'", "", regex=True)       # drop leading '
        .str.replace(r"\s+", "", regex=True)       # drop internal spaces
        .str.strip()
        .str.upper()
    )


def get_most_recent_specsheet_path(path=SPEC_SHEET_DIR, prefix=SPEC_SHEET_PREFIX):
    """Return absolute path to the newest spec sheet workbook, or None if not found."""
    try:
        files = [file for file in os.listdir(path) if file.startswith(prefix)]
    except FileNotFoundError:
        return None

    if not files:
        return None

    files.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
    return os.path.join(path, files[0])


def _dbg(message):
    """Write a line to both stdout and the audit log file."""
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} :: i_eat_the_specsheet.py :: {message}"
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # Avoid crashing due to log write failure
        pass
    print(line)


def get_spec_sheet():
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
        engine = create_engine("postgresql://", creator=lambda: conn)

        # Locate the workbook
        most_recent_specsheet = get_most_recent_specsheet_path()
        if not most_recent_specsheet:
            raise FileNotFoundError(f"No file starting with '{SPEC_SHEET_PREFIX}' found in {SPEC_SHEET_DIR}")
        print(f'{dt.datetime.now()} :: i_eat_the_specsheet.py :: get_spec_sheet :: {most_recent_specsheet}')

        columns_to_read = {
            "bill_of_materials": ["'BillNumber"],  # Original name before renaming to "ItemCode"
            "Lab Info": ["BillNumber", "Notes", "Current Footprint"],  # "BillNumber" before renaming to "ItemCode"
            "Weights": ["Product Code", "Min Weight (N)", "TARGET WEIGHT (N)", "Max Weight (N)"],  # "Product Code" before renaming to "ItemCode"
            "UPC SCC": ["PROD", "New UPC", "SCC"],  # "PROD" before renaming to "ItemCode"
            "BOL": ["PROD", "US - DOT", "Special Notes", "Europe HAZ", "Haz Symbols"],  # "PROD" before renaming to "ItemCode"
            "Item by Blend": ["BillNumber", "Item Description", "Part Number", "Revised Date", "Product Class", "Water Flush", "Solvent Flush", "Soap Flush", "Oil Flush", "Polish Flush", "Package Retain", "UV  Protection", "Freeze Protection", "Appearance", "Odor", "Spec. Gravity/Weight Per gallon 20C", "pH", "Viscosity", "API Gravity", "Miscellaneous", "Freeze Point", "% Water", "IR Scan Needed", "Notes", "Other Misc. Testing", "Oil Blends", "Comments", "Comments cont."],  # "BillNumber" and "Part Number" before renaming to "ItemCode" and "ComponentItemCode", "Notes" before renaming to "BlendNotes"
            "Freeze & UV": None,  # Assuming initially you need all columns for processing
            "Blend Specs": None,  # Assuming initially you need all columns for processing
            "Label Loc": None,  # Assuming initially you need all columns for restructuring
            "Raw Material Spec": ["Part Number", "Item Description:", "Item Description Cont.", "Supplier", "Bill Of Materials Description", "Revised Date:", "Appearance2", "Appearance", "Odor:", "Spec. Gravity/Weight Per gallon 20C", "API Gravity", "Boiling Point", "Freeze Point", "% Water", "pH", "Viscosity", "IR Scan Needed", "Comments", "Other Misc. Testing", "Comments Cont.", "Shelf Life"]  # "Part Number" before renaming to "ItemCode"
        }

        # Read only the necessary sheets and columns
        df = pd.read_excel(most_recent_specsheet, sheet_name=list(columns_to_read.keys()))

        # Rename the worksheet_merge_columns to "ItemCode"
        worksheet_merge_columns = [("bill_of_materials", "BillNumber"),
                                   ("Blend Specs", "Part Number"),
                                   ("Lab Info", "BillNumber"),
                                   ("Weights", "Product Code"),
                                   ("Freeze & UV", "PART #"),
                                   ("UPC SCC", "PROD"),
                                   ("BOL", "PROD"),
                                   ("Item by Blend", "BillNumber"),
                                   ("Label Loc", "Part Id"),
                                   ("Raw Material Spec", "Part Number"),]

        # Delete first row of Freeze & UV
        df['Freeze & UV'].rename(columns=df['Freeze & UV'].iloc[0, :], inplace=True)
        df['Freeze & UV'].drop(df['Freeze & UV'].index[0], inplace=True)

        # Delete unnecessary rows of Label Loc
        df['Label Loc'].rename(columns=df['Label Loc'].iloc[15], inplace=True)
        df['Label Loc'].drop(df['Label Loc'].index[0:18], inplace=True)
        df['Label Loc'].reset_index(drop=True, inplace=True)
        specsheetlabeldf = df['Label Loc']

        # Rename ItemCode-like columns to ItemCode
        for worksheet, column in worksheet_merge_columns:
            df[worksheet].rename(columns={column: "ItemCode"}, inplace=True)

        # Normalize ItemCode columns before any merges so joins do not miss due to types/whitespace
        df['bill_of_materials']['ItemCode'] = _normalize_item_code(df['bill_of_materials']['ItemCode'])
        df['Blend Specs']['ItemCode'] = _normalize_item_code(df['Blend Specs']['ItemCode'])
        df['Freeze & UV']['ItemCode'] = _normalize_item_code(df['Freeze & UV']['ItemCode'])
        df['Item by Blend']['ItemCode'] = _normalize_item_code(df['Item by Blend']['ItemCode'])
        if 'Part Number' in df['Item by Blend'].columns:
            df['Item by Blend']['Part Number'] = _normalize_item_code(df['Item by Blend']['Part Number'])

        # Rename Blend Specs column 'Notes' to 'Blend Notes'
        df['Blend Specs'].rename(columns={"Notes": "BlendNotes"}, inplace=True)

        # Pre-merge some sheets due to the data relationships in the original file
        blend_specs_copy = df['Blend Specs'].copy()
        blend_specs_copy.rename(columns={'ItemCode': 'ComponentItemCode'}, inplace=True)
        item_by_blend = df['Item by Blend'].merge(blend_specs_copy, on='ComponentItemCode', how='left')
        FreezeUV_copy = df['Freeze & UV'].copy()
        FreezeUV_copy.rename(columns={'ItemCode': 'ComponentItemCode'}, inplace=True)
        item_by_blend = item_by_blend.merge(FreezeUV_copy, on='ComponentItemCode', how='left')

        # Replace the original Item by Blend dataframe with the merged dataframe
        df['Item by Blend'] = item_by_blend

        # Setup bom_merged simply for uv_freeze_protect status checking
        blend_specs_copy_copy_finalv2 = df['Blend Specs'].copy()
        bom_merged = df['bill_of_materials'].merge(blend_specs_copy_copy_finalv2, on='ItemCode', how='left')
        FreezeUV_copy2 = df['Freeze & UV'].copy()
        bom_merged = bom_merged.merge(FreezeUV_copy2, on='ItemCode', how='left')

        # Filter rows based on condition
        bom_merged = bom_merged[bom_merged['Description'].str.startswith('BLEND')]

        # Select only the desired columns
        bom_merged = bom_merged[['ItemCode', 'UV  Protection', 'Freeze Protection']]

        # Remove duplicate rows from bom_merged
        bom_merged.drop_duplicates(inplace=True)

        # Set final_df as new DataFrame for final merge
        final_df = pd.DataFrame()

        # Define a list of dictionaries, where each dictionary represents a worksheet and the columns to keep
        worksheet_cols = [{"bill_of_materials": ["ItemCode"]},
                          {"Lab Info": ["ItemCode", "Notes", "Current Footprint"]},
                          {"Weights": ["ItemCode", "Min Weight (N)", "TARGET WEIGHT (N)", "Max Weight (N)"]},
                          {"UPC SCC": ["ItemCode", "New UPC", "SCC"]},
                          {"BOL": ["ItemCode", "US - DOT", "Special Notes", "Europe HAZ", "Haz Symbols"]},
                          {"Item by Blend": ["ItemCode", "Item Description", "ComponentItemCode", "Revised Date", "Product Class", "Water Flush", "Solvent Flush", "Soap Flush", "Oil Flush", "Polish Flush", "Package Retain", "UV  Protection", "Freeze Protection", "Appearance", "Odor", "Spec. Gravity/Weight Per gallon 20C", "pH", "Viscosity", "API Gravity", "Miscellaneous", "Freeze Point", "% Water", "IR Scan Needed", "BlendNotes", "Other Misc. Testing", "Oil Blends", "Comments", "Comments cont."]},
                          ]

        # Iterate over the list of dictionaries to remove all columns that are not specified in worksheet_cols
        for worksheet_col in worksheet_cols:
            worksheet = list(worksheet_col.keys())[0]
            cols = worksheet_col[worksheet]
            df[worksheet].drop(columns=[col for col in df[worksheet].columns if col not in cols], inplace=True)

        # Merge all items into final_df
        final_df = df["bill_of_materials"].merge(
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

        # Modify Raw Material Spec column names
        rawmatdf = df["Raw Material Spec"]
        rmcols_rename_list = [
            ('Item Description:', 'item_description'),
            ('Item Description Cont.', 'item_description2'),
            ('Supplier', 'supplier'),
            ('Bill Of Materials Description', 'bill_of_materials_description'),
            ('Revised Date:', 'revised_date'),
            ('Appearance2', 'appearance2'),
            ('Appearance', 'appearance'),
            ('Odor:', 'odor'),
            ('Spec. Gravity/Weight Per gallon 20C', 'spec_gravity_wpg'),
            ('API Gravity', 'api_gravity'),
            ('Boiling Point', 'boiling_point'),
            ('Freeze Point', 'freeze_point'),
            ('% Water', 'pct_water'),
            ('pH', 'ph'),
            ('Viscosity', 'viscosity'),
            ('IR Scan Needed', 'ir_scan'),
            ('Comments', 'comments'),
            ('Other Misc. Testing', 'other_testing'),
            ('Comments Cont.', 'comments2'),
            ('Shelf Life', 'shelf_life'),
        ]
        for col_orig, col_renamed in rmcols_rename_list:
            rawmatdf.rename(columns={col_orig: col_renamed}, inplace=True)

        # Create the tables in PostgreSQL
        final_df.to_sql("specsheet_data", engine, if_exists="replace", index=False)
        specsheetlabeldf.to_sql("specsheet_labels", engine, if_exists="replace", index=False)
        rawmatdf.to_sql("specsheet_raws", engine, if_exists="replace", index=False)
        bom_merged.to_sql("blend_protection", engine, if_exists="replace", index=False)

        # Close the connection to the database
        conn.close()

        print(f'{dt.datetime.now()} :: i_eat_the_specsheet.py :: get_spec_sheet :: =======spec sheet processed=======')
    except Exception as e:
        print(f'{dt.datetime.now()} :: i_eat_the_specsheet.py :: get_spec_sheet :: {str(e)}')


def find_uv_freeze_unmatched_ci_items(store_results=True):
    """
    Identify rows in the 'Freeze & UV' sheet whose ItemCode does not exist in CI_Item.
    Saves results to specsheet_uv_freeze_missing for consumption by the web app.
    """
    conn = None
    try:
        _dbg("find_uv_freeze_unmatched_ci_items starting")
        conn = psycopg2.connect('postgresql://postgres:REDACTED_DB_PASSWORD@localhost:5432/blendversedb')
        engine = create_engine("postgresql://", creator=lambda: conn)

        workbook_path = get_most_recent_specsheet_path()
        if not workbook_path:
            raise FileNotFoundError(f"No file starting with '{SPEC_SHEET_PREFIX}' found in {SPEC_SHEET_DIR}")

        _dbg(f"using workbook {workbook_path}")

        freeze_df = pd.read_excel(workbook_path, sheet_name="Freeze & UV")

        # Clean headers aggressively to avoid hidden chars / trailing spaces
        freeze_df.rename(columns=lambda c: str(c).strip(), inplace=True)
        freeze_df.rename(columns=freeze_df.iloc[0, :], inplace=True)
        freeze_df = freeze_df.drop(freeze_df.index[0])
        def _find_col(df, candidates):
            for c in df.columns:
                if str(c).strip().lower() in candidates:
                    return c
            return None

        part_col = _find_col(freeze_df, {'part #', 'part', 'prod', 'product code'})
        if not part_col:
            raise KeyError("Could not find a Part # column in Freeze & UV sheet")
        freeze_df.rename(columns={part_col: "ItemCode"}, inplace=True)
        freeze_df['ItemCode'] = _normalize_item_code(freeze_df['ItemCode'])

        desc_col = _find_col(freeze_df, {'description', 'desc', 'item description'})
        uv_col = _find_col(freeze_df, {'uv  protection', 'uv protection', 'uv_protection'})
        freeze_col = _find_col(freeze_df, {'freeze protection', 'freeze_protection'})

        freeze_df = freeze_df[['ItemCode'] + [c for c in [desc_col, uv_col, freeze_col] if c]].copy()
        rename_map = {'ItemCode': 'item_code'}
        if desc_col:
            rename_map[desc_col] = 'description'
        if uv_col:
            rename_map[uv_col] = 'uv_protection'
        if freeze_col:
            rename_map[freeze_col] = 'freeze_protection'
        freeze_df.rename(columns=rename_map, inplace=True)
        freeze_df.dropna(subset=['item_code'], inplace=True)
        freeze_df['item_code'] = freeze_df['item_code'].str.strip()
        freeze_df.drop_duplicates(subset=['item_code'], inplace=True)

        ci_items = pd.read_sql("SELECT itemcode FROM ci_item", engine)
        ci_items['itemcode'] = _normalize_item_code(ci_items['itemcode'].astype(str))

        freeze_codes = set(freeze_df['item_code'])
        ci_codes = set(ci_items['itemcode'])
        unmatched_codes = freeze_codes - ci_codes
        unmatched = freeze_df[freeze_df['item_code'].isin(unmatched_codes)].copy()
        unmatched['sheet_refreshed_at'] = dt.datetime.now()

        if store_results:
            unmatched.to_sql("specsheet_uv_freeze_missing", engine, if_exists="replace", index=False, schema="public")
            _dbg(f"wrote {len(unmatched)} rows to specsheet_uv_freeze_missing")

        # Helpful debug metrics
        _dbg(f"freeze rows: {len(freeze_df)} | unique codes: {len(freeze_codes)} | ci_item codes: {len(ci_codes)} | unmatched codes: {len(unmatched_codes)} | desc_col: {desc_col} | uv_col: {uv_col} | freeze_col: {freeze_col}")

        # Persist top 50 unmatched for quick inspection
        if unmatched_codes:
            debug_csv = os.path.join(os.path.dirname(DEBUG_LOG_PATH), "uv_freeze_unmatched_preview.csv")
            unmatched.head(50).to_csv(debug_csv, index=False)
            _dbg(f"preview saved to {debug_csv}")

        return unmatched
    except Exception as e:
        _dbg(f"ERROR find_uv_freeze_unmatched_ci_items: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Allow ad-hoc execution for local debugging
    find_uv_freeze_unmatched_ci_items()
