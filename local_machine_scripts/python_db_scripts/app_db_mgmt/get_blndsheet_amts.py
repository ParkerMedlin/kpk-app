import os
import openpyxl
import json
import win32com.client
import time
import pandas as pd
import psycopg2
import datetime as dt

def update_cell_value(file_path, sheet_name, cell_address, new_value, excel_instance):
    workbook = excel_instance.Workbooks.Open(file_path)
    worksheet = workbook.Worksheets(sheet_name)
    worksheet.Range(cell_address).Value = new_value
    workbook.Save()
    workbook.Close(SaveChanges=True)

def check_theory_gallons(file_path, excel_instance):
    cell_address = 'F3'
    sheet_name = 'BlendSheet'
    # check_sheet_names(file_path, excel_instance)
    if file_name.endswith(".xlsx") and '~' not in file_name: #check if the file is an xlsx file
        file_path = os.path.join(folder_path, file_name)
        cell_value = get_formula_output(file_path, sheet_name, cell_address, excel_instance)
        if cell_value != 1000:
            update_cell_value(file_path, sheet_name, cell_address, 1000, excel_instance)

def get_formula_output(file_path, sheet_name, cell_address, excel_instance):
    workbook = excel_instance.Workbooks.Open(file_path) # Open workbook    
    worksheet = workbook.Worksheets(sheet_name) # Select the desired worksheet
    cell_value = worksheet.Range(cell_address).Value # Get the cell value (formula output)
    workbook.Close(SaveChanges=False) # Close and release resources
    return cell_value

def qty_values_to_dataframe(file_path, excel_instance):
    workbook = excel_instance.Workbooks.Open(file_path)
    worksheet = workbook.Worksheets('BlendSheet')
    item_code =  str(worksheet.Range('D3').Value)
    item_code_list = []
    qty_values_dict = {}
    component_item_code_list = []
    percentage_list = []
    component_item_description_list = []
    calculated_amount_list = []
    unit_list = []
    for row in range(15):
        if '*' not in str(worksheet.Range('A' + str(row+7)).Value) and 'ItemCode' not in str(worksheet.Range('A' + str(row+7)).Value):
            item_code_list.append(item_code)
            component_item_code_list.append(worksheet.Range('A' + str(row+7)).Value)
            percentage_list.append(worksheet.Range('B' + str(row+7)).Value)
            component_item_description_list.append(worksheet.Range('C' + str(row+7)).Value)
            calculated_amount_list.append(worksheet.Range('D' + str(row+7)).Value)
            unit_list.append(worksheet.Range('E' + str(row+7)).Value)
        else:
            print(worksheet.Range('A' + str(row+7)).Value)
            continue
    qty_values_dict["component_item_code"] = component_item_code_list
    qty_values_dict["percentage"] = percentage_list
    qty_values_dict["component_item_description"] = component_item_description_list
    qty_values_dict["blndsht_calc_amount"] = calculated_amount_list
    qty_values_dict["blendsheet_unit"] = unit_list 
    qty_values_dict["item_code"] = item_code_list
    qty_values_df = pd.DataFrame(qty_values_dict)
    qty_values_df['blendsheet_unit'] = qty_values_df['blendsheet_unit'].str.lower()
    qty_values_df['blendsheet_unit'] = qty_values_df['blendsheet_unit'].str.replace('lbs', 'lb')
    qty_values_df.dropna(subset=['component_item_code'], inplace=True)
    
    return qty_values_df

def add_bom_information(dataframe, cursor_postgres):
    item_code = dataframe.iloc[0, dataframe.columns.get_loc('item_code')]
    qtyperbill_list = []
    weightpergal_list = []
    standard_uom_list = []

    for component_item_code in dataframe["component_item_code"]:
        # print(component_item_code)
        try:
            cursor_postgres.execute(f"""SELECT qtyperbill, weightpergal, standard_uom
                                    from bill_of_materials 
                                    where component_item_code = '{str(component_item_code)}'
                                    and item_code = '{item_code}'""")
            component_bom_info = (cursor_postgres.fetchall())
            qtyperbill_list.append(component_bom_info[0][0])
            weightpergal_list.append(component_bom_info[0][1])
            standard_uom_list.append(component_bom_info[0][2])
        except Exception as e:
            if 'list index out of range' in str(e):
                if component_item_code == 'WATER':
                    weightpergal_list.append("8.34")
            else:
                print(str(e))
                print(component_item_code)
                weightpergal_list.append("1")
            qtyperbill_list.append("0")
            standard_uom_list.append("Nope")
            continue
    try:
        dataframe["qtyperbill"] = qtyperbill_list
        dataframe["weightpergal"] = weightpergal_list
        dataframe["bom_unit"] = standard_uom_list
    except Exception as e:
        print(str(e))
        print("there's a bad part number in here and it has messed everything up")
    dataframe['weightpergal'] = dataframe['weightpergal'].str.replace('#', '')
    for i, row in dataframe.iterrows():
        if row['bom_unit'].lower() == row['blendsheet_unit'].lower():
            dataframe.at[i, 'calc_converted_bom_amt'] = row['qtyperbill'] * 1000
        elif 'gram' in  row['blendsheet_unit'].lower():
            dataframe.at[i, 'calc_converted_bom_amt'] = row['qtyperbill'] * 1000 * 454
        else:
            if not pd.isnull(row['weightpergal']):
                try:
                    dataframe.at[i, 'calc_converted_bom_amt'] = float(row['qtyperbill']) * 1000 * float(row['weightpergal'])
                except Exception as e:
                    print(str(e))
                    continue
    # dataframe.loc[dataframe['bom_unit'].lower() == dataframe['blendsheet_unit'].lower(), 'calc_converted_bom_amt'] = dataframe['qtyperbill'] * 1000
    # dataframe.loc[(dataframe['bom_unit'] != dataframe['blendsheet_unit']) & (~dataframe['weightpergal'].isnull()), 'calc_converted_bom_amt'] = dataframe['qtyperbill'] * 1000 * dataframe['weightpergal']
    return dataframe


excel_instance = win32com.client.Dispatch('Excel.Application')
excel_instance.Visible = False # Make Excel visible (optional)
folder_paths = [
    # 'U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\testing',
    'U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07',
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\1) -50 RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\2) -60 RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\3) -100RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\4) -200RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\Drying Agent Premix",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\NON-repel formulas",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\REPEL formulas",
    # "C:/Users/pmedlin/Desktop/testing",
    # "C:/Users/pmedlin/Desktop/testing/testmoar",
    # "C:/Users/pmedlin/Desktop/testing/1) -50 RVAF",
    # "C:/Users/pmedlin/Desktop/testing/1) -60 RVAF",
    # "C:/Users/pmedlin/Desktop/testing/1) -100 RVAF",
    # "C:/Users/pmedlin/Desktop/testing/1) -200 RVAF",
    # "C:/Users/pmedlin/Desktop/testing/1) -SPLASH W-W/Drying Agent Premix",
    # "C:/Users/pmedlin/Desktop/testing/1) -SPLASH W-W/NON-repel formulas",
    # "C:/Users/pmedlin/Desktop/testing/1) -SPLASH W-W/REPEL formulas"
    ]
sheet_name = 'BlendSteps'

connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
cursor_postgres = connection_postgres.cursor()

file_count = 0
for folder_path in folder_paths:
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx") and '~' not in file_name: #check if the file is an xlsx file
            print(file_name)
            file_path = os.path.join(folder_path, file_name)
            # check_sheet_names(file_path, excel_instance)
            check_theory_gallons(file_path, excel_instance)
            qty_values = qty_values_to_dataframe(file_path, excel_instance)
            add_bom_information(qty_values, cursor_postgres)
            print(qty_values)
            file_count += 1
print(str(file_count) + " files found")

cursor_postgres.close()
connection_postgres.close()
excel_instance.Quit()

# def get_blend_procedures():