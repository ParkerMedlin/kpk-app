from django.db import connection
from core.models import ImItemWarehouse, BlendCountRecord, BlendComponentCountRecord, WarehouseCountRecord
import logging
logger = logging.getLogger(__name__)

def get_latest_count_dates(item_codes, count_table):
    """
    Gets the most recent count dates and quantities for a list of item codes.
    
    Args:
        item_codes: List of item codes to look up
        count_table: Name of the table containing count records
        
    Returns:
        Dict mapping item codes to tuples of (counted_date, counted_quantity)
        for the most recent count of each item where counted=TRUE
    """
    placeholders = ','.join(['%s'] * len(item_codes))
    sql = f"""SELECT item_code, counted_date as latest_date, counted_quantity
            FROM {count_table}
            WHERE (item_code, counted_date) IN (
                SELECT item_code, MAX(counted_date)
                FROM {count_table}
                WHERE item_code IN ({placeholders})
                and counted=TRUE
                GROUP BY item_code
            )
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, item_codes)
        result = {item[0]: (item[1], item[2]) for item in cursor.fetchall()}

    return result

def get_item_quantity(item_code):
    try:
        item_warehouse = ImItemWarehouse.objects.get(
            itemcode=item_code, 
            warehousecode='MTG'
        )
        quantity_on_hand = item_warehouse.quantityonhand
    except ImItemWarehouse.DoesNotExist:
        quantity_on_hand = 0
    
    return quantity_on_hand

def get_count_record_model(record_type):
    """Get the appropriate count record model based on record type.

    Maps record type strings to their corresponding Django model classes for
    inventory count records.

    Args:
        record_type (str): Type of count record ('blend', 'blendcomponent', or 'warehouse')

    Returns:
        Model: Django model class for the specified record type
    """
    if record_type == 'blend':
        model = BlendCountRecord
    elif record_type == 'blendcomponent':
        model = BlendComponentCountRecord
    elif record_type == 'warehouse':
        model = WarehouseCountRecord
    return model

def get_excess_blends():
    sql = """
        SELECT
            ci.itemcode,
            ci.itemcodedesc,
            COALESCE(ct.total_demand, 0) AS total_demand,
            w.quantityonhand AS quantity_on_hand,
            COALESCE(ct.total_demand, 0) - w.quantityonhand AS excess_inventory,
            ci.averageunitcost,
            abs(ci.averageunitcost * (COALESCE(ct.total_demand, 0) - w.quantityonhand)) as excess_inventory_value
            FROM ci_item ci
            -- First, cull by description and limit to MTG warehouse stock > 0
            JOIN im_itemwarehouse w
                ON w.itemcode       = ci.itemcode
            AND w.warehousecode  = 'MTG'
            AND w.quantityonhand >  0
            -- Then aggregate demand only for surviving items
            LEFT JOIN (
                SELECT
                component_item_code AS itemcode,
                MAX(cumulative_component_run_qty) AS total_demand
                FROM component_usage
                GROUP BY component_item_code
            ) ct
                ON ct.itemcode = ci.itemcode
            WHERE
            ci.itemcodedesc LIKE 'BLEND%'
            and ci.procurementtype = 'M'
            and ci.itemcode not in ('100501K','841BLK.B','841WHT.B')
            AND COALESCE(ct.total_demand, 0) < w.quantityonhand;
        """

    excess_blends = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()
        for item in result:
            excess_blends.append({
                'item_code': item[0],
                'item_description': item[1],
                'total_demand': item[2],
                'quantity_on_hand': item[3],
                'excess_inventory': item[4],
                'average_unit_cost': item[5],
                'excess_inventory_value': item[6]
            })
    
    excess_blends.sort(key=lambda x: x['excess_inventory_value'], reverse=True)
    total_excess_inventory_value = sum(item['excess_inventory_value'] for item in excess_blends)

    return {'query_results' : excess_blends, 'total_excess_inventory_value' : total_excess_inventory_value}

def get_transactions_for_bom_check():
    """Get transactions for bill of materials quantity checking.
    
    Retrieves transactions from the database where ingredient quantities used in blends
    deviate significantly from expected amounts based on bill of materials. Specifically:
    
    - Looks at 'BI' and 'BR' transactions
    - Filters for ingredients that are Blends, Chemicals, or Fragrances
    - Flags transactions  where actual quantity differs from expected by >25%
    - Joins with lot records and bill of materials to calculate expected quantities
    
    Returns:
        list: Database rows containing transaction details including:
            - Item codes and descriptions
            - Transaction dates, codes and quantities 
            - Lot numbers and blend item codes
            - Expected quantities from bill of materials
            - Actual vs expected quantity variances
    """
    sql = """
        SELECT ith.itemcode, ith.transactioncode, ith.transactiondate, ith.entryno, ABS(ith.transactionqty) as transactionqty,
            ci.itemcodedesc as item_description, clr.lot_number, clr.item_code as blend_item_code,
            clr.lot_quantity, bom.qtyperbill, ci.shipweight, ci.standardunitofmeasure,
            (bom.qtyperbill * clr.lot_quantity) AS expected_quantity, ABS(ith.transactionqty) as transactionqty,
            (ABS(ith.transactionqty) - (bom.qtyperbill * clr.lot_quantity)) AS transaction_variance,
            (ABS(ith.transactionqty) / (bom.qtyperbill * clr.lot_quantity)) as variance_ratio
        FROM im_itemtransactionhistory ith
        JOIN ci_item ci ON ith.itemcode = ci.itemcode
        LEFT JOIN core_lotnumrecord clr ON SUBSTRING(ith.entryno, 2) = clr.lot_number
        LEFT JOIN bill_of_materials bom ON clr.item_code = bom.item_code AND ith.itemcode = bom.component_item_code
        WHERE ith.transactioncode in ('BI', 'BR')
        AND (
            ci.itemcodedesc LIKE 'BLEND%' OR
            ci.itemcodedesc LIKE 'CHEM%' OR
            ci.itemcodedesc LIKE 'FRAGRANCE%'
        )
        AND NOT (ith.transactioncode = 'BI' AND ci.itemcodedesc LIKE 'BLEND%')
        AND NOT (
            ABS(ith.transactionqty) BETWEEN (bom.qtyperbill * clr.lot_quantity) * 0.75 AND (bom.qtyperbill * clr.lot_quantity) * 1.25
        )
        ORDER BY ith.transactiondate DESC;
        """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        result = cursor.fetchall()
    
    return result

def get_latest_transaction_dates(item_codes):
    """
    Gets the most recent transaction dates and codes for a list of item codes.
    
    Args:
        item_codes: List of item codes to look up
        
    Returns:
        Dict mapping item codes to tuples of (transaction_date, transaction_code)
        where transaction_code is one of: 'BI', 'BR', 'II', 'IA'
    """
    placeholders = ','.join(['%s'] * len(item_codes))
    sql = f"""SELECT itemcode, transactiondate, transactioncode
            FROM im_itemtransactionhistory
            WHERE (itemcode, transactiondate) IN (
                SELECT itemcode, MAX(transactiondate)
                FROM im_itemtransactionhistory
                WHERE itemcode IN ({placeholders})
                AND transactioncode IN ('BI', 'BR', 'II', 'IA')
                GROUP BY itemcode
            )
            AND transactioncode IN ('BI', 'BR', 'II', 'IA')
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, item_codes)
        result = {item[0]: (item[1], item[2]) for item in cursor.fetchall()}
    
    return result

def get_lot_number_quantities(item_code):
    """
    Gets quantities and transaction dates for lot numbers of a given item code.

    Queries im_itemcost table to get quantity on hand and transaction date for each 
    lot number (receipt number) associated with the item code.

    Args:
        item_code (str): The item code to look up lot numbers for
        
    Returns:
        dict: Mapping of lot numbers to tuples of (quantity_on_hand, transaction_date)
    """

    sql = f"""
    SELECT receiptno, quantityonhand, transactiondate
    FROM im_itemcost
    WHERE itemcode = '{item_code}'
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, item_code)
        result = {item[0]: (item[1], item[2]) for item in cursor.fetchall()}
    
    return result

def get_relevant_ci_item_itemcodes(filter_string):
    """Get itemcodes from CI_Item table based on filter criteria.
    
    Retrieves itemcodes, descriptions and quantities on hand from CI_Item and IM_ItemWarehouse
    tables based on the provided filter string. Used to filter items for inventory counts.

    Args:
        filter_string (str): Type of items to retrieve - 'blend_components', 'blends', or 'non_blend'

    Returns:
        list: List of tuples containing (itemcode, itemcodedesc, quantityonhand) for matching items
        
    Note:
        Excludes items already in audit groups and specific excluded itemcodes.
        Only returns items with positive quantity on hand.
    """
    if filter_string == 'blends_and_components':
        sql_query = """
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE ( itemcodedesc like 'BLEND%' 
                or itemcodedesc like 'CHEM%' 
                or itemcodedesc like 'DYE%' 
                or itemcodedesc like 'FRAGRANCE%')
            AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    elif filter_string == 'blends':
        sql_query = """
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (itemcodedesc like 'BLEND%')
            AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    elif filter_string == 'non_blend':
        sql_query = """
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (or itemcodedesc like 'ADAPTER%' 
                or itemcodedesc like 'APPLICATOR%' 
                or itemcodedesc like 'BAG%' 
                or itemcodedesc like 'BAIL%' 
                or itemcodedesc like 'BASE%' 
                or itemcodedesc like 'BILGE PAD%' 
                or itemcodedesc like 'BOTTLE%' 
                or itemcodedesc like 'CABLE TIE%' 
                or itemcodedesc like 'CAN%' 
                or itemcodedesc like 'CAP%' 
                or itemcodedesc like 'CARD%' 
                or itemcodedesc like 'CARTON%' 
                or itemcodedesc like 'CLAM%' 
                or itemcodedesc like 'CLIP%' 
                or itemcodedesc like 'COLORANT%' 
                or itemcodedesc like 'CUP%' 
                or itemcodedesc like 'DISPLAY%' 
                or itemcodedesc like 'DIVIDER%' 
                or itemcodedesc like 'DRUM%' 
                or itemcodedesc like 'ENVELOPE%' 
                or itemcodedesc like 'FILLED BOTTLE%' 
                or itemcodedesc like 'FILLER%' 
                or itemcodedesc like 'FLAG%' 
                or itemcodedesc like 'FUNNEL%' 
                or itemcodedesc like 'GREASE%' 
                or itemcodedesc like 'HANGER%' 
                or itemcodedesc like 'HEADER%' 
                or itemcodedesc like 'HOLDER%' 
                or itemcodedesc like 'HOSE%' 
                or itemcodedesc like 'INSERT%' 
                or itemcodedesc like 'JAR%' 
                or itemcodedesc like 'LID%' 
                or itemcodedesc like 'PAD%' 
                or itemcodedesc like 'PAIL%' 
                or itemcodedesc like 'PLUG%' 
                or itemcodedesc like 'POUCH%' 
                or itemcodedesc like 'PUTTY STICK%' 
                or itemcodedesc like 'RESIN%' 
                or itemcodedesc like 'SCOOT%' 
                or itemcodedesc like 'SEAL DISC%' 
                or itemcodedesc like 'SLEEVE%' 
                or itemcodedesc like 'SPONGE%' 
                or itemcodedesc like 'STRIP%' 
                or itemcodedesc like 'SUPPORT%' 
                or itemcodedesc like 'TOILET PAPER%' 
                or itemcodedesc like 'TOOL%' 
                or itemcodedesc like 'TOTE%' 
                or itemcodedesc like 'TRAY%' 
                or itemcodedesc like 'TUB%' 
                or itemcodedesc like 'TUBE%')
            AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    else:
        sql_query = """
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (itemcodedesc like 'BLEND%' 
                or itemcodedesc like 'CHEM%' 
                or itemcodedesc like 'DYE%' 
                or itemcodedesc like 'FRAGRANCE%' 
                or itemcodedesc like 'ADAPTER%' 
                or itemcodedesc like 'APPLICATOR%' 
                or itemcodedesc like 'BAG%' 
                or itemcodedesc like 'BAIL%' 
                or itemcodedesc like 'BASE%' 
                or itemcodedesc like 'BILGE PAD%' 
                or itemcodedesc like 'BOTTLE%' 
                or itemcodedesc like 'CABLE TIE%' 
                or itemcodedesc like 'CAN%' 
                or itemcodedesc like 'CAP%' 
                or itemcodedesc like 'CARD%' 
                or itemcodedesc like 'CARTON%' 
                or itemcodedesc like 'CLAM%' 
                or itemcodedesc like 'CLIP%' 
                or itemcodedesc like 'COLORANT%' 
                or itemcodedesc like 'CUP%' 
                or itemcodedesc like 'DISPLAY%' 
                or itemcodedesc like 'DIVIDER%' 
                or itemcodedesc like 'DRUM%' 
                or itemcodedesc like 'ENVELOPE%' 
                or itemcodedesc like 'FILLED BOTTLE%' 
                or itemcodedesc like 'FILLER%' 
                or itemcodedesc like 'FLAG%' 
                or itemcodedesc like 'FUNNEL%' 
                or itemcodedesc like 'GREASE%' 
                or itemcodedesc like 'HANGER%' 
                or itemcodedesc like 'HEADER%' 
                or itemcodedesc like 'HOLDER%' 
                or itemcodedesc like 'HOSE%' 
                or itemcodedesc like 'INSERT%' 
                or itemcodedesc like 'JAR%' 
                or itemcodedesc like 'LID%' 
                or itemcodedesc like 'PAD%' 
                or itemcodedesc like 'PAIL%' 
                or itemcodedesc like 'PLUG%' 
                or itemcodedesc like 'POUCH%' 
                or itemcodedesc like 'PUTTY STICK%' 
                or itemcodedesc like 'RESIN%' 
                or itemcodedesc like 'SCOOT%' 
                or itemcodedesc like 'SEAL DISC%' 
                or itemcodedesc like 'SLEEVE%' 
                or itemcodedesc like 'SPONGE%' 
                or itemcodedesc like 'STRIP%' 
                or itemcodedesc like 'SUPPORT%' 
                or itemcodedesc like 'TOILET PAPER%' 
                or itemcodedesc like 'TOOL%' 
                or itemcodedesc like 'TOTE%' 
                or itemcodedesc like 'TRAY%' 
                or itemcodedesc like 'TUB%' 
                or itemcodedesc like 'TUBE%')
            AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
        
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        missing_items = [[item[0], item[1], item[3]] for item in cursor.fetchall()]

    return missing_items