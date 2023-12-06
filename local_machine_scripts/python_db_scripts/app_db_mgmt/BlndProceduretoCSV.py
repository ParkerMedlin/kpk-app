import pyexcel as pe
import pandas as pd
import os
import csv

def get_blend_procedures():

    # Loop through the main folder and then the AF/ww folders, building list of all filepaths.
    fileList = []
    ignoredFolders = ["6) ClO2 Pouches","8) Experimental Blends","9) Dead File","testing"]
    for root, dirs, files in os.walk(r'U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07'):
        for i in range(len(ignoredFolders)):
            if ignoredFolders[i] in dirs:
                dirs.remove(ignoredFolders[i])
        for file in files:
            if not file.endswith('.db') and not file.endswith('.tmp'):
                fileList.append(os.path.join(root,file))

    # Create the csv where we will write the info.
    headers = ["blend_item_code","trimmed_item_code","step_no","step_desc"]
    with open(os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\blendinstructions.csv", 'w') as my_new_csv:
        writer = csv.writer(my_new_csv)
        writer.writerow(headers)

    
        # For each file, create a dataframe and then append that dataframe to the csv.
        for i, srcFilePath in enumerate(fileList):
            try:
                if "~" in srcFilePath:
                    continue
                if not srcFilePath.endswith('.xlsx'):
                    continue

                # extract the blendsheet-level values. These are all the values that will be the same on every row--
                # they are attributes of the blend sheet as a whole rather than each individual step.
                pyexcelSheet = pe.get_sheet(file_name=srcFilePath, sheet_name='BlendSheet')
                item_codeVAL = pyexcelSheet.cell_value(0,8)

                # create the dataframe for this blendsheet.
                instructionSet = pd.read_excel(srcFilePath, 'BlendSheet', skiprows = 26, usecols = 'A:B')
                instructionSet = instructionSet.dropna(axis=0, how='any', subset=['Step']) # drop rows that are NaN in the Step column
                instructionSet['id'] = range(1,len(instructionSet)+1)
                instructionSet['blend_item_code'] = str(item_codeVAL)
                instructionSet['trimmed_item_code'] = str(item_codeVAL).replace('.','').replace('/','')

                #write to csv
                instructionSet.to_csv(os.path.expanduser(r'~\\Desktop\blendinstructions.csv'), mode='a', header=False, index=False) # Write to the csv in our folder

            except Exception as e:
                print(srcFilePath)
                print(str(e))
                continue

def get_cell_iOne():

    # Loop through the main folder and then the AF/ww folders, building list of all filepaths.
    fileList = []
    ignoredFolders = ["6) ClO2 Pouches","8) Experimental Blends","9) Dead File","testing"]
    for root, dirs, files in os.walk(r'U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07'):
        for i in range(len(ignoredFolders)):
            if ignoredFolders[i] in dirs:
                dirs.remove(ignoredFolders[i])
        for file in files:
            if not file.endswith('.db') and not file.endswith('.tmp'):
                fileList.append(os.path.join(root,file))

    # Create the csv where we will write the info.
    headers = ["blend_item_code","filepath"]
    with open(os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\itemcodes.csv", 'w') as my_new_csv:
        writer = csv.writer(my_new_csv)
        writer.writerow(headers)

    
        # For each file, create a dataframe and then append that dataframe to the csv.
        for i, srcFilePath in enumerate(fileList):
            try:
                if "~" in srcFilePath:
                    continue
                if not srcFilePath.endswith('.xlsx') or srcFilePath.endswith('.xls'):
                    continue

                # extract the blendsheet-level values. These are all the values that will be the same on every row--
                # they are attributes of the blend sheet as a whole rather than each individual step.
                pyexcelSheet = pe.get_sheet(file_name=srcFilePath, sheet_name='BlendSheet')
                item_codeVAL = pyexcelSheet.cell_value(0,8)

                # create the dataframe for this blendsheet.
                # thisFile = pd.DataFrame({
                #     'blend_item_code': [item_codeVAL],
                #     'filepath': [str(srcFilePath)]
                # })
                if not item_codeVAL:
                    print(srcFilePath)
                #write to csv
                # thisFile.to_csv(os.path.expanduser(r'~\\Desktop\itemcodes.csv'), mode='a', header=False, index=False) # Write to the csv in our folder

            except Exception as e: 
                print("Issue encountered with " + str(fileList[i]))
                print(srcFilePath)
                print(str(e))
                continue

# get_cell_iOne()
get_blend_procedures()