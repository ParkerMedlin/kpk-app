WITH ConsumedQuantity AS (
    SELECT 
        ith.entryno,
        ith.itemcode, 
        ith.transactiondate,
        ith.timeupdated,
        bom.qtyperbill,
        ith.transactionqty,
        ABS(ith.transactionqty) * (bom.qtyperbill / 0.975) AS calculated_consumed_qty
    FROM 
        im_itemtransactionhistory ith
    JOIN 
        bill_of_materials bom ON ith.itemcode = bom.item_code
    WHERE 
        ith.transactioncode IN ('BI', 'BR')
        AND bom.component_item_code = '87700.B'
),
ActualQuantity AS (
    SELECT 
        entryno,
        itemcode, 
        transactiondate,
        timeupdated,
        ABS(transactionqty) AS actual_transaction_qty
    FROM 
        im_itemtransactionhistory
    WHERE 
        itemcode = '87700.B'
        AND transactioncode IN ('BI', 'BR')
)
SELECT 
    cq.entryno,
    cq.itemcode AS component_itemcode,
    cq.transactiondate,
    cq.timeupdated,
    TO_CHAR(cq.qtyperbill, 'FM999999999.0000') AS qtyperbill,
    TO_CHAR(cq.transactionqty, 'FM999999999.0000') AS transactionqty,
    TO_CHAR(cq.calculated_consumed_qty, 'FM999999999.0000') AS calculated_consumed_qty,
    TO_CHAR(aq.actual_transaction_qty, 'FM999999999.0000') AS actual_transaction_qty,
    TO_CHAR((cq.calculated_consumed_qty - aq.actual_transaction_qty), 'FM999999999.0000') AS discrepancy
FROM 
    ConsumedQuantity cq
JOIN 
    ActualQuantity aq ON cq.entryno = aq.entryno
    AND cq.transactiondate = aq.transactiondate
    AND cq.timeupdated = aq.timeupdated
ORDER BY 
    cq.transactiondate DESC, cq.timeupdated DESC;