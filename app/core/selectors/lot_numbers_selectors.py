import base64
import datetime as dt
from django.db import connection
from django.db.models import Avg, Count, F, Max, Min, OuterRef, Subquery, Sum
from django.db.models import ExpressionWrapper, DurationField
from django.db.models.functions import Lower
from django.db.models.functions import Lower

from core.models import (
    LotNumRecord,
    HxBlendthese,
    DeskOneSchedule,
    DeskTwoSchedule,
    LetDeskSchedule,
    BlendSheetPrintLog,
)
from core.kpkapp_utils.dates import _is_date_string

RELEVANT_LINES = ['Dm', 'Totes', 'Hx']


def _duration_minutes(delta):
    if not delta:
        return None
    return delta.total_seconds() / 60


def _median(sorted_values):
    """Return median of a pre-sorted list of numbers."""
    if not sorted_values:
        return None
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2


def _round_or_none(value, ndigits=1):
    if value is None:
        return None
    return round(value, ndigits)


def _normalize_run_date(value):
    if not _is_date_string(value):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value


def _format_run_date(value):
    if not value:
        return None
    return value.strftime('%Y-%m-%d')


def _format_datetime(value):
    if not value:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.strftime('%Y-%m-%d')
    return value.strftime('%Y-%m-%d %H:%M')


def _get_scheduled_lot_numbers():
    schedule_querysets = (
        DeskOneSchedule.objects.exclude(lot__isnull=True).exclude(lot__exact='')
        .values_list('lot', flat=True),
        DeskTwoSchedule.objects.exclude(lot__isnull=True).exclude(lot__exact='')
        .values_list('lot', flat=True),
        LetDeskSchedule.objects.exclude(lot__isnull=True).exclude(lot__exact='')
        .values_list('lot', flat=True),
    )
    return {
        lot
        for queryset in schedule_querysets
        for lot in queryset
        if lot
    }


def _get_hx_match_keys():
    return {
        (
            item_code,
            prod_line,
            _normalize_run_date(run_date),
        )
        for item_code, prod_line, run_date in HxBlendthese.objects.filter(
            prod_line__in=RELEVANT_LINES
        ).values_list('component_item_code', 'prod_line', 'run_date')
        if item_code
    }


def get_orphaned_lots():
    """Return un-entered lot numbers that are not scheduled or matched to HX runs."""

    scheduled_lot_numbers = _get_scheduled_lot_numbers()
    hx_match_keys = _get_hx_match_keys()

    last_printed_subquery = Subquery(
        BlendSheetPrintLog.objects.filter(
            lot_num_record_id=OuterRef('pk')
        )
        .order_by('-printed_at')
        .values('printed_at')[:1]
    )

    orphaned_lots = []
    lots_queryset = (
        LotNumRecord.objects.filter(
            sage_entered_date__isnull=True
        )
        .exclude(item_code__in=['97200FLUSH','965GEL-PREMIX.B'])
        .annotate(last_printed_at=last_printed_subquery)
        .order_by('date_created')
        .values(
            'id',
            'item_code',
            'item_description',
            'line',
            'lot_number',
            'run_date',
            'date_created',
            'last_printed_at',
        )
    )

    for lot in lots_queryset:
        normalized_run_date = _normalize_run_date(lot['run_date'])

        if lot['lot_number'] in scheduled_lot_numbers:
            continue

        if (lot['item_code'], lot['line'], normalized_run_date) in hx_match_keys:
            continue

        date_created = lot['date_created']

        orphaned_lots.append(
            {
                'lot_id': lot['id'],
                'item_code': lot['item_code'],
                'prod_line': lot['line'],
                'item_description': lot['item_description'],
                'lot_number': lot['lot_number'],
                'run_date': _format_run_date(normalized_run_date),
                'date_created': _format_datetime(date_created),
                'encoded_item_code': base64.b64encode(lot['item_code'].encode()).decode()
                if lot['item_code'] else '',
                'last_printed_at': _format_datetime(lot.get('last_printed_at')),
            }
        )

    return orphaned_lots


def get_schedule_assignments_for_lots(lot_numbers):
    """Return schedule value/id pairs for the provided lot numbers.

    Args:
        lot_numbers (Iterable[str]): Lot numbers that need schedule metadata.

    Returns:
        dict[str, dict]: Mapping of the original lot number to a dict containing
            'schedule_value' and 'schedule_id'. Only the first matching schedule
            (Desk 1, Desk 2, LET Desk order) is captured to mirror legacy priority.
    """

    normalized_map = {
        lot_number.lower(): lot_number
        for lot_number in lot_numbers
        if isinstance(lot_number, str) and lot_number.strip()
    }

    if not normalized_map:
        return {}

    lot_keys = normalized_map.keys()
    assignments = {}

    schedule_priority = [
        ('Desk_1', DeskOneSchedule),
        ('Desk_2', DeskTwoSchedule),
        ('LET_Desk', LetDeskSchedule),
    ]

    for schedule_value, model in schedule_priority:
        schedule_rows = (
            model.objects
            .exclude(lot__isnull=True)
            .exclude(lot__exact='')
            .annotate(lot_lower=Lower('lot'))
            .filter(lot_lower__in=lot_keys)
        )

        for row in schedule_rows:
            lot_key = (row.lot or '').lower()
            original_lot = normalized_map.get(lot_key)
            if not original_lot or original_lot in assignments:
                continue

            assignments[original_lot] = {
                'schedule_value': schedule_value,
                'schedule_id': row.id,
            }

    return assignments


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


def get_blend_timestudy_report(min_samples=1):
    """Aggregate timestudy metrics by blend item code.

    Only includes lots with a non-null start_time and stop_time where stop_time
    occurs after start_time. Item codes with fewer than ``min_samples`` valid lots
    are excluded from the report.
    """

    valid_lots = (
        LotNumRecord.objects
        .filter(item_code__isnull=False)
        .exclude(item_code__exact='')
        .filter(start_time__isnull=False, stop_time__isnull=False)
        .filter(stop_time__gt=F('start_time'))
        .values('item_code', 'item_description', 'lot_number', 'start_time', 'stop_time')
    )

    grouped = {}
    for lot in valid_lots:
        item_code = (lot['item_code'] or '').strip()
        duration = lot['stop_time'] - lot['start_time']
        duration_minutes = _duration_minutes(duration)
        if not duration_minutes or duration_minutes <= 0:
            continue

        group = grouped.setdefault(
            item_code,
            {
                'item_description': None,
                'durations': [],
                'start_times': [],
                'lot_numbers': [],
            },
        )

        if not group['item_description'] and lot['item_description']:
            group['item_description'] = lot['item_description']

        group['durations'].append(duration_minutes)
        group['start_times'].append(lot['start_time'])
        group['lot_numbers'].append((lot['start_time'], lot['lot_number']))

    rows = []

    for item_code, data in grouped.items():
        durations = sorted(data['durations'])
        lot_count = len(durations)
        if lot_count < min_samples:
            continue

        total_minutes_for_item = sum(durations)

        rows.append(
            {
                'item_code': item_code,
                'item_description': data['item_description'] or '',
                'lot_count': lot_count,
                'avg_minutes': _round_or_none(total_minutes_for_item / lot_count, 1),
                'median_minutes': _round_or_none(_median(durations), 1),
                'min_minutes': _round_or_none(durations[0], 1),
                'max_minutes': _round_or_none(durations[-1], 1),
                'earliest_start': min(data['start_times']) if data['start_times'] else None,
                'latest_start': max(data['start_times']) if data['start_times'] else None,
                'most_recent_lot': max(data['lot_numbers'])[1] if data['lot_numbers'] else None,
            }
        )

    rows.sort(key=lambda row: (-row['lot_count'], row['item_code']))

    return {
        'rows': rows,
    }
