import base64
import datetime as dt
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List, Sequence, Optional

from core.models import (
    BillOfMaterials,
    BlendContainerClassification,
    CiItem,
    ComponentShortage,
    ComponentUsage,
    DeskOneSchedule,
    DeskTwoSchedule,
    LetDeskSchedule,
    LotNumRecord,
    ProductionHoliday,
    SubComponentUsage,
)
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


def _group_schedule_entries(schedule_queryset):
    grouped = defaultdict(list)
    for entry in schedule_queryset:
        if not entry.item_code:
            continue
        grouped[entry.item_code].append(entry)
    return grouped


def build_schedule_snapshot():
    """Build a snapshot of scheduled blends and lot quantities."""
    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()
    let_desk_queryset = LetDeskSchedule.objects.all()

    desk_one_map = _group_schedule_entries(desk_one_queryset)
    desk_two_map = _group_schedule_entries(desk_two_queryset)
    let_desk_map = _group_schedule_entries(let_desk_queryset)

    all_item_codes = set(desk_one_map.keys()) | set(desk_two_map.keys()) | set(let_desk_map.keys())

    if all_item_codes:
        lot_queryset = LotNumRecord.objects.filter(item_code__in=all_item_codes).only('lot_number', 'lot_quantity')
    else:
        lot_queryset = LotNumRecord.objects.none()

    lot_quantities = {lot.lot_number: (lot.lot_quantity or 0) for lot in lot_queryset}

    item_code_totals: Dict[str, float] = {}
    for item_code in all_item_codes:
        desk_one_lots = [entry.lot for entry in desk_one_map.get(item_code, []) if entry.lot]
        desk_two_lots = [entry.lot for entry in desk_two_map.get(item_code, []) if entry.lot]
        scheduled_lots = desk_one_lots + desk_two_lots
        item_code_totals[item_code] = sum(lot_quantities.get(lot, 0) for lot in scheduled_lots)

    batches_lookup = defaultdict(list)
    for desk_label, mapping in (
        ('Desk_1', desk_one_map),
        ('Desk_2', desk_two_map),
        ('LET_Desk', let_desk_map),
    ):
        for item_code, entries in mapping.items():
            for entry in entries:
                batches_lookup[item_code].append(
                    (desk_label, entry.lot, lot_quantities.get(entry.lot, 0))
                )

    logger.debug('Schedule snapshot built for %s item codes.', len(all_item_codes))
    logger.debug('Item code totals: %s', item_code_totals)

    return {
        'all_item_codes': all_item_codes,
        'desk_one_codes': set(desk_one_map.keys()),
        'desk_two_codes': set(desk_two_map.keys()),
        'let_desk_codes': set(let_desk_map.keys()),
        'item_code_totals': item_code_totals,
        'batches_by_item_code': dict(batches_lookup),
    }


def _build_bom_lookup(bom_queryset: Iterable[BillOfMaterials]):
    bom_lookup = defaultdict(list)
    for bom in bom_queryset:
        bom_lookup[bom.item_code].append(bom)
    return bom_lookup


def _build_component_shortage_lookup(component_shortage_queryset):
    shortages_by_item = defaultdict(list)
    max_possible_lookup = {}
    for shortage in component_shortage_queryset:
        shortages_by_item[shortage.component_item_code].append(shortage)
        max_possible_lookup.setdefault(shortage.component_item_code, shortage.max_possible_blend)
    return shortages_by_item, max_possible_lookup


def _get_classification_map(blend_item_codes: Sequence[str]):
    if not blend_item_codes:
        return {}
    classifications = BlendContainerClassification.objects.filter(item_code__in=blend_item_codes)
    return {classification.item_code: classification.tank_classification for classification in classifications}


def annotate_blend_shortage_records(
    blends,
    *,
    blend_item_codes,
    latest_transactions_dict,
    bom_queryset,
    component_shortage_queryset,
    schedule_snapshot,
    advance_blends,
):
    """Hydrate blend shortage rows with scheduling, BOM and shortage metadata."""
    bom_lookup = _build_bom_lookup(bom_queryset or [])
    component_shortage_list = list(component_shortage_queryset or [])
    shortages_by_item, max_possible_lookup = _build_component_shortage_lookup(component_shortage_list)
    classification_map = _get_classification_map(blend_item_codes)

    batches_by_item = schedule_snapshot.get('batches_by_item_code', {})
    item_code_totals = schedule_snapshot.get('item_code_totals', {})
    scheduled_item_codes = schedule_snapshot.get('all_item_codes', set())
    desk_one_codes = schedule_snapshot.get('desk_one_codes', set())
    desk_two_codes = schedule_snapshot.get('desk_two_codes', set())
    let_desk_codes = schedule_snapshot.get('let_desk_codes', set())

    component_shortages_exist = bool(component_shortage_list)

    for blend in blends:
        item_code = blend.component_item_code

        if item_code in advance_blends:
            blend.advance_blend = 'yes'

        transaction_tuple = latest_transactions_dict.get(item_code, ('', ''))
        if transaction_tuple[0]:
            blend.last_date = transaction_tuple[0]
        else:
            blend.last_date = dt.datetime.today() - dt.timedelta(days=360)

        if item_code in scheduled_item_codes:
            additional_qty = item_code_totals.get(item_code, 0)
            new_shortage = calculate_new_shortage(item_code, additional_qty)
            logger.debug(
                'Processing blend %s: on_hand=%s scheduled_total=%s new_shortage=%s',
                item_code,
                getattr(blend, 'component_on_hand_qty', None),
                additional_qty,
                new_shortage,
            )
            if new_shortage:
                blend.shortage_after_blends = new_shortage['start_time']
                blend.short_quantity_after_blends = blend.total_shortage - additional_qty
            blend.scheduled = True
        else:
            blend.scheduled = False

        short_qty = getattr(blend, 'short_quantity_after_blends', None)
        if short_qty is not None and short_qty < 0:
            blend.surplus_quantity = abs(short_qty)
        else:
            blend.surplus_quantity = 0

        encoded_bytes = base64.b64encode(item_code.encode('UTF-8'))
        blend.encoded_component_item_code = encoded_bytes.decode('UTF-8')

        bom_entries = bom_lookup.get(item_code, [])
        blend.ingredients_list = (
            f'Sage OH for blend {item_code}:\n{round(getattr(blend, "component_on_hand_qty", 0) or 0, 0)} gal '\
            '\n\nINGREDIENTS:\n'
        )
        for bom_entry in bom_entries:
            blend.ingredients_list += f'{bom_entry.component_item_code}: {bom_entry.component_item_description}\n'

        if blend.last_txn_date and blend.last_count_date:
            needs_count = (
                blend.last_txn_date > blend.last_count_date
                and blend.last_txn_code not in ['II', 'IA', 'IZ']
            )
            blend.needs_count = needs_count
        else:
            blend.needs_count = False

        batches = batches_by_item.get(item_code, [])
        blend.batches = batches

        in_desk_one = item_code in desk_one_codes
        in_desk_two = item_code in desk_two_codes
        in_let_desk = item_code in let_desk_codes

        if in_desk_one and in_desk_two:
            blend.desk = 'Desk 1 & 2'
        elif in_desk_one:
            blend.desk = 'Desk 1'
        elif in_desk_two:
            blend.desk = 'Desk 2'
        elif in_let_desk:
            blend.desk = 'LET Desk'

        if not in_desk_one and not in_desk_two:
            blend.schedule_value = 'LET Desk' if in_let_desk else 'Not Scheduled'
        elif in_let_desk:
            blend.schedule_value = 'LET Desk'

        if component_shortages_exist:
            shortage_entries = shortages_by_item.get(item_code)
            if shortage_entries:
                shortage_component_item_codes = []
                for entry in shortage_entries:
                    if entry.subcomponent_item_code not in shortage_component_item_codes:
                        shortage_component_item_codes.append(entry.subcomponent_item_code)
                blend.shortage_flag_list = shortage_component_item_codes
                blend.max_producible_quantity = max_possible_lookup.get(item_code)
        else:
            blend.shortage_flag = None

        blend.tank_classification = classification_map.get(item_code, 'N/A')

def get_relevant_blend_runs(item_code, item_quantity, start_time):
    """Get relevant blend runs and their component usage for a given item.
    
    Retrieves and processes blend run data for a specified item, calculating component
    usage quantities and tracking inventory levels. Identifies potential shortages
    based on projected usage.

    Args:
        item_code (str): Code identifying the blend item
        item_quantity (float): Quantity of blend item needed
        start_time (float): Starting time reference point for usage calculations
        
    Returns:
        list: Blend run details including:
            - Component and subcomponent item codes and descriptions
            - Start times and production lines
            - Projected inventory levels after runs
            - Shortage flags for components below 0 quantity
    """
    blend_subcomponent_queryset = BillOfMaterials.objects \
        .filter(item_code__iexact=item_code) \
        .exclude(component_item_code__iexact='030143') \
        .exclude(component_item_code__startswith='/') \
        .distinct('component_item_code')
    this_blend_subcomponent_item_codes = [item.component_item_code for item in blend_subcomponent_queryset]

    this_blend_component_usages = {} # this will store the quantity used for each component
    for subcomponent_item_code in this_blend_subcomponent_item_codes:
        try:
            this_blend_component_usages[subcomponent_item_code] = float(BillOfMaterials.objects \
                                                                    .filter(item_code__iexact=item_code) \
                                                                    .filter(component_item_code__iexact=subcomponent_item_code) \
                                                                    .first().qtyperbill) * float(item_quantity)
        except TypeError as e:
            print(str(e))
            continue
    
    blend_subcomponent_usage_queryset = SubComponentUsage.objects \
        .filter(subcomponent_item_code__in=this_blend_subcomponent_item_codes) \
        .exclude(subcomponent_item_code__startswith='/') \
        .order_by('start_time')
    
    blend_subcomponent_usage_list = [
            {
                'component_item_code' : usage.component_item_code,
                'component_item_description' : usage.component_item_description,
                'subcomponent_item_code' : usage.subcomponent_item_code,
                'subcomponent_item_description' : usage.subcomponent_item_description,
                'start_time' : float(usage.start_time),
                'prod_line' : usage.prod_line,
                'subcomponent_onhand_after_run' : usage.subcomponent_onhand_after_run,
                'subcomponent_run_qty' : usage.subcomponent_run_qty,
                'run_source' : 'original'
            }
            for usage in blend_subcomponent_usage_queryset
        ]

    for key, value in this_blend_component_usages.items():
        for item in blend_subcomponent_usage_list:
            if item['subcomponent_item_code'] == key:
                if float(item['start_time']) > float(start_time):
                    item['subcomponent_onhand_after_run'] = float(item['subcomponent_onhand_after_run']) - float(value)
                item['subcomponent_item_description'] = CiItem.objects.filter(itemcode__iexact=item['subcomponent_item_code']).first().itemcodedesc

    for item in blend_subcomponent_usage_list:
        if item['subcomponent_onhand_after_run'] < 0:
            item['subcomponent_shortage'] = True
        else:
            item['subcomponent_shortage'] = False
        if "SCHEDULED: " in item['prod_line']:
            item['prod_line'] = item['prod_line'].replace("SCHEDULED: ", "")

    return blend_subcomponent_usage_list

def get_relevant_item_runs(item_code, item_quantity, start_time):
    """
    Retrieves and processes component usage data for a specific item.

    Args:
        item_code (str): The code identifying the item
        item_quantity (float): Quantity of the item being produced
        start_time (float): Unix timestamp marking start of production

    Returns:
        list: List of dicts containing component usage data, with fields:
            - item_code: Code of the finished item
            - item_description: Description of the finished item  
            - component_item_code: Code of the component
            - component_item_description: Description of the component
            - start_time: Production start time
            - prod_line: Production line
            - component_onhand_after_run: Component quantity remaining after run
            - component_run_qty: Component quantity used in run
            - run_source: Source of the run data
            - component_shortage: Boolean indicating if component will be short
    """
    item_component_queryset = BillOfMaterials.objects \
        .filter(item_code__iexact=item_code) \
        .exclude(component_item_code__startswith='/') \
        .distinct('component_item_code')
    this_item_component_item_codes = [item.component_item_code for item in item_component_queryset]

    this_item_component_usages = {} # this will store the quantity used for each component
    for component_item_code in this_item_component_item_codes:
        try:
            this_item_component_usages[component_item_code] = float(BillOfMaterials.objects \
                                                                    .filter(item_code__iexact=item_code) \
                                                                    .filter(component_item_code__iexact=component_item_code) \
                                                                    .first().qtyperbill) * float(item_quantity)
        except TypeError as e:
            print(str(e))
            continue
    
    item_component_usage_queryset = ComponentUsage.objects \
        .filter(component_item_code__in=this_item_component_item_codes) \
        .exclude(component_item_code__startswith='/') \
        .order_by('start_time')
    item_codes = list(item_component_usage_queryset.values_list('item_code', flat=True))
    item_descriptions = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__in=item_codes)}
    item_component_usage_list = [
            {
                'item_code' : usage.item_code,
                'item_description' : item_descriptions[usage.item_code],
                'component_item_code' : usage.component_item_code,
                'component_item_description' : usage.component_item_description,
                'start_time' : float(usage.start_time),
                'prod_line' : usage.prod_line,
                'component_onhand_after_run' : usage.component_onhand_after_run,
                'component_run_qty' : usage.run_component_qty,
                'run_source' : 'original'
            }
            for usage in item_component_usage_queryset
        ]

    for key, value in this_item_component_usages.items():
        for item in item_component_usage_list:
            if item['component_item_code'] == key:
                if float(item['start_time']) > float(start_time):
                    item['component_onhand_after_run'] = float(item['component_onhand_after_run']) - float(value)
                item['component_item_description'] = CiItem.objects.filter(itemcode__iexact=item['component_item_code']).first().itemcodedesc

    for item in item_component_usage_list:
        if item['component_onhand_after_run'] < 0:
            item['component_shortage'] = True
        else:
            item['component_shortage'] = False
        if "SCHEDULED: " in item['prod_line']:
            item['prod_line'] = item['prod_line'].replace("SCHEDULED: ", "")

    return item_component_usage_list

def calculate_new_shortage(item_code, additional_qty):
    """
    Calculates the new first shortage time for an item based on a new on-hand quantity.
    
    Args:
        item_code (str): The item code to check
        new_onhand_qty (float): The new on-hand quantity to use in calculations
        
    Returns:
        float: The new shortage time in hours, or None if no shortage found
    """
    # Get all component usage records for this item where quantity goes negative
    usage_records = ComponentUsage.objects.filter(
        component_item_code__iexact=item_code,
        component_onhand_after_run__lt=0
    ).order_by('start_time')
    
    if not usage_records.exists():
        return None
    if item_code=='TOTE-USED/NEW':
        return None
    
    # Normalize the incoming quantity so we don't mix Decimal and float
    try:
        additional_qty_decimal = Decimal(str(additional_qty))
    except Exception:
        # Fallback in case additional_qty is None or an unexpected type
        additional_qty_decimal = Decimal('0')

    # Add additional quantity to each record's component_onhand_after_run
    for record in usage_records:
        # print(f'{record.component_item_code}, start_time = {record.start_time}, oh after = {record.component_onhand_after_run}')
        adjusted_onhand = record.component_onhand_after_run + additional_qty_decimal
        # print(f'adjusted_onhand = {adjusted_onhand}')

        # If adjusted quantity is still negative, this is where shortage occurs
        if adjusted_onhand < 0:
            return {'start_time' : record.start_time, 'component_onhand_after_run' : record.component_onhand_after_run}

    # No shortage found
    return None

def get_component_consumption(component_item_code, blend_item_code_to_exclude):
    """Get component consumption details for a given component item code.

    Calculates how much of a component is needed by different blends, excluding a specified
    blend item code. Looks at component shortages and bill of materials to determine:
    - Which blends use this component
    - How much of the component each blend needs
    - Total component usage across all blends
    
    Args:
        component_item_code (str): Item code of the component to analyze
        blend_item_code_to_exclude (str): Item code of blend to exclude from analysis
        
    Returns:
        dict: Component consumption details including:
            - Per blend: item code, description, qty needed, first shortage date, component usage
            - Total component usage across all blends
    """
    item_codes_using_this_component = []
    for bill in BillOfMaterials.objects.filter(component_item_code__iexact=component_item_code).exclude(item_code__iexact=blend_item_code_to_exclude).exclude(item_code__startswith="/"):
        item_codes_using_this_component.append(bill.item_code)
    shortages_using_this_component = ComponentShortage.objects.filter(component_item_code__in=item_codes_using_this_component).exclude(component_item_code__iexact=blend_item_code_to_exclude)
    total_component_usage = 0
    component_consumption = {}
    for shortage in shortages_using_this_component:
        this_bill = BillOfMaterials.objects.filter(item_code__iexact=shortage.component_item_code) \
            .filter(component_item_code__iexact=component_item_code) \
            .exclude(item_code__startswith="/") \
            .first()
        # shortage.component_usage = shortage.adjustedrunqty * this_bill.qtyperbill
        total_component_usage += float(shortage.run_component_qty)
        component_consumption[shortage.component_item_code] = {
            'blend_item_code' : shortage.component_item_code,
            'blend_item_description' : shortage.component_item_description,
            'blend_total_qty_needed' : shortage.three_wk_short,
            'blend_first_shortage' : shortage.start_time,
            'component_usage' : shortage.run_component_qty
            }
    component_consumption['total_component_usage'] = float(total_component_usage)
    return component_consumption


# ---------------------------------------------------------------------------
# Production holiday CRUD helpers


def _serialize_production_holiday(holiday: ProductionHoliday) -> Dict:
    return {
        'id': holiday.id,
        'date': holiday.date.isoformat() if holiday.date else None,
        'description': holiday.description or '',
        'active': bool(holiday.active),
        'created_at': holiday.created_at.isoformat() if holiday.created_at else None,
        'updated_at': holiday.updated_at.isoformat() if holiday.updated_at else None,
    }


def list_production_holidays(include_inactive: bool = False) -> List[Dict]:
    qs = ProductionHoliday.objects.all()
    if not include_inactive:
        qs = qs.filter(active=True)
    qs = qs.order_by('date')
    return [_serialize_production_holiday(h) for h in qs]


def create_production_holiday(*, date: dt.date, description: str = '', active: bool = True) -> Dict:
    if not isinstance(date, dt.date):
        raise ValueError('date must be a datetime.date instance')

    holiday, created = ProductionHoliday.objects.get_or_create(
        date=date,
        defaults={'description': description or '', 'active': active},
    )

    if not created:
        raise ValueError('A holiday for this date already exists')

    return _serialize_production_holiday(holiday)


def update_production_holiday(holiday_id: int, *, date: Optional[dt.date] = None,
                              description: Optional[str] = None, active: Optional[bool] = None) -> Dict:
    try:
        holiday = ProductionHoliday.objects.get(pk=holiday_id)
    except ProductionHoliday.DoesNotExist:
        raise ValueError('Holiday not found')

    if date is not None:
        if not isinstance(date, dt.date):
            raise ValueError('date must be a datetime.date instance')
        if ProductionHoliday.objects.exclude(pk=holiday_id).filter(date=date).exists():
            raise ValueError('Another holiday already uses this date')
        holiday.date = date

    if description is not None:
        holiday.description = description

    if active is not None:
        holiday.active = bool(active)

    holiday.save()
    return _serialize_production_holiday(holiday)


def delete_production_holiday(holiday_id: int) -> None:
    deleted, _ = ProductionHoliday.objects.filter(pk=holiday_id).delete()
    if not deleted:
        raise ValueError('Holiday not found')


# Production calendar helpers
PRODUCTION_START_HOUR = 6
PRODUCTION_END_HOUR = 15  # Exclusive
DAILY_PRODUCTION_HOURS = PRODUCTION_END_HOUR - PRODUCTION_START_HOUR
EXCLUDED_WEEKDAYS = {4, 5, 6}  # Friday=4, Saturday=5, Sunday=6


def _is_production_day(candidate_date: dt.date, holiday_set: set) -> bool:
    """Return True when the date is an allowed production day."""
    return candidate_date.weekday() not in EXCLUDED_WEEKDAYS and candidate_date not in holiday_set


def _get_active_holiday_dates() -> set:
    """Return a set of holiday dates that should be skipped."""
    holiday_qs = ProductionHoliday.objects.filter(active=True).values_list('date', flat=True)
    return set(holiday_qs)


def _next_production_day_start(reference_dt: dt.datetime, holiday_set: set) -> dt.datetime:
    """Return 6 AM on the next eligible production day on/after the reference date."""
    tz = timezone.get_current_timezone()
    candidate_date = reference_dt.astimezone(tz).date()

    while not _is_production_day(candidate_date, holiday_set):
        candidate_date += dt.timedelta(days=1)

    start_naive = dt.datetime.combine(candidate_date, dt.time(hour=PRODUCTION_START_HOUR))
    start_dt = timezone.make_aware(start_naive, tz) if timezone.is_naive(start_naive) else start_naive
    return start_dt


def _normalize_start_datetime(start_dt: dt.datetime, holiday_set: set) -> dt.datetime:
    """Shift a start datetime onto the production calendar and inside working hours."""
    tz = timezone.get_current_timezone()
    current = start_dt.astimezone(tz)
    current_date = current.date()

    if not _is_production_day(current_date, holiday_set):
        return _next_production_day_start(current + dt.timedelta(days=1), holiday_set)

    day_start_naive = dt.datetime.combine(current_date, dt.time(hour=PRODUCTION_START_HOUR))
    day_end_naive = dt.datetime.combine(current_date, dt.time(hour=PRODUCTION_END_HOUR))

    day_start = timezone.make_aware(day_start_naive, tz) if timezone.is_naive(day_start_naive) else day_start_naive
    day_end = timezone.make_aware(day_end_naive, tz) if timezone.is_naive(day_end_naive) else day_end_naive

    if current < day_start:
        return day_start
    if current >= day_end:
        return _next_production_day_start(current + dt.timedelta(days=1), holiday_set)
    return current


def project_datetime_from_production_hours(
    production_hours: float,
    *,
    start: Optional[dt.datetime] = None,
    holidays: Optional[Iterable[dt.date]] = None,
) -> dt.datetime:
    """Translate production hours into a wall-clock datetime on the production calendar.

    Args:
        production_hours: Number of production hours to project forward. Must be non-negative.
        start: Optional baseline datetime. Defaults to now.
        holidays: Optional iterable of ``datetime.date`` objects that should be skipped.

    Returns:
        A timezone-aware datetime representing when the production hours will be reached.
    """

    if production_hours < 0:
        raise ValueError('production_hours must be non-negative')

    tz = timezone.get_current_timezone()
    if holidays is None:
        holiday_set = _get_active_holiday_dates()
    else:
        holiday_set = {h if isinstance(h, dt.date) else h.date() for h in holidays}

    baseline = start or timezone.now()
    if timezone.is_naive(baseline):
        baseline = timezone.make_aware(baseline, tz)
    baseline = baseline.astimezone(tz)

    current = _normalize_start_datetime(baseline, holiday_set)
    remaining_hours = float(production_hours)

    while True:
        day_end = current.replace(
            hour=PRODUCTION_END_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )
        available_today = (day_end - current).total_seconds() / 3600

        if remaining_hours <= available_today:
            return current + dt.timedelta(hours=remaining_hours)

        remaining_hours -= available_today
        next_day_reference = current + dt.timedelta(days=1)
        current = _next_production_day_start(next_day_reference, holiday_set)
