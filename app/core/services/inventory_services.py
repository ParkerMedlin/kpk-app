from core.models import ItemLocation, CiItem, ImItemWarehouse, ImItemTransactionHistory, AuditGroup, PurchasingAlias
from core.models import CountCollectionLink, ComponentUsage, ComponentShortage, BlendCountRecord, PartialContainerLabelLog
from core.forms import ItemLocationForm, AuditGroupForm, PurchasingAliasForm
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Sum, F, Max
from django.db.models.functions import Upper
from django.db import connection
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import datetime as dt
import base64
import json
import redis
from core.kpkapp_utils.string_utils import get_unencoded_item_code
import logging
from core.selectors.inventory_selectors import (
    get_count_record_model,
    get_item_quantity,
    get_ci_items_for_audit_group,
    get_qty_and_units_for_items,
    get_upcoming_runs_for_items,
    get_audit_group_records,
    get_distinct_audit_groups,
    get_latest_count_dates,
    get_latest_transaction_dates,
    get_recently_counted_item_codes,
    get_relevant_ci_item_itemcodes,
    get_last_counted_dates,
)
from core.services.purchasing_alias_services import extract_supply_type

logger = logging.getLogger(__name__)

_COMPONENT_PREFIXES = ('CHEM-', 'DYE-', 'FRAGRANCE-')

def get_item_recency_thresholds(*, today=None, rare_days=146, epic_days=273):
    """Return date thresholds for rare/epic blend designations."""
    reference_date = today or dt.datetime.now().date()
    thresholds = {
        'today': reference_date,
        'rare_date': reference_date - dt.timedelta(days=rare_days),
        'epic_date': reference_date - dt.timedelta(days=epic_days),
    }
    logger.debug('Calculated recency thresholds: %s', thresholds)
    return thresholds


def get_tintpaste_needs(
    *,
    black_item_code='841BLK.B',
    white_item_code='841WHT.B',
    black_threshold=150,
    white_threshold=300,
):
    """Determine whether black/white tintpaste need replenishment."""
    black_quantity = get_item_quantity(black_item_code)
    white_quantity = get_item_quantity(white_item_code)

    needs = {
        'black_quantity': black_quantity,
        'white_quantity': white_quantity,
        'need_black_tintpaste': black_quantity < black_threshold,
        'need_white_tintpaste': white_quantity < white_threshold,
    }
    logger.debug('Tintpaste needs evaluated: %s', needs)
    return needs


def build_count_list_display_data(*, record_type, count_list_id):
    """Build the enriched record set needed by the count list view."""
    if not record_type:
        raise ValueError('record_type is required')
    if not count_list_id:
        raise ValueError('count_list_id is required')

    count_list = CountCollectionLink.objects.get(pk=count_list_id)
    raw_id_list = count_list.count_id_list or []
    count_ids = [count_id for count_id in raw_id_list if count_id]

    model = get_count_record_model(record_type)
    count_records = list(model.objects.filter(pk__in=count_ids))

    record_lookup = {str(record.pk): record for record in count_records}
    ordered_records = []
    seen_ids = set()
    for pk in count_ids:
        key = str(pk)
        record = record_lookup.get(key)
        if record and key not in seen_ids:
            ordered_records.append(record)
            seen_ids.add(key)
    for key, record in record_lookup.items():
        if key not in seen_ids:
            ordered_records.append(record)

    if not ordered_records:
        return {
            'count_list_name': count_list.collection_name,
            'count_list_id': count_list_id,
            'record_type': record_type,
            'count_records': [],
        }

    item_codes = [record.item_code for record in ordered_records if getattr(record, 'item_code', None)]
    normalized_codes = {
        code.upper()
        for code in item_codes
        if isinstance(code, str) and code.strip()
    }

    ci_lookup = {}
    location_lookup = {}
    audit_group_lookup = {}

    if normalized_codes:
        ci_items = (
            CiItem.objects
            .annotate(itemcode_upper=Upper('itemcode'))
            .filter(itemcode_upper__in=normalized_codes)
        )
        ci_lookup = {item.itemcode_upper: item for item in ci_items}

        locations = (
            ItemLocation.objects
            .annotate(item_code_upper=Upper('item_code'))
            .filter(item_code_upper__in=normalized_codes)
            .order_by('id')
        )
        for location in locations:
            location_lookup.setdefault(location.item_code_upper, location)

        audit_groups = (
            AuditGroup.objects
            .annotate(item_code_upper=Upper('item_code'))
            .filter(item_code_upper__in=normalized_codes)
            .order_by('id')
        )
        for audit_group in audit_groups:
            audit_group_lookup.setdefault(audit_group.item_code_upper, audit_group)

    def _float_or_none(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    for count in ordered_records:
        normalized_code = count.item_code.upper() if isinstance(count.item_code, str) else ''

        ci_item = ci_lookup.get(normalized_code)
        if ci_item:
            count.standard_uom = ci_item.standardunitofmeasure
            count.shipweight = ci_item.shipweight

        location = location_lookup.get(normalized_code)
        if location:
            count.location = location.zone

        audit_group = audit_group_lookup.get(normalized_code)
        if audit_group:
            count.counting_unit = audit_group.counting_unit

        count.converted_expected_quantity = count.expected_quantity
        standard_uom = getattr(count, 'standard_uom', None)
        counting_unit = getattr(count, 'counting_unit', None)
        expected_value = _float_or_none(count.expected_quantity)
        shipweight_value = _float_or_none(getattr(count, 'shipweight', None))

        if (
            standard_uom
            and counting_unit
            and standard_uom != counting_unit
            and expected_value is not None
        ):
            std = standard_uom.upper() if isinstance(standard_uom, str) else standard_uom
            unit = counting_unit.upper() if isinstance(counting_unit, str) else counting_unit
            if std == 'GAL' and unit in ('LB', 'LBS') and shipweight_value is not None:
                count.converted_expected_quantity = expected_value * shipweight_value
            elif (
                std in ('LB', 'LBS')
                and unit == 'GAL'
                and shipweight_value not in (None, 0)
                and shipweight_value > 0
            ):
                count.converted_expected_quantity = expected_value / shipweight_value

    return {
        'count_list_name': count_list.collection_name,
        'count_list_id': count_list_id,
        'record_type': record_type,
        'count_records': ordered_records,
    }


def build_audit_group_display_items(
    record_type,
    *,
    search_query='',
    audit_group_filter='',
):
    """Build the enriched item list and audit group choices for the UI."""
    ci_queryset = get_ci_items_for_audit_group(record_type)

    if search_query:
        ci_queryset = ci_queryset.filter(
            Q(itemcode__icontains=search_query) |
            Q(itemcodedesc__icontains=search_query)
        )

    if audit_group_filter:
        filtered_item_codes = AuditGroup.objects.filter(
            audit_group__iexact=audit_group_filter
        ).values_list('item_code', flat=True)
        ci_queryset = ci_queryset.filter(itemcode__in=filtered_item_codes)

    ci_item_values = (
        ci_queryset
        .values('itemcode', 'itemcodedesc')
        .distinct()
        .order_by('itemcode')
    )

    audit_items = [
        {'item_code': item['itemcode'], 'item_description': item['itemcodedesc']}
        for item in ci_item_values
    ]

    item_codes = [item['item_code'] for item in audit_items]
    if not item_codes:
        return audit_items, get_distinct_audit_groups()

    qty_and_units = get_qty_and_units_for_items(item_codes)
    upcoming_runs, count_table = get_upcoming_runs_for_items(item_codes, record_type)
    latest_count_dates = get_latest_count_dates(item_codes, count_table)
    latest_transactions = get_latest_transaction_dates(item_codes)
    audit_group_records = get_audit_group_records(item_codes)

    for item in audit_items:
        item_code = item['item_code']
        transaction_tuple = latest_transactions.get(item_code, ('', ''))
        item['transaction_info'] = transaction_tuple
        item['last_transaction_date'] = transaction_tuple[0]
        item['next_usage'] = upcoming_runs.get(item_code, '')
        item['qty_on_hand'] = qty_and_units.get(item_code, '')
        item['last_count'] = latest_count_dates.get(item_code, ('', ''))

        audit_group_record = audit_group_records.get(item_code)
        if audit_group_record:
            item['audit_group'] = audit_group_record.audit_group or ''
            item['counting_unit'] = audit_group_record.counting_unit or ''
            item['id'] = audit_group_record.id
            item['item_type'] = audit_group_record.item_type or record_type
        else:
            item['audit_group'] = ''
            item['counting_unit'] = ''
            item['id'] = None
            item['item_type'] = record_type

    audit_group_list = get_distinct_audit_groups()
    return audit_items, audit_group_list


def update_audit_group_assignment(item_id, form_data):
    """Persist changes for an existing AuditGroup record via AuditGroupForm."""
    if not item_id:
        return False, None, 'Item not found'

    try:
        audit_group_item = AuditGroup.objects.get(id=item_id)
    except AuditGroup.DoesNotExist:
        return False, None, 'Item not found'

    form = AuditGroupForm(form_data, instance=audit_group_item)
    if form.is_valid():
        try:
            updated_item = form.save()
            return True, updated_item, None
        except Exception as exc:
            logger.exception('Failed to update audit group %s', audit_group_item.item_code)
            return False, None, str(exc)

    return False, audit_group_item, form.errors


def build_uncounted_items_display(
    *,
    days=3,
    item_type=None,
    search_query='',
):
    """Build display list of uncounted items with audit group and last-counted data."""
    counted_codes = get_recently_counted_item_codes(days)
    counted_codes = {code for code in counted_codes if isinstance(code, str) and code.strip()}

    filter_map = {
        'blend': 'blends',
        'component': 'components',
        'warehouse': 'non_blend',
    }
    filter_string = filter_map.get(item_type)

    all_items = get_relevant_ci_item_itemcodes(
        filter_string,
        exclude_audit_group_items=False,
    )

    uncounted_items = [
        item for item in all_items
        if item[0] not in counted_codes
    ]

    if search_query:
        search_value = search_query.strip().lower()
        if search_value:
            uncounted_items = [
                item for item in uncounted_items
                if search_value in item[0].lower() or search_value in item[1].lower()
            ]

    uncounted_items.sort(key=lambda x: x[0])

    item_codes = [item[0] for item in uncounted_items]
    audit_groups = get_audit_group_records(item_codes)
    last_counted_dates = get_last_counted_dates(item_codes)

    display_items = []
    for item in uncounted_items:
        item_code = item[0]
        item_desc = item[1]

        audit_group_record = audit_groups.get(item_code)
        if filter_string:
            display_type = item_type
        else:
            display_type = _classify_by_description(item_desc)
        display_items.append({
            'item_code': item_code,
            'item_description': item_desc or '',
            'item_type': display_type,
            'audit_group': audit_group_record.audit_group if audit_group_record else None,
            'audit_group_id': audit_group_record.id if audit_group_record else None,
            'last_counted_date': last_counted_dates.get(item_code),
        })

    return display_items


def create_countlist_from_item_codes(item_codes):
    """Create a countlist for a homogeneous set of item codes."""
    if not item_codes:
        raise ValueError('item_codes is required')

    normalized_codes = [
        code.strip()
        for code in item_codes
        if isinstance(code, str) and code.strip()
    ]
    if not normalized_codes:
        raise ValueError('item_codes is required')

    record_types = {_classify_item_code(code) for code in normalized_codes}
    record_types.discard(None)
    if not record_types:
        raise ValueError('Unable to determine record_type for item_codes')
    if len(record_types) > 1:
        raise ValueError('Item codes must share the same record_type')

    record_type = record_types.pop()

    valid_codes = set(
        CiItem.objects
        .filter(itemcode__in=normalized_codes)
        .values_list('itemcode', flat=True)
    )
    warehouse_codes = set(
        ImItemWarehouse.objects
        .filter(itemcode__in=normalized_codes, warehousecode__iexact='MTG')
        .values_list('itemcode', flat=True)
    )
    valid_codes = valid_codes & warehouse_codes

    seen_codes = set()
    filtered_codes = []
    for code in normalized_codes:
        if code not in valid_codes or code in seen_codes:
            continue
        filtered_codes.append(code)
        seen_codes.add(code)
    if not filtered_codes:
        raise ValueError('No valid item codes provided')

    list_info = add_count_records(filtered_codes, record_type)
    now_str = dt.datetime.now().strftime('%m-%d-%Y_%H:%M')

    new_count_collection = CountCollectionLink(
        link_order=CountCollectionLink.objects.aggregate(Max('link_order'))['link_order__max'] + 1
        if CountCollectionLink.objects.exists()
        else 1,
        collection_name=f'{record_type}_count_{now_str}',
        count_id_list=list(list_info['primary_keys']),
        collection_id=list_info['collection_id'],
        record_type=record_type,
    )
    new_count_collection.save()

    event_data = {
        'id': new_count_collection.id,
        'link_order': new_count_collection.link_order,
        'collection_name': new_count_collection.collection_name,
        'collection_id': new_count_collection.collection_id,
        'record_type': record_type,
    }
    append_count_collection_event('collection_added', event_data)
    broadcast_count_collection_event('collection_added', event_data)

    return new_count_collection


def _classify_item_code(item_code):
    if not item_code:
        return None
    code = item_code.strip()
    if not code:
        return None
    upper_code = code.upper()
    if upper_code.startswith('BLEND-'):
        return 'blend'
    if upper_code.startswith(_COMPONENT_PREFIXES):
        return 'blendcomponent'
    return 'warehouse'


def _classify_by_description(description):
    if not description:
        return 'warehouse'
    text = str(description).strip()
    if not text:
        return 'warehouse'
    upper_desc = text.upper()
    if upper_desc.startswith('BLEND'):
        return 'blend'
    if upper_desc.startswith(('CHEM', 'DYE', 'FRAGRANCE')):
        return 'component'
    return 'warehouse'


try:
    redis_client = redis.StrictRedis(host='kpk-app_redis_1', port=6379, db=0, decode_responses=True)
except redis.RedisError as exc:
    logger.warning("Redis unavailable for count collection state persistence: %s", exc)
    redis_client = None

COUNT_COLLECTION_EVENTS_KEY = 'count_collection:global'
COUNT_COLLECTION_EVENT_LIMIT = 25
_COUNT_COLLECTION_GROUPS = (
    'count_collection_unique_count_collection_global',
    'count_collection_unique_global',  # legacy group name for backward compatibility
)

def append_count_collection_event(event_type: str, payload: dict) -> None:
    if redis_client is None:
        return
    try:
        existing = redis_client.get(COUNT_COLLECTION_EVENTS_KEY)
        if existing:
            try:
                state = json.loads(existing)
            except json.JSONDecodeError:
                state = {'events': []}
        else:
            state = {'events': []}
        events = state.get('events', [])
        events.append({'event': event_type, 'data': payload})
        state['events'] = events[-COUNT_COLLECTION_EVENT_LIMIT:]
        redis_client.set(COUNT_COLLECTION_EVENTS_KEY, json.dumps(state))
    except redis.RedisError as exc:
        logger.error("Error recording count collection event: %s", exc)

def broadcast_count_collection_event(event_type: str, event_data: dict) -> None:
    """
    Broadcast a count collection websocket event to the default and legacy channel groups.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("Channel layer unavailable; skipping broadcast for %s", event_type)
        return

    payload = {'type': event_type, **event_data}
    for group_name in _COUNT_COLLECTION_GROUPS:
        try:
            async_to_sync(channel_layer.group_send)(group_name, payload)
        except Exception as exc:
            logger.warning(
                "Failed to broadcast %s to %s: %s", event_type, group_name, exc
            )

def update_item_location(request, item_location_id):
    """
    Updates an existing item location record with new data from POST request.
    
    Args:
        request: HTTP request object containing form data
        item_location_id: ID of the item location record to update
        
    Returns:
        HttpResponseRedirect to item locations page after update
        
    Raises:
        Http404: If item location record with given ID does not exist
    """
    print('here we are')
    if request.method == "POST":
        try:
            print(item_location_id)
            item_location = get_object_or_404(ItemLocation, id=item_location_id)
            edit_item_location = ItemLocationForm(request.POST or None, instance=item_location, prefix='editItemLocationModal')

            if edit_item_location.is_valid():
                edit_item_location.save()
            
            return JsonResponse({'success': f'successfully updated item location for {edit_item_location.cleaned_data["item_code"]}'})

        except Exception as e:
            return JsonResponse({'Exception thrown' : str(e)})

def add_missing_item_locations(request):
    """
    Adds ItemLocation records for items in CI_Item that don't have location records yet.
    
    Identifies items in the CI_Item table that don't have corresponding entries in the
    ItemLocation table and creates new location records for them. Can filter by item_type.
    
    Args:
        item_type (str, optional): Filter to only add items of a specific type.
                                  If None, adds all missing items.
    
    Returns:
        int: Number of new item location records created
    """
    try:
        item_type = request.GET.get('item-type', None)
        print(item_type)

        existing_item_codes = set(ItemLocation.objects.values_list('item_code', flat=True))
        missing_items_query = CiItem.objects.exclude(itemcode__in=existing_item_codes)
        
        if item_type:
            if item_type == 'blend':
                missing_items_query = missing_items_query.filter(itemcodedesc__startswith='BLEND-')
            elif item_type == 'blendcomponent':
                missing_items_query = missing_items_query.filter(
                    Q(itemcodedesc__startswith='CHEM') |
                    Q(itemcodedesc__startswith='DYE') |
                    Q(itemcodedesc__startswith='FRAGRANCE')
                )
        
        # Create new ItemLocation records
        new_locations_count = 0
        for item in missing_items_query:
            determined_item_type = 'warehouse'
            if item.itemcodedesc.startswith('BLEND'):
                determined_item_type = 'blend'
            elif item.itemcodedesc.startswith('CHEM'):
                determined_item_type = 'blendcomponent'

            new_location = ItemLocation(
                item_code=item.itemcode,
                item_description=item.itemcodedesc,
                unit=item.standardunitofmeasure if hasattr(item, 'standardunitofmeasure') else '',
                storage_type='',  # Default value
                zone='',          # Default value
                bin='',           # Default value
                item_type=determined_item_type
            )
            new_location.save()
            new_locations_count += 1
        
        response_data = {
            'status': 'success',
            'message': f'Added {new_locations_count} new item location records',
            'count': new_locations_count
        }
    except Exception as e:
        print(str(e))
        response_data = {
                'status': 'failure',
                'message': f'{ str(e) }',
                'count': new_locations_count
            }

    return JsonResponse(response_data)

def check_automated_count_exists(request):
    """
    Scans the archives for automated count lists created on the current day.

    Returns:
        JsonResponse: A mystical object revealing if 'blend' and 'blendcomponent' counts exist for today.
    """
    today = dt.date.today()

    blend_exists_today = False
    blendcomponent_exists_today = False
    
    automated_counts = CountCollectionLink.objects.filter(collection_name__endswith='auto')
    
    for count_link in automated_counts:
        try:
            name_parts = count_link.collection_name.split('_')
            
            date_str = name_parts[-1]
            
            collection_date = dt.datetime.strptime(date_str, '%m-%d-%Y').date()
            
            if collection_date == today:
                if 'blendcomponent' in count_link.collection_name:
                    blendcomponent_exists_today = True
                elif 'blend' in count_link.collection_name:
                    blend_exists_today = True

        except (IndexError, ValueError):
            pass
            
    return JsonResponse({
        'blend_exists': blend_exists_today,
        'blendcomponent_exists': blendcomponent_exists_today
    })

def create_automated_countlist(request):
    """Create an automated count list based on specified criteria.
    
    Generates a new count list for either blend items or blend components based on 
    the record type parameter. Handles the request and delegates to generate_countlist()
    for actual list creation.

    Args:
        request: HTTP request object containing recordType parameter ('blend' or 'blendcomponent')

    Returns:
        JsonResponse containing:
            - success message and count list name if generated successfully
            - 'no action needed' message if list already exists
            - error details if generation failed
    """
    record_type = request.GET.get('recordType','No Record Type')
    try:
        countlist_result = _generate_automated_countlist(record_type)
        if countlist_result == 'Name already exists':
            result = { 'no action needed' : 'Count list already exists' }
        else:
            result = { 'success' : f'{countlist_result} generated' }
    except Exception as e:
        result = { 'failure' : str(e) }

    return JsonResponse(result, safe=False)

def _generate_automated_countlist(record_type):
    """Generate an automated count list for inventory tracking.
    
    Creates a new count list for either blend items or blend components based on specified
    record type. For blend items, selects items from recent component usage and shortage 
    reports. Filters out any blends that have been counted since the last run.
    For blend components, selects chemical/dye/fragrance items excluding those 
    already scheduled or in tanks.

    Args:
        record_type (str): Type of count list to generate - either 'blend' or 'blendcomponent'
        
    Returns:
        str: Name of generated count list if successful, or 'Name already exists' if a list
             with that name already exists for today's date
        
    Raises:
        Exception: If there are errors accessing the database or creating the count list
    """
    now_str = dt.datetime.now().strftime('%m-%d-%Y')
    if record_type == 'blend':
        # Check if a CountCollectionLink with the given name already exists
        existing_count = CountCollectionLink.objects.filter(collection_name=f'{record_type}_count_{now_str}').exists()
        if existing_count:
            return 'Name already exists'
        production_item_code_list = ComponentUsage.objects.filter(
            prod_line='INLINE',
            component_item_description__startswith='BLEND',
            start_time__gt=8
        ).values_list('component_item_code', flat=True).distinct().order_by('component_item_code')[:15]
        production_item_code_list = list(production_item_code_list)
        for item in production_item_code_list:
            if ImItemTransactionHistory.objects\
                .filter(itemcode=item, transactioncode__in=['II','IA','IZ']) \
                .filter(warehousecode__iexact='MTG') \
                .order_by('-transactiondate').exists():
                last_inventory_adjustment = ImItemTransactionHistory.objects\
                    .filter(itemcode=item, transactioncode__in=['II','IA','IZ']) \
                    .filter(warehousecode__iexact='MTG') \
                    .order_by('-transactiondate').first().transactiondate
            if ImItemTransactionHistory.objects\
                .filter(itemcode=item, transactioncode__in=['BI']) \
                .filter(warehousecode__iexact='MTG') \
                .order_by('-transactiondate').exists():
                last_production_transaction = ImItemTransactionHistory.objects\
                    .filter(itemcode=item, transactioncode__in=['BI']) \
                    .filter(warehousecode__iexact='MTG') \
                    .order_by('-transactiondate').first().transactiondate
            if last_inventory_adjustment > last_production_transaction:
                production_item_code_list.remove(item)
            
            
        blend_shortage_item_codes = ComponentShortage.objects.filter(last_txn_date__gt=F('last_count_date')) \
            .exclude(prod_line__iexact='Dm') \
            .exclude(prod_line__iexact='Hx') \
            .exclude(prod_line__iexact='Totes') \
            .exclude(component_item_code='100501K') \
            .values_list('component_item_code', flat=True) \
            .distinct().order_by('start_time')[:15]
        item_codes = list(blend_shortage_item_codes) + list(production_item_code_list)

        # Get blend count records from the last 3 days for items in item_codes
        three_days_ago = dt.datetime.now() - dt.timedelta(days=3)
        
        # Remove duplicates from item_codes while preserving order
        item_codes = list(dict.fromkeys(item_codes))
        recent_blend_count_records = BlendCountRecord.objects.filter(
            item_code__in=item_codes,
            counted_date__gt=three_days_ago,
            counted=True
        ).values_list('item_code', flat=True).distinct()
        item_codes = [item_code for item_code in item_codes if item_code not in recent_blend_count_records]

        # Get component item codes for PD LINE and JB LINE with BLEND descriptions and start_time < 8
        pd_jb_blend_codes = ComponentUsage.objects.filter(
            prod_line__in=['PD LINE', 'JB LINE'],
            component_item_description__startswith='BLEND',
            start_time__lt=8
        ).values_list('component_item_code', flat=True).distinct()
        
        # Add these codes to the existing item_codes list
        item_codes.extend(list(pd_jb_blend_codes))
        
        # Remove duplicates while preserving order
        item_codes = list(dict.fromkeys(item_codes))

        item_codes = [item_code for item_code in item_codes if item_code not in pd_jb_blend_codes]

    elif record_type == 'blendcomponent':
        tank_chems = ['030033','050000G','050000','031018','601015','050000G','500200',
            '030066','100427','100507TANKB','100428M6','100507TANKD','100449',
            '100421G2','100560','100421G2','100501K','27200.B','100507TANKO']
        
        component_item_codes_to_skip = tank_chems

        blendcomponent_item_codes = CiItem.objects.filter(
            Q(itemcodedesc__startswith='CHEM') |
            Q(itemcodedesc__startswith='DYE') |
            Q(itemcodedesc__startswith='FRAGRANCE')
        ).exclude(itemcode__in=component_item_codes_to_skip).values_list('itemcode', flat=True)

        try:
            # Get the sum of II transactions for each item code
            with connection.cursor() as cursor:
                cursor.execute("""SELECT itemcode, SUM(transactionqty) as ii_total
                    FROM im_itemtransactionhistory
                    WHERE transactioncode = 'II'
                    group by itemcode""")
                ii_transactions_sum = { row[0] : row[1] for row in cursor.fetchall() }
                cursor.execute("""SELECT itemcode, SUM(transactionqty) as ia_total
                    FROM im_itemtransactionhistory
                    WHERE transactioncode = 'IA'
                    group by itemcode""")
                ia_transactions_sum = { row[0] : row[1] for row in cursor.fetchall() }
                cursor.execute("""SELECT itemcode, SUM(transactionqty) as iz_total
                    FROM im_itemtransactionhistory
                    WHERE transactioncode = 'IZ'
                    group by itemcode""")
                iz_transactions_sum = { row[0] : row[1] for row in cursor.fetchall() }
                cursor.execute("""SELECT itemcode, SUM(transactionqty) as bi_total
                    FROM im_itemtransactionhistory
                    WHERE transactioncode = 'BI'
                    group by itemcode""")
                bi_transactions_sum = { row[0] : row[1] for row in cursor.fetchall() }
        except Exception as e:
            print(str(e))

        adjustment_sums = { item_code : (ii_transactions_sum.get(item_code,0) + ia_transactions_sum.get(item_code,0) + iz_transactions_sum.get(item_code,0)) for item_code in blendcomponent_item_codes }
        # kind of dumb but basically if there are no BI transactions i am dividing 
        # by an insanely large number so that the ratio is very very small 
        # and that particular itemcode gets shunted to the bottom of the list. 
        adjustment_ratios = { item_code : adjustment_sums.get(item_code,0) / bi_transactions_sum.get(item_code,10000000) for item_code in blendcomponent_item_codes }
        # Sort adjustment_ratios by value (ratio), largest to smallest
        sorted_adjustment_ratios = dict(sorted(adjustment_ratios.items(), key=lambda item: item[1], reverse=True))
        
        # Get the first six keys from the sorted_adjustment_ratios
        item_codes = list(sorted_adjustment_ratios.keys())[:8]

    list_info = add_count_records(item_codes, record_type)
    
    new_count_collection = CountCollectionLink(
        link_order = CountCollectionLink.objects.aggregate(Max('link_order'))['link_order__max'] + 1 if CountCollectionLink.objects.exists() else 1,
        collection_name = f'{record_type}_count_{now_str}_auto',
        count_id_list = list(list_info['primary_keys']),
        collection_id = list_info['collection_id'],
        record_type = record_type
    )
    new_count_collection.save()
    event_data = {
        'id': new_count_collection.id,
        'link_order': new_count_collection.link_order,
        'collection_name': new_count_collection.collection_name,
        'collection_id': new_count_collection.collection_id,
        'record_type': record_type
    }
    append_count_collection_event('collection_added', event_data)
    broadcast_count_collection_event('collection_added', event_data)

    result = f'{record_type}_count_{now_str}'

    return result

def add_count_list(request):
    """Add a new count list for inventory tracking.
    
    Processes requests to create new count lists, handling both edit and create operations.
    For edit requests, creates a new CountCollectionLink record and broadcasts the update
    via websockets. For create requests, decodes item codes and creates count records.

    Args:
        request: HTTP request containing:
            itemsToAdd (str): Base64 encoded list of item codes
            recordType (str): Type of count records ('blend', 'blendcomponent', 'warehouse') 
            requestType (str): Operation type ('edit' or 'create')

    Returns:
        JsonResponse with result message on success or error details on failure
        
    Raises:
        Exception: If there are errors creating records or broadcasting updates
    """
    try:
        encoded_item_code_list = request.GET.get('itemsToAdd')
        record_type = request.GET.get('recordType')
        request_type = request.GET.get('requestType')
        print(f'encoded_item_code_list: {encoded_item_code_list}')
        print(f'request_type: {request_type}')
        if request_type == 'edit':
            try:
                model = get_count_record_model(record_type)
                unique_values_count = model.objects.filter(counted_date=dt.date.today()).values('collection_id').distinct().count()
                today_string = dt.date.today().strftime("%Y%m%d")
                this_collection_id = f'B{unique_values_count+1}-{today_string}'
                item_codes_bytestr = base64.b64decode(encoded_item_code_list)
                item_codes_str = item_codes_bytestr.decode()
                print(list(item_codes_str.replace('"','').split(',')))
                now_str = dt.datetime.now().strftime('%m-%d-%Y')
                new_count_collection = CountCollectionLink(
                    link_order = CountCollectionLink.objects.aggregate(Max('link_order'))['link_order__max'] + 1 if CountCollectionLink.objects.exists() else 1,
                    collection_name = f'{record_type}_count_{now_str}',
                    count_id_list = list(item_codes_str.replace('"','').split(',')),
                    collection_id = this_collection_id,
                    record_type = record_type
                )
                new_count_collection.save()
                event_data = {
                    'id': new_count_collection.id,
                    'link_order': new_count_collection.link_order,
                    'collection_name': new_count_collection.collection_name,
                    'collection_id': new_count_collection.collection_id,
                    'record_type': record_type
                }
                append_count_collection_event('collection_added', event_data)
                broadcast_count_collection_event('collection_added', event_data)
            except Exception as e:
                print(str(e))
            
            response = {'result' : 'Countlist successfully added.'}
            return JsonResponse(response, safe=False)

        item_codes_bytestr = base64.b64decode(encoded_item_code_list)
        item_codes_str = item_codes_bytestr.decode()
    
        item_codes_list = list(item_codes_str.replace('[', '').replace(']', '').replace('"', '').split(","))
        print(f'item_code_list: {item_codes_list}' )
        list_info = add_count_records(item_codes_list, record_type)

        now_str = dt.datetime.now().strftime('%m-%d-%Y_%H:%M')

        try:
            new_count_collection = CountCollectionLink(
                link_order = CountCollectionLink.objects.aggregate(Max('link_order'))['link_order__max'] + 1 if CountCollectionLink.objects.exists() else 1,
                collection_name = f'{record_type}_count_{now_str}',
                count_id_list = list(list_info['primary_keys']),
                collection_id = list_info['collection_id'],
                record_type = record_type
            )
            new_count_collection.save()
            event_data = {
                'id': new_count_collection.id,
                'link_order': new_count_collection.link_order,
                'collection_name': new_count_collection.collection_name,
                'collection_id': new_count_collection.collection_id,
                'record_type': record_type
            }
            append_count_collection_event('collection_added', event_data)
            broadcast_count_collection_event('collection_added', event_data)
        except Exception as e:
            print(str(e))

        response = {'result' : 'Countlist successfully added.'}
    except Exception as e:
        print(str(e))
        response = {'result' : 'failure'}

    return JsonResponse(response, safe=False)

def update_count_list(request):
    """Updates a count list by adding or removing count records.
    
    Args:
        request: HTTP request object containing:
            recordType: Type of count record ('component' or 'blend' or 'warehouse')
            countListId: ID of the CountCollectionLink to update
            countId: ID of the count record to add/remove
            action: 'add' or 'delete'
            
    Returns:
        JsonResponse with result status:
            {'result': 'Countlist successfully updated'} on success
            {'result': 'failure'} on error
    """
    try:
        count_list_id = request.GET.get('countListId')
        count_id = request.GET.get('countId')
        action = request.GET.get('action')
        this_count_list = CountCollectionLink.objects.get(pk=count_list_id)

        if action == 'delete':
            if count_id in this_count_list.count_id_list:
                this_count_list.count_id_list.remove(count_id)
            this_count_list.save()
        elif action == 'add':
            this_count_list.id_list.append(count_id)
            this_count_list.save()
        response = {'result' : 'Countlist successfully updated.'}

    except Exception as e:
        print(str(e))
        response = {'result' : 'failure'}
    return JsonResponse(response, safe=False)

def add_count_records(item_codes_list, record_type):
    """Creates new count records for a list of item codes.
    
    Args:
        item_codes_list (list): List of item codes to create count records for
        record_type (str): Type of count record ('component', 'blend', or 'warehouse')
        
    Returns:
        dict: Dictionary containing:
            collection_id (str): ID for this collection of count records
            primary_keys (list): List of primary keys for the created count records
            
    Creates count records in the appropriate model based on record_type.
    Looks up item descriptions and quantities from CiItem and ImItemWarehouse.
    Generates a unique collection ID and assigns it to all records.
    Returns collection ID and list of primary keys for created records.
    """
    item_descriptions = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__in=item_codes_list)}
    item_quantities = {item.itemcode : item.quantityonhand for item in ImItemWarehouse.objects.filter(itemcode__in=item_codes_list).filter(warehousecode__iexact='MTG')}
    model = get_count_record_model(record_type)
    today_string = dt.date.today().strftime("%Y%m%d")
    unique_values_count = model.objects.filter(counted_date=dt.date.today()).values('collection_id').distinct().count()
    this_collection_id = f'B{unique_values_count+1}-{today_string}'
    primary_keys = []
    for item_code in item_codes_list:
        this_description = item_descriptions[item_code]
        this_item_onhandquantity = item_quantities[item_code]
        try:
            new_count_record = model(
                item_code = item_code,
                item_description = this_description,
                expected_quantity = this_item_onhandquantity,
                counted_quantity = 0,
                counted_date = dt.date.today(),
                variance = 0 - this_item_onhandquantity,
                count_type = record_type,
                collection_id = this_collection_id
            )
            new_count_record.save()
            print(f'adding {new_count_record.pk} to primary_keys') 
            primary_keys.append(new_count_record.pk)

        except Exception as e:
            print(str(e))
            continue

    return {'collection_id' : this_collection_id, 'primary_keys' : primary_keys}

def add_item_to_new_group(request):
    """Add an item to a new audit group.
    
    Takes an item ID and new audit group name from request parameters and updates
    the item's audit group assignment. Used for organizing inventory items into
    different counting/auditing groups.

    Args:
        request: HTTP request containing:
            recordType: Type of count record ('blend', 'blendcomponent', 'warehouse')
            auditGroup: Name of new audit group to assign
            redirectPage: Page to redirect to after update
            itemID: ID of item to update
            
    Returns:
        HttpResponseRedirect to items-by-audit-group page for the record type
    """
    record_type = request.GET.get('recordType')
    new_audit_group = request.GET.get('auditGroup')
    item_id = request.GET.get('itemID')
    # print(f'record_type:{record_type}\nnew_audit_group:{new_audit_group}\nredirect_page:{redirect_page}\nitem_id:{item_id}')
    this_item = get_object_or_404(AuditGroup, id = item_id)
    this_item.audit_group = new_audit_group
    this_item.save()

    return HttpResponseRedirect(f'/core/items-by-audit-group?recordType={record_type}')

def add_audit_group(request):
    """Add a new audit group.
    
    Processes POST request to create a new audit group for organizing inventory items.
    Validates and saves the audit group form data.

    Args:
        request: HTTP request containing POST data with audit group form fields
        
    Returns:
        HttpResponseRedirect to home page on success
        Rendered form template with errors on validation failure
    """
    if 'addNewAuditGroup' in request.POST:
        add_audit_group_form = AuditGroupForm(request.POST)
        if add_audit_group_form.is_valid():
            new_audit_group = add_audit_group_form.save()
        else:
            return render(request, {'add_audit_group_form' : add_audit_group_form})
    else:
        return HttpResponseRedirect('/')

def update_collection_link_order(request):
    """Update the display order of count collection links.
    
    Processes AJAX requests to update the order/position of count collection links
    in the UI. Decodes a base64 encoded JSON string containing collection IDs and 
    their new positions.

    Args:
        request: HTTP request containing:
            encodedCollectionLinkOrder (str): Base64 encoded JSON mapping collection IDs to positions

    Returns:
        JsonResponse with:
            success: Success message if update succeeds
            failure: Error message if update fails
    """
    base64_collection_link_order = request.GET.get('encodedCollectionLinkOrder')
    json_collection_link_order = base64.b64decode(base64_collection_link_order).decode()
    collection_link_order = json.loads(json_collection_link_order)
    try:
        for key, value in collection_link_order.items():
            print(f'setting countlink {key} to position {value}')
            this_item = CountCollectionLink.objects.get(collection_id=key)
            this_item.link_order = value
            this_item.save()
        response_json = {'success' : 'success'}
    except Exception as e:
        response_json = {'failure' : str(e)}

    return JsonResponse(response_json, safe=False)

def get_variance_analysis(count_record, from_date, to_date):
    """Analyze inventory count variances for a count record.
    
    Calculates key variance metrics by analyzing transaction history:
    - Total BI (blend ingredient) quantity used since last II/IA transaction
    - Variance as percentage of total BI quantity
    - Previous year's variance from II/IA transactions
    
    Args:
        count_record: CountRecord object containing count data
        from_date (date): Start date for historical analysis
        to_date (date): End date for historical analysis
        
    Returns:
        dict: Analysis results containing:
            - total_bi_qty_since_last_ii_ia: Total BI quantity used
            - variance_as_percentage_of_BI: Variance as % of BI usage
            - variance_last_year: Previous year's variance amount
    """
    if ImItemTransactionHistory.objects \
        .filter(itemcode__iexact=count_record.item_code) \
        .filter(transactioncode__in=['II','IA']) \
        .filter(transactiondate__gte=from_date) \
        .filter(transactiondate__lte=to_date) \
        .order_by('transactionqty').first():
        variance_last_year = ImItemTransactionHistory.objects \
            .filter(itemcode__iexact=count_record.item_code) \
            .filter(transactioncode__in=['II','IA']) \
            .filter(transactiondate__gte=from_date) \
            .filter(transactiondate__lte=to_date) \
            .order_by('-transactionqty').first().transactionqty
    else:
        variance_last_year = "Not found"
    if ImItemTransactionHistory.objects \
        .filter(itemcode__iexact=count_record.item_code) \
        .filter(transactioncode__in=['II', 'IA']) \
        .order_by('-transactiondate').exists():
        last_transaction_date = ImItemTransactionHistory.objects \
            .filter(itemcode__iexact=count_record.item_code) \
            .filter(transactioncode__in=['II', 'IA']) \
            .order_by('-transactiondate') \
            .first().transactiondate
    else:
        last_transaction_date = dt.datetime.now() - dt.timedelta(days=365)

    total_bi_qty_since_last_ii_ia = ImItemTransactionHistory.objects \
            .filter(itemcode__iexact=count_record.item_code) \
            .filter(transactioncode__iexact='BI') \
            .filter(transactiondate__gt=last_transaction_date) \
            .aggregate(total_qty=Sum('transactionqty'))['total_qty']
    variance_as_percentage_of_BI = (0 if count_record.variance is None else count_record.variance) / (1 if total_bi_qty_since_last_ii_ia == 0 or total_bi_qty_since_last_ii_ia is None else total_bi_qty_since_last_ii_ia)
    variance_as_percentage_of_BI = abs(variance_as_percentage_of_BI) * 100

    return {'total_bi_qty_since_last_ii_ia' : total_bi_qty_since_last_ii_ia,
            'variance_as_percentage_of_BI' : variance_as_percentage_of_BI, 
            'variance_last_year' : variance_last_year}

def delete_count_collection_links(request):
    """Delete selected count collection links.
    
    Deletes CountCollectionLink records based on provided list of IDs.
    Used to remove unwanted count collection links from the system.

    Args:
        request: HTTP request containing:
            list (str): Comma-separated list of collection link IDs to delete

    Returns:
        HttpResponseRedirect to count collection links display page
    """
    pk_list = request.GET.get("list")

    collection_ids_list = list(pk_list.replace('[', '').replace(']', '').replace('"', '').split(","))

    for collection_id in collection_ids_list:
        this_collection_link = CountCollectionLink.objects.get(pk=collection_id)
        this_collection_link.delete()
    
    return HttpResponseRedirect("/core/display-count-collection-links/")

def update_count_collection_link(request):
    """Update collection ID for a count collection link.
    
    Updates the collection_id field of a CountCollectionLink record based on provided 
    primary key and new collection ID values. Used to modify existing count collection
    links.

    Args:
        request: HTTP request containing:
            thisPk (str): Primary key of CountCollectionLink to update
            newCollectionId (str): New collection ID value to set

    Returns:
        JsonResponse with:
            Status: 'success' or 'failure'
            result: New collection ID or error message
    """
    this_pk = request.GET.get("thisPk")
    new_collection_id = request.GET.get("newCollectionId")
    try:
        this_collection_link = CountCollectionLink.objects.get(pk=this_pk)
        this_collection_link.collection_id = new_collection_id
        this_collection_link.save()
        response_item = {"Status" : "success",
                         "result" : f'New collection_id is {this_collection_link.collection_id}'}
    except Exception as e:
        response_item = {"Status" : "failure",
                         "result" : str(e)}

    return JsonResponse(response_item, safe=False)

def log_container_label_print(request):
    """Log when a partial container label is printed.
    
    Creates a PartialContainerLabelLog record to track when labels are printed
    for partial containers of specific items.
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code
            
    Returns:
        JsonResponse containing:
            result (str): 'success' if log created, 'error: <message>' if failed
    """
    encoded_item_code = request.GET.get("encodedItemCode", "")
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    response_json = {'result' : 'success'}
    try: 
        new_log = PartialContainerLabelLog(item_code=item_code)
        new_log.save()
    except Exception as e:
        response_json = { 'result' : 'error: ' + str(e)}
    return JsonResponse(response_json, safe=False)
    

@login_required
@require_POST
def update_purchasing_alias_audit(request):
    """Mark a purchasing alias as audited for the current date."""

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    requested_supply_type = extract_supply_type(request, payload)

    alias_id = payload.get('alias_id')
    if not alias_id:
        return JsonResponse({'status': 'error', 'error': 'Missing alias_id.'}, status=400)

    alias = get_object_or_404(PurchasingAlias, pk=alias_id)
    if requested_supply_type and alias.supply_type != requested_supply_type:
        return JsonResponse({'status': 'error', 'error': 'Alias does not match requested supply type.'}, status=400)

    if not alias.monthly_audit_needed:
        return JsonResponse({'status': 'error', 'error': 'Alias is not configured for monthly audit.'}, status=400)

    is_counted = payload.get('is_counted')
    if is_counted is None:
        is_counted = True

    audit_date = timezone.localdate() if is_counted else None
    alias.last_audit_date = audit_date
    alias.save(update_fields=['last_audit_date', 'updated_at'])

    return JsonResponse(
        {
            'status': 'success',
            'alias_id': alias_id,
            'last_audit_date': audit_date.isoformat() if audit_date else None,
            'last_audit_date_formatted': audit_date.strftime('%Y-%m-%d') if audit_date else None,
            'counted_this_month': bool(audit_date),
            'supply_type': alias.supply_type,
        }
    )


@login_required
@require_POST
def update_purchasing_alias(request, alias_id):
    """Persist inline edits to a purchasing alias."""

    alias = get_object_or_404(PurchasingAlias, pk=alias_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    requested_supply_type = extract_supply_type(request, payload)
    if requested_supply_type and alias.supply_type != requested_supply_type:
        return JsonResponse({'status': 'error', 'error': 'Alias does not match requested supply type.'}, status=400)

    logger.info('Purchasing alias update payload received for %s: %s', alias_id, payload)

    merged_data = {}
    for field in PurchasingAliasForm.Meta.fields:
        if field in payload:
            merged_data[field] = payload[field]
        else:
            merged_data[field] = getattr(alias, field)

    logger.info('Merged purchasing alias data for %s: %s', alias_id, merged_data)

    form = PurchasingAliasForm(data=merged_data, instance=alias)
    if not form.is_valid():
        logger.warning('Purchasing alias update validation failed for %s: %s', alias_id, form.errors)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    updated_alias = form.save()
    changed_fields = form.changed_data

    logger.info('Purchasing alias %s updated fields: %s', alias_id, changed_fields)

    return JsonResponse(
        {
            'status': 'success',
            'alias_id': alias_id,
            'changed_fields': changed_fields,
            'alias': {
                'supply_type': updated_alias.supply_type,
                'vendor': updated_alias.vendor,
                'vendor_part_number': updated_alias.vendor_part_number,
                'vendor_description': updated_alias.vendor_description,
                'link': updated_alias.link,
                'blending_notes': updated_alias.blending_notes,
                'monthly_audit_needed': updated_alias.monthly_audit_needed,
                'last_audit_date': updated_alias.last_audit_date.isoformat() if updated_alias.last_audit_date else None,
                'updated_at': updated_alias.updated_at.isoformat() if updated_alias.updated_at else None,
            },
        }
    )


@login_required
@require_POST
def create_purchasing_alias(request):
    """Create a placeholder purchasing alias record for inline editing."""

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

    normalized_supply_type = extract_supply_type(
        request,
        payload,
        default=PurchasingAlias.SUPPLY_TYPE_OPERATING,
    ) or PurchasingAlias.SUPPLY_TYPE_OPERATING
    payload['supply_type'] = normalized_supply_type
    payload.setdefault('monthly_audit_needed', False)

    form = PurchasingAliasForm(data=payload)
    if not form.is_valid():
        logger.warning('Purchasing alias creation failed validation: %s', form.errors)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    alias = form.save()

    logger.info('Purchasing alias created with id %s', alias.id)

    return JsonResponse(
        {
            'status': 'success',
            'alias': {
                'id': alias.id,
                'supply_type': alias.supply_type,
                'vendor': alias.vendor,
                'vendor_part_number': alias.vendor_part_number,
                'vendor_description': alias.vendor_description,
                'link': alias.link,
                'blending_notes': alias.blending_notes,
                'monthly_audit_needed': alias.monthly_audit_needed,
                'created_at': alias.created_at.isoformat() if alias.created_at else None,
                'updated_at': alias.updated_at.isoformat() if alias.updated_at else None,
            },
        },
        status=201,
    )


@login_required
@require_POST
def delete_purchasing_alias(request, alias_id):
    """Delete a purchasing alias record."""

    alias = get_object_or_404(PurchasingAlias, pk=alias_id)

    requested_supply_type = extract_supply_type(request)
    if requested_supply_type and alias.supply_type != requested_supply_type:
        return JsonResponse({'status': 'error', 'error': 'Alias does not match requested supply type.'}, status=400)

    alias.delete()

    logger.info('Purchasing alias %s deleted', alias_id)

    return JsonResponse({'status': 'success', 'alias_id': alias_id})
