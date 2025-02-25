SELECT DISTINCT
    vs.VendorNo,
    vs.VendorName AS Vendor,
    vs.TransactionDate,
    vs.ItemCode,
    vs.ItemCodeDesc,
    vs.UnitCost,
    vs.QtyPurchased,
    vs.ExtendedCost,
    vs.YTDRunningTotal
FROM 
    (SELECT 
        poh.VendorNo,
        poh.PurchaseName AS VendorName,
        ith.TransactionDate,
        ith.ItemCode,
        ci.ItemCodeDesc,
        ith.UnitCost,
        ith.TransactionQty AS QtyPurchased,
        ith.ExtendedCost,
        -- Extract year from transaction date for filtering
        CAST(strftime('%Y', ith.TransactionDate) AS INTEGER) AS TransactionYear,
        -- Create a partition by vendor and year for the running total
        SUM(CAST(ith.ExtendedCost AS REAL)) OVER (
            PARTITION BY poh.VendorNo, strftime('%Y', ith.TransactionDate) 
            ORDER BY ith.TransactionDate
        ) AS YTDRunningTotal
    FROM 
        IM_ItemTransactionHistory ith
    JOIN 
        -- Use a more specific join to get only the latest/relevant PO header
        (SELECT 
            ph.VendorNo, 
            ph.APDivisionNo, 
            ph.PurchaseName,
            -- Use row_number to get the most recent PO for each vendor
            ROW_NUMBER() OVER (PARTITION BY ph.VendorNo, ph.APDivisionNo ORDER BY ph.DateUpdated DESC, ph.TimeUpdated DESC) as rn
         FROM 
            PO_PurchaseOrderHeader ph) poh 
        ON ith.VendorNo = poh.VendorNo 
        AND ith.APDivisionNo = poh.APDivisionNo
        AND poh.rn = 1  -- Only get the most recent PO header
    LEFT JOIN 
        CI_Item ci ON ith.ItemCode = ci.ItemCode
    WHERE 
        -- Only include purchase transactions (PO transaction code)
        ith.TransactionCode = 'PO'
        -- Filter for positive quantities (actual purchases, not returns)
        AND CAST(ith.TransactionQty AS REAL) > 0
    ) vs
WHERE 
    vs.TransactionYear IN (2023, 2024, 2025)
ORDER BY 
    vs.VendorNo, vs.TransactionDate; 