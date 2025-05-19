Option Explicit

Dim objArgs, itemCode, lotNumber, lotQuantity
Dim excelApp, excelWorkbook, excelSheet
Dim templatePath, templateDir, templateFile
Dim retries
Const MAX_RETRIES = 3
Const RETRY_DELAY = 2000 ' 2 seconds

Set objArgs = WScript.Arguments

If objArgs.Count <> 3 Then
    WScript.Echo "Error: Incorrect number of arguments. Usage: BlndSheetGen.vbs <ItemCode> <LotNumber> <LotQuantity>"
    WScript.Quit(1)
End If

itemCode = objArgs(0)
lotNumber = objArgs(1)
lotQuantity = objArgs(2)

' ///Opens the blend sheet workbook for the blend on the row you click. Inputs the qty into said blend sheet.///////////////

'String for current workbook name
Dim src As String
src = ActiveWorkbook.Name
Dim fileName As String
Dim fso As Object
Set fso = CreateObject("Scripting.FileSystemObject")
Dim folder As Object
Dim file As Object
Dim fileNameParts As Variant
Dim i As Integer
Dim completed As Boolean
Dim wordApp As Object
Set wordApp = CreateObject("Word.Application")

Dim blendInfo(5) As Variant
'Copy the value of the shortage qty cell
blendInfo(0) = ActiveCell.Value         'qty
blendInfo(1) = ActiveCell.Offset(0, -10).Value 'lot number
blendInfo(2) = ActiveCell.Offset(0, -7).Value  'line
blendInfo(3) = ActiveCell.Offset(0, -11).Value 'blend desc
blendInfo(4) = ActiveCell.Offset(0, 6).Value  'run date
blendInfo(5) = ActiveCell.Offset(0, -12).Value 'blend itemcode
blendInfo(5) = Replace(blendInfo(5), "/", "-")

'// print GHS label
Dim picPath As String
Dim oFSO As Object
Dim oFolder As Object
Dim oFile As Object

'Search for GHS label file matching blend item code
Set folder = fso.GetFolder("U:\qclab\My Documents\Blend GHS Tote Label")

Dim foundMatch As Boolean
foundMatch = False

For Each file In folder.Files
    fileName = file.Name
    fileName = Replace(fileName, "/", "-")

    If InStr(fileName, blendInfo(5)) = 1 And InStr(fileName, "~") = 0 Then
        wordApp.Documents.Open file.Path
        wordApp.ActiveDocument.PrintOut
        wordApp.ActiveDocument.Close
        wordApp.Quit
        Set wordApp = Nothing
        foundMatch = True
        Exit For
    End If
Next file

If Not foundMatch Then
    'No match found, open GHS sheet and fill in blend code
    Worksheets("GHSsheet").Visible = True
    Worksheets("GHSsheet").Activate
    Range("C3").Value = blendInfo(5)
    Range("C4").Value = blendInfo(3)
    Range("C5").Value = blendInfo(1)
    Range("C27").Value = blendInfo(5)
    Range("C28").Value = blendInfo(3)
    Range("C29").Value = blendInfo(1)
    ActiveSheet.PrintOut
    Worksheets("GHSsheet").Visible = False
End If

'Go to blend schedule and filter [BlendPN] by the PN copied from Lot Number Gen
Worksheets("pickSheetTable").Visible = True
Worksheets("pickSheetTable").Range("D:D").ColumnWidth = 60
Worksheets("pickSheetTable").Activate
ActiveSheet.ListObjects("pickSheetTable_query").Range.AutoFilter Field:=1, Criteria1:=blendInfo(5)
'Insert row, write in Date and Time fields, format it, then print
Rows("1:1").Select
Selection.Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove
Selection.Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove
Range("C1").Select
ActiveCell.FormulaR1C1 = "Required chemicals for " & blendInfo(5) + " " + blendInfo(3) + ", Lot " + blendInfo(1)
Range("C2").Select
ActiveCell.FormulaR1C1 = "Printed on " & Now()
Range("C1:C2").Select
With Selection.Font
    .Name = "Calibri"
    .Size = 18
    .Strikethrough = False
    .Superscript = False
    .Subscript = False
    .OutlineFont = False
    .Shadow = False
    .Underline = xlUnderlineStyleNone
    .ThemeColor = xlThemeColorLight1
    .TintAndShade = 0
    .ThemeFont = xlThemeFontMinor
End With
Selection.HorizontalAlignment = xlLeft
Worksheets("pickSheetTable").PageSetup.Orientation = xlLandscape
ActiveSheet.PrintOut

'Cleanup and hide worksheet
Rows("1").Delete
Rows("1").Delete
ActiveSheet.ListObjects("pickSheetTable_query").Range.AutoFilter Field:=1
Worksheets("pickSheetTable").Visible = False

Dim folderPaths(11) As Variant
folderPaths(0) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07"
folderPaths(1) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\1) -50 RVAF"
folderPaths(2) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\2) -60 RVAF"
folderPaths(3) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\3) -100RVAF"
folderPaths(4) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\4) -200RVAF"
folderPaths(5) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\5) -SPLASH W-W"
folderPaths(6) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\5) -SPLASH W-W\Drying Agent Premix"
folderPaths(7) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\5) -SPLASH W-W\NON-repel formulas"
folderPaths(8) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\5) -SPLASH W-W\REPEL formulas"
folderPaths(9) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\7) LET BLENDS"
folderPaths(10) = "U:\qclab\My Documents\Lab Sheets 04 10 07\Blend Sheets 06 15 07\BLEND SHEETS 06 15 07\6) Teak Sealer"

completed = False

For i = 0 To UBound(folderPaths) - 1
    Debug.Print folderPaths(i)
    Set folder = fso.GetFolder(folderPaths(i))
    For Each file In folder.Files
        fileName = file.Name
            ' If InStr(fileName, "_") = 0 Then
            '     Debug.Print fileName
            ' End If
            If InStr(fileName, "_") > 0 And InStr(fileName, "~") = 0 And InStr(fileName, ".db") = 0 Then
                fileNameParts = Split(fileName, "_")
                If UBound(fileNameParts) > 0 Then
                    ' Debug.Print fileNameParts(0)
                    If fileNameParts(0) = blendInfo(5) Then
                        On Error GoTo BlendSheetPrintHandle
                            Dim blndShtPath As String
                            blndShtPath = folder & "\" & fileName
                            Debug.Print blndShtPath
                            Workbooks.Open fileName:=blndShtPath
                            Application.Calculation = xlAutomatic

                            'Put the lot qty and lot num into the sheet and print
                            Cells.Find(what:="Theory Gallons", After:=ActiveCell, LookIn:=xlFormulas2, lookat:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlNext, MatchCase:=False, SearchFormat:=False).Activate
                            ActiveCell.Offset(1, 0).Value = blendInfo(0)
                            Cells.Find(what:="Lot Number:", After:=ActiveCell, LookIn:=xlFormulas2, lookat:=xlPart, SearchOrder:=xlByRows, SearchDirection:=xlNext, MatchCase:=False, SearchFormat:=False).Activate
                            ActiveCell.Offset(0, 1).Value = blendInfo(1)
                            ActiveSheet.PrintOut
                            ActiveWorkbook.Close SaveChanges:=False
                            
                            'Log the lot that was just printed
                            Windows(src).Activate
                            ActiveWorkbook.Sheets("Printed").Activate
                            Rows(1).Insert Shift:=xlDown
                            Range("A1").Value = blendInfo(1)
                            ActiveWorkbook.Sheets("LotNumRecord").Activate
                            Set fso = Nothing
                            Exit Sub

                    End If
                End If
        End If
    Next file
Next i
Set fso = Nothing

MsgBox "Couldn't find this blend sheet--please contact Parker."

BlendSheetPrintHandle:

' --- CONFIGURATION --- 
' !!! IMPORTANT: Update this path to your actual blend sheet template directory !!!
templateDir = "C:\BlendSheetTemplates\"
' Assuming template file is named like 'ITEMCODE_BlendSheet.xlsx' or 'ITEMCODE_BlendSheet.xls'
' Adjust if your naming convention or file extension is different.
templateFile = templateDir & blendInfo(5) & "_BlendSheet.xlsx" 

' Cell locations for data population - !!! UPDATE THESE AS NEEDED !!!
Const ITEM_CODE_CELL = "A1" ' Example: Cell for Item Code (might be pre-filled or for verification)
Const LOT_NUMBER_CELL = "B1" ' Example: Cell for Lot Number
Const LOT_QUANTITY_CELL = "C1" ' Example: Cell for Lot Quantity

' --- END CONFIGURATION ---

On Error Resume Next ' Defer error handling

' Check if template file exists
Dim fs
Set fs = CreateObject("Scripting.FileSystemObject")
If Not fs.FileExists(templateFile) Then
    ' Try with .xls extension as a fallback
    templateFile = templateDir & blendInfo(5) & "_BlendSheet.xls"
    If Not fs.FileExists(templateFile) Then
        WScript.Echo "Error: Template file not found for item code '" & blendInfo(5) & "' at '" & templateFile & "' (and .xlsx/.xls)"
        WScript.Quit(2)
    End If
End If
Set fs = Nothing

For retries = 0 To MAX_RETRIES
    Set excelApp = CreateObject("Excel.Application")
    If Err.Number <> 0 Then
        WScript.Echo "Error: Could not create Excel.Application object. Error " & Err.Number & ": " & Err.Description
        Err.Clear
        If retries < MAX_RETRIES Then
            WScript.Sleep RETRY_DELAY
        Else
            WScript.Quit(3)
        End If
    Else
        Exit For ' Successfully created Excel object
    End If
Next

On Error GoTo 0 ' Enable normal error handling again for subsequent operations

excelApp.DisplayAlerts = False ' Suppress alerts like "file in use"
excelApp.Visible = False      ' Keep Excel hidden

' Open the workbook
On Error Resume Next
Set excelWorkbook = excelApp.Workbooks.Open(templateFile)
If Err.Number <> 0 Then
    WScript.Echo "Error: Could not open workbook '" & templateFile & "'. Error " & Err.Number & ": " & Err.Description
    excelApp.Quit
    Set excelApp = Nothing
    WScript.Quit(4)
End If
On Error GoTo 0

' Assume the first sheet is the one to work with
Set excelSheet = excelWorkbook.Sheets(1)
If Err.Number <> 0 Then
    WScript.Echo "Error: Could not access the first sheet in the workbook. Error " & Err.Number & ": " & Err.Description
    excelWorkbook.Close False ' False = Don't save changes
    excelApp.Quit
    Set excelApp = Nothing
    Set excelWorkbook = Nothing
    WScript.Quit(5)
End If

' Populate the cells
On Error Resume Next
excelSheet.Range(ITEM_CODE_CELL).Value = blendInfo(5) ' Or verify if it's already there
excelSheet.Range(LOT_NUMBER_CELL).Value = blendInfo(1)
excelSheet.Range(LOT_QUANTITY_CELL).Value = blendInfo(0)
If Err.Number <> 0 Then
    WScript.Echo "Error: Failed to write data to cells. Check cell references. Error " & Err.Number & ": " & Err.Description
    ' Continue to try printing, but log the error
    Err.Clear
End If
On Error GoTo 0

' Allow formulas to recalculate
excelApp.Calculate

' Print the active sheet to the default printer
On Error Resume Next
excelSheet.PrintOut
If Err.Number <> 0 Then
    WScript.Echo "Error: Printing failed. Error " & Err.Number & ": " & Err.Description
    excelWorkbook.Close False
    excelApp.Quit
    Set excelSheet = Nothing
    Set excelWorkbook = Nothing
    Set excelApp = Nothing
    WScript.Quit(6)
End If
On Error GoTo 0

' Wait a bit for print job to be spooled (optional, adjust as needed)
' WScript.Sleep 5000 ' 5 seconds

' Close the workbook without saving changes
excelWorkbook.Close False

' Quit Excel
excelApp.Quit

' Clean up
Set excelSheet = Nothing
Set excelWorkbook = Nothing
Set excelApp = Nothing

WScript.Echo "Success: Blend sheet for item '" & blendInfo(5) & "' sent to printer."
WScript.Quit(0)