import logging
from django.shortcuts import get_object_or_404
from core.models import LotNumRecord, DeskOneSchedule, DeskTwoSchedule, LetDeskSchedule
from core.forms import LotNumRecordForm
from core.websockets.serializer import serialize_for_websocket
from core.websockets.publishers import broadcast_blend_schedule_update
from django.http import JsonResponse
from django.template.loader import render_to_string
import datetime as dt
from asgiref.sync import sync_to_async
from django.db import transaction
import base64
from core.services.blend_scheduling_services import add_message_to_schedule, add_lot_to_schedule

logger = logging.getLogger(__name__)

def generate_next_lot_number():
    """
    Generates the next sequential lot number based on current date and latest lot record.
    
    The lot number format is: [MonthLetter][YearLastTwoDigits][4DigitSequence]
    Example: A23[0001-9999]
    
    Returns:
        str: The next lot number in sequence. If year changes, sequence resets to 0000.
    """
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    
    # Get the latest lot number
    latest_lot = LotNumRecord.objects.order_by('id').last().lot_number
    # Extract the year from the latest lot number
    latest_year = int(latest_lot[1:3])
    
    # Check if the year has changed
    if latest_year != today.year % 100:
        # If the year has changed, reset the last four digits to '0000'
        four_digit_number = '0000'
    else:
        # If the year has not changed, increment the last four digits as before
        four_digit_number = str(int(str(latest_lot)[-4:]) + 1).zfill(4)
    
    next_lot_number = monthletter_and_year + four_digit_number

    return next_lot_number

def update_lot_num_record(request, lot_num_id):
    """
    Updates an existing lot number record with new data from POST request.
    
    Args:
        request: HTTP request object containing form data
        lot_num_id: ID of the lot number record to update
        
    Returns:
        HttpResponseRedirect to lot number records page after update
        
    Raises:
        Http404: If lot number record with given ID does not exist
    """
    logger.info(f"🔍 update_lot_num_record called for lot_num_id: {lot_num_id}")
    
    if request.method == "POST":
        try:
            lot_num_record = get_object_or_404(LotNumRecord, id=lot_num_id)
            original_date_created = lot_num_record.date_created
            edit_lot_form = LotNumRecordForm(request.POST or None, instance=lot_num_record, prefix='editLotNumModal')
            
            if edit_lot_form.is_valid():
                logger.info(f"🔍 Form is valid, about to save lot record {lot_num_id}")
                updated_record = edit_lot_form.save(commit=False)
                updated_record.date_created = original_date_created
                updated_record.save()
                logger.info(f"🔍 Lot record {lot_num_id} saved successfully")
                
                try:
                    schedule_models_to_query = [
                        (DeskOneSchedule, 'Desk_1'),
                        (DeskTwoSchedule, 'Desk_2'), 
                        (LetDeskSchedule, 'LET_Desk'),
                    ]

                    message_count = 0
                    for model_class, area_name in schedule_models_to_query:
                        logger.info(f"🔍 Querying {model_class.__name__} for lot: {updated_record.lot_number}")
                        schedule_items = model_class.objects.filter(lot=updated_record.lot_number)
                        logger.info(f"🔍 Found {schedule_items.count()} items in {model_class.__name__}")
                        
                        for schedule_item in schedule_items:
                            logger.info(f"🔍 Processing schedule item {schedule_item.pk} in {area_name}")
                            data_for_update = {
                                'blend_id': schedule_item.pk,
                                'lot_id': updated_record.pk,
                                'lot_number': updated_record.lot_number,
                                'item_code': schedule_item.item_code,
                                'item_description': schedule_item.item_description,
                                'quantity': updated_record.lot_quantity,
                                'line': updated_record.line,
                                'start_time': updated_record.start_time.isoformat() if updated_record.start_time else None,
                                'stop_time': updated_record.stop_time.isoformat() if updated_record.stop_time else None,
                                'run_date': updated_record.run_date.strftime('%Y-%m-%d') if updated_record.run_date else None,
                                'blend_area': schedule_item.blend_area,
                                'lot_num_record_id': updated_record.pk,
                                'has_been_printed': bool(updated_record.last_blend_sheet_print_event),
                                'last_print_event_str': updated_record.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y') if updated_record.last_blend_sheet_print_event else '<em>Not Printed</em>',
                                'print_history_json': getattr(updated_record, 'blend_sheet_print_history_json_data', '[]'),
                                'was_edited_after_last_print': getattr(updated_record, 'was_edited_after_last_print', False),
                                'is_urgent': getattr(updated_record, 'is_urgent', False),
                            }
                            
                            # Apply financial-grade serialization
                            serialized_data_for_update = serialize_for_websocket(data_for_update)
                            
                            logger.info(f"🔍 Sending lot_updated message for blend_id {schedule_item.pk}")
                            broadcast_blend_schedule_update('lot_updated', serialized_data_for_update, areas=[schedule_item.blend_area])
                            message_count += 1
                            
                            logger.info(f"🔍 Sending blend_status_changed message for blend_id {schedule_item.pk}")
                            broadcast_blend_schedule_update('blend_status_changed', serialized_data_for_update, areas=[schedule_item.blend_area])
                            message_count += 1

                    if updated_record.line in ['Hx', 'Dm', 'Totes']:
                        logger.info(f"🔍 Processing non-desk schedule for line: {updated_record.line}")
                        non_desk_data = {
                            'blend_id': updated_record.pk,
                            'lot_id': updated_record.pk,
                            'lot_number': updated_record.lot_number,
                            'item_code': updated_record.item_code,
                            'item_description': updated_record.item_description,
                            'quantity': updated_record.lot_quantity,  # Will be serialized by serialize_for_websocket
                            'line': updated_record.line,
                            'start_time': updated_record.start_time.isoformat() if updated_record.start_time else None,
                            'stop_time': updated_record.stop_time.isoformat() if updated_record.stop_time else None,
                            'run_date': updated_record.run_date.strftime('%Y-%m-%d') if updated_record.run_date else None,
                            'blend_area': updated_record.line,
                            'lot_num_record_id': updated_record.pk,
                            'has_been_printed': bool(updated_record.last_blend_sheet_print_event),
                            'last_print_event_str': updated_record.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y') if updated_record.last_blend_sheet_print_event else '<em>Not Printed</em>',
                            'print_history_json': getattr(updated_record, 'blend_sheet_print_history_json_data', '[]'),
                            'was_edited_after_last_print': getattr(updated_record, 'was_edited_after_last_print', False),
                            'is_urgent': getattr(updated_record, 'is_urgent', False),
                        }
                        
                        # Apply financial-grade serialization
                        serialized_non_desk_data = serialize_for_websocket(non_desk_data)
                        
                        logger.info(f"🔍 Sending non-desk lot_updated message for lot_id {updated_record.pk}")
                        broadcast_blend_schedule_update('lot_updated', serialized_non_desk_data, areas=[updated_record.line])
                        message_count += 1
                        
                        logger.info(f"🔍 Sending non-desk blend_status_changed message for lot_id {updated_record.pk}")
                        broadcast_blend_schedule_update('blend_status_changed', serialized_non_desk_data, areas=[updated_record.line])
                        message_count += 1
                    
                    logger.info(f"🔍 Total WebSocket messages sent: {message_count}")
                    
                except Exception as ws_error:
                    logger.error(f"❌ WebSocket error in update_lot_num_record: {ws_error}", exc_info=True)

                return JsonResponse({'success': f'successfully updated lot number {lot_num_id}'})
            else:
                logger.warning(f"🔍 Form validation failed for lot_num_id {lot_num_id}: {edit_lot_form.errors}")
                return JsonResponse({'error': 'Form validation failed', 'errors': edit_lot_form.errors}, status=400)
        except Exception as e:
            logger.error(f"❌ Exception in update_lot_num_record: {e}", exc_info=True)
            return JsonResponse({'Exception thrown': str(e)})
    else:
        logger.warning(f"🔍 Non-POST request to update_lot_num_record: {request.method}")
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

def _lot_num_record_addition(request):
    """
    Creates a new lot number record and optionally duplicates it.
    
    Handles POST requests to create a new lot number record with the next sequential 
    lot number. Can create multiple duplicate records with incremented lot numbers.
    The lot is also added to the production schedule based on desk assignment.
    
    Args:
        request: HTTP request object containing form data
        
    Returns:
        None - Redirects back to referring page after saving
        
    Form Fields:
        - item_code: Product code
        - item_description: Product description 
        - lot_quantity: Quantity for the lot
        - line: Production line
        - desk: Production desk assignment
        - run_date: Scheduled run date
        - duplicates: Number of duplicate records to create (optional)
    """
    next_lot_number = generate_next_lot_number()
    duplicates_param = request.GET.get('duplicates', 0)
    try:
        duplicates_count = int(duplicates_param)
    except (TypeError, ValueError):
        duplicates_count = 0
    error = ''

    add_lot_form = LotNumRecordForm(request.POST or None, prefix='addLotNumModal')

    if 'addNewLotNumRecord' not in request.POST:
        return {
            'success': False,
            'error': 'Missing addNewLotNumRecord flag in submission.',
            'duplicates': duplicates_param,
            'form': add_lot_form,
            'errors': {'__all__': ['The add lot submission flag was not provided.']},
        }

    if not add_lot_form.is_valid():
        return {
            'success': False,
            'error': 'Form validation failed.',
            'duplicates': duplicates_param,
            'form': add_lot_form,
            'errors': add_lot_form.errors,
        }

    try:
        new_lot_submission = add_lot_form.save(commit=False)
        new_lot_submission.date_created = dt.datetime.now()
        new_lot_submission.lot_number = next_lot_number
        new_lot_submission.save()
        this_lot_prodline = add_lot_form.cleaned_data['line']
        this_lot_desk = add_lot_form.cleaned_data['desk']
        if new_lot_submission.item_code == '100501K':
            add_message_to_schedule(this_lot_desk, "Turn on boiler 24 hours prior to TCW3")
        add_lot_to_schedule(this_lot_desk, add_lot_form, new_lot_submission)

        for count in range(duplicates_count):
            last_four_chars = next_lot_number[-4:]
            next_suffix = int(last_four_chars) + 1
            next_lot_number = next_lot_number[:-4] + str(next_suffix).zfill(4)
            next_duplicate_lot_num_record = LotNumRecord(
                item_code=add_lot_form.cleaned_data['item_code'],
                item_description=add_lot_form.cleaned_data['item_description'],
                lot_number=next_lot_number,
                lot_quantity=add_lot_form.cleaned_data['lot_quantity'],
                date_created=dt.datetime.now(),
                line=add_lot_form.cleaned_data['line'],
                desk=this_lot_desk,
                run_date=add_lot_form.cleaned_data['run_date'],
            )
            next_duplicate_lot_num_record.save()
            add_lot_form.cleaned_data['lot_number'] = next_lot_number
            add_lot_to_schedule(this_lot_desk, add_lot_form, next_duplicate_lot_num_record)

    except Exception as e:
        error = str(e)
        add_lot_form.add_error(None, error)
        return {
            'success': False,
            'error': error,
            'duplicates': duplicates_param,
            'form': add_lot_form,
            'errors': add_lot_form.errors,
        }

    return {
        'success': True,
        'error': error,
        'duplicates': duplicates_param,
        'form': add_lot_form,
    }

async def add_lot_num_record(request):
    try:
        result = await sync_to_async(_lot_num_record_addition)(request)
        if result.get('success'):
            return JsonResponse({'status': 'success', 'data': result})
        return JsonResponse({'status': 'error', 'data': result}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def process_lot_num_form_submission(request):
    """
    Synchronous wrapper around the lot number creation workflow.
    Used by traditional Django views to surface validation errors.
    """
    return _lot_num_record_addition(request)

def delete_lot_num_records(request, records_to_delete):
    """
    Deletes specified lot number records and their associated schedule entries.
    
    Args:
        request: HTTP request object
        records_to_delete: Base64 encoded string containing list of record IDs to delete
        
    Returns:
        Redirect to lot number records display page
        
    Notes:
        - Decodes base64 records_to_delete parameter into list of record IDs
        - For each record:
            - Deletes the LotNumRecord
            - Attempts to delete matching DeskOneSchedule entry
            - Attempts to delete matching DeskTwoSchedule entry
        - Continues processing remaining records if deletion errors occur
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    try:
        items_to_delete_bytestr = base64.b64decode(records_to_delete)
        items_to_delete_str = items_to_delete_bytestr.decode()
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid delete payload'}, status=400)

    items_to_delete_list = [
        item.strip()
        for item in items_to_delete_str.replace('[', '').replace(']', '').replace('"', '').split(",")
        if item.strip()
    ]

    deleted_ids = []
    not_found_ids = []
    deletion_errors = []

    for item_pk_str in items_to_delete_list:
        try:
            item_pk = int(item_pk_str)
        except ValueError:
            deletion_errors.append({'id': item_pk_str, 'error': 'invalid-id'})
            continue

        lot_number_for_schedules = None
        lot_line_for_hx_dm_totes = None

        try:
            with transaction.atomic():
                selected_lot = LotNumRecord.objects.get(pk=item_pk)
                lot_number_for_schedules = selected_lot.lot_number
                lot_line_for_hx_dm_totes = selected_lot.line

                selected_lot.delete()
                deleted_ids.append(item_pk)

                if lot_line_for_hx_dm_totes in ['Hx', 'Dm', 'Totes']:
                    broadcast_blend_schedule_update(
                        'blend_deleted',
                        {
                            'blend_id': item_pk,
                            'blend_area': lot_line_for_hx_dm_totes,
                            'lot_num_record_id': item_pk,
                            'lot_num_record_deleted': True,
                            'lot_number': lot_number_for_schedules,
                        },
                        areas=[lot_line_for_hx_dm_totes]
                    )
        except LotNumRecord.DoesNotExist:
            not_found_ids.append(item_pk)
            continue
        except Exception as e_lot_del:
            deletion_errors.append({'id': item_pk, 'error': str(e_lot_del)})
            continue

        if not lot_number_for_schedules:
            continue

        schedule_models_to_check = {
            'Desk_1': DeskOneSchedule,
            'Desk_2': DeskTwoSchedule,
            'LET_Desk': LetDeskSchedule
        }

        for area_name, model_class in schedule_models_to_check.items():
            try:
                schedule_items_to_delete = model_class.objects.filter(lot__iexact=lot_number_for_schedules)
                for schedule_item in schedule_items_to_delete:
                    try:
                        with transaction.atomic():
                            blend_id_for_ws = schedule_item.pk
                            schedule_item.delete()

                            broadcast_blend_schedule_update(
                                'blend_deleted',
                                {
                                    'blend_id': blend_id_for_ws,
                                    'blend_area': area_name,
                                    'lot_num_record_id': item_pk,
                                    'lot_num_record_deleted': True,
                                    'lot_number': lot_number_for_schedules,
                                },
                                areas=[area_name]
                            )
                    except Exception as e_schedule_item_del:
                        deletion_errors.append({'id': blend_id_for_ws, 'error': str(e_schedule_item_del)})
            except Exception as e_model_processing:
                deletion_errors.append({'id': lot_number_for_schedules, 'error': str(e_model_processing)})

    has_errors = bool(deletion_errors)
    has_missing = bool(not_found_ids)

    response_payload = {
        'status': 'success' if not has_errors and not has_missing else 'partial-success',
        'deleted_ids': deleted_ids,
        'not_found_ids': not_found_ids,
        'errors': deletion_errors,
    }

    if not deleted_ids and (has_errors or has_missing):
        response_payload['status'] = 'error'
        return JsonResponse(response_payload, status=400)

    status_code = 200 if not has_errors and not has_missing else 207
    return JsonResponse(response_payload, status=status_code)

def get_rendered_lot_row(request, lot_id):
    """
    Renders a single lot number record row as HTML for WebSocket-driven updates.
    
    Fetches a lot record by ID, enriches it with schedule information and encoded
    item code, then renders the lotnumrecordrow.html template. This allows WebSocket
    handlers to request server-rendered HTML for dynamic row insertion.
    
    Args:
        request: HTTP request object
        lot_id: Primary key of the LotNumRecord to render
        
    Returns:
        JsonResponse containing:
            - html: Rendered HTML string of the lot record row
            - lot_number: The lot number for reference
            - status: 'success' or 'error'
            
    Notes:
        Reuses the same logic as display_lot_num_records to ensure consistency
        with synchronous page loads. Determines schedule assignment by checking
        DeskOneSchedule, DeskTwoSchedule, and LetDeskSchedule.
    """
    try:
        lot_record = LotNumRecord.objects.filter(pk=lot_id).first()
        if not lot_record:
            return JsonResponse({
                'status': 'error',
                'message': f'Lot record {lot_id} not found'
            }, status=404)
        # Create a dictionary representation of the lot record
        lot_record_data = {
            'id': lot_record.id,
            'item_code': lot_record.item_code,
            'item_description': lot_record.item_description,
            'lot_number': lot_record.lot_number,
            'lot_quantity': lot_record.lot_quantity,
            'date_created': lot_record.date_created,
            'line': lot_record.line,
            'desk': lot_record.desk,
            'run_date': lot_record.run_date,
        }
        
        item_code_bytes = lot_record.item_code.encode('UTF-8')
        encoded_item_code_bytes = base64.b64encode(item_code_bytes)
        lot_record_data['encoded_item_code'] = encoded_item_code_bytes.decode('UTF-8')
        
        if DeskOneSchedule.objects.filter(lot__iexact=lot_record.lot_number).exists():
            lot_record_data['schedule_value'] = 'Desk_1'
            lot_record_data['schedule_id'] = DeskOneSchedule.objects.filter(lot__iexact=lot_record.lot_number).first().id
        elif DeskTwoSchedule.objects.filter(lot__iexact=lot_record.lot_number).exists():
            lot_record_data['schedule_value'] = 'Desk_2'
            lot_record_data['schedule_id'] = DeskTwoSchedule.objects.filter(lot__iexact=lot_record.lot_number).first().id
        elif LetDeskSchedule.objects.filter(lot__iexact=lot_record.lot_number).exists():
            lot_record_data['schedule_value'] = 'LET_Desk'
            lot_record_data['schedule_id'] = LetDeskSchedule.objects.filter(lot__iexact=lot_record.lot_number).first().id
        elif lot_record.line != 'Prod':
            lot_record_data['schedule_value'] = lot_record.line
        else:
            lot_record_data['schedule_value'] = 'Not Scheduled'
        
        rendered_html = render_to_string(
            'core/lotnumbers/lotnumrecordrow.html',
            { 'item': lot_record_data, 'user': request.user }
        )
        print(rendered_html)
        
        return JsonResponse({
            'status': 'success',
            'html': rendered_html,
            'lot_number': lot_record.lot_number,
            'lot_id': lot_id
        })
        
    except LotNumRecord.DoesNotExist:
        logger.error(f"Lot record {lot_id} not found for rendering")
        return JsonResponse({
            'status': 'error',
            'message': f'Lot record {lot_id} not found'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error rendering lot row {lot_id}: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

