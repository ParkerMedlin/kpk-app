-- Report: Sum of BR transaction quantities for BLEND items grouped by labor component
WITH labor_components AS (
    SELECT DISTINCT
        bom.item_code,
        bom.component_item_code AS labor_type
    FROM bill_of_materials bom
    WHERE bom.component_item_code LIKE '/BLD%'
      AND bom.component_item_code NOT LIKE '/BLDLABPCH'
),
blend_br_transactions AS (
    SELECT
        ith.itemcode,
        ith.transactionqty
    FROM im_itemtransactionhistory ith
    JOIN ci_item ci
      ON ci.itemcode = ith.itemcode
    WHERE ith.transactioncode = 'BR'
      AND ci.itemcodedesc LIKE 'BLEND%'
      AND ith.transactiondate >= DATE '2024-10-01'
      AND ith.transactiondate < DATE '2025-10-01'
)
SELECT
    lc.labor_type,
    labor_ci.standardunitcost AS labor_standard_unit_cost,
    SUM(t.transactionqty) AS total_transaction_qty
FROM blend_br_transactions t
JOIN labor_components lc
  ON lc.item_code = t.itemcode
LEFT JOIN ci_item labor_ci
  ON labor_ci.itemcode = lc.labor_type
GROUP BY
    lc.labor_type,
    labor_ci.standardunitcost
ORDER BY
    lc.labor_type;
