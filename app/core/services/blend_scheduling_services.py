import logging
from django.db.models import Max
from core.models import DeskOneSchedule, DeskTwoSchedule, LetDeskSchedule, LotNumRecord, ImItemWarehouse, CiItem
from core.models import ImItemCost, HxBlendthese, BillOfMaterials, ComponentShortage
from django.http import JsonResponse, HttpResponseRedirect
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from core.services.production_planning_services import calculate_new_shortage
import base64
import json
import datetime as dt
from collections import deque, defaultdict
from django.db.models import Sum
from core.websockets.serializer import serialize_for_websocket
from core.websockets.publishers import broadcast_blend_schedule_update

logger = logging.getLogger(__name__)

advance_blends = ['602602','602037US','602037','602011','602037EUR','93700.B','94700.B','93800.B','94600.B','94400.B','602067']

def add_message_to_schedule(desk, message):
    if desk == 'Desk_2':
        max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskOneSchedule(
            item_code = '!!!!!',
            item_description = message,
            lot = '!!!!!',
            blend_area = desk,
            order = max_number + 1
            )
        new_schedule_item.save()
    if desk == 'Desk_1':
        max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskOneSchedule(
            item_code = '!!!!!',
            item_description = message,
            lot = '!!!!!',
            blend_area = desk,
            order = max_number + 1
            )
        new_schedule_item.save()

def add_lot_to_schedule(this_lot_desk, add_lot_form, lot_record=None):
    """
    Adds a new lot to the specified desk's schedule.
    
    Takes a desk identifier and form data, creates a new schedule entry with
    an incremented order number at the end of the specified desk's schedule.
    
    Args:
        this_lot_desk (str): Identifier for which desk schedule to add to ('Desk_1' or 'Desk_2')
        add_lot_form (Form): Form containing the lot and item details to add
        
    Returns:
        None - Creates and saves new DeskOneSchedule or DeskTwoSchedule object
    """
    new_schedule_item = None
    lot_number = None
    item_code = None
    item_description = None
    form_line = None

    if lot_record:
        lot_number = lot_record.lot_number
        item_code = lot_record.item_code
        item_description = lot_record.item_description
        form_line = lot_record.line
    else:
        lot_number = add_lot_form.cleaned_data.get('lot_number')
        item_code = add_lot_form.cleaned_data.get('item_code')
        item_description = add_lot_form.cleaned_data.get('item_description')
        form_line = add_lot_form.cleaned_data.get('line')
    
    if this_lot_desk == 'Desk_1':
        max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskOneSchedule(
            item_code=item_code,
            item_description=item_description,
            lot=lot_number,
            blend_area=add_lot_form.cleaned_data['desk'],
            order=max_number + 1
        )
        new_schedule_item.save()
        
    elif this_lot_desk == 'Desk_2':
        max_number = DeskTwoSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskTwoSchedule(
            item_code=item_code,
            item_description=item_description,
            lot=lot_number,
            blend_area=add_lot_form.cleaned_data['desk'],
            order=max_number + 1
        )
        new_schedule_item.save()
        
    elif this_lot_desk == 'LET_Desk':
        max_number = LetDeskSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = LetDeskSchedule(
            item_code=item_code,
            item_description=item_description,
            lot=lot_number,
            blend_area=add_lot_form.cleaned_data['desk'],
            order=max_number + 1
        )
        new_schedule_item.save()
    elif this_lot_desk == 'Horix':
        lot_rec = lot_record
        if not lot_rec and lot_number:
            try:
                lot_rec = LotNumRecord.objects.get(lot_number=lot_number)
            except LotNumRecord.DoesNotExist:
                lot_rec = None

        if lot_rec:
            lot_id = lot_rec.pk
            has_been_printed = bool(lot_rec.last_blend_sheet_print_event)
            last_print_str = (
                lot_rec.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y')
                if lot_rec.last_blend_sheet_print_event else '<em>Not Printed</em>'
            )
            is_urgent = getattr(lot_rec, 'is_urgent', False)
            line = lot_rec.line or 'Hx'
            resolved_item_code = lot_rec.item_code
            resolved_item_desc = lot_rec.item_description
        else:
            lot_id = None
            has_been_printed = False
            last_print_str = '<em>Not Printed</em>'
            is_urgent = False
            line = form_line or 'Hx'
            resolved_item_code = item_code
            resolved_item_desc = item_description

        quantity = None
        run_date_str = None

        if lot_rec:
            quantity = getattr(lot_rec, 'lot_quantity', None)
            run_date_value = getattr(lot_rec, 'run_date', None)
            run_date_str = run_date_value.strftime('%Y-%m-%d') if run_date_value else None

        add_data = {
            'blend_id': lot_id,
            'lot_id': lot_id,
            'lot_num_record_id': lot_id,
            'lot_number': lot_number,
            'item_code': resolved_item_code,
            'item_description': resolved_item_desc,
            'blend_area': 'Hx',
            'line': line or 'Hx',
            'quantity': quantity,
            'run_date': run_date_str,
            'has_been_printed': has_been_printed,
            'last_print_event_str': last_print_str,
            'is_urgent': is_urgent,
        }
        
        broadcast_blend_schedule_update(
            'new_blend_added',
            add_data,
            areas=['Hx'],
        )
        return

    if new_schedule_item:
        try:
            lot_rec = LotNumRecord.objects.get(lot_number=new_schedule_item.lot)
            lot_id = lot_rec.pk
            has_been_printed = bool(lot_rec.last_blend_sheet_print_event)
            last_print_str = lot_rec.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y') if lot_rec.last_blend_sheet_print_event else '<em>Not Printed</em>'
            is_urgent = getattr(lot_rec, 'is_urgent', False)
            line = lot_rec.line
        except LotNumRecord.DoesNotExist:
            lot_id = None
            has_been_printed = False
            last_print_str = '<em>Not Printed</em>'
            is_urgent = False
            line = None
            quantity = None
            run_date_str = None
        else:
            quantity = getattr(lot_rec, 'lot_quantity', None)
            run_date_value = getattr(lot_rec, 'run_date', None)
            run_date_str = run_date_value.strftime('%Y-%m-%d') if run_date_value else None

        add_data = {
            'blend_id': new_schedule_item.pk,
            'lot_id': lot_id,
            'lot_number': new_schedule_item.lot,
            'item_code': new_schedule_item.item_code,
            'item_description': new_schedule_item.item_description,
            'blend_area': new_schedule_item.blend_area,
            'line': line,
            'quantity': quantity,
            'run_date': run_date_str,
            'has_been_printed': has_been_printed,
            'last_print_event_str': last_print_str,
            'is_urgent': is_urgent,
        }
        
        broadcast_blend_schedule_update(
            'new_blend_added',
            add_data,
            areas=[new_schedule_item.blend_area],
        )

def clean_completed_blends(blend_area):
    """
    Removes completed blends from all schedule tables.
    
    A blend is considered completed when its lot number exists in ImItemCost records.
    This indicates the blend has been processed and is no longer needed in the schedule.
    """
    schedule_areas = ["Desk_1","Desk_2","LET_Desk"]
    schedule_tables = {
        "Desk_1" : DeskOneSchedule, 
        "Desk_2" : DeskTwoSchedule,
        "LET_Desk" : LetDeskSchedule
        }
    
    if blend_area in schedule_areas:
        model = schedule_tables[blend_area]

        for scheduled_blend in model.objects.all():
            if scheduled_blend.item_code not in ['INVENTORY', '******', '!!!!!']:
                if ImItemCost.objects.filter(receiptno__iexact=scheduled_blend.lot).exists():
                    blend_id = scheduled_blend.pk
                    blend_area = scheduled_blend.blend_area
                    lot_number = scheduled_blend.lot

                    scheduled_blend.delete()

                    deletion_payload = serialize_for_websocket({
                        'blend_id': blend_id,
                        'blend_area': blend_area,
                        'lot_number': lot_number,
                    })
                    broadcast_blend_schedule_update(
                        'blend_deleted',
                        deletion_payload,
                        areas=[blend_area],
                    )

def get_blend_schedule_querysets():
    """
    Retrieves blend schedule querysets for all production areas.
    
    Returns:
        dict: Mapping of area codes to their respective queryset of scheduled blends
    """
    return {
        'Desk_1': DeskOneSchedule.objects.all().order_by('order'),
        'Desk_2': DeskTwoSchedule.objects.all().order_by('order'),
        'LET_Desk': LetDeskSchedule.objects.all().order_by('order'),
        'Hx': HxBlendthese.objects
            .filter(prod_line__iexact='Hx')
            .filter(component_item_description__startswith='BLEND-')
            .order_by('run_date'),
        'Dm': HxBlendthese.objects
            .filter(prod_line__iexact='Dm')
            .filter(component_item_description__startswith='BLEND-')
            .order_by('run_date'),
        'Totes': HxBlendthese.objects
            .filter(prod_line__iexact='Totes')
            .filter(component_item_description__startswith='BLEND-')
            .order_by('run_date')
    }

def _calculate_shortage_time_for_blend(blend, queryset, area):
    """
    Internal helper to calculate shortage start time and cumulative quantity for a blend.
    """
    hourshort = getattr(blend, 'hourshort', 9999)
    cumulative_qty = 0

    if not ComponentShortage.objects.filter(component_item_code__iexact=blend.item_code).exists():
        logger.debug("No component shortages found for %s", blend.item_code)
        return hourshort, cumulative_qty

    earliest_shortage = ComponentShortage.objects.filter(
        component_item_code__iexact=blend.item_code
    ).order_by('start_time').first()

    if earliest_shortage:
        hourshort = earliest_shortage.start_time

    lot_list = [blend.lot for blend in queryset.filter(item_code=blend.item_code, order__lt=blend.order)]

    if len(lot_list) == 1 and earliest_shortage:
        hourshort = earliest_shortage.start_time

    cumulative_qty = LotNumRecord.objects.filter(lot_number__in=lot_list) \
        .aggregate(Sum('lot_quantity'))['lot_quantity__sum'] or 0

    if cumulative_qty == 0 and earliest_shortage:
        hourshort = earliest_shortage.start_time
    else:
        new_shortage = calculate_new_shortage(blend.item_code, cumulative_qty)
        if new_shortage:
            hourshort = new_shortage['start_time']

    if 'LET' not in area:
        if blend.item_code in advance_blends:
            hourshort = max((hourshort - 30), 5)
        else:
            hourshort = max((hourshort - 5), 1)

    return hourshort, cumulative_qty

def calculate_shortage_times(queryset, area):
    """
    Calculate shortage times for all blends in a queryset.

    This can be executed independently of prepare_blend_schedule_queryset.

    Args:
        queryset (QuerySet): Blend schedule queryset.
        area (str): Blend area code (e.g., 'Desk_1', 'Desk_2').

    Returns:
        list: [{blend_id: (hourshort, cumulative_qty)}, ...]
    """
    results = []
    for blend in queryset:
        hourshort, cumulative_qty = _calculate_shortage_time_for_blend(blend, queryset, area)
        results.append({blend.pk: (hourshort, cumulative_qty)})
    return results

def prepare_blend_schedule_queryset(area, queryset):
    """Prepare blend schedule queryset by adding additional  attributes and filtering.

    Processes a blend schedule queryset for a specific area by:
    - Adding quantity, line, and run date from LotNumRecord
    - Checking for component shortages and setting hourshort
    - Calculating max blend figures per component
    - Setting tank options for desk areas
    - Removing invalid records

    Args:
        area (str): Blend area code ('Desk_1', 'Desk_2', 'Hx', 'Dm', 'Totes')
        queryset (QuerySet): Django queryset of blend schedule records

    Returns:
        QuerySet: Modified queryset with additional attributes set
    """

    this_desk_tanks = ['']
    if area == 'Desk_1':
        this_desk_tanks = ['300gal Polish Tank','400gal Stainless Tank','King W/W Tank',
                    'LET Drum','Oil Bowl','MSR Tank','Startron Tank','Startron Amber Tank',
                    'Tank 11','Tank 12','Tank 13','Tank M','Tank M1','Tank M2','Tank M3',
                    'Tank N','Tank P1','Tank P2','Tank P3','Teak Oil Tank','Tote','Waterproofing Tank']
    elif area == 'Desk_2':
        this_desk_tanks = ['300gal Polish Tank','400gal Stainless Tank','King W/W Tank','Startron Tank',
                          'Startron Amber Tank','Tank 14','Tank 15','Tank 19','Tank 20','Tank 21',
                          'Teak Oil Tank','Tote']

    if 'Desk' in area:
        if queryset.exists():
            item_code_list = [blend.item_code for blend in queryset]
            max_blend_numbers_dict = {}
            for item_code in item_code_list:
                max_blend_figures_per_component = []
                this_item_boms = BillOfMaterials.objects.filter(item_code__iexact=item_code) \
                                    .exclude(component_item_code__startswith='/') \
                                    .exclude(component_item_code__startswith='030143')
                for bom in this_item_boms:
                    if not int(bom.qtyperbill) == 0:
                        max_blend_figures_per_component.append({bom.component_item_code : float(bom.qtyonhand) / float(bom.qtyperbill)})
                    else:
                        max_blend_figures_per_component.append({bom.component_item_code : "QtyPerBill is zero"})
                max_blend_numbers_dict[item_code] = max_blend_figures_per_component
            shortage_lookup = {
                list(item.keys())[0]: list(item.values())[0]
                for item in calculate_shortage_times(queryset, area)
            }
            for blend in queryset:
                blend.hourshort = 9999
                blend.lot_num_record_obj = None
                try:
                    lot_record = LotNumRecord.objects.get(lot_number=blend.lot)
                    blend.lot_num_record_obj = lot_record
                    blend.quantity = lot_record.lot_quantity
                    blend.line = lot_record.line
                    blend.run_date = lot_record.run_date
                    blend.lot_id = lot_record.pk
                except LotNumRecord.DoesNotExist:
                    if blend.item_code not in ['INVENTORY', '******', '!!!!!']:
                        blend.delete()
                        continue
                except LotNumRecord.MultipleObjectsReturned:
                    pass
                except Exception:
                    pass
                # calculate the earliest shortage and cumulative quantity for scheduling
                blend.hourshort, blend.cumulative_qty = shortage_lookup.get(blend.pk, (getattr(blend, 'hourshort', 9999), 0))
                for component in max_blend_numbers_dict[blend.item_code]:
                    for key, value in component.items():
                        if not value == 'QtyPerBill is zero':
                            if value < blend.quantity:
                                blend.short_chemical = key
                if blend.tank:
                    this_blend_tank_options = [tank for tank in this_desk_tanks if tank != blend.tank]
                    blend.tank_options = this_blend_tank_options
                else: 
                    blend.tank_options = this_desk_tanks

                blend.encoded_item_code = base64.b64encode(blend.item_code.encode()).decode()

    else:
        these_item_codes = list(queryset.values_list('component_item_code', flat=True))
        two_days_ago = dt.datetime.now().date() - dt.timedelta(days=2)
         
        horix_groups = defaultdict(list)
        for blend in queryset:
            # Convert run_date to date for consistent keys
            run_date_key = blend.run_date.date() if hasattr(blend.run_date, 'date') else blend.run_date
            key = (blend.component_item_code, run_date_key)
            horix_groups[key].append(blend)

        lot_deques = defaultdict(deque)
        lot_records = LotNumRecord.objects.filter(
            item_code__in=these_item_codes,
            run_date__gt=two_days_ago,
            line__iexact=area
        ).order_by('run_date', 'pk')

        for record in lot_records:
            run_date_key = record.run_date.date() if hasattr(record.run_date, 'date') else record.run_date
            key = (record.item_code, run_date_key)
            lot_deques[key].append(record)

        for key, horix_blends in horix_groups.items():
            if key in lot_deques:
                lots_deque = lot_deques[key]
                excess = max(len(lots_deque) - len(horix_blends), 0)
                for _ in range(excess):
                    lots_deque.popleft()  # Remove oldest lots

        for blend in queryset:
            run_date_key = blend.run_date.date() if hasattr(blend.run_date, 'date') else blend.run_date
            key = (blend.component_item_code, run_date_key)
            
            blend.hourshort = 0
            blend.lot_number = 'Not found.'
            blend.lot_num_record_obj = None
            blend.lot_id = None
            
            if key in lot_deques and lot_deques[key]:
                lot_record = lot_deques[key].popleft()
                blend.lot_number = lot_record.lot_number
                blend.lot_quantity = lot_record.lot_quantity
                blend.lot_num_record_obj = lot_record
                blend.lot_id = lot_record.pk
                blend.turned_in = lot_record.sage_entered_date

            # Continue with existing warehouse/product line logic
            blend.quantityonhand = ImItemWarehouse.objects \
                .filter(itemcode__iexact=blend.component_item_code) \
                .filter(warehousecode__iexact='MTG') \
                .first().quantityonhand
            blend.productline = CiItem.objects \
                .filter(itemcode__iexact=blend.component_item_code) \
                .first().productline
    
    return queryset

def get_available_tanks_for_desk(request):
    """Get available tank options for a specific desk area.
    
    Returns JSON response with tank options for the specified desk area.
    Used by the tank selection modal when moving blends between desks.

    Args:
        request: HTTP request containing 'desk_area' parameter

    Returns:
        JsonResponse with tank options list
    """
    desk_area = request.GET.get('desk_area', '')
    
    tank_options = []
    if desk_area == 'Desk_1':
        tank_options = ['300gal Polish Tank','400gal Stainless Tank','King W/W Tank',
                       'LET Drum','Oil Bowl','MSR Tank','Startron Tank','Startron Amber Tank',
                       'Tank 11','Tank 12','Tank 13','Tank M','Tank M1','Tank M2','Tank M3',
                       'Tank N','Tank P1','Tank P2','Tank P3','Teak Oil Tank','Tote','Waterproofing Tank']
    elif desk_area == 'Desk_2':
        tank_options = ['300gal Polish Tank','400gal Stainless Tank','King W/W Tank','Startron Tank',
                       'Startron Amber Tank','Tank 14','Tank 15','Tank 19','Tank 20','Tank 21',
                       'Teak Oil Tank','Tote']
    elif desk_area == 'LET_Desk':
        tank_options = ['LET Drum','Tote']  # Add LET_Desk tank options
    
    return JsonResponse({
        'tank_options': tank_options,
        'desk_area': desk_area
    })

def move_blend_with_tank_selection(request):
    """Handle blend moves with tank compatibility checking and selection.
    
    This endpoint checks if the current tank is compatible with the destination desk.
    If not, it returns tank options for user selection. If compatible or tank is selected,
    it performs the move with WebSocket notifications.

    Args:
        request: HTTP request containing move parameters

    Returns:
        JsonResponse with move result or tank selection requirements
    """
    
    logger = logging.getLogger(__name__)
    
    try:
        # Extract parameters
        blend_area = request.GET.get('blend_area')
        blend_id = request.GET.get('blend_id')
        destination_desk = request.GET.get('destination_desk')
        selected_tank = request.GET.get('selected_tank')  # Optional - provided in second call
        hourshort = request.GET.get('hourshort')
        
        logger.info(f"🔄 Tank-aware blend move request: {blend_id} from {blend_area} to {destination_desk}")
        
        # Get the blend
        schedule_models = {
            'Desk_1': DeskOneSchedule,
            'Desk_2': DeskTwoSchedule,
            'LET_Desk': LetDeskSchedule
        }
        
        blend_model = schedule_models.get(blend_area)
        blend = blend_model.objects.get(pk=blend_id)
        original_tank = getattr(blend, 'tank', None)
        
        # Define tank options for each desk
        desk_tanks = {
            'Desk_1': ['300gal Polish Tank','400gal Stainless Tank','King W/W Tank',
                      'LET Drum','Oil Bowl','MSR Tank','Startron Tank','Startron Amber Tank',
                      'Tank 11','Tank 12','Tank 13','Tank M','Tank M1','Tank M2','Tank M3',
                      'Tank N','Tank P1','Tank P2','Tank P3','Teak Oil Tank','Tote','Waterproofing Tank'],
            'Desk_2': ['300gal Polish Tank','400gal Stainless Tank','King W/W Tank','Startron Tank',
                      'Startron Amber Tank','Tank 14','Tank 15','Tank 19','Tank 20','Tank 21',
                      'Teak Oil Tank','Tote'],
            'LET_Desk': ['LET Drum','Tote']
        }
        
        destination_tanks = desk_tanks.get(destination_desk, [])
        tank_compatible = original_tank in destination_tanks if original_tank else True
        
        logger.info(f"🚰 Tank compatibility check: '{original_tank}' in {destination_desk} = {tank_compatible}")
        
        # If tank is incompatible and no tank selected, return tank selection options
        if original_tank and not tank_compatible and not selected_tank:
            logger.info(f"🚰 Requiring tank selection for incompatible tank '{original_tank}'")
            return JsonResponse({
                'requires_tank_selection': True,
                'original_tank': original_tank,
                'destination_desk': destination_desk,
                'available_tanks': destination_tanks,
                'blend_info': {
                    'blend_id': blend_id,
                    'blend_area': blend_area,
                    'lot_number': blend.lot,
                    'item_code': blend.item_code,
                    'item_description': blend.item_description
                }
            })
        
        # Proceed with the move
        destination_model = schedule_models.get(destination_desk)
        max_number = destination_model.objects.aggregate(Max('order'))['order__max'] or 0
        
        # Handle tank assignment with special case for "None"
        if selected_tank:
            final_tank = None if selected_tank == 'None' else selected_tank
            logger.info(f"🚰 Moving blend with user-selected tank: '{selected_tank}' -> '{final_tank}'")
        else:
            final_tank = original_tank if tank_compatible else None
            logger.info(f"🚰 Moving blend with preserved tank: '{final_tank}' (compatible: {tank_compatible})")
        
        # Create new schedule item
        new_schedule_item = destination_model(
            item_code=blend.item_code,
            item_description=blend.item_description,
            lot=blend.lot,
            blend_area=destination_desk,
            order=max_number + 1,
            tank=final_tank
        )
        new_schedule_item.save()
        
        # Store original data for WebSocket
        original_blend_id = blend.pk
        original_blend_area = blend.blend_area
        
        # Delete original blend
        blend.delete()
        
        # Get lot record information for WebSocket
        lot_record = None
        has_been_printed = False
        last_print_str = '<em>Not Printed</em>'
        is_urgent = False
        quantity = 0
        
        try:
            lot_record = LotNumRecord.objects.get(lot_number=new_schedule_item.lot)
            has_been_printed = bool(lot_record.last_blend_sheet_print_event)
            last_print_str = lot_record.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y') if lot_record.last_blend_sheet_print_event else '<em>Not Printed</em>'
            is_urgent = getattr(lot_record, 'is_urgent', False)
            quantity = lot_record.lot_quantity if hasattr(lot_record, 'lot_quantity') else 0
        except LotNumRecord.DoesNotExist:
            logger.warning(f"⚠️ Could not find lot record for blend: {new_schedule_item.lot}")
        
        # Build row classes
        row_classes = ['tableBodyRow', destination_desk]
        if lot_record and hasattr(lot_record, 'line') and lot_record.line:
            row_classes.append(f'{lot_record.line}Row')
        if new_schedule_item.item_code == "******":
            row_classes.append('NOTE')
        elif new_schedule_item.item_code == "!!!!!":
            row_classes.append('priorityMessage')
        if is_urgent:
            row_classes.append('priorityMessage')
        
        # Handle hourshort value
        try:
            hourshort_value = float(hourshort) if hourshort else 999.0
        except (ValueError, TypeError):
            hourshort_value = 999.0
        
        # Prepare WebSocket data
        websocket_data = {
            'old_blend_id': original_blend_id,
            'old_blend_area': original_blend_area,
            'new_blend_id': new_schedule_item.pk,
            'new_blend_area': destination_desk,
            'lot_num_record_id': lot_record.pk if lot_record else None,
            'lot_id': lot_record.pk if lot_record else None,
            'lot_number': new_schedule_item.lot,
            'item_code': new_schedule_item.item_code,
            'item_description': new_schedule_item.item_description,
            'quantity': quantity,
            'order': new_schedule_item.order,
            'tank': final_tank,
            'has_been_printed': has_been_printed,
            'last_print_event_str': last_print_str,
            'print_history_json': getattr(lot_record, 'blend_sheet_print_history_json_data', '[]') if lot_record else '[]',
            'was_edited_after_last_print': getattr(lot_record, 'was_edited_after_last_print', False) if lot_record else False,
            'is_urgent': is_urgent,
            'row_classes': ' '.join(row_classes),
            'hourshort': hourshort_value,
            'line': getattr(lot_record, 'line', None) if lot_record else None,
            'run_date': lot_record.run_date.strftime('%Y-%m-%d') if lot_record and lot_record.run_date else None,
        }
        
        # Send WebSocket notification
        serialized_data = serialize_for_websocket(websocket_data)
        broadcast_blend_schedule_update(
            'blend_moved',
            serialized_data,
            areas=[original_blend_area, destination_desk],
        )
        
        logger.info("✅ Tank-aware blend move completed successfully")
        
        return JsonResponse({
            'success': True,
            'message': f'Blend moved to {destination_desk} with tank: {final_tank or "None"}',
            'new_blend_id': new_schedule_item.pk,
            'tank_assigned': final_tank
        })
        
    except Exception as e:
        logger.error(f"❌ Error in tank-aware blend move: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def manage_blend_schedule(request, request_type, blend_area, blend_id):
    """Manage blend schedule operations for a specific blend.
    
    Handles operations like deleting blends or switching them between schedules.
    Supports operations from different request sources (lot records, desk schedules).

    Args:
        request: The HTTP request object
        request_type: Type of operation to perform ('delete' or 'switch-schedules')
        blend_area: Area the blend is scheduled in ('Desk_1' or 'Desk_2')
        blend_id: ID of the blend schedule entry to operate on

    Returns:
        HttpResponseRedirect to appropriate page based on request source
    """
    import logging
    logger = logging.getLogger(__name__)
    
    request_source = request.GET.get('request-source', 0)
    destination_desk = request.GET.get('switch-to', 0)

    schedule_models = {
        'Desk_1': DeskOneSchedule,
        'Desk_2': DeskTwoSchedule,
        'LET_Desk': LetDeskSchedule
    }
    
    blend_model = schedule_models.get(blend_area)
    blend = blend_model.objects.get(pk=blend_id)

    if request_type == 'delete':
        original_blend_id = blend.pk
        original_blend_area = blend.blend_area
        blend.delete()
        
        logger.info(
            "🗑️ SENDING blend_deleted WebSocket message for blend_id: %s, area: %s",
            original_blend_id,
            original_blend_area,
        )
        broadcast_blend_schedule_update(
            'blend_deleted',
            {'blend_id': original_blend_id, 'blend_area': original_blend_area},
            areas=[original_blend_area],
        )
        logger.info("✅ blend_deleted WebSocket message sent successfully")

    if request_type == 'switch-schedules':
        destination_model = schedule_models.get(destination_desk, 0)
        max_number = destination_model.objects.aggregate(Max('order'))['order__max'] or 0
        
        original_blend_id = blend.pk
        original_blend_area = blend.blend_area
        
        logger.info(f"🔄 Starting blend switch: {original_blend_id} from {original_blend_area} to {destination_desk}")
        
        new_schedule_item = destination_model(
            item_code=blend.item_code,
            item_description=blend.item_description,
            lot=blend.lot,
            blend_area=destination_desk,
            order=max_number + 1
        )
        new_schedule_item.save()
        blend.delete()
        
        # Get lot record information (single lookup for efficiency)
        lot_record = None
        has_been_printed = False
        last_print_str = '<em>Not Printed</em>'
        is_urgent = False
        quantity = 0
        
        try:
            lot_record = LotNumRecord.objects.get(lot_number=new_schedule_item.lot)
            has_been_printed = bool(lot_record.last_blend_sheet_print_event)
            last_print_str = lot_record.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y') if lot_record.last_blend_sheet_print_event else '<em>Not Printed</em>'
            is_urgent = getattr(lot_record, 'is_urgent', False)
            quantity = lot_record.lot_quantity if hasattr(lot_record, 'lot_quantity') else 0
        except LotNumRecord.DoesNotExist:
            logger.warning(f"⚠️ Could not find lot record for blend: {new_schedule_item.lot}")

        row_classes = []
        
        if lot_record and hasattr(lot_record, 'line') and lot_record.line:
            row_classes.append(f'{lot_record.line}Row')
            logger.info(f"🎨 Added line-specific class: {lot_record.line}Row")
        
        row_classes.append('tableBodyRow')
        row_classes.append(destination_desk)
        if new_schedule_item.item_code == "******":
            row_classes.append('NOTE')
        elif new_schedule_item.item_code == "!!!!!":
            row_classes.append('priorityMessage')
        if is_urgent:
            row_classes.append('priorityMessage')
                
        # 🎯 ELEGANT SOLUTION: Use hourshort value from frontend instead of complex recalculation
        hourshort_value = request.GET.get('hourshort')
        run_date = None
        line = None
        
        # Get basic lot record information for other fields
        if lot_record:
            line = getattr(lot_record, 'line', None)
            run_date = getattr(lot_record, 'run_date', None)
        
        # Convert hourshort to float if provided, otherwise use fallback
        try:
            if hourshort_value is not None:
                hourshort_value = float(hourshort_value)
                logger.info(f"🎯 Using hourshort value from frontend: {hourshort_value}")
            else:
                hourshort_value = 999.0  # Default fallback
                logger.warning(f"⚠️ No hourshort provided from frontend, using default: {hourshort_value}")
        except (ValueError, TypeError) as e:
            hourshort_value = 999.0  # Safe fallback
            logger.warning(f"⚠️ Invalid hourshort value from frontend, using default: {hourshort_value} (error: {e})")

        websocket_data = {
            'old_blend_id': original_blend_id,
            'old_blend_area': original_blend_area,
            'new_blend_id': new_schedule_item.pk,
            'new_blend_area': destination_desk,
            'lot_num_record_id': lot_record.pk if lot_record else None,
            'lot_id': lot_record.pk if lot_record else None,
            'lot_number': new_schedule_item.lot,
            'item_code': new_schedule_item.item_code,
            'item_description': new_schedule_item.item_description,
            'quantity': quantity,
            'order': new_schedule_item.order,
            'tank': getattr(new_schedule_item, 'tank', None),  # 🚰 Include tank assignment
            'has_been_printed': has_been_printed,
            'last_print_event_str': last_print_str,
            'print_history_json': getattr(lot_record, 'blend_sheet_print_history_json_data', '[]') if lot_record else '[]',
            'was_edited_after_last_print': getattr(lot_record, 'was_edited_after_last_print', False) if lot_record else False,
            'is_urgent': is_urgent,
            'row_classes': ' '.join(row_classes),
            'hourshort': hourshort_value,
            'line': line,
            'run_date': run_date.strftime('%Y-%m-%d') if run_date else None,
        }
        
        logger.info(f"📊 WebSocket data hourshort: {hourshort_value}, line: {line}, run_date: {run_date}")
        logger.info(f"🚰 WebSocket data tank: '{websocket_data['tank']}' (type: {type(websocket_data['tank'])})")
        
        serialized_data = serialize_for_websocket(websocket_data)

        broadcast_blend_schedule_update(
            'blend_moved',
            serialized_data,
            areas=[original_blend_area, destination_desk],
        )
        
        logger.info("✅ blend_moved WebSocket message sent successfully")

    # 🎯 ENHANCED: Return JSON response for AJAX requests (no page reload needed!)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
        # AJAX request - return JSON response, WebSocket handles UI updates
        if request_type == 'delete':
            return JsonResponse({
                'success': True,
                'message': f'Blend deleted successfully from {blend_area}',
                'action': 'delete',
                'blend_id': original_blend_id,
                'blend_area': original_blend_area
            })
        elif request_type == 'switch-schedules':
            return JsonResponse({
                'success': True,
                'message': f'Blend moved successfully from {original_blend_area} to {destination_desk}',
                'action': 'move',
                'old_blend_id': original_blend_id,
                'old_blend_area': original_blend_area,
                'new_blend_id': new_schedule_item.pk,
                'new_blend_area': destination_desk
            })
    
    # Traditional browser request - redirect as before
    if request_source == 'lot-num-records':
        return HttpResponseRedirect('/core/lot-num-records')
    elif request_source == 'desk-1-schedule':
        return HttpResponseRedirect('/core/blend-schedule/?blend-area=Desk_1')
    elif request_source == 'desk-2-schedule':
        return HttpResponseRedirect('/core/blend-schedule/?blend-area=Desk_2')
    elif request_source == 'LET-desk-schedule':
        return HttpResponseRedirect('/core/blend-schedule/?blend-area=LET_Desk')

def add_note_line_to_schedule(request):
    """Add a note line marker to a blend desk schedule.
    
    Adds a special line item to either Desk 1 or Desk 2 blend schedule
    to add special notes or instructions.

    Args:
        request: The HTTP request object containing 'desk' parameter specifying
                which desk schedule to update ('Desk_1' or 'Desk_2')
                
    Returns:
        JsonResponse with status 'success' or 'failure' and error details if failed
    """
    try:
        desk = request.GET.get('desk','')
        note = request.GET.get('note','')
        lot = request.GET.get('lot','')
        new_schedule_item = None
        
        if desk == 'Desk_1':
            max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
            if not max_number:
                max_number = 0
            new_schedule_item = DeskOneSchedule(
                item_code = "******",
                item_description = note,
                lot = lot,
                blend_area = "Desk_1",
                order = max_number + 1,
                tank = None  # 🎯 FIXED: Schedule notes don't need tank assignments
                )
            new_schedule_item.save()
        elif desk == 'Desk_2':
            max_number = DeskTwoSchedule.objects.aggregate(Max('order'))['order__max']
            if not max_number:
                max_number = 0
            new_schedule_item = DeskTwoSchedule(
                item_code = "******",
                item_description = note,
                lot = lot,
                blend_area = "Desk_2",
                order = max_number + 1,
                tank = None  # 🎯 FIXED: Schedule notes don't need tank assignments
                )
            new_schedule_item.save()
        
        # 🎯 WEBSOCKET BROADCAST: Notify all connected clients of new schedule note
        if new_schedule_item:
            # Prepare WebSocket data for the new schedule note
            websocket_data = {
                'new_blend_id': new_schedule_item.pk,
                'new_blend_area': desk,
                'blend_area': desk,
                'lot_number': lot,
                'item_code': "******",
                'item_description': note,
                'quantity': 0,  # Schedule notes don't have quantities
                'order': new_schedule_item.order,
                'tank': None,  # Schedule notes don't have tanks
                'has_been_printed': False,
                'last_print_event_str': '<em>Not Printed</em>',
                'print_history_json': '[]',
                'was_edited_after_last_print': False,
                'is_urgent': False,
                'row_classes': f'tableBodyRow {desk} NOTE',  # Include NOTE class for schedule notes
                'hourshort': 999.0,  # Default value for schedule notes
                'line': None,
                'run_date': None,
            }
            
            logger.info(f"📝 Sending new_blend_added WebSocket message for schedule note: {lot} in {desk}")
            
            broadcast_blend_schedule_update(
                'new_blend_added',
                serialize_for_websocket(websocket_data),
                areas=[desk],
            )
            
            logger.info("✅ new_blend_added WebSocket message sent successfully for schedule note")
        
        response_json = { 'status' : 'success' }
        
    except Exception as e:
        logger.error(f"❌ Error adding schedule note: {str(e)}")
        response_json = { 'status' : 'failure',
                            'error' : str(e)}

    return JsonResponse(response_json, safe=False)

def update_scheduled_blend_tank(request):
    """Update the tank assignment for a scheduled blend.
    
    Updates the tank field for a scheduled blend in either Desk 1 or Desk 2 schedule.
    Takes base64 encoded lot number and tank values from request parameters to prevent
    special character issues. Broadcasts changes via WebSocket to all connected users.

    Args:
        request: HTTP request containing:
            - encodedLotNumber: Base64 encoded lot number string
            - encodedTank: Base64 encoded tank identifier string 
            - blendArea: Schedule area ('Desk_1' or 'Desk_2')

    Returns:
        JsonResponse with result message indicating success or failure
    """
    try:
        encoded_lot_number = request.GET.get('encodedLotNumber', '')
        lot_number_bytestr = base64.b64decode(encoded_lot_number)
        lot_number = lot_number_bytestr.decode().replace('"', "")

        encoded_tank = request.GET.get('encodedTank', '')
        tank_bytestr = base64.b64decode(encoded_tank)
        tank = tank_bytestr.decode().replace('"', "")

        blend_area = request.GET.get('blendArea', '')        

        # 🎯 ENHANCED: Handle "all" area by determining actual desk from lot number
        actual_blend_area = blend_area
        this_schedule_item = None
        
        if blend_area == 'all':
            # When on "all schedules" page, determine the actual desk by searching both
            try:
                this_schedule_item = DeskOneSchedule.objects.get(lot__iexact=lot_number)
                actual_blend_area = 'Desk_1'
            except DeskOneSchedule.DoesNotExist:
                try:
                    this_schedule_item = DeskTwoSchedule.objects.get(lot__iexact=lot_number)
                    actual_blend_area = 'Desk_2'
                except DeskTwoSchedule.DoesNotExist:
                    try:
                        this_schedule_item = LetDeskSchedule.objects.get(lot__iexact=lot_number)
                        actual_blend_area = 'LET_Desk'
                    except LetDeskSchedule.DoesNotExist:
                        raise ValueError(f"Lot number {lot_number} not found in any desk schedule")
        elif blend_area == 'Desk_1':
            this_schedule_item = DeskOneSchedule.objects.get(lot__iexact=lot_number)
        elif blend_area == 'Desk_2':
            this_schedule_item = DeskTwoSchedule.objects.get(lot__iexact=lot_number)
        elif blend_area == 'LET_Desk':
            this_schedule_item = LetDeskSchedule.objects.get(lot__iexact=lot_number)
        else:
            raise ValueError(f"Invalid blend area: {blend_area}")

        # Store old tank for WebSocket message
        old_tank = this_schedule_item.tank
        
        this_schedule_item.tank = tank
        this_schedule_item.save()
        
        # 🎯 BROADCAST TANK UPDATE VIA WEBSOCKET
        websocket_data = {
            'blend_id': this_schedule_item.pk,
            'blend_area': actual_blend_area,  # Use actual desk area, not "all"
            'lot_number': lot_number,
            'old_tank': old_tank,
            'new_tank': tank,
            'item_code': this_schedule_item.item_code,
            'item_description': this_schedule_item.item_description
        }
        
        logger.info(f"🚰 SENDING tank_updated WebSocket message for blend_id: {this_schedule_item.pk}, lot: {lot_number}, tank: {old_tank} → {tank}")
        
        broadcast_blend_schedule_update(
            'tank_updated',
            serialize_for_websocket(websocket_data),
            areas=[actual_blend_area],
        )
        
        logger.info("✅ tank_updated WebSocket message sent successfully")
        
        response_json = { 'result' : f'Success. Lot {lot_number} has been assigned to {tank}' }
    except Exception as e:
        logger.error(f"❌ Error updating tank assignment: {str(e)}")
        response_json = { 'result' : f'Error: {str(e)}' }

    return JsonResponse(response_json, safe=False)

def update_desk_order(request):
    """Update the order of items in desk schedules.
    
    Takes a base64 encoded JSON string containing desk schedule ordering information
    and updates the order field for the corresponding DeskOneSchedule or 
    DeskTwoSchedule records.
    
    Args:
        request: HTTP GET request containing:
            encodedDeskScheduleOrder (str): Base64 encoded JSON with:
                desk (str): 'Desk_1' or 'Desk_2' indicating which desk schedule
                lot_number: new order position pairs
                
    Returns:
        JsonResponse containing:
            status (str): 'success' or 'error'
            message (str): Description of result
            results (list): List of updated records with lot numbers and new orders
    """
    try:
        base64_schedule_order = request.GET.get('encodedDeskScheduleOrder')
        json_schedule_order = base64.b64decode(base64_schedule_order).decode()
        schedule_order = json.loads(json_schedule_order)
        
        results = []
        desk = schedule_order.get('desk')
        
        for key, value in schedule_order.items():
            if not key == 'desk':
                try:
                    if desk == 'Desk_1':
                        this_item = DeskOneSchedule.objects.get(lot=key)
                    elif desk == 'Desk_2':
                        this_item = DeskTwoSchedule.objects.get(lot=key)
                    elif desk == 'LET_Desk':
                        this_item = LetDeskSchedule.objects.get(lot=key)
                    else:
                        raise ValueError(f"Invalid desk value: {desk}")
                        
                    this_item.order = value
                    this_item.save()
                    
                    results.append({
                        'lot': key,
                        'new_order': value,
                        'desk': desk
                    })
                    
                except (DeskOneSchedule.DoesNotExist, DeskTwoSchedule.DoesNotExist, LetDeskSchedule.DoesNotExist) as e:
                    logger.error(f"Failed to update order for lot {key}: {str(e)}")
                    continue
        
        # 🎯 WEBSOCKET BROADCAST: Notify all connected clients of schedule reordering
        if results:  # Only send WebSocket message if there were successful updates
            # Prepare reordered items data for WebSocket
            reordered_items = [
                {
                    'blend_id': None,  # We don't have blend_id in this context, but lot is unique
                    'lot_number': result['lot'],
                    'new_order': int(result['new_order'])
                }
                for result in results
            ]
            
            # Determine blend area for WebSocket routing
            blend_area = desk  # desk is already 'Desk_1', 'Desk_2', or 'LET_Desk'
            
            websocket_data = {
                'blend_area': blend_area,
                'reordered_items': reordered_items,
                'total_reordered': len(results),
                'update_source': 'manual_sort'  # Distinguish from drag-and-drop
            }
            
            serialized_data = serialize_for_websocket(websocket_data)
            
            logger.info(f"🎯 Sending schedule_reordered WebSocket message for {blend_area} with {len(results)} items")
            
            broadcast_blend_schedule_update(
                'schedule_reordered',
                serialized_data,
                areas=[blend_area],
            )
            
            logger.info("✅ schedule_reordered WebSocket message sent successfully")
        
        response_json = {
            'status': 'success',
            'message': f'Successfully updated {len(results)} records',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error updating desk order: {str(e)}")
        response_json = {
            'status': 'error',
            'message': f'Error updating desk order: {str(e)}',
            'results': []
        }
    
    return JsonResponse(response_json, safe=False)
