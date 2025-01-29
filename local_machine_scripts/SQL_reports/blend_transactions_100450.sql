-- First, let us divine which recipes contain our mysterious component
WITH parent_items AS (
    SELECT DISTINCT
        item_code AS parent_item,
        component_item_code,
        item_description AS parent_description,
        qtyperbill
    FROM bill_of_materials
    WHERE component_item_code = '100450'
)
-- Now, we shall peer into the transaction void for these items
SELECT 
    t.transactiondate,
    t.timeupdated,
    t.itemcode,
    p.parent_item AS "used_in_item",
    p.parent_description,
    p.qtyperbill AS "qty_per_parent",
    t.transactioncode,
    t.transactionqty,
    t.unitcost,
    t.extendedcost,
    t.warehousecode,
    t.imtransactionentrycomment AS transaction_notes,
    t.workticketno
FROM im_itemtransactionhistory t
JOIN parent_items p ON t.itemcode = '100450'
WHERE 
    t.itemcode = '100450'
    AND t.transactioncode IN ('BI', 'BR', 'BU')
ORDER BY 
    t.transactiondate DESC,
    t.timeupdated DESC;