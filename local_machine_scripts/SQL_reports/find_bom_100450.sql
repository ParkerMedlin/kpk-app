-- PowerShell command to execute:
-- $env:PGPASSWORD=(Get-Content .env | Select-String '^DB_PASS=(.*)$').Matches.Groups[1].Value; psql -h 192.168.178.169 -U postgres -d blendversedb -f local_machine_scripts/SQL_reports/find_bom_100450.sql

-- Find bill_of_materials entries that use component 100450 but not 100424
SELECT 
    b.item_code,
    b.item_description,
    b.component_item_code,
    b.component_item_description,
    b.qtyperbill,
    b.standard_uom
FROM 
    bill_of_materials b
WHERE 
    b.component_item_code = '100450'
    AND b.item_code NOT IN (
        SELECT item_code 
        FROM bill_of_materials 
        WHERE component_item_code = '100424'
    )
ORDER BY 
    b.item_code; 