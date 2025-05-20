Param(
    [Parameter(Mandatory=$true)][string]$ItemCodeForTemplateLookup,
    [Parameter(Mandatory=$true)][string]$LotQuantity, 
    [Parameter(Mandatory=$true)][string]$LotNumber,
    [Parameter(Mandatory=$true)][string]$BlendDescription,
    [Parameter(Mandatory=$true)][string]$GHSLabelBaseFolderPath,
    [Parameter(Mandatory=$true)][string]$GHSExcelSheetName,
    [Parameter(Mandatory=$true)][string]$PathToGHSNonHazardExcelTemplate
)

$ErrorActionPreference = "Stop"
$global:ExcelApp = $null
$global:WordApp = $null 
$global:Workbook = $null
$global:WordDocument = $null
$TempWorkbookPath = $null # Will store the path to the temporary copy

# Define the array of folder paths to search for blend sheets
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
    # Add new folder "U:\\qclab\\My Documents\\Lab Sheets 04 10 07\\Blend Sheets 06 15 07\\BLEND SHEETS 06 15 07\\11) RVAF LOW ODOR"
    # folderPaths(11) was mentioned in a previous user message's VBA snippet but its value was not shown, it implies an 11th path
    # For now, I will stick to the 11 paths (index 0-10) explicitly defined in the latest VBA snippet.
    # If the 12th path (index 11) is required, it should be added here.
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
            Write-Host "PS: Excel Workbook released."
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
    }
}

try {
    Write-Host "PS: Starting Direct Excel Edit for Item Code: $ItemCodeForTemplateLookup"

    # --- New Template Discovery Logic ---
    $OriginalTemplatePath = $null
    Write-Host "PS: Searching for template for ItemCode '$ItemCodeForTemplateLookup' in defined folders."

    foreach ($folderPath in $BlendSheetFolders) {
        if (-not (Test-Path $folderPath -PathType Container)) {
            Write-Warning "PS: Folder path not found or is not a directory, skipping: $folderPath"
            continue
        }
        Write-Host "PS: Searching in folder: $folderPath"
        $foundFiles = Get-ChildItem -Path $folderPath -File | Where-Object {
            $_.Name -like "$ItemCodeForTemplateLookup`_*" -and # Must start with ItemCode and an underscore
            $_.Name -notlike "*~*" -and                     # Exclude temporary files
            $_.Name -notlike "*.db"                         # Exclude .db files
        } | Select-Object -First 1

        if ($foundFiles) {
            $OriginalTemplatePath = $foundFiles.FullName
            Write-Host "PS: Found matching template: $OriginalTemplatePath"
            break 
        }
    }

    if (-not $OriginalTemplatePath) {
        throw "Blend sheet template file for Item Code '$ItemCodeForTemplateLookup' not found in any specified folder."
    }
    # --- End New Template Discovery Logic ---
    
    if (-not (Test-Path $OriginalTemplatePath -PathType Leaf)) { # Check if it's a file
        throw "Blend sheet template file path is invalid or file not found: '$OriginalTemplatePath' (dynamically found for item '$ItemCodeForTemplateLookup')"
    }
    $Result.found_template_path = $OriginalTemplatePath 
    Write-Host "PS: Original template path confirmed: $OriginalTemplatePath"

    # Create a unique name for the temporary workbook using the original extension
    $OriginalExtension = [System.IO.Path]::GetExtension($OriginalTemplatePath)
    $TempFileName = "temp_excel_edit_$([System.Guid]::NewGuid().ToString())$OriginalExtension"
    $TempWorkbookPath = Join-Path $env:TEMP $TempFileName
    
    Write-Host "PS: Creating temporary copy of '$OriginalTemplatePath' at: $TempWorkbookPath"
    Copy-Item -Path $OriginalTemplatePath -Destination $TempWorkbookPath -Force
    Write-Host "PS: Temporary copy created successfully."

    $global:ExcelApp = New-Object -ComObject Excel.Application
    $global:ExcelApp.Visible = $false
    $global:ExcelApp.DisplayAlerts = $false
    $global:Workbook = $global:ExcelApp.Workbooks.Open($TempWorkbookPath) # Open the temporary copy
    $Sheet = $global:Workbook.ActiveSheet 
    if (-not $Sheet) {
        throw "Could not get active sheet from temporary workbook '$TempWorkbookPath'."
    }
    Write-Host "PS: Opened temporary Excel template: $TempWorkbookPath. Active sheet: $($Sheet.Name)"

    # Conversion of LotQuantity (already present)
    $NumericLotQuantity = $null
    try {
        $NumericLotQuantity = [System.Convert]::ToDouble($LotQuantity)
        Write-Host "PS: Converted LotQuantity '$LotQuantity' to numeric: $NumericLotQuantity (Type: $($NumericLotQuantity.GetType().FullName))"
    } catch {
        Write-Warning "PS: Could not convert LotQuantity '$LotQuantity' to a number. Using as string. Error: $($_.Exception.Message)"
        $NumericLotQuantity = $LotQuantity 
    }

    Write-Host "PS: --- Processing Theory Gallons ---"
    $FoundTheoryGallonsCell = $null # Initialize to null
    try {
        Write-Host "PS: Attempting to execute \$Sheet.Cells.Find('Theory Gallons', Missing, Missing, LookAt:=xlPart (2))"
        $FoundTheoryGallonsCell = $Sheet.Cells.Find(
            "Theory Gallons", 
            [System.Reflection.Missing]::Value, # After
            [System.Reflection.Missing]::Value, # LookIn
            2                                 # LookAt (xlPart)
        )
        Write-Host "PS: \$Sheet.Cells.Find('Theory Gallons') executed. Result raw: '$($FoundTheoryGallonsCell)'"
        if ($FoundTheoryGallonsCell -ne $null) {
            Write-Host "PS: Result type: $($FoundTheoryGallonsCell.GetType().FullName)"
        } else {
            Write-Host "PS: Result is null."
        }
    } catch {
        Write-Warning "PS: CRITICAL ERROR during $Sheet.Cells.Find('Theory Gallons') call or initial result handling. Error: $($_.Exception.ToString())" 
        throw # Re-throw to be caught by the main catch block
    }
    
    # Proceed with the logic only if $FoundTheoryGallonsCell seems to be a valid COM object
    if ($FoundTheoryGallonsCell -and $FoundTheoryGallonsCell.GetType().FullName -eq 'System.__ComObject') {
        Write-Host "PS: 'Theory Gallons' found at $($FoundTheoryGallonsCell.Address($false,$false,[Microsoft.Office.Interop.Excel.XlReferenceStyle]::xlA1,$false,$null)). Type: $($FoundTheoryGallonsCell.GetType().FullName)"
        $TargetQtyCell = $FoundTheoryGallonsCell.Offset(1, 0)
        if ($TargetQtyCell -and $TargetQtyCell.GetType().FullName -eq 'System.__ComObject') {
            Write-Host "PS: Target Quantity Cell is at $($TargetQtyCell.Address($false,$false,[Microsoft.Office.Interop.Excel.XlReferenceStyle]::xlA1,$false,$null)). Type: $($TargetQtyCell.GetType().FullName)"
            try {
                Write-Host "PS: Attempting to set Lot Quantity '$NumericLotQuantity' to cell $($TargetQtyCell.Address($false,$false,[Microsoft.Office.Interop.Excel.XlReferenceStyle]::xlA1,$false,$null))"
                $TargetQtyCell.Value = $NumericLotQuantity 
                Write-Host "PS: Lot Quantity '$NumericLotQuantity' populated successfully."
            } catch {
                Write-Warning "PS: FAILED to set Lot Quantity. Error: $($_.Exception.Message)" 
                throw # Re-throw to be caught by the main catch block
            }
        } else {
            Write-Warning "PS: Target Quantity Cell (Offset from 'Theory Gallons') is null or not a COM object. Type: $($TargetQtyCell.GetType().FullName)"
            $Result.details += "Warning: Target Qty Cell (Offset from 'Theory Gallons') is invalid. "
        }
    } else {
        Write-Warning "PS: 'Theory Gallons' text not found or invalid COM object. Cell Object: '$($FoundTheoryGallonsCell)'. Lot Quantity not populated."
        $Result.details += "Warning: 'Theory Gallons' not found; Lot Quantity not set. "
    }

    Write-Host "PS: --- Processing Lot Number ---"
    $FoundLotNumberCell = $null # Initialize to null
    try {
        Write-Host "PS: Attempting to execute \$Sheet.Cells.Find('Lot Number:', Missing, Missing, LookAt:=xlWhole (1))"
        $FoundLotNumberCell = $Sheet.Cells.Find(
            "Lot Number:", 
            [System.Reflection.Missing]::Value, # After
            [System.Reflection.Missing]::Value, # LookIn
            1                                 # LookAt (xlWhole)
        )
        Write-Host "PS: \$Sheet.Cells.Find('Lot Number:') executed. Result raw: '$($FoundLotNumberCell)'"
        if ($FoundLotNumberCell -ne $null) {
            Write-Host "PS: Result type: $($FoundLotNumberCell.GetType().FullName)"
        } else {
            Write-Host "PS: Result is null."
        }
    } catch {
        Write-Warning "PS: CRITICAL ERROR during \$Sheet.Cells.Find('Lot Number:') call or initial result handling. Error: $($_.Exception.ToString())" 
        throw # Re-throw to be caught by the main catch block
    }

    # Proceed with the logic only if $FoundLotNumberCell seems to be a valid COM object
    if ($FoundLotNumberCell -and $FoundLotNumberCell.GetType().FullName -eq 'System.__ComObject') {
        Write-Host "PS: 'Lot Number:' found at $($FoundLotNumberCell.Address($false,$false,[Microsoft.Office.Interop.Excel.XlReferenceStyle]::xlA1,$false,$null)). Type: $($FoundLotNumberCell.GetType().FullName)"
        $TargetLotCell = $FoundLotNumberCell.Offset(0, 1)
        if ($TargetLotCell -and $TargetLotCell.GetType().FullName -eq 'System.__ComObject') {
            Write-Host "PS: Target Lot Cell is at $($TargetLotCell.Address($false,$false,[Microsoft.Office.Interop.Excel.XlReferenceStyle]::xlA1,$false,$null)). Type: $($TargetLotCell.GetType().FullName)"
            try {
                Write-Host "PS: Attempting to directly set Lot Number '$LotNumber' (Type: $($LotNumber.GetType().FullName)) to cell $($TargetLotCell.Address($false,$false,[Microsoft.Office.Interop.Excel.XlReferenceStyle]::xlA1,$false,$null)) using .Value2"
                $TargetLotCell.Value2 = $LotNumber
                Write-Host "PS: Lot Number '$LotNumber' populated successfully (direct assignment using .Value2)."
            } catch {
                Write-Warning "PS: FAILED to set Lot Number using .Value2. Error: $($_.Exception.Message)"
                throw 
            }
        } else {
            Write-Warning "PS: Target Lot Cell (Offset from 'Lot Number:') is null or not a COM object. Type: $($TargetLotCell.GetType().FullName)"
            $Result.details += "Warning: Target Lot Cell (Offset from 'Lot Number:') is invalid. "
        }
    } else {
        Write-Warning "PS: 'Lot Number:' text not found or invalid COM object. Cell Object: '$($FoundLotNumberCell)'. Lot Number not populated."
        $Result.details += "Warning: 'Lot Number:' not found; Lot Number not set. "
    }
    
    Write-Host "PS: Starting GHS Label process."
    $GHSItemCodeFormatted = $ItemCodeForTemplateLookup -replace "/", "-"
    $GHSPattern = "$GHSItemCodeFormatted*.doc*" 
    
    $GHSWordFiles = Get-ChildItem -Path $GHSLabelBaseFolderPath -Filter $GHSPattern | Where-Object { $_.Name -notlike "~*" } | Select-Object -First 1
    
    if ($GHSWordFiles) {
        $GHSWordFileToPrint = $GHSWordFiles.FullName
        Write-Host "PS: Found GHS Word label: $GHSWordFileToPrint"
        try {
            $global:WordApp = New-Object -ComObject Word.Application
            $global:WordApp.Visible = $false
            $global:WordDocument = $global:WordApp.Documents.Open($GHSWordFileToPrint)
            $global:WordDocument.PrintOut()
            Start-Sleep -Seconds 3 
            $Result.ghs_printed_via = "word_document_found_and_printed"
            Write-Host "PS: GHS Word label print command sent."
        } catch {
            Write-Warning "PS: Error printing GHS Word label '$GHSWordFileToPrint': $($_.Exception.Message)"
            $Result.ghs_printed_via = "word_document_error"
            $Result.details += "Error printing GHS Word label: $($_.Exception.Message). "
        } finally {
            if ($global:WordDocument) { $global:WordDocument.Close($false); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:WordDocument) | Out-Null; $global:WordDocument = $null }
            if ($global:WordApp) { $global:WordApp.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:WordApp) | Out-Null; $global:WordApp = $null }
        }
    } else {
        Write-Host "PS: No GHS Word label found. Attempting to use GHS Non-Hazard Excel template: $PathToGHSNonHazardExcelTemplate"
        if (-not (Test-Path $PathToGHSNonHazardExcelTemplate -PathType Leaf)) {
            Write-Warning "PS: GHS Non-Hazard Excel template not found or is not a file: $PathToGHSNonHazardExcelTemplate"
            $Result.ghs_printed_via = "ghs_non_hazard_template_not_found"
            $Result.details += "GHS Non-Hazard Excel template not found: $PathToGHSNonHazardExcelTemplate. "
        } else {
            $TempGHSWorkbookPath = $null
            $GHSWorkbook = $null
            $GHSSheet = $null
            $OriginalExcelDisplayAlerts = $null
            
            try {
                Write-Host "PS: Creating temporary copy of GHS Non-Hazard template."
                $GHSNonHazardExtension = [System.IO.Path]::GetExtension($PathToGHSNonHazardExcelTemplate)
                $TempGHSFileName = "temp_ghs_nonhazard_$([System.Guid]::NewGuid().ToString())$GHSNonHazardExtension"
                $TempGHSWorkbookPath = Join-Path $env:TEMP $TempGHSFileName
                Copy-Item -Path $PathToGHSNonHazardExcelTemplate -Destination $TempGHSWorkbookPath -Force
                Write-Host "PS: Temporary GHS Non-Hazard template created at $TempGHSWorkbookPath"

                # Ensure Excel App is available (it should be from main sheet processing)
                if (-not $global:ExcelApp) {
                    Write-Warning "PS: Excel Application not initialized. Cannot process GHS Non-Hazard template."
                    throw "Excel Application not initialized."
                }
                
                $OriginalExcelDisplayAlerts = $global:ExcelApp.DisplayAlerts
                $global:ExcelApp.DisplayAlerts = $false # Suppress alerts for this operation

                $GHSWorkbook = $global:ExcelApp.Workbooks.Open($TempGHSWorkbookPath)
                $GHSSheet = $GHSWorkbook.Sheets.Item("BlankGHSsheet") # As per VBA: Worksheets("BlankGHSsheet")
                
                if (-not $GHSSheet) {
                    throw "Sheet 'BlankGHSsheet' not found in GHS Non-Hazard template: $PathToGHSNonHazardExcelTemplate"
                }
                Write-Host "PS: Opened GHS Non-Hazard template sheet 'BlankGHSsheet'."

                # Make sheet visible if it's hidden (e.g., xlSheetVeryHidden)
                $OriginalGHSSheetVisibility = $GHSSheet.Visible
                if ($OriginalGHSSheetVisibility -ne -1) { # -1 is xlSheetVisible
                    $GHSSheet.Visible = -1 
                    Write-Host "PS: Made 'BlankGHSsheet' visible."
                }

                Write-Host "PS: Populating GHS Non-Hazard template."
                $GHSSheet.Range("C3").Value2 = $ItemCodeForTemplateLookup 
                $GHSSheet.Range("C4").Value2 = $BlendDescription      
                $GHSSheet.Range("C24").Value2 = $ItemCodeForTemplateLookup             
                $GHSSheet.Range("C25").Value2 = $BlendDescription
                Write-Host "PS: GHS Non-Hazard template populated. Printing..."
                
                $GHSSheet.PrintOut()
                Start-Sleep -Seconds 3 
                $Result.ghs_printed_via = "ghs_non_hazard_template_printed"
                Write-Host "PS: GHS Non-Hazard template print command sent."

            } catch {
                 Write-Warning "PS: Error processing GHS Non-Hazard Excel template: $($_.Exception.Message). ScriptStackTrace: $($_.ScriptStackTrace)"
                 $Result.ghs_printed_via = "ghs_non_hazard_template_error"
                 $Result.details += "Error with GHS Non-Hazard template: $($_.Exception.Message). "
            } finally {
                if ($GHSSheet) {
                    try {
                        if ($OriginalGHSSheetVisibility -ne $null -and $OriginalGHSSheetVisibility -ne -1) { # If we changed visibility
                           $GHSSheet.Visible = $OriginalGHSSheetVisibility
                           Write-Host "PS: Restored 'BlankGHSsheet' visibility to original state: $OriginalGHSSheetVisibility"
                        }
                    } catch { Write-Warning "PS: Could not reset GHS Non-Hazard sheet visibility."}
                    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($GHSSheet) | Out-Null
                    $GHSSheet = $null
                }
                if ($GHSWorkbook) {
                    $GHSWorkbook.Close($false) # Close without saving
                    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($GHSWorkbook) | Out-Null
                    $GHSWorkbook = $null
                    Write-Host "PS: GHS Non-Hazard workbook closed."
                }
                if ($OriginalExcelDisplayAlerts -ne $null) { # Restore original DisplayAlerts setting
                    $global:ExcelApp.DisplayAlerts = $OriginalExcelDisplayAlerts
                }
                if ($TempGHSWorkbookPath -and (Test-Path $TempGHSWorkbookPath)) {
                    try {
                        Start-Sleep -Milliseconds 200 # Brief pause
                        Remove-Item -Path $TempGHSWorkbookPath -Force -ErrorAction Stop
                        Write-Host "PS: Temporary GHS Non-Hazard workbook '$TempGHSWorkbookPath' deleted."
                    } catch {
                        Write-Warning "PS: Failed to delete temporary GHS Non-Hazard workbook '$TempGHSWorkbookPath'. Error: $($_.Exception.Message)"
                        $Result.details += "Warning: Failed to delete temp GHS Non-Hazard file $TempGHSWorkbookPath. "
                    }
                }
            }
        }
    }

    Write-Host "PS: Printing main blend sheet from '$OriginalTemplatePath'."
    $Sheet.PrintOut() 
    Start-Sleep -Seconds 3 
    Write-Host "PS: Main blend sheet print command sent (from temporary copy)."

    $Result.status = "success"
    $Result.message = "Blend sheet process completed for '$ItemCodeForTemplateLookup' using temporary copy."

} catch {
    $ErrorMessage = "PS_ERROR: $($_.Exception.ToString()) Starting at: $($_.InvocationInfo.ScriptLineNumber)"
    Write-Error $ErrorMessage
    $Result.status = "error"
    $Result.message = $ErrorMessage
    $Result.script_details = "$($_.ScriptStackTrace)"
} finally {
    Release-ComObjects

    if ($TempWorkbookPath -and (Test-Path $TempWorkbookPath)) {
        Write-Host "PS: Attempting to delete temporary workbook: $TempWorkbookPath"
        try {
            # Brief pause to ensure file lock is released, especially if Excel is slow to close
            Start-Sleep -Milliseconds 500 
            Remove-Item -Path $TempWorkbookPath -Force -ErrorAction Stop
            Write-Host "PS: Temporary workbook '$TempWorkbookPath' deleted successfully."
        } catch {
            Write-Warning "PS: Failed to delete temporary workbook '$TempWorkbookPath'. Error: $($_.Exception.Message). This might require manual cleanup from $env:TEMP."
            $Result.details += "Warning: Failed to auto-delete temp file $TempWorkbookPath. "
        }
    }
    Write-Host "PS: Invoke-DirectExcelEdit.ps1 finished."
    $Result | ConvertTo-Json -Compress | Write-Output
} 