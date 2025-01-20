# PostgreSQL GridView Query Runner

## Quick Command Template
```powershell
$env:PGPASSWORD=(Get-Content .env | Select-String '^DB_PASS=(.*)$').Matches.Groups[1].Value; psql -h 192.168.178.169 -U postgres -d blendversedb -A -F "`t" -f YOUR_SCRIPT.sql | ConvertFrom-Csv -Delimiter "`t" | Out-GridHtml -Title "$([System.IO.Path]::GetFileNameWithoutExtension('YOUR_SCRIPT.sql'))"
```

## Command Breakdown
1. **Password Extraction**:
   ```powershell
   $env:PGPASSWORD=(Get-Content .env | Select-String '^DB_PASS=(.*)$').Matches.Groups[1].Value
   ```
   - Reads DB_PASS from .env file
   - Sets it as environment variable

2. **PostgreSQL Connection**:
   - Host: 192.168.178.169
   - User: postgres
   - Database: blendversedb
   - Flags:
     - `-A`: Unaligned output mode
     - `-F "\t"`: Tab-separated output
     - `-f`: Specifies input script file

3. **PowerShell Processing**:
   - `ConvertFrom-Csv -Delimiter "\t"`: Converts tab-delimited output to objects
   - `Out-GridView`: Displays in sortable/filterable window

## Usage
1. Place your SQL script in `local_machine_scripts/SQL_reports/`
2. Replace `YOUR_SCRIPT.sql` with your script's filename
3. Optionally customize the GridView title

## Example
```powershell
# For a script named inventory_report.sql:
$env:PGPASSWORD=(Get-Content .env | Select-String '^DB_PASS=(.*)$').Matches.Groups[1].Value; psql -h 192.168.178.169 -U postgres -d blendversedb -A -F "`t" -f local_machine_scripts/SQL_reports/inventory_report.sql | ConvertFrom-Csv -Delimiter "`t" | Out-GridView -Title "Inventory Report"
``` 