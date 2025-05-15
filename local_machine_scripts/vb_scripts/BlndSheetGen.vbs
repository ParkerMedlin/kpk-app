Sub blndSheetGen()
    '///Opens the blend sheet workbook for the blend on the row you click. Inputs the qty into said blend sheet.///////////////

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
    

End Sub