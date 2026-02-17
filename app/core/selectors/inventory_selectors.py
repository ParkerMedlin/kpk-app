from datetime import timedelta

from django.db import connection
from django.db.models import Q, Max, OuterRef, Subquery
from django.utils import timezone
from core.models import (
    ImItemWarehouse,
    BlendCountRecord,
    BlendComponentCountRecord,
    CiItem,
    BillOfMaterials,
    ComponentUsage,
    SubComponentUsage,
    AuditGroup,
    CountCollectionLink,
)
from prodverse.models import WarehouseCountRecord
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
    if not item_codes:
        return {}

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
    if not item_codes:
        return {}

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


def get_latest_transactions_for_items(item_codes):
    """
    Gets the most recent transaction details for a list of item codes.

    Args:
        item_codes: List of item codes to look up

    Returns:
        Dict mapping item codes to dicts of:
            - transactioncode
            - transactiondate
            - transactionqty
        Limited to transaction codes in ('BI', 'BR', 'II', 'IA')
    """
    if not item_codes:
        return {}

    placeholders = ','.join(['%s'] * len(item_codes))
    sql = f"""SELECT itemcode, transactioncode, transactiondate, transactionqty
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
        result = {
            item[0]: {
                'transactioncode': item[1],
                'transactiondate': item[2],
                'transactionqty': item[3],
            }
            for item in cursor.fetchall()
        }

    return result

def get_relevant_ci_item_itemcodes(filter_string, exclude_audit_group_items=True):
    """Get itemcodes from CI_Item table based on filter criteria.
    
    Retrieves itemcodes, descriptions and quantities on hand from CI_Item and IM_ItemWarehouse
    tables based on the provided filter string. Used to filter items for inventory counts.

    Args:
        filter_string (str): Type of items to retrieve - 'blends_and_components', 'blends', 'components', 'non_blend', or None for all
        exclude_audit_group_items (bool): When True, exclude items assigned to audit groups.

    Returns:
        list: List of tuples containing (itemcode, itemcodedesc, quantityonhand) for matching items
        
    Note:
        Optionally excludes items already in audit groups and specific excluded itemcodes.
        Only returns items with positive quantity on hand.
    """
    audit_group_clause = (
        "AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)"
        if exclude_audit_group_items
        else ""
    )
    if filter_string == 'blends_and_components':
        sql_query = f"""
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE ( itemcodedesc like 'BLEND%' 
                or itemcodedesc like 'CHEM%' 
                or itemcodedesc like 'DYE%' 
                or itemcodedesc like 'FRAGRANCE%')
            {audit_group_clause}
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    elif filter_string == 'blends':
        sql_query = f"""
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (itemcodedesc like 'BLEND%')
            {audit_group_clause}
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    elif filter_string == 'components':
        sql_query = f"""
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand, ci.standardunitofmeasure FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (itemcodedesc like 'CHEM%'
                or itemcodedesc like 'DYE%'
                or itemcodedesc like 'FRAGRANCE%')
            {audit_group_clause}
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    elif filter_string == 'non_blend':
        sql_query = f"""
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
            {audit_group_clause}
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    else:
        sql_query = f"""
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
            {audit_group_clause}
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
        
    with connection.cursor() as cursor:
        cursor.execute(sql_query)
        missing_items = [[item[0], item[1], item[3]] for item in cursor.fetchall()]

    return missing_items

def get_ci_items_for_audit_group(record_type=None):
    """Return CI items eligible for display in the audit-group view."""
    queryset = (
        CiItem.objects
        .exclude(itemcode__startswith='/')
        .exclude(itemcodedesc__istartswith='do not use')
    )

    if record_type == 'blend':
        queryset = queryset.filter(itemcodedesc__istartswith='BLEND')
    elif record_type == 'blendcomponent':
        queryset = queryset.filter(
            Q(itemcodedesc__istartswith='CHEM') |
            Q(itemcodedesc__istartswith='DYE') |
            Q(itemcodedesc__istartswith='FRAGRANCE')
        )
    elif record_type is None:
        queryset = queryset.filter(
            Q(itemcodedesc__istartswith='BLEND') |
            Q(itemcodedesc__istartswith='CHEM') |
            Q(itemcodedesc__istartswith='DYE') |
            Q(itemcodedesc__istartswith='FRAGRANCE')
        )

    return queryset.distinct()


def get_qty_and_units_for_items(item_codes):
    """Return mapping of item_code -> formatted quantity with units."""
    if not item_codes:
        return {}

    qty_and_units = {}
    bills = BillOfMaterials.objects.filter(component_item_code__in=item_codes).exclude(standard_uom__isnull=True)
    for bill in bills:
        qty_value = bill.qtyonhand if bill.qtyonhand is not None else 0
        qty_and_units[bill.component_item_code] = f"{round(float(qty_value), 4)} {bill.standard_uom}"
    return qty_and_units


def get_upcoming_runs_for_items(item_codes, record_type=None):
    """Return upcoming production runs keyed by item code and count table name."""
    count_table_lookup = {
        'blend': 'core_blendcountrecord',
        'blendcomponent': 'core_blendcomponentcountrecord',
        'warehouse': 'prodverse_warehousecountrecord',
    }
    count_table = count_table_lookup.get(record_type, 'prodverse_warehousecountrecord')

    if not item_codes:
        return {}, count_table

    if record_type == 'blend':
        usage_qs = ComponentUsage.objects.filter(component_item_code__in=item_codes)
        runs = {usage.component_item_code: usage.start_time for usage in usage_qs.order_by('start_time')}
    else:
        usage_qs = SubComponentUsage.objects.filter(subcomponent_item_code__in=item_codes)
        runs = {usage.subcomponent_item_code: usage.start_time for usage in usage_qs.order_by('start_time')}

    return runs, count_table


def get_audit_group_records(item_codes):
    """Return AuditGroup records keyed by item_code."""
    if not item_codes:
        return {}

    return {record.item_code: record for record in AuditGroup.objects.filter(item_code__in=item_codes)}


def get_distinct_audit_groups(record_type=None):
    """Return ordered list of distinct audit group names."""
    audit_groups = AuditGroup.objects
    if record_type:
        audit_groups = audit_groups.filter(item_type=record_type)
    else:
        audit_groups = audit_groups.filter(item_type__in=['blend', 'blendcomponent'])
    return list(
        audit_groups
        .values_list('audit_group', flat=True)
        .distinct()
        .order_by('audit_group')
    )


def get_recently_counted_item_codes(days=3):
    """Return set of item codes included in countlists created within the last X days."""
    try:
        days_value = int(days)
    except (TypeError, ValueError):
        days_value = 3

    if days_value < 0:
        days_value = 0

    cutoff = timezone.now() - timedelta(days=days_value)
    recent_links = CountCollectionLink.objects.filter(created_at__gte=cutoff)

    count_ids = set()
    item_codes = set()
    for link in recent_links:
        for raw_id in link.count_id_list or []:
            if raw_id is None:
                continue
            if isinstance(raw_id, int):
                count_ids.add(raw_id)
                continue
            raw_str = str(raw_id).strip()
            if not raw_str:
                continue
            if raw_str.isdigit():
                count_ids.add(int(raw_str))
            else:
                item_codes.add(raw_str)

    if count_ids:
        blend_codes = BlendCountRecord.objects.filter(id__in=count_ids).values_list('item_code', flat=True)
        component_codes = BlendComponentCountRecord.objects.filter(id__in=count_ids).values_list('item_code', flat=True)
        item_codes.update(code for code in blend_codes if code)
        item_codes.update(code for code in component_codes if code)

    return item_codes


def get_last_counted_dates(item_codes):
    """Return mapping of item_code -> last counted_date for provided items."""
    if not item_codes:
        return {}

    blend_dates = dict(
        BlendCountRecord.objects
        .filter(item_code__in=item_codes, counted_date__isnull=False, counted=True)
        .values('item_code')
        .annotate(last_date=Max('counted_date'))
        .values_list('item_code', 'last_date')
    )

    component_dates = dict(
        BlendComponentCountRecord.objects
        .filter(item_code__in=item_codes, counted_date__isnull=False, counted=True)
        .values('item_code')
        .annotate(last_date=Max('counted_date'))
        .values_list('item_code', 'last_date')
    )

    last_dates = dict(blend_dates)
    for item_code, date_value in component_dates.items():
        existing = last_dates.get(item_code)
        if existing is None or (date_value and date_value > existing):
            last_dates[item_code] = date_value

    for item_code in item_codes:
        last_dates.setdefault(item_code, None)

    return last_dates


def get_latest_count_dates_any(item_codes):
    """Return mapping of item_code -> latest counted_date regardless of counted flag."""
    if not item_codes:
        return {}

    blend_dates = dict(
        BlendCountRecord.objects
        .filter(item_code__in=item_codes, counted_date__isnull=False)
        .values('item_code')
        .annotate(last_date=Max('counted_date'))
        .values_list('item_code', 'last_date')
    )

    component_dates = dict(
        BlendComponentCountRecord.objects
        .filter(item_code__in=item_codes, counted_date__isnull=False)
        .values('item_code')
        .annotate(last_date=Max('counted_date'))
        .values_list('item_code', 'last_date')
    )

    last_dates = dict(blend_dates)
    for item_code, date_value in component_dates.items():
        existing = last_dates.get(item_code)
        if existing is None or (date_value and date_value > existing):
            last_dates[item_code] = date_value

    for item_code in item_codes:
        last_dates.setdefault(item_code, None)

    return last_dates


def get_latest_count_details(item_codes):
    """
    Return mapping of item_code -> latest count details for counted items.

    Uses ORM subqueries to fetch the row with MAX(counted_date) per item_code
    from both BlendCountRecord and BlendComponentCountRecord, and prefers the
    most recent date when an item exists in both.
    """
    if not item_codes:
        return {}

    def build_latest_counts(model):
        latest_qs = model.objects.filter(
            item_code=OuterRef('item_code'),
            counted=True,
            counted_date__isnull=False,
        ).order_by('-counted_date')

        rows = (
            model.objects
            .filter(item_code__in=item_codes, counted=True, counted_date__isnull=False)
            .values('item_code')
            .distinct()
            .annotate(
                counted_date=Subquery(latest_qs.values('counted_date')[:1]),
                counted=Subquery(latest_qs.values('counted')[:1]),
                counted_quantity=Subquery(latest_qs.values('counted_quantity')[:1]),
                variance=Subquery(latest_qs.values('variance')[:1]),
            )
        )
        return {
            row['item_code']: {
                'counted_date': row['counted_date'],
                'counted': row['counted'],
                'counted_quantity': row['counted_quantity'],
                'variance': row['variance'],
            }
            for row in rows
        }

    blend_counts = build_latest_counts(BlendCountRecord)
    component_counts = build_latest_counts(BlendComponentCountRecord)

    merged = dict(blend_counts)
    for item_code, details in component_counts.items():
        existing = merged.get(item_code)
        if existing is None:
            merged[item_code] = details
            continue
        existing_date = existing.get('counted_date')
        new_date = details.get('counted_date')
        if existing_date is None or (new_date and new_date > existing_date):
            merged[item_code] = details

    for item_code in item_codes:
        merged.setdefault(
            item_code,
            {
                'counted_date': None,
                'counted': None,
                'counted_quantity': None,
                'variance': None,
            },
        )

    return merged


def get_count_status_rows(record_type=None, counted_filter='all'):
    """
    Return count status rows with latest transaction and latest count details.

    This is optimized as a single SQL pipeline using CTEs and DISTINCT ON
    to avoid expensive Python-side joins/merges and correlated subqueries.
    """
    record_type_clause = """
        AND (
            ci.itemcodedesc ILIKE 'BLEND%%'
            OR ci.itemcodedesc ILIKE 'CHEM%%'
            OR ci.itemcodedesc ILIKE 'DYE%%'
            OR ci.itemcodedesc ILIKE 'FRAGRANCE%%'
        )
    """
    if record_type == 'blend':
        record_type_clause = "AND ci.itemcodedesc ILIKE 'BLEND%%'"
    elif record_type == 'blendcomponent':
        record_type_clause = """
            AND (
                ci.itemcodedesc ILIKE 'CHEM%%'
                OR ci.itemcodedesc ILIKE 'DYE%%'
                OR ci.itemcodedesc ILIKE 'FRAGRANCE%%'
            )
        """

    counted_filter_clause = ""
    if counted_filter == 'yes':
        counted_filter_clause = "WHERE rr.counted IS TRUE"
    elif counted_filter == 'not_yes':
        counted_filter_clause = "WHERE rr.counted IS DISTINCT FROM TRUE"

    sql = f"""
        WITH filtered_items AS (
            SELECT DISTINCT ci.itemcode AS item_code, ci.itemcodedesc AS item_description
            FROM ci_item ci
            WHERE ci.itemcode IS NOT NULL
              AND ci.itemcode NOT LIKE '/%%'
              AND (ci.itemcodedesc IS NULL OR ci.itemcodedesc NOT ILIKE 'DO NOT USE%%')
              {record_type_clause}
        ),
        latest_txn AS (
            SELECT DISTINCT ON (ith.itemcode)
                ith.itemcode AS item_code,
                ith.transactioncode,
                ith.transactiondate,
                ith.transactionqty
            FROM im_itemtransactionhistory ith
            INNER JOIN filtered_items fi ON fi.item_code = ith.itemcode
            WHERE ith.transactioncode IN ('BI', 'BR', 'II', 'IA')
            ORDER BY ith.itemcode, ith.transactiondate DESC, ith.id DESC
        ),
        latest_blend_count AS (
            SELECT DISTINCT ON (b.item_code)
                b.item_code,
                b.counted_date,
                b.counted,
                b.counted_quantity,
                b.variance,
                b.collection_id
            FROM core_blendcountrecord b
            INNER JOIN filtered_items fi ON fi.item_code = b.item_code
            WHERE b.counted = TRUE
              AND b.counted_date IS NOT NULL
            ORDER BY b.item_code, b.counted_date DESC, b.id DESC
        ),
        latest_component_count AS (
            SELECT DISTINCT ON (c.item_code)
                c.item_code,
                c.counted_date,
                c.counted,
                c.counted_quantity,
                c.variance,
                c.collection_id
            FROM core_blendcomponentcountrecord c
            INNER JOIN filtered_items fi ON fi.item_code = c.item_code
            WHERE c.counted = TRUE
              AND c.counted_date IS NOT NULL
            ORDER BY c.item_code, c.counted_date DESC, c.id DESC
        ),
        qty_on_hand AS (
            SELECT
                iw.itemcode AS item_code,
                SUM(iw.quantityonhand) AS qty_on_hand
            FROM im_itemwarehouse iw
            INNER JOIN filtered_items fi ON fi.item_code = iw.itemcode
            WHERE iw.warehousecode = 'MTG'
            GROUP BY iw.itemcode
        ),
        report_rows AS (
            SELECT
                fi.item_code,
                COALESCE(fi.item_description, '') AS item_description,
                qoh.qty_on_hand,
                lt.transactioncode,
                lt.transactiondate,
                lt.transactionqty,
                CASE
                    WHEN lbc.counted_date IS NULL THEN lcc.counted_date
                    WHEN lcc.counted_date IS NULL THEN lbc.counted_date
                    WHEN lbc.counted_date >= lcc.counted_date THEN lbc.counted_date
                    ELSE lcc.counted_date
                END AS counted_date,
                CASE
                    WHEN lbc.counted_date IS NULL THEN lcc.counted
                    WHEN lcc.counted_date IS NULL THEN lbc.counted
                    WHEN lbc.counted_date >= lcc.counted_date THEN lbc.counted
                    ELSE lcc.counted
                END AS counted,
                CASE
                    WHEN lbc.counted_date IS NULL THEN lcc.counted_quantity
                    WHEN lcc.counted_date IS NULL THEN lbc.counted_quantity
                    WHEN lbc.counted_date >= lcc.counted_date THEN lbc.counted_quantity
                    ELSE lcc.counted_quantity
                END AS counted_quantity,
                CASE
                    WHEN lbc.counted_date IS NULL THEN lcc.variance
                    WHEN lcc.counted_date IS NULL THEN lbc.variance
                    WHEN lbc.counted_date >= lcc.counted_date THEN lbc.variance
                    ELSE lcc.variance
                END AS variance,
                CASE
                    WHEN lbc.counted_date IS NULL THEN COALESCE(ccl_lcc.is_hidden, FALSE)
                    WHEN lcc.counted_date IS NULL THEN COALESCE(ccl_lbc.is_hidden, FALSE)
                    WHEN lbc.counted_date >= lcc.counted_date THEN COALESCE(ccl_lbc.is_hidden, FALSE)
                    ELSE COALESCE(ccl_lcc.is_hidden, FALSE)
                END AS is_hidden_collection
            FROM filtered_items fi
            LEFT JOIN qty_on_hand qoh ON qoh.item_code = fi.item_code
            LEFT JOIN latest_txn lt ON lt.item_code = fi.item_code
            LEFT JOIN latest_blend_count lbc ON lbc.item_code = fi.item_code
            LEFT JOIN latest_component_count lcc ON lcc.item_code = fi.item_code
            LEFT JOIN core_countcollectionlink ccl_lbc ON ccl_lbc.collection_id = lbc.collection_id
            LEFT JOIN core_countcollectionlink ccl_lcc ON ccl_lcc.collection_id = lcc.collection_id
        )
        SELECT
            rr.item_code,
            rr.item_description,
            rr.qty_on_hand,
            rr.transactioncode,
            rr.transactiondate,
            rr.transactionqty,
            rr.counted_date,
            rr.counted,
            rr.counted_quantity,
            rr.variance,
            rr.is_hidden_collection
        FROM report_rows rr
        {counted_filter_clause}
        ORDER BY rr.item_code;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return [
        {
            'item_code': row[0],
            'item_description': row[1],
            'qty_on_hand': row[2],
            'transaction_code': row[3],
            'transaction_date': row[4],
            'transaction_qty': row[5],
            'counted_date': row[6],
            'counted': row[7],
            'counted_quantity': row[8],
            'variance': row[9],
            'is_hidden_collection': row[10],
        }
        for row in rows
    ]
