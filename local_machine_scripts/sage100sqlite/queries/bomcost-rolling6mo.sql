WITH DateParams AS (
    SELECT 
        date(datetime('now', '-6 months')) as CutoffDate,
        COALESCE(:SalesOrderCutoffDate, '2025-01-01') as SalesOrderCutoffDate
),
RecentSalesItems AS (
    SELECT DISTINCT sod.ItemCode
    FROM SO_SalesOrderDetail sod
    CROSS JOIN DateParams dp
    WHERE date(sod.PromiseDate) >= dp.SalesOrderCutoffDate
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
    SELECT DISTINCT
        bd.BillNo as bomItemCode,
        ci.ItemCodeDesc as bomDescription,
        bd.ComponentItemCode,
        CAST(bd.QuantityPerBill AS REAL) as QtyPerBill
    FROM BM_BillDetail bd
    INNER JOIN RecentSalesItems rs ON bd.BillNo = rs.ItemCode
    LEFT JOIN CI_Item ci ON bd.BillNo = ci.ItemCode
),
BOMCosts AS (
    SELECT 
        bs.bomItemCode,
        bs.bomDescription,
        SUM(bs.QtyPerBill * COALESCE(cc.LowestCost, 0)) as LowestTotalBOMCost,
        SUM(bs.QtyPerBill * COALESCE(cc.HighestCost, 0)) as HighestTotalBOMCost,
        MAX(vc.Cost) as ItemHighestCost
    FROM BOMStructure bs
    LEFT JOIN ComponentCosts cc ON bs.ComponentItemCode = cc.ItemCode
    LEFT JOIN ValidCosts vc ON bs.bomItemCode = vc.ItemCode AND vc.rn = 1
    GROUP BY 
        bs.bomItemCode,
        bs.bomDescription
)
SELECT 
    bomItemCode,
    bomDescription,
    ROUND(LowestTotalBOMCost, 4) as LowestTotalBOMCost,
    ROUND(HighestTotalBOMCost, 4) as HighestTotalBOMCost,
    ROUND(ItemHighestCost, 4) as ItemHighestCost
FROM BOMCosts
ORDER BY bomItemCode