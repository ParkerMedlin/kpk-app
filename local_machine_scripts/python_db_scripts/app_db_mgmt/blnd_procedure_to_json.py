import os
import openpyxl
import json
import win32com.client
import time
import pandas as pd
import psycopg2
import datetime as dt


# def update_cell_formula(file_path, sheet_name, cell_address, formula, excel_instance):
#     workbook = excel_instance.Workbooks.Open(file_path)
#     if not workbook.Worksheets(sheet_name):
#         worksheet = workbook.Worksheets.Add()
#         worksheet.Name = sheet_name
#     worksheet.Range(cell_address).Value = formula
#     workbook.Save()
#     workbook.Close(SaveChanges=True)
    
# def check_sheet_names(file_path, excel_instance):
#     workbook = excel_instance.Workbooks.Open(file_path)
#     if workbook.Worksheets('LandscapeTemplate'):
#         workbook.Worksheets('LandscapeTemplate').Name = 'BlendSheet'
#     if not workbook.Worksheets('BlendSheet'):
#         print(f'NO SHEET NAMED "BlendSheet" found in {file_path}')

# def add_blendinfo_sheet(file_path, excel_instance):
#     workbook = excel_instance.Workbooks.Open(file_path)
#     blendinfo_sheet = workbook.Worksheets.Add()
#     try:
#         blendinfo_sheet.Name = "BlendInfo"
#         headers = ["item_code","ref_no","prepared_by","prepared_date","lbs_gal"]
#         for column_number, header in enumerate(headers):
#             blendinfo_sheet.Cells(1, column_number+1).Value = header
#         formulas = ["=BlendSheet!D3","=BlendSheet!A3","=BlendSheet!A5","=BlendSheet!B5","=BlendSheet!J3"]
#         for column_number, formula in enumerate(formulas):
#             blendinfo_sheet.Cells(2, column_number+1).Formula = formula    
#             # update_cell_formula(file_path, "BlendSteps", cell_address, formula, excel_instance)
#     except Exception as e:
#         print(str(e))

# def add_blendsteps_sheet(file_path, excel_instance):
#     workbook = excel_instance.Workbooks.Open(file_path)
#     blendsteps_sheet = workbook.Worksheets.Add()
#     try:
#         blendsteps_sheet.Name = "BlendSteps"
#         headers = ["step_number","step_desc","empty_col1","step_ratio","step_unit",
#                    "component_item_code","notes_1","notes_2","start_time","end_time"]
#         for column_number, header in enumerate(headers):
#             blendsteps_sheet.Cells(1, column_number+1).Value = header
        
#         formulas = ["=ROW()-1","=BlendSheet!B","=BlendSheet!D","=BlendSheet!B5","=BlendSheet!J3",
#                     "=BlendSheet!D3","=BlendSheet!A3","=BlendSheet!A5","=BlendSheet!B5","=BlendSheet!J3"]
#         for column_number, formula in enumerate(formulas):
#             blendsteps_sheet.Cells(2, column_number+1).Formula = formula    
#             # update_cell_formula(file_path, "BlendSteps", cell_address, formula, excel_instance)
#     except Exception as e:
#         print(str(e))

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

def update_cell_value(file_path, sheet_name, cell_address, new_value, excel_instance):
    workbook = excel_instance.Workbooks.Open(file_path)
    worksheet = workbook.Worksheets(sheet_name)
    worksheet.Range(cell_address).Value = new_value
    workbook.Save()
    workbook.Close(SaveChanges=True)  

def cell_values_to_json(file_path, excel_instance):
    workbook = excel_instance.Workbooks.Open(file_path)
    worksheet = workbook.Worksheets('BlendSheet')
    steps_dict = {}
    for step in range(30):
        try:
            qty_ratio = str(worksheet.Range('D' + str(step+28)).Value / worksheet.Range('F3').Value)
        except:
            qty_ratio = 0
        steps_dict[str(step)] = {
            "step_description" : worksheet.Range('B' + str(step+28)).Value,
            "qty_ratio" : qty_ratio,
            "unit" : worksheet.Range('E' + str(step+28)).Value,
            "component_item_code" : worksheet.Range('F' + str(step+28)).Value,
            "notes_1" : worksheet.Range('G' + str(step+28)).Value,
            "notes_2" : worksheet.Range('H' + str(step+28)).Value,
            "start_time" : worksheet.Range('I' + str(step+28)).Value,
            "end_time" : worksheet.Range('J' + str(step+28)).Value,
            "checked_by" : "",
            "double_checked_by" : ""
            }
    try:
        prepared_date = dt.datetime.strftime(worksheet.Range('B5').Value, '%Y-%m-%d')
    except:
        prepared_date = ''
    blend_procedure_dict = {"item_code" : worksheet.Range('D3').Value,
                            "ref_no" : worksheet.Range('A3').Value,
                            "prepared_by" : worksheet.Range('A5').Value,
                            "prepared_date" : prepared_date,
                            "lbs_gal" : worksheet.Range('J3').Value,
                            "steps" : steps_dict,
                            "lab_check" : ""
                             }
    return blend_procedure_dict
    # print(blend_status_template['steps'])
    # f = pd.DataFrame(steps_dict)
    # f = f.transpose()
    # print(f)

def push_json_to_db(blend_procedure_template, cursor_postgres, connection_postgres):
    item_code = blend_procedure_template['item_code']
    blend_procedure_JSON = json.dumps(blend_procedure_template).replace("'", "")
    try:
        print(item_code)
        cursor_postgres.execute(f'''
            INSERT INTO blend_procedure_TEMP (item_code, json_column) 
            VALUES ('{item_code}', '{blend_procedure_JSON}')
            ''')
        connection_postgres.commit()
    except Exception as this_error:
        print(f'error pushing to db: {str(this_error)}')
        print(blend_procedure_JSON)

def create_temp_procedure_table(cursor_postgres, connection_postgres):
    try:
        cursor_postgres.execute('''
            drop table if exists blend_procedure_TEMP;
            CREATE TABLE IF NOT EXISTS blend_procedure_TEMP(
                id SERIAL PRIMARY KEY,
                item_code TEXT,
                json_column JSON
            );
            ''')
        connection_postgres.commit()
    except Exception as this_error:
        print(f'error pushing to db: {str(this_error)}')

def rename_temp_procedure_table(cursor_postgres, connection_postgres):
    try:
        cursor_postgres.execute('''
            drop table if exists blend_procedure;
            alter table blend_procedure_TEMP rename to blend_procedure;
            ''')
        connection_postgres.commit()
    except Exception as this_error:
        print(f'error pushing to db: {str(this_error)}')


t1 = time.time()
# print('The formula output value of cell {} in sheet {} is: {}'.format(cell_address, sheet_name, formula_output))
excel_instance = win32com.client.Dispatch('Excel.Application')
excel_instance.Visible = False # Make Excel visible (optional)
folder_paths = [
    # "C:/Users/pmedlin/Desktop/testing/testmoar",
    'U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07',
    # "C:/Users/pmedlin/Desktop/testing",
    # "C:/Users/pmedlin/Desktop/testing/testmoar",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\1) -50 RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\2) -60 RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\3) -100RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\4) -200RVAF",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\Drying Agent Premix",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\NON-repel formulas",
    # "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\REPEL formulas"
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
create_temp_procedure_table(cursor_postgres, connection_postgres)

file_count = 0
for folder_path in folder_paths:
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx") and '~' not in file_name: #check if the file is an xlsx file
            print(file_name)
            file_path = os.path.join(folder_path, file_name)
            # check_sheet_names(file_path, excel_instance)
            check_theory_gallons(file_path, excel_instance)
            blend_procedure_json = cell_values_to_json(file_path, excel_instance)
            push_json_to_db(blend_procedure_json, cursor_postgres, connection_postgres)
            file_count += 1
print(str(file_count) + " files found")

rename_temp_procedure_table(cursor_postgres, connection_postgres)
cursor_postgres.close()
connection_postgres.close()
excel_instance.Quit()

# def get_blend_procedures():

def check_for_duplicates(list):
    my_list = [1, 2, 3, 2, 4, 5, 3, 6, 7, 6, 8]
    duplicates = []
    for item in my_list:
        if my_list.count(item) > 1:
            if item not in duplicates:
                duplicates.append(item)
    print("The duplicates in the list are:", duplicates)