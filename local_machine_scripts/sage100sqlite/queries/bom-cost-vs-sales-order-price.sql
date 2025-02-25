WITH DateParams AS (
    SELECT 
        date(datetime('now', '-6 months')) as CutoffDate,
        COALESCE(:SalesOrderCutoffDate, '2025-01-01') as SalesOrderCutoffDate
),
ValidCosts AS (
    SELECT 
        ic.ItemCode,
        CAST(ic.UnitCost AS REAL) as Cost,
        ic.DateCreated,
        ROW_NUMBER() OVER (PARTITION BY ic.ItemCode ORDER BY 
            CASE WHEN date(ic.DateCreated) >= (SELECT CutoffDate FROM DateParams) THEN 0 ELSE 1 END,
            ic.DateCreated DESC
        ) as rn
    FROM IM_ItemCost ic
    WHERE ic.TierType = '1'
    AND ic.ReceiptNo != 'OVERDIST'
    AND CAST(ic.UnitCost AS REAL) > 0
),
ComponentCosts AS (
    SELECT 
        ItemCode,
        MIN(Cost) as LowestCost,
        MAX(Cost) as HighestCost
    FROM (
        SELECT ItemCode, Cost FROM ValidCosts WHERE rn = 1
        UNION ALL
        SELECT ItemCode, CAST(StandardUnitCost AS REAL) as Cost
        FROM CI_Item 
        WHERE ItemCode LIKE '/%'
        AND CAST(StandardUnitCost AS REAL) > 0
    )
    GROUP BY ItemCode
),
BOMStructure AS (
    SELECT 
        bd.BillNo as bomItemCode,
        bd.ComponentItemCode,
        CAST(bd.QuantityPerBill AS REAL) as QtyPerBill
    FROM BM_BillDetail bd
    GROUP BY 
        bd.BillNo,
        bd.ComponentItemCode,
        bd.QuantityPerBill
),
BOMCosts AS (
    SELECT 
        bs.bomItemCode,
        SUM(bs.QtyPerBill * COALESCE(cc.LowestCost, 0)) as LowestTotalBOMCost,
        SUM(bs.QtyPerBill * COALESCE(cc.HighestCost, 0)) as HighestTotalBOMCost,
        MAX(vc.Cost) as ItemHighestCost
    FROM BOMStructure bs
    LEFT JOIN ComponentCosts cc ON bs.ComponentItemCode = cc.ItemCode
    LEFT JOIN ValidCosts vc ON bs.bomItemCode = vc.ItemCode AND vc.rn = 1
    GROUP BY 
        bs.bomItemCode
),
SalesOrderItems AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY SalesOrderNo, LineSeqNo, ItemCode
            ORDER BY id
        ) as rn
    FROM SO_SalesOrderDetail
    WHERE date(PromiseDate) >= (SELECT SalesOrderCutoffDate FROM DateParams)
)
SELECT 
    soi.id,
    soi.SalesOrderNo,
    soi.LineSeqNo,
    soi.ItemCode,
    soi.ItemCodeDesc,
    CAST(soi.QuantityOrdered AS REAL) as QuantityOrdered,
    CAST(soi.UnitPrice AS REAL) as UnitPrice,
    CAST(soi.UnitCost AS REAL) as UnitCost,
    CAST(soi.ExtensionAmt AS REAL) as ExtensionAmt,
    ROUND(bc.LowestTotalBOMCost, 4) as BOMLowestCost,
    ROUND(bc.HighestTotalBOMCost, 4) as BOMHighestCost,
    ROUND(bc.ItemHighestCost, 4) as ItemHighestCost,
    soi.PromiseDate
FROM SalesOrderItems soi
LEFT JOIN BOMCosts bc ON soi.ItemCode = bc.bomItemCode
WHERE soi.rn = 1
ORDER BY soi.SalesOrderNo, soi.LineSeqNo