import pyexcel as pe
import pandas as pd
import os
import csv

def get_blend_procedures():
    print("we start now. We start NOW.")

    # Loop through the main folder and then the AF/ww folders, building list of all filepaths.
    fileList = []
    ignoredFolders = ["6) ClO2 Pouches","7) LET BLENDS","8) Experimental Blends","9) Dead File"]
    for root, dirs, files in os.walk(r'U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07'):
        for i in range(len(ignoredFolders)):
            if ignoredFolders[i] in dirs:
                dirs.remove(ignoredFolders[i])
        for file in files:
            if not file.endswith('.db') and not file.endswith('.tmp'):
                fileList.append(os.path.join(root,file))

    # Create the csv where we will write the info.
    headers = ["step_no","step_desc","empty_col1","step_qty","step_unit","component_item_code","notes_1","notes_2",
                "empty_col2","empty_col2","blend_part_num","ref_no","prepared_by","prepared_date","lbs_gal"]
    with open(os.path.expanduser('~\\Documents')+"\\kpk-app\\db_imports\\blendinstructions.csv", 'w') as my_new_csv:
        writer = csv.writer(my_new_csv)
        writer.writerow(headers)

    # For each file, create a dataframe and then append that dataframe to the csv. 
    for i in range(len(fileList)):
        # get the file
        srcFilePath = fileList[i]
        if "~" in srcFilePath:
            continue
        if not srcFilePath.endswith('.xlsx'):
            continue
        print(fileList[i])
        # extract the blendsheet-level values. These are all the values that will be the same on every row--
        # they are attributes of the blend sheet as a whole rather than each individual step.
        pyexcelSheet = pe.get_sheet(file_name=srcFilePath, sheet_name='BlendSheet')
        item_codeVAL = pyexcelSheet.cell_value(0,8)
        ref_noVAL = pyexcelSheet.cell_value(2,0)
        prepared_byVAL = pyexcelSheet.cell_value(4,0)
        prepared_dateVAL = pyexcelSheet.cell_value(4,1)
        lbs_galVAL = pyexcelSheet.cell_value(2,9)

        # create the dataframe for this blendsheet.
        instructionSet = pd.read_excel(srcFilePath, 'BlendSheet', skiprows = 26, usecols = 'A:J')
        instructionSet = instructionSet.dropna(axis=0, how='any', subset=['Step']) # drop rows that are NaN in the Step column 
        instructionSet['id'] = range(1,len(instructionSet)+1)

        # Create empty columns in the dataframe for all those blendsheet-level values from above.
        # Then, populate the columns with appropriate values.
        singleItemNames = ["item_code","ref_no","prepared_by","prepared_date","lbs_gal"]
        singleItemValues = [item_codeVAL,ref_noVAL,prepared_byVAL,prepared_dateVAL,lbs_galVAL]
        for i in range(len(singleItemNames)):
            instructionSet[singleItemNames[i]] = " "
        instructionSet = instructionSet.assign(item_code = item_codeVAL)
        instructionSet = instructionSet.assign(ref_no = ref_noVAL)
        instructionSet = instructionSet.assign(prepared_by = prepared_byVAL)
        instructionSet = instructionSet.assign(prepared_date = prepared_dateVAL)
        instructionSet = instructionSet.assign(lbs_gal = lbs_galVAL)
        instructionSet.to_csv(r'db_imports\blendinstructions.csv', mode='a', header=False, index=False) # Write to the csv in our folder
    print("example:")
    print(instructionSet)
    print("done")
    
get_blend_procedures()