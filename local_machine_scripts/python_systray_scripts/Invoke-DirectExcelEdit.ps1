Param(
    [Parameter(Mandatory=$true)][string]$CommandType,
    [Parameter(Mandatory=$true)][string]$ItemCodeForTemplateLookup,
    [Parameter(Mandatory=$true)][string]$LotQuantity,
    [Parameter(Mandatory=$true)][string]$LotNumber,
    [Parameter(Mandatory=$true)][string]$BlendDescription,
    [Parameter(Mandatory=$true)][string]$GHSLabelBaseFolderPath,
    [Parameter(Mandatory=$true)][string]$GHSExcelSheetName,
    [Parameter(Mandatory=$true)][string]$PathToGHSNonHazardExcelTemplate,
    [Parameter(Mandatory=$false)][string]$ComponentsForPickSheetJson
)

$ErrorActionPreference = "Stop"
$global:ExcelApp = $null
$global:WordApp = $null
$global:Workbook = $null
$global:WordDocument = $null
$TempWorkbookPath = $null

$BlendSheetFolders = @(
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\1) -50 RVAF",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\2) -60 RVAF",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\3) -100RVAF",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\4) -200RVAF",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\Drying Agent Premix",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\NON-repel formulas",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\5) -SPLASH W-W\\REPEL formulas",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\7) LET BLENDS",
    "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\6) Teak Sealer"
)

$Result = @{
    status = "pending"
    message = "Script execution started."
    details = ""
    found_template_path = ""
    ghs_printed_via = "none"
}

function Release-ComObjects {
    try {
        if ($global:WordDocument) {
            $global:WordDocument.Close($false)
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:WordDocument) | Out-Null
            $global:WordDocument = $null
            Write-Host "PS: Word Document released."
        }
        if ($global:WordApp) {
            $global:WordApp.Quit()
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:WordApp) | Out-Null
            $global:WordApp = $null
            Write-Host "PS: Word Application released."
        }
        if ($global:Workbook) {
            $global:Workbook.Close($false)
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:Workbook) | Out-Null
            $global:Workbook = $null
            Write-Host "PS: Main Excel Workbook (Blend Sheet) released."
        }
        if ($global:ExcelApp) {
            $global:ExcelApp.Quit()
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:ExcelApp) | Out-Null
            $global:ExcelApp = $null
            Write-Host "PS: Excel Application released."
        }
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    } catch {
        Write-Warning "PS: Warning during COM object release: $($_.Exception.Message)"
        $Result.details += "Warning during COM object release: $($_.Exception.Message). "
    }
}

function Initialize-ExcelApp {
    if (-not $global:ExcelApp) {
        Write-Host "PS: Initializing Excel Application..."
        $global:ExcelApp = New-Object -ComObject Excel.Application
        $global:ExcelApp.Visible = $false
        $global:ExcelApp.DisplayAlerts = $false
        Write-Host "PS: Excel Application initialized."
    }
}

function Process-GHSLabel {
    Param(
        [string]$LocalItemCodeForGHS,
        [string]$LocalBlendDescriptionForGHS,
        [string]$LocalGHSLabelBaseFolderPath,
        [string]$LocalPathToGHSNonHazardExcelTemplate
    )
    Write-Host "PS: Starting GHS Label process for Item Code: $LocalItemCodeForGHS"
    $GHSItemCodeFormatted = $LocalItemCodeForGHS -replace "/", "-"
    $GHSPattern = "$GHSItemCodeFormatted*.doc*"
    $GHSWordFiles = Get-ChildItem -Path $LocalGHSLabelBaseFolderPath -Filter $GHSPattern | Where-Object { $_.Name -notlike "~*" } | Select-Object -First 1

    if ($GHSWordFiles) {
        $GHSWordFileToPrint = $GHSWordFiles.FullName
        Write-Host "PS: Found GHS Word label: $GHSWordFileToPrint"
        $TempWordApp = $null
        $TempWordDoc = $null
        try {
            $TempWordApp = New-Object -ComObject Word.Application
            $TempWordApp.Visible = $false
            $TempWordDoc = $TempWordApp.Documents.Open($GHSWordFileToPrint)
            $TempWordDoc.PrintOut()
            Start-Sleep -Seconds 3
            $Result.ghs_printed_via = "word_document_found_and_printed"
            $Result.details += "GHS Word label printed. "
            Write-Host "PS: GHS Word label print command sent."
        } catch {
            Write-Warning "PS: Error printing GHS Word label '$GHSWordFileToPrint': $($_.Exception.Message)"
            $Result.ghs_printed_via = "word_document_error"
            $Result.details += "Error printing GHS Word label: $($_.Exception.Message). "
        } finally {
            if ($TempWordDoc) { $TempWordDoc.Close($false); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($TempWordDoc) | Out-Null }
            if ($TempWordApp) { $TempWordApp.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($TempWordApp) | Out-Null }
        }
    } else {
        Write-Host "PS: No GHS Word label found. Attempting to use GHS Non-Hazard Excel template: $LocalPathToGHSNonHazardExcelTemplate"
        if (-not (Test-Path $LocalPathToGHSNonHazardExcelTemplate -PathType Leaf)) {
            Write-Warning "PS: GHS Non-Hazard Excel template not found or is not a file: $LocalPathToGHSNonHazardExcelTemplate"
            $Result.ghs_printed_via = "ghs_non_hazard_template_not_found"
            $Result.details += "GHS Non-Hazard Excel template not found: $LocalPathToGHSNonHazardExcelTemplate. "
        } else {
            Initialize-ExcelApp
            $TempGHSWorkbookPath = $null
            $GHSWorkbookLocal = $null
            $GHSSheetLocal = $null
            $OriginalExcelDisplayAlerts = $null
            try {
                Write-Host "PS: Creating temporary copy of GHS Non-Hazard template."
                $GHSNonHazardExtension = [System.IO.Path]::GetExtension($LocalPathToGHSNonHazardExcelTemplate)
                $TempGHSFileName = "temp_ghs_nonhazard_$([System.Guid]::NewGuid().ToString())$GHSNonHazardExtension"
                $TempGHSWorkbookPath = Join-Path $env:TEMP $TempGHSFileName
                Copy-Item -Path $LocalPathToGHSNonHazardExcelTemplate -Destination $TempGHSWorkbookPath -Force
                Write-Host "PS: Temporary GHS Non-Hazard template created at $TempGHSWorkbookPath"

                $OriginalExcelDisplayAlerts = $global:ExcelApp.DisplayAlerts
                $global:ExcelApp.DisplayAlerts = $false

                $GHSWorkbookLocal = $global:ExcelApp.Workbooks.Open($TempGHSWorkbookPath)
                $GHSSheetLocal = $GHSWorkbookLocal.Sheets.Item("BlankGHSsheet")
                if (-not $GHSSheetLocal) {
                    throw "Sheet 'BlankGHSsheet' not found in GHS Non-Hazard template: $LocalPathToGHSNonHazardExcelTemplate"
                }
                Write-Host "PS: Opened GHS Non-Hazard template sheet 'BlankGHSsheet'."
                $OriginalGHSSheetVisibility = $GHSSheetLocal.Visible
                if ($OriginalGHSSheetVisibility -ne -1) { $GHSSheetLocal.Visible = -1; Write-Host "PS: Made 'BlankGHSsheet' visible." }

                Write-Host "PS: Populating GHS Non-Hazard template."
                $GHSSheetLocal.Range("C3").Value2 = $LocalItemCodeForGHS
                $GHSSheetLocal.Range("C4").Value2 = $LocalBlendDescriptionForGHS
                $GHSSheetLocal.Range("C24").Value2 = $LocalItemCodeForGHS
                $GHSSheetLocal.Range("C25").Value2 = $LocalBlendDescriptionForGHS
                Write-Host "PS: GHS Non-Hazard template populated. Printing..."
                $GHSSheetLocal.PrintOut()
                Start-Sleep -Seconds 3
                $Result.ghs_printed_via = "ghs_non_hazard_template_printed"
                $Result.details += "GHS Non-Hazard Excel template printed. "
                Write-Host "PS: GHS Non-Hazard template print command sent."
            } catch {
                 Write-Warning "PS: Error processing GHS Non-Hazard Excel template: $($_.Exception.Message). ScriptStackTrace: $($_.ScriptStackTrace)"
                 $Result.ghs_printed_via = "ghs_non_hazard_template_error"
                 $Result.details += "Error with GHS Non-Hazard template: $($_.Exception.Message). "
            } finally {
                if ($GHSSheetLocal) {
                    try { if ($OriginalGHSSheetVisibility -ne $null -and $OriginalGHSSheetVisibility -ne -1) { $GHSSheetLocal.Visible = $OriginalGHSSheetVisibility } } catch {}
                    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($GHSSheetLocal) | Out-Null
                }
                if ($GHSWorkbookLocal) { $GHSWorkbookLocal.Close($false); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($GHSWorkbookLocal) | Out-Null; Write-Host "PS: GHS Non-Hazard workbook closed."}
                if ($OriginalExcelDisplayAlerts -ne $null) { $global:ExcelApp.DisplayAlerts = $OriginalExcelDisplayAlerts }
                if ($TempGHSWorkbookPath -and (Test-Path $TempGHSWorkbookPath)) {
                    try { Start-Sleep -Milliseconds 200; Remove-Item -Path $TempGHSWorkbookPath -Force -ErrorAction SilentlyContinue; Write-Host "PS: Temporary GHS Non-Hazard workbook deleted." } catch { Write-Warning "PS: Failed to delete temp GHS workbook $TempGHSWorkbookPath" }
                }
            }
        }
    }
    Write-Host "PS: GHS Label process finished."
}

function Process-PickSheet {
    Param(
        [string]$JsonComponents,
        [string]$ParentItemCode,
        [string]$ParentLotNumber,
        [string]$ParentLotQuantityParam
    )
    Write-Host "PS: Starting Pick Sheet generation for Item: $ParentItemCode, Lot: $ParentLotNumber."
    $PickSheetWorkbookLocal = $null
    $PickSheetSheetLocal = $null

    try {
        $Components = $JsonComponents | ConvertFrom-Json
        if (-not $Components -or $Components.Count -eq 0) {
            Write-Host "PS: No components provided or JSON empty for Pick Sheet. Skipping Pick Sheet."
            $Result.details += "Warning: No components for Pick Sheet; Pick Sheet skipped. "
            return
        }
        Initialize-ExcelApp

        $PickSheetWorkbookLocal = $global:ExcelApp.Workbooks.Add()
        $PickSheetSheetLocal = $PickSheetWorkbookLocal.Worksheets.Item(1)
        $PickSheetSheetLocal.Name = "PickSheet"

        $PickSheetSheetLocal.PageSetup.Orientation = 2 # xlLandscape

        $PickSheetSheetLocal.Cells.Item(1,1).Value2 = "Blend Item:"
        $PickSheetSheetLocal.Cells.Item(1,2).Value2 = $ParentItemCode
        $PickSheetSheetLocal.Cells.Item(2,1).Value2 = "Lot Number:"
        $PickSheetSheetLocal.Cells.Item(2,2).Value2 = $ParentLotNumber
        $PickSheetSheetLocal.Cells.Item(3,1).Value2 = "Lot Quantity:"
        $PickSheetSheetLocal.Cells.Item(3,2).Value2 = $ParentLotQuantityParam
        
        $PickSheetSheetLocal.Range("A1:A3").Font.Bold = $true

        $HeaderRow = 5
        $PickSheetSheetLocal.Cells.Item($HeaderRow,1).Value2 = "ChemPN"
        $PickSheetSheetLocal.Cells.Item($HeaderRow,2).Value2 = "Chem"
        $PickSheetSheetLocal.Cells.Item($HeaderRow,3).Value2 = "GenLocation"
        
        $HeaderRange = $PickSheetSheetLocal.Range("A$($HeaderRow):C$($HeaderRow)")
        $HeaderRange.Font.Bold = $true
        $HeaderRange.Font.ColorIndex = 2 # White
        $HeaderRange.Font.Size = $HeaderRange.Font.Size + 2 # Increase font size
        $HeaderRange.Interior.ColorIndex = 1 # Black
        
        $row = $HeaderRow + 1
        foreach ($component in $Components) {
            $PickSheetSheetLocal.Cells.Item($row,1).Value2 = $component.componentItemCode
            $PickSheetSheetLocal.Cells.Item($row,2).Value2 = $component.componentItemDesc
            $PickSheetSheetLocal.Cells.Item($row,3).Value2 = $component.componentItemLocation
            $row++
        }
        # Autofit columns first to get a baseline
        $PickSheetSheetLocal.Columns.Item("A:C").AutoFit() | Out-Null

        # Explicitly set column widths for more breathing room
        # Column A (ChemPN) - 1.5x its autofit width
        $ColumnA = $PickSheetSheetLocal.Columns.Item("A")
        $ColumnA.ColumnWidth = $ColumnA.ColumnWidth * 1.5

        # Column B (Chem) - 2x its autofit width
        $ColumnB = $PickSheetSheetLocal.Columns.Item("B")
        $ColumnB.ColumnWidth = $ColumnB.ColumnWidth * 2
        
        # Column C (GenLocation) can remain autofitted or given a specific moderate width if needed
        # For now, leaving it as autofitted from the A:C range autofit earlier.

        Write-Host "PS: Pick Sheet populated. Printing..."
        $PickSheetSheetLocal.PrintOut()
        Start-Sleep -Seconds 3
        Write-Host "PS: Pick Sheet print command sent."
        $Result.details += "Pick Sheet printed successfully. "
    } catch {
        Write-Warning "PS: Error generating or printing Pick Sheet: $($_.Exception.Message). ScriptStackTrace: $($_.ScriptStackTrace)"
        $Result.details += "Error during Pick Sheet generation: $($_.Exception.Message). "
    } finally {
        if ($PickSheetSheetLocal) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($PickSheetSheetLocal) | Out-Null }
        if ($PickSheetWorkbookLocal) {
            $PickSheetWorkbookLocal.Close($false)
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($PickSheetWorkbookLocal) | Out-Null
            Write-Host "PS: Pick Sheet workbook closed and COM objects released."
        }
    }
    Write-Host "PS: Pick Sheet process finished."
}

function Process-BlendSheet {
    Param(
        [string]$LocalItemCodeForLookup,
        [string]$LocalLotQuantity,
        [string]$LocalLotNumber
    )
    Write-Host "PS: Starting Blend Sheet processing for Item Code: $LocalItemCodeForLookup"
    Initialize-ExcelApp

    $OriginalTemplatePathLocal = $null
    # Replace forward slash with hyphen FOR TEMPLATE LOOKUP ONLY
    $ItemCodeForFileSystemLookup = $LocalItemCodeForLookup -replace '/', '-'
    Write-Host "PS: Searching for blend sheet template for ItemCode '$LocalItemCodeForLookup' (using '$ItemCodeForFileSystemLookup' for file search)."
    foreach ($folderPath in $BlendSheetFolders) {
        if (-not (Test-Path $folderPath -PathType Container)) { Write-Warning "PS: Folder path not found, skipping: $folderPath"; continue }
        $foundFiles = Get-ChildItem -Path $folderPath -File | Where-Object {
            $_.Name -like "$ItemCodeForFileSystemLookup`_*" -and $_.Name -notlike "*~*" -and $_.Name -notlike "*.db"
        } | Select-Object -First 1
        if ($foundFiles) { $OriginalTemplatePathLocal = $foundFiles.FullName; Write-Host "PS: Found matching template: $OriginalTemplatePathLocal"; break }
    }
    if (-not $OriginalTemplatePathLocal) { throw "Blend sheet template file for Item Code '$LocalItemCodeForLookup' (searched as '$ItemCodeForFileSystemLookup') not found." } # Updated error message
    if (-not (Test-Path $OriginalTemplatePathLocal -PathType Leaf)) { throw "Blend sheet template path invalid: '$OriginalTemplatePathLocal'" }
    
    $Result.found_template_path = $OriginalTemplatePathLocal
    $OriginalExtension = [System.IO.Path]::GetExtension($OriginalTemplatePathLocal)
    $TempFileName = "temp_blendsheet_edit_$([System.Guid]::NewGuid().ToString())$OriginalExtension"
    $global:TempWorkbookPath = Join-Path $env:TEMP $TempFileName
    
    Write-Host "PS: Creating temporary copy of '$OriginalTemplatePathLocal' at: $global:TempWorkbookPath"
    Copy-Item -Path $OriginalTemplatePathLocal -Destination $global:TempWorkbookPath -Force
    
    $global:Workbook = $global:ExcelApp.Workbooks.Open($global:TempWorkbookPath)
    $Sheet = $global:Workbook.ActiveSheet
    if (-not $Sheet) { throw "Could not get active sheet from temporary blend workbook '$global:TempWorkbookPath'." }
    Write-Host "PS: Opened temporary Excel blend template: $($Sheet.Name)"

    $NumericLotQuantity = $null
    try { $NumericLotQuantity = [System.Convert]::ToDouble($LocalLotQuantity) } catch { $NumericLotQuantity = $LocalLotQuantity }

    $FoundTheoryGallonsCell = $Sheet.Cells.Find("Theory Gallons", [System.Reflection.Missing]::Value, [System.Reflection.Missing]::Value, 2)
    if ($FoundTheoryGallonsCell -and $FoundTheoryGallonsCell.GetType().FullName -eq 'System.__ComObject') {
        $TargetQtyCell = $FoundTheoryGallonsCell.Offset(1, 0)
        if ($TargetQtyCell -and $TargetQtyCell.GetType().FullName -eq 'System.__ComObject') {
            $TargetQtyCell.Value = $NumericLotQuantity; Write-Host "PS: Lot Quantity '$NumericLotQuantity' populated."
        } else { Write-Warning "PS: Target Qty Cell (Offset from 'Theory Gallons') invalid." }
    } else { Write-Warning "PS: 'Theory Gallons' not found; Lot Quantity not set." }

    # IMPORTANT: Use the ORIGINAL $LocalItemCodeForLookup for GHS and Pick Sheet, and for data within the blend sheet itself if needed.
    # The $ItemCodeForFileSystemLookup is ONLY for finding the template file.

    $FoundLotNumberCell = $Sheet.Cells.Find("Lot Number:", [System.Reflection.Missing]::Value, [System.Reflection.Missing]::Value, 1)
    if ($FoundLotNumberCell -and $FoundLotNumberCell.GetType().FullName -eq 'System.__ComObject') {
        $TargetLotCell = $FoundLotNumberCell.Offset(0, 1)
        if ($TargetLotCell -and $TargetLotCell.GetType().FullName -eq 'System.__ComObject') {
            $TargetLotCell.Value2 = $LocalLotNumber; Write-Host "PS: Lot Number '$LocalLotNumber' populated."
        } else { Write-Warning "PS: Target Lot Cell (Offset from 'Lot Number:') invalid." }
    } else { Write-Warning "PS: 'Lot Number:' not found; Lot Number not set." }
    
    Write-Host "PS: Printing main blend sheet from temporary copy."
    $Sheet.PrintOut()
    Start-Sleep -Seconds 3
    Write-Host "PS: Main blend sheet print command sent."
    $Result.details += "Blend Sheet printed. "
}

try {
    Write-Host "PS: Invoke-DirectExcelEdit.ps1 started. CommandType: $CommandType"

    if ($CommandType -eq "GenerateProductionPackage") {
        if (-not $ComponentsForPickSheetJson -or $ComponentsForPickSheetJson -eq "" ) {
            throw "Parameter -ComponentsForPickSheetJson is required and cannot be empty when CommandType is GenerateProductionPackage."
        }
        Write-Host "PS: Executing GenerateProductionPackage..."
        Process-GHSLabel -LocalItemCodeForGHS $ItemCodeForTemplateLookup -LocalBlendDescriptionForGHS $BlendDescription -LocalGHSLabelBaseFolderPath $GHSLabelBaseFolderPath -LocalPathToGHSNonHazardExcelTemplate $PathToGHSNonHazardExcelTemplate
        Process-PickSheet -JsonComponents $ComponentsForPickSheetJson -ParentItemCode $ItemCodeForTemplateLookup -ParentLotNumber $LotNumber -ParentLotQuantityParam $LotQuantity
        Process-BlendSheet -LocalItemCodeForLookup $ItemCodeForTemplateLookup -LocalLotQuantity $LotQuantity -LocalLotNumber $LotNumber
        
        $Result.message = "Production package (GHS, Pick Sheet, Blend Sheet) processed for '$ItemCodeForTemplateLookup'."

    } elseif ($CommandType -eq "GenerateBlendSheetOnly") {
        Write-Host "PS: Executing GenerateBlendSheetOnly..."
        Process-GHSLabel -LocalItemCodeForGHS $ItemCodeForTemplateLookup -LocalBlendDescriptionForGHS $BlendDescription -LocalGHSLabelBaseFolderPath $GHSLabelBaseFolderPath -LocalPathToGHSNonHazardExcelTemplate $PathToGHSNonHazardExcelTemplate
        Process-BlendSheet -LocalItemCodeForLookup $ItemCodeForTemplateLookup -LocalLotQuantity $LotQuantity -LocalLotNumber $LotNumber
        
        $Result.message = "GHS and Blend Sheet processed for '$ItemCodeForTemplateLookup'."
    } else {
        throw "Invalid CommandType specified: '$CommandType'. Must be 'GenerateProductionPackage' or 'GenerateBlendSheetOnly'."
    }
    $Result.status = "success"

} catch {
    $ErrorMessage = "PS_ERROR: $($_.Exception.ToString()) Line: $($_.InvocationInfo.ScriptLineNumber)"
    Write-Error $ErrorMessage
    $Result.status = "error"
    $Result.message = $ErrorMessage
    $Result.script_details = "$($_.ScriptStackTrace)"
} finally {
    Release-ComObjects

    if ($global:TempWorkbookPath -and (Test-Path $global:TempWorkbookPath)) {
        Write-Host "PS: Attempting to delete temporary blend sheet workbook: $global:TempWorkbookPath"
        try {
            Start-Sleep -Milliseconds 500
            Remove-Item -Path $global:TempWorkbookPath -Force -ErrorAction SilentlyContinue
            Write-Host "PS: Temporary blend sheet workbook deleted."
        } catch {
            Write-Warning "PS: Failed to delete temporary blend sheet workbook '$global:TempWorkbookPath'. Error: $($_.Exception.Message)"
            $Result.details += "Warning: Failed to auto-delete temp blend sheet file $global:TempWorkbookPath. "
        }
    }
    Write-Host "PS: Invoke-DirectExcelEdit.ps1 finished."
    $Result | ConvertTo-Json -Compress | Write-Output
} 