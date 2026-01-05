from django.db import connection
from django.utils import timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import logging

CENTRAL_TZ = ZoneInfo('America/Chicago')

logger = logging.getLogger(__name__)


# =============================================================================
# XmR TANK CONTROL LIMITS FUNCTIONS
# =============================================================================

def get_all_tank_names():
    """Get list of all tank names from the tank level log."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT tank_name
            FROM core_tanklevellog
            ORDER BY tank_name
        """)
        return [row[0] for row in cursor.fetchall()]


def calculate_xmr_control_limits(tank_name, lookback_days=60):
    """
    Calculate XmR control limits for a tank based on historical non-op hours data.

    Uses Wheeler's Statistical Process Control method:
    - UCL = X̄ + 2.66 * mR̄
    - LCL = X̄ - 2.66 * mR̄

    Non-operation hours: 6pm-3am Mon-Fri, all day Sat/Sun (Central Time)

    IMPORTANT: Only compares CONSECUTIVE hours within the same non-op period.
    Excludes transitions between periods (e.g., 6pm vs previous 3am) since
    production happens in between.

    Args:
        tank_name: The tank identifier
        lookback_days: Days of historical data to use (default 60)

    Returns:
        dict with avg_change, avg_mr, ucl, lcl, n_samples or None if insufficient data
    """
    sql = """
    WITH hourly AS (
        SELECT
            date_trunc('hour', timestamp AT TIME ZONE 'America/Chicago') as hour,
            AVG(filled_gallons::float) as avg_gallons
        FROM core_tanklevellog
        WHERE tank_name = %s
            AND timestamp > NOW() - INTERVAL '%s days'
            AND (
                -- Weekends (0=Sunday, 6=Saturday)
                EXTRACT(DOW FROM timestamp AT TIME ZONE 'America/Chicago') IN (0, 6)
                -- Weekday evenings (6pm onwards)
                OR EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/Chicago') >= 18
                -- Weekday early morning (before 3am)
                OR EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/Chicago') < 3
            )
        GROUP BY date_trunc('hour', timestamp AT TIME ZONE 'America/Chicago')
        ORDER BY hour
    ),
    with_lag AS (
        SELECT
            hour,
            avg_gallons,
            LAG(avg_gallons) OVER (ORDER BY hour) as prev_gallons,
            LAG(hour) OVER (ORDER BY hour) as prev_hour
        FROM hourly
    ),
    moving_ranges AS (
        SELECT
            avg_gallons - prev_gallons as change,
            ABS(avg_gallons - prev_gallons) as moving_range
        FROM with_lag
        WHERE prev_gallons IS NOT NULL
          -- Only include if hours are consecutive (1 hour apart)
          -- This excludes transitions like 3am->6pm (15 hours) or 3am Fri->6pm Mon
          AND EXTRACT(EPOCH FROM (hour - prev_hour)) / 3600 = 1
    )
    SELECT
        AVG(change) as avg_change,
        AVG(moving_range) as avg_mr,
        COUNT(*) as n_samples
    FROM moving_ranges;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [tank_name, lookback_days])
        row = cursor.fetchone()

        if row and row[0] is not None and row[1] is not None and row[2] >= 10:
            avg_change = float(row[0])
            avg_mr = float(row[1])
            n_samples = int(row[2])
            return {
                'avg_change': avg_change,
                'avg_mr': avg_mr,
                'ucl': avg_change + 2.66 * avg_mr,
                'lcl': avg_change - 2.66 * avg_mr,
                'n_samples': n_samples
            }
    return None


def recalculate_and_store_control_limits(lookback_days=60):
    """
    Recalculate XmR control limits for all tanks and store in database.

    Returns:
        dict with 'updated': count of tanks updated, 'skipped': count of tanks skipped
    """
    from core.models import TankControlLimits

    tank_names = get_all_tank_names()
    updated = 0
    skipped = 0

    for tank_name in tank_names:
        limits = calculate_xmr_control_limits(tank_name, lookback_days)
        if limits:
            TankControlLimits.objects.create(
                tank_name=tank_name,
                lookback_days=lookback_days,
                n_samples=limits['n_samples'],
                avg_change=Decimal(str(limits['avg_change'])),
                avg_moving_range=Decimal(str(limits['avg_mr'])),
                upper_control_limit=Decimal(str(limits['ucl'])),
                lower_control_limit=Decimal(str(limits['lcl'])),
            )
            updated += 1
        else:
            skipped += 1
            logger.warning(f"Insufficient data to calculate limits for tank {tank_name}")

    return {'updated': updated, 'skipped': skipped}


def get_current_control_limits():
    """
    Get the most recent control limits for each tank.

    Returns:
        list of dicts with tank control limit data
    """
    sql = """
    WITH ranked AS (
        SELECT
            tank_name,
            calculated_at,
            lookback_days,
            n_samples,
            avg_change,
            avg_moving_range,
            upper_control_limit,
            lower_control_limit,
            ROW_NUMBER() OVER (PARTITION BY tank_name ORDER BY calculated_at DESC) as rn
        FROM core_tankcontrollimits
    )
    SELECT
        tank_name,
        calculated_at,
        lookback_days,
        n_samples,
        avg_change,
        avg_moving_range,
        upper_control_limit,
        lower_control_limit
    FROM ranked
    WHERE rn = 1
    ORDER BY tank_name;
    """

    limits = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        for row in cursor.fetchall():
            limits.append({
                'tank_name': row[0],
                'calculated_at': row[1],
                'lookback_days': row[2],
                'n_samples': row[3],
                'avg_change': float(row[4]),
                'avg_moving_range': float(row[5]),
                'upper_control_limit': float(row[6]),
                'lower_control_limit': float(row[7]),
            })
    return limits


def get_last_non_op_period():
    """
    Calculate the most recent completed non-operation period boundaries.

    Non-op hours: 6pm-3am Mon-Fri, all day Sat/Sun (Central Time)

    Returns:
        dict with 'start' and 'end' datetime objects in Central Time,
        plus 'label' describing the period (e.g., "Sun Dec 29" or "Mon Dec 30 6pm-3am")
    """
    import datetime
    now = datetime.datetime.now(CENTRAL_TZ)
    hour = now.hour
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    # Determine if we're currently IN a non-op period
    is_weekend = weekday >= 5
    is_evening = hour >= 18
    is_early_morning = hour < 3

    if is_weekend:
        # Weekend: show current weekend period (started Friday 6pm)
        days_since_friday = (weekday - 4) % 7
        friday = now - datetime.timedelta(days=days_since_friday)
        start = friday.replace(hour=18, minute=0, second=0, microsecond=0)
        # End is Monday 3am
        monday = friday + datetime.timedelta(days=3)
        end = monday.replace(hour=3, minute=0, second=0, microsecond=0)
        label = f"Weekend {start.strftime('%b %d')} - {end.strftime('%b %d')}"
    elif is_evening:
        # Currently in evening non-op (6pm+), show this period
        start = now.replace(hour=18, minute=0, second=0, microsecond=0)
        tomorrow = now + datetime.timedelta(days=1)
        end = tomorrow.replace(hour=3, minute=0, second=0, microsecond=0)
        label = f"{now.strftime('%a %b %d')} 6pm-3am"
    elif is_early_morning:
        # Currently in early morning non-op (before 3am), show last night's period
        yesterday = now - datetime.timedelta(days=1)
        start = yesterday.replace(hour=18, minute=0, second=0, microsecond=0)
        end = now.replace(hour=3, minute=0, second=0, microsecond=0)
        label = f"{yesterday.strftime('%a %b %d')} 6pm-3am"
    else:
        # Daytime hours (3am-6pm weekday): show LAST completed non-op period
        if weekday == 0:  # Monday daytime - show weekend
            friday = now - datetime.timedelta(days=3)
            start = friday.replace(hour=18, minute=0, second=0, microsecond=0)
            end = now.replace(hour=3, minute=0, second=0, microsecond=0)
            label = f"Weekend {start.strftime('%b %d')} - {now.strftime('%b %d')}"
        else:
            # Tue-Fri daytime: show previous night (yesterday 6pm to today 3am)
            yesterday = now - datetime.timedelta(days=1)
            start = yesterday.replace(hour=18, minute=0, second=0, microsecond=0)
            end = now.replace(hour=3, minute=0, second=0, microsecond=0)
            label = f"{yesterday.strftime('%a %b %d')} 6pm-3am"

    return {
        'start': start,
        'end': end,
        'label': label
    }


def get_tank_xmr_chart_data(tank_name):
    """
    Get tank level data for the most recent non-operation period.

    Shows only the last non-op period (e.g., previous evening 6pm-3am,
    or weekend if viewing on Monday).

    Returns hourly averages and hour-over-hour changes for charting.
    All timestamps are returned in Central Time.

    Args:
        tank_name: The tank identifier

    Returns:
        dict with 'timestamps', 'levels', 'changes' lists for charting,
        plus 'period_label' describing the time range shown
    """
    period = get_last_non_op_period()
    start_utc = period['start'].astimezone(timezone.utc)
    end_utc = period['end'].astimezone(timezone.utc)

    sql = """
    WITH hourly AS (
        SELECT
            date_trunc('hour', timestamp AT TIME ZONE 'America/Chicago') as hour_ct,
            AVG(filled_gallons::float) as avg_gallons
        FROM core_tanklevellog
        WHERE tank_name = %s
            AND timestamp >= %s
            AND timestamp <= %s
        GROUP BY date_trunc('hour', timestamp AT TIME ZONE 'America/Chicago')
        ORDER BY hour_ct
    ),
    with_changes AS (
        SELECT
            hour_ct,
            avg_gallons,
            avg_gallons - LAG(avg_gallons) OVER (ORDER BY hour_ct) as change
        FROM hourly
    )
    SELECT
        hour_ct AT TIME ZONE 'America/Chicago' as hour_utc,
        avg_gallons,
        change
    FROM with_changes
    ORDER BY hour_ct;
    """

    timestamps = []
    levels = []
    changes = []

    with connection.cursor() as cursor:
        cursor.execute(sql, [tank_name, start_utc, end_utc])
        for row in cursor.fetchall():
            if row[0]:
                utc_dt = row[0]
                central_dt = utc_dt.astimezone(CENTRAL_TZ)
                # Output WITHOUT timezone offset so JS treats as local time
                timestamps.append(central_dt.strftime('%Y-%m-%dT%H:%M:%S'))
            else:
                timestamps.append(None)
            levels.append(float(row[1]) if row[1] else None)
            changes.append(float(row[2]) if row[2] else None)

    return {
        'timestamps': timestamps,
        'levels': levels,
        'changes': changes,
        'period_label': period['label']
    }


def get_all_tanks_xmr_data():
    """
    Get XmR chart data for all tanks along with their control limits.

    Charts show data from the most recent non-operation period only.

    Returns:
        dict with:
          - 'period_label': description of the time period shown
          - 'tanks': dict mapping tank_name to {limits: {...}, chart_data: {...}}
    """
    limits_list = get_current_control_limits()
    limits_by_tank = {l['tank_name']: l for l in limits_list}

    tanks_data = {}
    tank_names = get_all_tank_names()
    period_label = None

    for tank_name in tank_names:
        chart_data = get_tank_xmr_chart_data(tank_name)
        if period_label is None:
            period_label = chart_data.get('period_label', '')
        tanks_data[tank_name] = {
            'limits': limits_by_tank.get(tank_name),
            'chart_data': chart_data
        }

    return {
        'period_label': period_label or '',
        'tanks': tanks_data
    }

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


def get_blend_costing_report_data(item_code_filter=None):
    """
    Return blend costing rows comparing actual labor hours to standard blend cost and labor cost.

    Args:
        item_code_filter (str | None): optional blend item code to filter results (currently unused).

    Returns:
        dict: {
            'rows': list of row dicts
        }
    """
    params = ['/BLD%']
    data_sql = """
        SELECT
            lr.lot_number,
            lr.lot_quantity,
            lr.item_code,
            ci.standardunitcost AS standard_unit_cost,
            (ci.standardunitcost * lr.lot_quantity) AS extended_lot_cost,
            EXTRACT(EPOCH FROM (lr.stop_time - lr.start_time)) / 3600.0 AS hours,
            dlr.hourly_rate AS desk_hourly_rate,
            (dlr.hourly_rate * (EXTRACT(EPOCH FROM (lr.stop_time - lr.start_time)) / 3600.0)) AS labor_cost
        FROM core_lotnumrecord lr
        LEFT JOIN bill_of_materials bom
            ON lr.item_code = bom.item_code
        LEFT JOIN ci_item ci
            ON bom.component_item_code = ci.itemcode
        LEFT JOIN core_desklaborrate dlr
            ON lr.desk = dlr.desk_name
        WHERE bom.component_item_code LIKE %s
          AND lr.start_time IS NOT NULL
          AND lr.stop_time IS NOT NULL
    """

    data_sql += " ORDER BY lr.lot_number DESC"

    rows = []

    with connection.cursor() as cursor:
        cursor.execute(data_sql, params)
        for (
            lot_number,
            lot_quantity,
            item_code,
            standard_unit_cost,
            extended_lot_cost,
            hours,
            desk_hourly_rate,
            labor_cost,
        ) in cursor.fetchall():
            rows.append({
                'lot_number': lot_number,
                'lot_quantity': lot_quantity,
                'item_code': item_code,
                'standard_unit_cost': standard_unit_cost,
                'extended_lot_cost': extended_lot_cost,
                'hours': hours,
                'desk_hourly_rate': desk_hourly_rate,
                'labor_cost': labor_cost,
            })
    return {'rows': rows}


def get_transaction_history_table_name(use_deeptime=False):
    """Return the appropriate transaction history table name for raw SQL queries."""
    if use_deeptime:
        return 'im_itemtransactionhistory_deeptime'
    return 'im_itemtransactionhistory'


def get_blend_item_status_data(use_deeptime=False):
    """
    Return blend item status data showing whether each blend item is "dead" or "active".

    A blend item is considered "dead" if:
    - It has NO transaction history in the selected transaction history table, AND
    - It is NOT a parent item in bill_of_materials

    Excluded from this report:
    - Items where itemcode starts with '/BLDLAB'
    - Items where itemcodedesc starts with 'BLEND-Grease '
    - Specific itemcodes: PK303000.B, 301000.B, 303000.B, 302000.B, 304000.B

    Args:
        use_deeptime: If True, use im_itemtransactionhistory_deeptime (full history).
                     If False, use im_itemtransactionhistory (rolling 1-year, default).

    Returns:
        dict: {
            'rows': list of row dicts with item_code, item_description, status,
                    last_transaction_date, in_bom
            'use_deeptime': boolean indicating which table was used
        }
    """
    table_name = get_transaction_history_table_name(use_deeptime)
    sql = f"""
        SELECT
            ci.itemcode AS item_code,
            ci.itemcodedesc AS item_description,
            MAX(th.transactiondate) AS last_transaction_date,
            CASE WHEN EXISTS (
                SELECT 1 FROM bill_of_materials bom WHERE bom.item_code = ci.itemcode
            ) THEN TRUE ELSE FALSE END AS in_bom,
            CASE
                WHEN MAX(th.transactiondate) IS NULL
                    AND NOT EXISTS (SELECT 1 FROM bill_of_materials bom WHERE bom.item_code = ci.itemcode)
                THEN 'Dead'
                ELSE 'Active'
            END AS status
        FROM ci_item ci
        LEFT JOIN {table_name} th ON th.itemcode = ci.itemcode
        WHERE ci.itemcodedesc LIKE 'BLEND%'
            AND ci.itemcode NOT LIKE '/BLDLAB%'
            AND ci.itemcodedesc NOT LIKE 'BLEND-Grease %'
            AND ci.itemcode NOT IN ('PK303000.B', '301000.B', '303000.B', '302000.B', '304000.B')
        GROUP BY ci.itemcode, ci.itemcodedesc
        ORDER BY
            CASE
                WHEN MAX(th.transactiondate) IS NULL
                    AND NOT EXISTS (SELECT 1 FROM bill_of_materials bom WHERE bom.item_code = ci.itemcode)
                THEN 0
                ELSE 1
            END,
            ci.itemcode
    """

    rows = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        for item_code, item_description, last_transaction_date, in_bom, status in cursor.fetchall():
            rows.append({
                'item_code': item_code,
                'item_description': item_description,
                'last_transaction_date': last_transaction_date,
                'in_bom': 'Yes' if in_bom else 'No',
                'status': status,
            })

    dead_count = sum(1 for row in rows if row['status'] == 'Dead')
    active_count = len(rows) - dead_count

    return {
        'rows': rows,
        'dead_count': dead_count,
        'active_count': active_count,
        'total_count': len(rows),
        'use_deeptime': use_deeptime,
    }
