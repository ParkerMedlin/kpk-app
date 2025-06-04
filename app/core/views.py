import urllib
import uuid
import math
import datetime as dt
from datetime import date
import time
import pytz
import os
import base64
import logging
import smtplib
import requests
import decimal
from bs4 import BeautifulSoup
import redis
import aiohttp
import asyncio
from asgiref.sync import async_to_sync, sync_to_async
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.contrib.auth.decorators import login_required
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core.paginator import Paginator
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Subquery, OuterRef, Q, CharField, Max, F
from channels.layers import get_channel_layer
from core.models import *
from prodverse.models import *
from core.forms import *
from prodverse.forms import *
from core import taskfunctions
from .models import *
from .zebrafy_image import ZebrafyImage
import json

logger = logging.getLogger(__name__)

def serialize_for_websocket(data):
    """
    Serialize data for WebSocket transmission with financial-grade precision handling.
    
    Converts Decimal objects to float for msgpack compatibility while maintaining
    precision standards used in professional banking systems.
    
    Args:
        data (dict): Dictionary containing data to be serialized
        
    Returns:
        dict: Serialized data with Decimal objects converted to float
    """
    if isinstance(data, dict):
        return {key: serialize_for_websocket(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_for_websocket(item) for item in data]
    elif isinstance(data, decimal.Decimal):
        return float(data) if data is not None else 0.0
    else:
        return data

advance_blends = ['602602','602037US','602037','602011','602037EUR','93700.B','94700.B','93800.B','94600.B','94400.B','602067']

def get_json_forklift_serial(request):
    """
    Retrieves and returns the serial number for a forklift as JSON response.
    
    Args:
        request: HTTP request object containing 'unit-number' GET parameter
        
    Returns:
        JsonResponse containing the forklift's serial number
        
    Raises:
        Forklift.DoesNotExist: If no forklift matches the given unit number
    """
    if request.method == "GET":
        forklift_unit_number = request.GET.get('unit-number', 0)
        forklift = Forklift.objects.get(unit_number=forklift_unit_number)
    return JsonResponse(forklift.serial_no, safe=False)

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
    latest_lot = LotNumRecord.objects.latest('date_created').lot_number
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

def display_attendance_records(request):
    """
    Displays paginated attendance records sorted by punch date and employee name.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with attendance records context
        
    Template:
        core/attendance_records.html
    """

    attendance_records = AttendanceRecord.objects.all().order_by('-punch_date', 'employee_name')

    context = {
        'attendance_records': attendance_records
    }

    return render(request, 'core/attendance_records.html', context)

def display_forklift_checklist(request):
    """
    Displays forklift checklist form for operators to complete daily inspections.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with checklist form context
        
    Template:
        core/forkliftchecklist.html
    """
    submitted = False
    forklift_queryset = Forklift.objects.all()
    if request.method == "POST":
        checklist_form = ChecklistLogForm(request.POST or None)
        if checklist_form.is_valid():
            checklist_submission = checklist_form.save(commit=False)
            current_user = request.user
            checklist_submission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklist_submission.save()
            return HttpResponseRedirect('/core/forklift-checklist?submitted=True')
        else:
            return render(request, 'core/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})
    else:
        checklist_form = ChecklistLogForm
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})

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

def display_blend_shortages(request):
    """
    Displays a page showing blend shortages and related information.
    
    Fetches blend shortages from ComponentShortage model, filtering for items that:
    - Start with 'BLEND', have procurement type 'M' 
    - Are the first instance of that blend
    - Are not on Horix production line
    
    For each blend shortage:
    - Checks if it's an advance blend (needs a lead time of 30 production hours)
    - Gets latest transaction dates
    - Gets scheduling info from desk schedules
    - Gets the bill of materials so we can list all ingredients in the tooltips
    - Checks for component shortages for all ingredients found in bill of materials
    - Finds max producible quantity if components are short (DOES NOT account for usage on other blends)
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with context containing:
        - blend_shortages_queryset: QuerySet of filtered ComponentShortage objects
        - foam_factor_is_populated: Boolean if FoamFactor table has data (to make sure decisions aren't being made on incorrect calculations)
        - add_lot_form: Form for adding lot numbers
        - latest_transactions_dict: Dict of latest transaction dates per item
        - rare_date: Date threshold for rare items (180 days ago)
        - epic_date: Date threshold for epic items (360 days ago)
    """
    blend_shortages_queryset = ComponentShortage.objects \
        .filter(component_item_description__startswith='BLEND') \
        .filter(procurement_type__iexact='M') \
        .order_by('start_time') \
        .filter(component_instance_count=1) \
        .exclude(prod_line__iexact='Hx')

    component_item_codes = blend_shortages_queryset.values_list('component_item_code', flat=True)
    blend_item_codes = list(component_item_codes.distinct())
    latest_transactions_dict = get_latest_transaction_dates(blend_item_codes)

    for blend in blend_shortages_queryset:
        if blend.component_item_code in advance_blends:
            blend.advance_blend = 'yes'
        this_blend_transaction_tuple = latest_transactions_dict.get(blend.component_item_code, ('',''))
        if this_blend_transaction_tuple[0]:
            blend.last_date = this_blend_transaction_tuple[0]
        else:
            blend.last_date = dt.datetime.today() - dt.timedelta(days=360)

    foam_factor_is_populated = FoamFactor.objects.all().exists()

    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_one_item_codes = desk_one_queryset.values_list('item_code', flat=True)

    desk_two_queryset = DeskTwoSchedule.objects.all()
    desk_two_item_codes = desk_two_queryset.values_list('item_code', flat=True)

    let_desk_queryset = LetDeskSchedule.objects.all()
    let_desk_item_codes = let_desk_queryset.values_list('item_code', flat=True)

    all_item_codes = list(set(desk_one_item_codes) | set(desk_two_item_codes) | set(let_desk_item_codes))
    lot_quantities = { lot.lot_number : lot.lot_quantity for lot in LotNumRecord.objects.filter(item_code__in=all_item_codes) }

    # Calculate total quantity for each item code from lot numbers
    item_code_totals = {}
    for item_code in all_item_codes:
        desk_one_lots = [lot.lot for lot in desk_one_queryset.filter(item_code=item_code)]
        desk_two_lots = [lot.lot for lot in desk_two_queryset.filter(item_code=item_code)]
        all_lots = desk_one_lots + desk_two_lots
        
        total = sum(lot_quantities.get(lot, 0) for lot in all_lots)
        item_code_totals[item_code] = total
    print(item_code_totals)
    bom_objects = BillOfMaterials.objects.filter(item_code__in=component_item_codes)

    component_shortage_queryset = SubComponentShortage.objects \
        .filter(component_item_code__in=component_item_codes)
    if component_shortage_queryset.exists():
        subcomponentshortage_item_code_list = list(component_shortage_queryset.distinct('component_item_code').values_list('component_item_code', flat=True))
        component_shortages_exist = True
    else:
        component_shortages_exist = False

    for blend in blend_shortages_queryset:
        if blend.component_item_code in all_item_codes:
            new_shortage = calculate_new_shortage(blend.component_item_code, item_code_totals[blend.component_item_code])
            if blend.component_item_code == '93100GAS.B':
                print(f"Processing blend {blend.component_item_code}")
                print(f"Current on-hand quantity: {blend.component_on_hand_qty}")
                print(f"Total scheduled quantity: {item_code_totals[blend.component_item_code]}")
                print(f"New shortage calculation result: {new_shortage}")
            if new_shortage:
                blend.shortage_after_blends = new_shortage['start_time']
                blend.short_quantity_after_blends = blend.total_shortage - item_code_totals[blend.component_item_code]
            blend.scheduled = True
        item_code_str_bytes = blend.component_item_code.encode('UTF-8')
        encoded_item_code_bytes = base64.b64encode(item_code_str_bytes)
        blend.encoded_component_item_code = encoded_item_code_bytes.decode('UTF-8')
        this_blend_bom = bom_objects.filter(item_code__iexact=blend.component_item_code)
        blend.ingredients_list = f'Sage OH for blend {blend.component_item_code}:\n{str(round(blend.component_on_hand_qty, 0))} gal \n\nINGREDIENTS:\n'
        for item in this_blend_bom:
            blend.ingredients_list += item.component_item_code + ': ' + item.component_item_description + '\n'
        if blend.last_txn_date and blend.last_count_date:
            if blend.last_txn_date > blend.last_count_date:
                blend.needs_count = True
        else:
            blend.needs_count = False

        this_blend_batches = []
        batch_for_desk_one = desk_one_queryset.filter(item_code__iexact=blend.component_item_code).exists()
        batch_for_desk_two = desk_two_queryset.filter(item_code__iexact=blend.component_item_code).exists()
        batch_for_LET_desk = LetDeskSchedule.objects.filter(item_code__iexact=blend.component_item_code).exists()
        
        if batch_for_desk_one:
            these_blends = desk_one_queryset.filter(item_code__iexact=blend.component_item_code)
            for batch in these_blends:
                this_blend_batches.append(("Desk_1",batch.lot,lot_quantities[batch.lot]))
            blend.batches = this_blend_batches
            blend.desk = "Desk 1"
            # print(f"Desk 1. {blend.component_item_code} \n{blend.batches}")
        
        if batch_for_desk_two:
            these_blends = desk_two_queryset.filter(item_code__iexact=blend.component_item_code)
            for batch in these_blends:
                this_blend_batches.append(("Desk_2",batch.lot,lot_quantities[batch.lot]))
            blend.batches = this_blend_batches
            blend.desk = "Desk 2"
        
        if batch_for_LET_desk:
            these_blends = LetDeskSchedule.objects.filter(item_code__iexact=blend.component_item_code)
            for batch in these_blends:
                this_blend_batches.append(("LET_Desk",batch.lot,lot_quantities[batch.lot]))
            blend.batches = this_blend_batches
            blend.desk = "LET Desk"


        desk_one_item_codes = list(desk_one_item_codes)
        desk_two_item_codes = list(desk_two_item_codes)
        if batch_for_desk_one and batch_for_desk_two:
            blend.desk = "Desk 1 & 2"

        if not batch_for_desk_one and not batch_for_desk_two:
            blend.schedule_value = "Not Scheduled"

        if batch_for_LET_desk:
            blend.schedule_value = "LET Desk"

        if component_shortages_exist:
            if blend.component_item_code in subcomponentshortage_item_code_list:
                shortage_component_item_codes = []
                for item in component_shortage_queryset.filter(component_item_code__iexact=blend.component_item_code):
                    if item.subcomponent_item_code not in shortage_component_item_codes:
                        shortage_component_item_codes.append(item.subcomponent_item_code)
                blend.shortage_flag_list = shortage_component_item_codes
                blend.max_producible_quantity = component_shortage_queryset.filter(component_item_code__iexact=blend.component_item_code).first().max_possible_blend

        else:
            component_shortage_queryset = None
            blend.shortage_flag = None
            continue
        
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()

    add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number':next_lot_number, 'date_created':today,})
    
    # Fetch the latest transaction date for each item code
    today = dt.datetime.now().date()
    rare_date = today - dt.timedelta(days=146)
    epic_date = today - dt.timedelta(days=273)

    black_tintpaste_quantity_on_hand = get_item_quantity('841BLK.B')
    white_tintpaste_quantity_on_hand = get_item_quantity('841WHT.B')

    if black_tintpaste_quantity_on_hand < 150:
        need_black_tintpaste = True
    else: 
        need_black_tintpaste = False
    if white_tintpaste_quantity_on_hand < 300:
        need_white_tintpaste = True
    else: 
        need_white_tintpaste = False

    return render(request, 'core/blendshortages.html', {
        'need_black_tintpaste' : need_black_tintpaste,
        'need_white_tintpaste' : need_white_tintpaste,
        'blend_shortages_queryset': blend_shortages_queryset,
        'foam_factor_is_populated' : foam_factor_is_populated,
        'add_lot_form' : add_lot_form,
        'latest_transactions_dict': latest_transactions_dict,
        'rare_date' : rare_date,
        'epic_date' : epic_date })



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

def get_json_lot_details(request, lot_id):
    """
    Retrieves all fields for a specific lot number by its ID and returns them as JSON.
    
    Args:
        request: The HTTP request object
        lot_id: The ID of the lot number record to retrieve
        
    Returns:
        JsonResponse containing all fields of the requested lot number
    """
    try:
        # Get the lot number record by ID
        lot_record = LotNumRecord.objects.get(id=lot_id)
        print(lot_record)
        
        # Convert the model instance to a dictionary
        lot_data = {
            'id': lot_id,
            'lot_number': lot_record.lot_number,
            'item_code': lot_record.item_code,
            'item_description': lot_record.item_description,
            'lot_quantity': float(lot_record.lot_quantity) if lot_record.lot_quantity else None,
            'date_created': lot_record.date_created.strftime('%Y-%m-%d'),
            'line': lot_record.line,
            'desk': lot_record.desk,
            'sage_entered_date': lot_record.sage_entered_date.strftime('%Y-%m-%d') if lot_record.sage_entered_date else None,
            'sage_qty_on_hand': float(lot_record.sage_qty_on_hand) if lot_record.sage_qty_on_hand else None,
            'run_date': lot_record.run_date.strftime('%Y-%m-%d') if lot_record.run_date else None,
            'run_day': lot_record.run_day
        }
        
        return JsonResponse(lot_data)
    
    except LotNumRecord.DoesNotExist:
        return JsonResponse({'error': f'Lot record with ID {lot_id} not found'}, status=404)
    
    except Exception as e:
        return JsonResponse({'error': str(e)})

def get_scheduled_item_codes():
    """
    Gets distinct item codes from both desk schedules.
    
    Returns:
        list: Combined distinct item codes from DeskOneSchedule and DeskTwoSchedule
    """
    desk_one_codes = DeskOneSchedule.objects.values_list('item_code', flat=True).distinct()
    desk_two_codes = DeskTwoSchedule.objects.values_list('item_code', flat=True).distinct()
    
    # Combine and deduplicate codes using set
    all_codes = list(set(desk_one_codes) | set(desk_two_codes))
    
    # Filter out special codes
    filtered_codes = [code for code in all_codes if code not in ['INVENTORY', '******']]
    
    return filtered_codes

def get_scheduled_lots_by_item(item_codes):
    """
    Gets all scheduled lot numbers and quantities for given item codes from both desk schedules.
    
    Args:
        item_codes (list): List of item codes to look up
        
    Returns:
        dict: Dictionary mapping item codes to lists of lot number/quantity dicts
        Example: {
            'ITEM1': [{'LOT123': 100.0}, {'LOT456': 200.0}],
            'ITEM2': [{'LOT789': 150.0}]
        }
    """

    # Get all scheduled lots from both desks for our item codes
    desk_one_lots = list(DeskOneSchedule.objects.filter(
        item_code__in=item_codes
    ).order_by('order').values_list('lot', flat=True))
    
    desk_two_lots = list(DeskTwoSchedule.objects.filter(
        item_code__in=item_codes
    ).order_by('order').values_list('lot', flat=True))
    
    # Combine and deduplicate lots from both desks
    lot_numbers = list(set(desk_one_lots + desk_two_lots))
    lot_num_records = LotNumRecord.objects.filter(lot_number__in=lot_numbers)

    result = {}

    for item_code in item_codes:
        lots_this_item_code = []
        for record in lot_num_records.filter(item_code__iexact=item_code):
            this_lot_pair = {
                'lot_number' : record.lot_number,
                'lot_quantity' : record.lot_quantity
            }
            lots_this_item_code.append(this_lot_pair)
        result[item_code] = lots_this_item_code

    return result


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
    
    # Add additional quantity to each record's component_onhand_after_run
    for record in usage_records:
        print(f'{record.component_item_code}, start_time = {record.start_time}, oh after = {record.component_onhand_after_run}')
        adjusted_onhand = record.component_onhand_after_run + additional_qty
        print(f'adjusted_onhand = {adjusted_onhand}')

        # If adjusted quantity is still negative, this is where shortage occurs
        if adjusted_onhand < 0:
            return {'start_time' : record.start_time, 'component_onhand_after_run' : record.component_onhand_after_run}

    # No shortage found
    return None

def add_lot_num_record(request):
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
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    redirect_page = request.GET.get('redirect-page', 0)
    # print(redirect_page)
    duplicates = request.GET.get('duplicates', 0)
    error = ''

    if 'addNewLotNumRecord' in request.POST:
        add_lot_form = LotNumRecordForm(request.POST, prefix='addLotNumModal', )
        if add_lot_form.is_valid():
            new_lot_submission = add_lot_form.save(commit=False)
            new_lot_submission.date_created = today
            new_lot_submission.lot_number = next_lot_number
            new_lot_submission.save()
            this_lot_prodline = add_lot_form.cleaned_data['line']
            this_lot_desk = add_lot_form.cleaned_data['desk']
            if new_lot_submission.item_code == '100501K':
                add_message_to_schedule(this_lot_desk, "Turn on boiler 24 hours prior to TCW3")
            add_lot_to_schedule(this_lot_desk, add_lot_form)

            for count in range(int(duplicates)):
                last_four_chars = next_lot_number[-4:]
                next_suffix = int(last_four_chars) + 1
                next_lot_number = next_lot_number[:-4] + str(next_suffix).zfill(4)
                # print(next_lot_number)
                next_duplicate_lot_num_record = LotNumRecord(
                    item_code = add_lot_form.cleaned_data['item_code'],
                    item_description = add_lot_form.cleaned_data['item_description'],
                    lot_number = next_lot_number,
                    lot_quantity = add_lot_form.cleaned_data['lot_quantity'],
                    date_created = add_lot_form.cleaned_data['date_created'],
                    line = add_lot_form.cleaned_data['line'],
                    desk = this_lot_desk,
                    run_date = add_lot_form.cleaned_data['run_date']
                )
                next_duplicate_lot_num_record.save()
                if not this_lot_prodline == 'Hx':
                    add_lot_form.cleaned_data['lot_number'] = next_lot_number
                    add_lot_to_schedule(this_lot_desk, add_lot_form)

            #set up the new blend sheet with quantities and date
            # this_lot_record = LotNumRecord.objects.get(lot_number=new_lot_submission.lot_number)

            # this_blend_sheet_template = BlendSheetTemplate.objects.get(item_code=new_lot_submission.item_code)

            # this_lot_blend_sheet = this_blend_sheet_template.blend_sheet_template
            # this_lot_blend_sheet['lot_number'] = new_lot_submission.lot_number
            # this_lot_blend_sheet['total_weight'] = new_lot_submission.lot_quantity * this_lot_blend_sheet['lbs_per_gallon']

            # need to set quantities and date here
            # new_blend_sheet = BlendSheet(lot_number = this_lot_record,
            #                              blend_sheet = this_lot_blend_sheet_template.blend_sheet_template
            #                              )
            # new_blend_sheet.save()

            if redirect_page == 'blend-schedule':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=all')
            elif redirect_page == 'blend-schedule-desk-1':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=Desk_1')
            elif redirect_page == 'blend-schedule-desk-2':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=Desk_2')
            elif redirect_page == 'blend-schedule-hx':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=Hx')
            elif redirect_page == 'blend-schedule-dm':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=Dm')
            elif redirect_page == 'blend-schedule-totes':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=Totes')
            elif redirect_page == 'blend-shortages':
                return HttpResponseRedirect('/core/blend-shortages?recordType=blend')
            else:
                return HttpResponseRedirect('/core/lot-num-records')
        else:
            return render(request, 'core/lotnumerrorform.html', {'add_lot_form' : add_lot_form})
    else:
        return HttpResponseRedirect('/')

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
    items_to_delete_bytestr = base64.b64decode(records_to_delete)
    items_to_delete_str = items_to_delete_bytestr.decode()
    items_to_delete_list = list(items_to_delete_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    
    channel_layer = get_channel_layer()

    for item_pk_str in items_to_delete_list:
        item_pk = None
        try:
            item_pk = int(item_pk_str)
        except ValueError:
            continue

        lot_number_for_schedules = None
        lot_line_for_hx_dm_totes = None

        try:
            with transaction.atomic():
                selected_lot = LotNumRecord.objects.get(pk=item_pk)
                lot_number_for_schedules = selected_lot.lot_number
                lot_line_for_hx_dm_totes = selected_lot.line

                selected_lot.delete()

                if lot_line_for_hx_dm_totes in ['Hx', 'Dm', 'Totes']:
                    async_to_sync(channel_layer.group_send)(
                        'blend_schedule_updates',
                        {
                            'type': 'blend_schedule_update',
                            'update_type': 'blend_deleted',
                            'data': {'blend_id': item_pk, 'blend_area': lot_line_for_hx_dm_totes}
                        }
                    )
        except LotNumRecord.DoesNotExist:
            continue
        except Exception as e_lot_del:
            continue

        if lot_number_for_schedules:
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

                                async_to_sync(channel_layer.group_send)(
                                    'blend_schedule_updates',
                                    {
                                        'type': 'blend_schedule_update',
                                        'update_type': 'blend_deleted',
                                        'data': {'blend_id': blend_id_for_ws, 'blend_area': area_name}
                                    }
                                )
                        except Exception as e_schedule_item_del:
                            pass
                except Exception as e_model_processing:
                    pass

    return redirect('display-lot-num-records')

def display_lot_num_records(request):
    """
    Displays paginated lot number records with editing capabilities.
    
    Handles displaying lot number records in a paginated table view with options to:
    - Add new lot numbers via modal form
    - Edit existing lot numbers via modal form
    - Delete lot numbers
    - View schedule assignments
    
    Returns:
        Rendered template with context containing:
        - Paginated lot number records
        - Add/edit forms
        - Modal state flags
        - Schedule information

    Template:
        core/lotnumrecords.html
    """

    # May need to revisit the logic of load-edit-modal + edit-yes-no. I think
    # the proper way to handle this would be ajax. As we stand, you have to reload
    # the entire page in order to populate the editLotNumModal with the LotNumRecord
    # instance you wanted to edit. I don't want to dive into that right now though.
    submitted = False
    load_edit_modal = False
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()

    if request.method == "GET":
        edit_yes_no = request.GET.get('edit-yes-no', 0)
        load_add_modal = request.GET.get('load-add-modal', 0)
        lot_id = request.GET.get('lot-id', 0)
        lot_number_to_edit = ""
        add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number' : next_lot_number, 'date_created' : today})
        if edit_yes_no == 'yes' and LotNumRecord.objects.filter(pk=lot_id).exists():
            load_edit_modal = True
            lot_number_to_edit = LotNumRecord.objects.get(pk=lot_id)
            edit_lot_form = LotNumRecordForm(instance=lot_number_to_edit, prefix='editLotNumModal')
        else:
            edit_lot_form = LotNumRecordForm(instance=LotNumRecord.objects.all().first(), prefix='editLotNumModal')
        if 'submitted' in request.GET:
            submitted=True

    lot_num_queryset = LotNumRecord.objects.order_by('-date_created')
    # for lot in lot_num_queryset:
    #     item_code_str_bytes = lot.item_code.encode('UTF-8')
    #     encoded_item_code_str_bytes = base64.b64encode(item_code_str_bytes)
    #     encoded_item_code = encoded_item_code_str_bytes.decode('UTF-8')
    #     lot.encoded_item_code = encoded_item_code

    lot_num_paginator = Paginator(lot_num_queryset, 100)
    page_num = request.GET.get('page')
    current_page = lot_num_paginator.get_page(page_num)
    lotnum_list = []
    for lot in current_page:
        lotnum_list.append(lot.lot_number)

    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()
    for lot in current_page:
        if desk_one_queryset.filter(lot__iexact=lot.lot_number).exists():
            lot.schedule_value = 'Desk_1'
            lot.schedule_id = desk_one_queryset.filter(lot__iexact=lot.lot_number).first().id
        elif desk_two_queryset.filter(lot__iexact=lot.lot_number).exists():
            lot.schedule_value = 'Desk_2'
            lot.schedule_id = desk_two_queryset.filter(lot__iexact=lot.lot_number).first().id
        elif LetDeskSchedule.objects.filter(lot__iexact=lot.lot_number).exists():
            lot.schedule_value = 'LET_Desk'
            lot.schedule_id = LetDeskSchedule.objects.filter(lot__iexact=lot.lot_number).first().id
        elif lot.line != 'Prod':
            lot.schedule_value = lot.line
        else:
            lot.schedule_value = 'Not Scheduled'

    context = {
        'add_lot_form' : add_lot_form,
        'edit_lot_form' : edit_lot_form,
        'edit_yes_no' : edit_yes_no,
        'submitted' : submitted,
        'next_lot_number' : next_lot_number,
        'current_page' : current_page,
        'load_edit_modal' : load_edit_modal,
        'load_add_modal' : load_add_modal,
        'lot_number_to_edit' : lot_number_to_edit,
        'lotnum_list' : lotnum_list,
        'lot_id' : lot_id
        }

    return render(request, 'core/lotnumrecords.html', context)

def get_json_latest_lot_num_record(request):
    """
    Retrieves the latest lot number record and returns it as JSON.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing the latest lot number record data
        
    Fields returned:
        id: Record ID
        lot_number: Lot number string
        item_code: Item code
        item_description: Item description
        date_created: Creation date
        desk: Desk assignment
        line: Production line
        lot_quantity: Quantity in lot
    """
    latest_lot_num_record = LotNumRecord.objects.latest('id')
    data = {
        'id': latest_lot_num_record.id,
        'lot_number': latest_lot_num_record.lot_number,
        'item_code': latest_lot_num_record.item_code,
        'item_description': latest_lot_num_record.item_description,
        'date_created': latest_lot_num_record.date_created,
        'desk': latest_lot_num_record.desk,
        'line': latest_lot_num_record.line,
        'lot_quantity': latest_lot_num_record.lot_quantity,
    }
    return JsonResponse(data)

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
                    channel_layer = get_channel_layer()
                    logger.info(f"🔍 Channel layer obtained: {channel_layer}")
                    
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
                                'quantity': updated_record.lot_quantity,  # Will be serialized by serialize_for_websocket
                                'line': schedule_item.blend_area,
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
                            async_to_sync(channel_layer.group_send)(
                                'blend_schedule_updates',
                                {
                                    'type': 'blend_schedule_update',
                                    'update_type': 'lot_updated',
                                    'data': serialized_data_for_update
                                }
                            )
                            message_count += 1
                            
                            logger.info(f"🔍 Sending blend_status_changed message for blend_id {schedule_item.pk}")
                            async_to_sync(channel_layer.group_send)(
                                'blend_schedule_updates',
                                {
                                    'type': 'blend_schedule_update', 
                                    'update_type': 'blend_status_changed',
                                    'data': serialized_data_for_update
                                }
                            )
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
                        async_to_sync(channel_layer.group_send)(
                            'blend_schedule_updates',
                            {
                                'type': 'blend_schedule_update',
                                'update_type': 'lot_updated', 
                                'data': serialized_non_desk_data
                            }
                        )
                        message_count += 1
                        
                        logger.info(f"🔍 Sending non-desk blend_status_changed message for lot_id {updated_record.pk}")
                        async_to_sync(channel_layer.group_send)(
                            'blend_schedule_updates',
                            {
                                'type': 'blend_schedule_update',
                                'update_type': 'blend_status_changed',
                                'data': serialized_non_desk_data
                            }
                        )
                        message_count += 1
                    
                    logger.info(f"🔍 Total WebSocket messages sent: {message_count}")
                    
                except Exception as ws_error:
                    logger.error(f"❌ WebSocket error in update_lot_num_record: {ws_error}", exc_info=True)
                    
                return JsonResponse({'success': f'successfully updated lot number {lot_num_id}'})
            else:
                logger.warning(f"🔍 Form validation failed for lot_num_id {lot_num_id}: {edit_lot_form.errors}")
                return JsonResponse({'error': 'Form validation failed', 'errors': edit_lot_form.errors})
        except Exception as e:
            logger.error(f"❌ Exception in update_lot_num_record: {e}", exc_info=True)
            return JsonResponse({'Exception thrown': str(e)})
    else:
        logger.warning(f"🔍 Non-POST request to update_lot_num_record: {request.method}")
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

def test_websocket_send(request):
    """Temporary test endpoint to verify WebSocket functionality"""
    try:
        channel_layer = get_channel_layer()
        logger.info(f"🔍 Test WebSocket - Channel layer: {channel_layer}")
        
        test_data = {
            'blend_id': 'test_123',
            'lot_number': 'TEST_LOT',
            'message': 'Test message from Django',
            'timestamp': timezone.now().isoformat()
        }
        
        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'test_message',
                'data': test_data
            }
        )
        
        logger.info("🔍 Test WebSocket message sent successfully")
        return JsonResponse({'status': 'Test WebSocket message sent', 'data': test_data})
        
    except Exception as e:
        logger.error(f"❌ Test WebSocket error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)       
    
def update_foam_factor(request, foam_factor_id):
    """
    Updates an existing foam factor record with new data from POST request.
    
    Args:
        request: HTTP request object containing form data
        foam_factor_id: ID of the foam factor record to update
        
    Returns:
        HttpResponseRedirect to foam factors page after update
        
    Raises:
        Http404: If foam factor record with given ID does not exist
    """
    if request.method == "POST":
        print(foam_factor_id)
        request.GET.get('edit-yes-no', 0)
        foam_factor = get_object_or_404(FoamFactor, id = foam_factor_id)
        edit_foam_factor = FoamFactorForm(request.POST or None, instance=foam_factor, prefix='editFoamFactorModal')

        if edit_foam_factor.is_valid():
            edit_foam_factor.save()

        return HttpResponseRedirect('/core/foam-factors')

def delete_foam_factor(request, foam_factor_id):
    """
    Deletes a foam factor record with the specified ID.
    
    Args:
        request: HTTP request object
        foam_factor_id: ID of the foam factor record to delete
        
    Returns:
        Redirect to foam factors display page after deletion
        
    Raises:
        FoamFactor.DoesNotExist: If foam factor with given ID does not exist
    """
    try:
        foam_factor_to_delete = FoamFactor.objects.get(pk=foam_factor_id)
        foam_factor_to_delete.delete()
    except Exception as e:
        print(str(e))

    return redirect('display-foam-factors')

def display_foam_factors(request):
    """
    Displays foam factor records with forms for adding/editing.
    
    Handles displaying all foam factor records in a paginated view, along with forms
    for adding new records and editing existing ones. Includes logic for showing
    edit/add modals based on request parameters.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with foam factor records and forms context

    Template:
        core/foamfactors.html
    """
    submitted = False
    load_edit_modal = False

    if request.method == "GET":
        edit_yes_no = request.GET.get('edit-yes-no', 0)
        load_add_modal = request.GET.get('load-add-modal', 0)
        foam_factor_id = request.GET.get('foam-factor-id', 0)
        foam_factor_to_edit = ""
        add_foam_factor_form = FoamFactorForm(prefix='addFoamFactorModal')
        if edit_yes_no == 'yes' and FoamFactor.objects.filter(pk=foam_factor_id).exists():
            load_edit_modal = True
            foam_factor_to_edit = FoamFactor.objects.get(pk=foam_factor_id)
            edit_foam_factor_form = FoamFactorForm(instance=foam_factor_to_edit, prefix='editFoamFactorModal')
        else:
            edit_foam_factor_form = FoamFactorForm(instance=FoamFactor.objects.all().first(), prefix='editFoamFactorModal')
        if 'submitted' in request.GET:
            submitted=True

    foam_factor_queryset = FoamFactor.objects.order_by('item_code')

    context = {
        'foam_factor_queryset' : foam_factor_queryset,
        'add_foam_factor_form' : add_foam_factor_form,
        'edit_foam_factor_form' : edit_foam_factor_form,
        'edit_yes_no' : edit_yes_no,
        'submitted' : submitted,
        'load_edit_modal' : load_edit_modal,
        'load_add_modal' : load_add_modal,
        'foam_factor_to_edit' : foam_factor_to_edit,
        'foam_factor_id' : foam_factor_id
        }
    
    return render(request, 'core/foamfactors.html', context)

def add_foam_factor(request):
    """
    Handles adding new foam factor records.
    
    Validates and saves new foam factor submissions, checking for duplicates.
    If duplicate item code found, returns error form for editing existing record.
    
    Args:
        request: HTTP request object containing form data
        
    Returns:
        Redirect to foam factors list on success, or error form on validation failure
        
    Template:
        core/foamfactorerrorform.html (on error)
    """

    if 'addNewFoamFactor' in request.POST:
        add_foam_factor_form = FoamFactorForm(request.POST, prefix='addFoamFactorModal')
        distinct_item_codes = FoamFactor.objects.values_list('item_code', flat=True).distinct()
        if add_foam_factor_form.is_valid() and add_foam_factor_form.cleaned_data['item_code'] not in distinct_item_codes:
            new_foam_factor = FoamFactor()
            new_foam_factor = add_foam_factor_form.save()
            return redirect('display-foam-factors')
        else:
            if add_foam_factor_form.cleaned_data['item_code'] in distinct_item_codes:
                specific_error_designation = "The item below already had a foam factor. If you'd like to edit it, you may do so below."
                foam_factor_id = FoamFactor.objects.filter(item_code__iexact=add_foam_factor_form.cleaned_data['item_code']).first().id
                foam_factor = FoamFactor.objects.get(pk=foam_factor_id)
                foam_factor_form = FoamFactorForm(instance=foam_factor, prefix='editFoamFactorModal')
                edit_or_add = 'edit'
            else:
                specific_error_designation = None
                edit_or_add = 'add'
            return render(request, 'core/foamfactorerrorform.html', {'foam_factor_form' : foam_factor_form, 
                                                                     'specific_error' : specific_error_designation,
                                                                     'foam_factor_id' : foam_factor_id,
                                                                     'edit_or_add' : edit_or_add})

def get_json_all_foam_factors(request):
    """
    Retrieves all FoamFactor objects and returns them as a JSON response.
    """
    try:
        foam_factors = FoamFactor.objects.all()
        # Serialize the queryset to a list of dictionaries
        # Ensuring that all relevant fields are included.
        
        simplified_data = [
            {
                'item_code': factor.item_code,
                'factor': factor.factor
            }
            for factor in foam_factors
        ]
            
        return JsonResponse({'foam_factors': simplified_data}, safe=False)
    except Exception as e:
        # Log the exception e
        return JsonResponse({'error': 'Failed to retrieve foam factors', 'details': str(e)}, status=500)

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


def display_all_item_locations(request):
    """
    Displays all item locations with their current quantities on hand.
    
    Retrieves ItemLocation records and joins with BillOfMaterials to get current
    quantities and units. Handles cases where multiple BOM records exist for an item
    by summing quantities.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with item locations and quantities
        
    Template:
        core/allItemLocations.html
    """
    item_type_filter = request.GET.get('item-type', None)

    item_locations = ItemLocation.objects.all().order_by('item_code')
    if item_type_filter:
        item_locations = item_locations.filter(item_type__iexact=item_type_filter)
    
    item_codes = item_locations.values_list('item_code', flat=True)

    # Create an instance of the ItemLocationForm for editing item locations
    edit_item_location_form = ItemLocationForm(prefix='editItemLocationModal')

    # Query BillOfMaterials objects once and create a dictionary mapping component item codes to lists of (qtyonhand, standard_uom) tuples
    bom_data = {}
    for bom in BillOfMaterials.objects.filter(component_item_code__in=item_codes):
        if bom.component_item_code not in bom_data:
            bom_data[bom.component_item_code] = []
        bom_data[bom.component_item_code].append((bom.qtyonhand, bom.standard_uom))

    for item in item_locations:
        bom_info_list = bom_data.get(item.item_code, [])
        if bom_info_list:
            # Here you'll need to decide how to handle multiple BillOfMaterials objects for the same component_item_code
            # For example, you might want to sum the qtyonhand and take the first standard_uom
            item.qtyonhand = sum(info[0] for info in bom_info_list)
            item.standard_uom = bom_info_list[0][1]
        else:
            print(f"No BillOfMaterials object found for component_item_code: {item.item_code}")
            continue

    return render(request, 'core/itemlocations.html', {'item_locations': item_locations, 
                                                        'edit_item_location_form' : edit_item_location_form})



def get_json_item_location_details(request, item_location_id):
    """
    Retrieves all fields for a specific item location by its ID and returns them as JSON.
    
    Args:
        request: The HTTP request object
        item_location_id: The ID of the item location record to retrieve
        
    Returns:
        JsonResponse containing all fields of the requested item location
    """
    try:
        # Get the item location record by ID
        item_location = ItemLocation.objects.get(id=item_location_id)
        
        # Convert the model instance to a dictionary
        item_location_data = {
            'id': item_location_id,
            'item_code': item_location.item_code,
            'item_description': item_location.item_description,
            'unit': item_location.unit,
            'storage_type': item_location.storage_type,
            'zone': item_location.zone,
            'bin': item_location.bin,
            'item_type': item_location.item_type
        }
        
        return JsonResponse(item_location_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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

def add_lot_to_schedule(this_lot_desk, add_lot_form):
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
    channel_layer = get_channel_layer()
    new_schedule_item = None
    
    if this_lot_desk == 'Desk_1':
        max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskOneSchedule(
            item_code=add_lot_form.cleaned_data['item_code'],
            item_description=add_lot_form.cleaned_data['item_description'],
            lot=add_lot_form.cleaned_data['lot_number'],
            blend_area=add_lot_form.cleaned_data['desk'],
            order=max_number + 1
        )
        new_schedule_item.save()
        
    elif this_lot_desk == 'Desk_2':
        max_number = DeskTwoSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskTwoSchedule(
            item_code=add_lot_form.cleaned_data['item_code'],
            item_description=add_lot_form.cleaned_data['item_description'],
            lot=add_lot_form.cleaned_data['lot_number'],
            blend_area=add_lot_form.cleaned_data['desk'],
            order=max_number + 1
        )
        new_schedule_item.save()
        
    elif this_lot_desk == 'LET_Desk':
        max_number = LetDeskSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = LetDeskSchedule(
            item_code=add_lot_form.cleaned_data['item_code'],
            item_description=add_lot_form.cleaned_data['item_description'],
            lot=add_lot_form.cleaned_data['lot_number'],
            blend_area=add_lot_form.cleaned_data['desk'],
            order=max_number + 1
        )
        new_schedule_item.save()

    if new_schedule_item:
        try:
            lot_rec = LotNumRecord.objects.get(lot_number=new_schedule_item.lot)
            lot_id = lot_rec.pk
            has_been_printed = bool(lot_rec.last_blend_sheet_print_event)
            last_print_str = lot_rec.last_blend_sheet_print_event.printed_at.strftime('%b %d, %Y') if lot_rec.last_blend_sheet_print_event else '<em>Not Printed</em>'
            is_urgent = getattr(lot_rec, 'is_urgent', False)
        except LotNumRecord.DoesNotExist:
            lot_id = None
            has_been_printed = False
            last_print_str = '<em>Not Printed</em>'
            is_urgent = False

        add_data = {
            'blend_id': new_schedule_item.pk,
            'lot_id': lot_id,
            'lot_number': new_schedule_item.lot,
            'item_code': new_schedule_item.item_code,
            'item_description': new_schedule_item.item_description,
            'blend_area': new_schedule_item.blend_area,
            'has_been_printed': has_been_printed,
            'last_print_event_str': last_print_str,
            'is_urgent': is_urgent,
        }
        
        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'new_blend_added',
                'data': add_data
            }
        )

def display_blend_run_order(request):
    """
    Displays the blend run order report showing upcoming blend runs.
    
    Queries ComponentUsage for items with descriptions starting with 'BLEND'
    and gets their earliest scheduled run time. Orders results by start time
    to show chronological blend schedule.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with upcoming blend runs context
        
    Template:
        core/reports/blendrunorder.html
    """

    upcoming_runs = ComponentUsage.objects.filter(
        component_item_description__startswith='BLEND',
        start_time=Subquery(
            ComponentUsage.objects.filter(
                component_item_code=OuterRef('component_item_code')
            ).order_by('start_time').values('start_time')[:1]
        )
    ).order_by('start_time')


    context = {
        'upcoming_runs' : upcoming_runs
    }
    return render(request, 'core/reports/blendrunorder.html', context)

def display_report_center(request):
    """
    Displays the report center page where users can generate available reports.
    The list of options is contained in the html of the page.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template for report center
        
    Template:
        core/reportcenter.html
    """

    return render(request, 'core/reportcenter.html', {})

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

def create_report(request, which_report):
    """
    Creates a report based on the specified report type and item code.
    
    Decodes base64-encoded item code from request and generates either:
    - Lot number report showing lot numbers and quantities for an item
    - Upcoming runs report showing scheduled production runs using an item
    
    Args:
        request: HTTP request object containing encoded item code
        which_report (str): Type of report to generate ('Lot-Numbers' or 'All-Upcoming-Runs')
        
    Returns:
        Rendered template for requested report type
        
    Templates:
        core/reports/lotnumsreport.html
        core/reports/upcomingrunreport.html
    """

    encoded_item_code = request.GET.get('itemCode')
    item_code_bytestr = base64.b64decode(encoded_item_code)
    item_code = item_code_bytestr.decode()
    if which_report=="Lot-Numbers":
        no_lots_found = False
        lot_num_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created', '-lot_number')
        if lot_num_queryset.exists():
            item_description = lot_num_queryset.first().item_description
        lot_num_paginator = Paginator(lot_num_queryset, 25)
        page_num = request.GET.get('page')
        current_page = lot_num_paginator.get_page(page_num)
        # lot_number_quantities = { lot.receiptno : (lot.quantityonhand, lot.transactiondate) for lot in ImItemCost.objects.filter(itemcode__iexact=item_code)}
        lot_number_quantities = get_lot_number_quantities(item_code)
        for lot in current_page:
            this_lot_number = lot_number_quantities.get(lot.lot_number,('',''))
            lot.qty_on_hand = this_lot_number[0]
            lot.date_entered = this_lot_number[1]

        blend_info = {'item_code' : item_code, 'item_description' : item_description}

        return render(request, 'core/reports/lotnumsreport.html', {'no_lots_found' : no_lots_found, 'current_page' : current_page, 'blend_info': blend_info})

    elif which_report=="All-Upcoming-Runs":
        no_runs_found = False
        report_type = ''
        this_bill = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first()
        component_prefixes = ['BLEND','BLISTER','ADAPTER','APPLICATOR','BAG','BAIL','BASE','BILGE PAD','BOTTLE',
            'CABLE TIE','CAN','CAP','CARD','CARTON','CLAM','CLIP','COLORANT',
            'CUP','DISPLAY','DIVIDER','DRUM','ENVELOPE','FILLED BOTTLE','FILLER',
            'FLAG','FUNNEL','GREASE','HANGER','HEADER','HOLDER','HOSE','INSERT',
            'JAR','LABEL','LID','PAD','PAIL','PLUG','POUCH','PUTTY STICK','RESIN',
            'SCOOT','SEAL DISC','SLEEVE','SPONGE','STRIP','SUPPORT','TOILET PAPER',
            'TOOL','TOTE','TRAY','TUB','TUBE','WINT KIT','WRENCH','REBATE',
            'RUBBERBAND']
        subcomponent_prefixes = ['CHEM','DYE','FRAGRANCE']
        starbrite_item_codes = ['080100UN','080116UN','081318UN','081816PUN','082314UN',
            '082708PUN','083416UN','083821UN','083823UN','085700UN','085716PUN','085732UN',
            '087208UN','087308UN','087516UN','089600UN','089616PUN','089632PUN']
        if any(this_bill.component_item_description.startswith(prefix) for prefix in component_prefixes) or item_code in starbrite_item_codes:
            upcoming_runs = ComponentUsage.objects.filter(component_item_code__iexact=item_code).order_by('start_time')
            report_type = 'Component'
        else:
            upcoming_runs = SubComponentUsage.objects.filter(subcomponent_item_code__iexact=item_code).order_by('start_time')
            report_type = 'SubComponent'
        # upcoming_runs = TimetableRunData.objects.filter(component_item_code__iexact=item_code).order_by('starttime')
        if upcoming_runs.exists():
            item_description = upcoming_runs.first().component_item_description
        else:
            no_runs_found = True
            item_description = ''
        item_info = {
                'item_code' : item_code, 
                'item_description' : this_bill.component_item_description, 
                'standard_uom' : this_bill.standard_uom
                }
        context = {
            'report_type' : report_type,
            'no_runs_found' : no_runs_found,
            'upcoming_runs' : upcoming_runs,
            'item_info' : item_info
        }
        return render(request, 'core/reports/upcomingrunsreport/upcomingrunsreport.html', context)

    elif which_report=="Startron-Runs":
        startron_item_codes = ['14000.B', '14308.B', '14308AMBER.B', '93100DSL.B', '93100GAS.B', '93100XBEE.B', '93100TANK.B', '93100GASBLUE.B', '93100GASAMBER.B']
        startron_runs = TimetableRunData.objects.filter(component_item_code__in=startron_item_codes)
        return render(request, 'core/reports/startronreport.html', {'startron_runs' : startron_runs})

    elif which_report=="Transaction-History":
        no_transactions_found = False
        if ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).exists():
            transactions_list = ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).order_by('-transactiondate')
            item_description = CiItem.objects.filter(itemcode=item_code).first().itemcodedesc
        else:
            no_transactions_found = True
            transactions_list = {}
            item_description = ''
        for item in transactions_list:
            item.item_description = item_description
        item_info = {'item_code' : item_code, 'item_description' : item_description}
        return render(request, 'core/reports/transactionsreport.html', {'no_transactions_found' : no_transactions_found, 'transactions_list' : transactions_list, 'item_info': item_info})
        
    elif which_report=="Count-History":
        counts_not_found = False
        if BlendCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendCountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
        elif BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
        else:
            counts_not_found = True
            count_records = {}
        
        item_info = {'item_code' : item_code,
                    'item_description' : BillOfMaterials.objects \
                        .filter(component_item_code__iexact=item_code) \
                        .first().component_item_description
                    }
        context = {'counts_not_found' : counts_not_found,
            'blend_count_records' : count_records,
            'item_info' : item_info
            }
        return render(request, 'core/reports/inventorycountsreport.html', context)

    elif which_report=="Counts-And-Transactions":
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        
        if BlendCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendCountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(count_records):
                count.count_order = str(order) + "counts"
        elif BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(count_records):
                count.count_order = str(order) + "counts"
        elif WarehouseCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = WarehouseCountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(count_records):
                count.count_order = str(order) + "counts"
        else:
            counts_not_found = True
            count_records = {}
        if ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).exists():
            transactions_list = ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).order_by('-transactiondate')
            for order, count in enumerate(transactions_list):
                count.transaction_order = str(order) + "txns"
        else:
            no_transactions_found = True
            transactions_list = {}
        counts_and_transactions = {}
        for iteration, item in enumerate(count_records):
            item.iteration = iteration
            item.ordering_date = str(item.counted_date) + 'b' + str(item.iteration)
            counts_and_transactions[item.ordering_date] = item
            item.transactioncode = 'Count'
            print(count for count in counts_and_transactions)
        for iteration, item in enumerate(transactions_list):
            item.iteration = iteration
            item.ordering_date = str(item.transactiondate) + 'a' + str(item.iteration)
            counts_and_transactions[item.ordering_date] = item
        count_and_txn_keys = list(counts_and_transactions.keys())
        count_and_txn_keys.sort()
        count_and_txn_keys.reverse()
        counts_and_transactions_list = []
        for item in count_and_txn_keys:
            counts_and_transactions_list.append(counts_and_transactions[item])

        item_info = {'item_code' : item_code,
                    'item_description' : item_description
                    }
        context = {'counts_and_transactions_list' : counts_and_transactions_list,
            'item_info' : item_info
        }
        return render(request, 'core/reports/countsandtransactionsreport.html', context)
    
    elif which_report=="Where-Used":
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        all_bills_where_used = BillOfMaterials.objects.filter(component_item_code__iexact=item_code)
        item_info = {'item_code' : item_code,
                    'item_description' : item_description
                    }
        context = {'all_bills_where_used' : all_bills_where_used,
            'item_info' : item_info
            }
        # may want to do pagination if this gets ugly
        return render(request, 'core/reports/whereusedreport.html', context)

    elif which_report=="Purchase-Orders":
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
        two_days_ago = dt.datetime.today() - dt.timedelta(days = 2)
        orders_not_found = False
        procurementtype = BillOfMaterials.objects \
            .filter(component_item_code__iexact=item_code) \
            .first().procurementtype
        if not procurementtype == 'M':
            all_purchase_orders = PoPurchaseOrderDetail.objects \
                    .filter(itemcode=item_code) \
                    .filter(requireddate__gte=two_days_ago) \
                    .order_by('-requireddate')
        else:
            orders_not_found = True
            all_purchase_orders = None
        item_info = {
                    'item_code' : item_code,
                    'item_description' : item_description,
                    'standard_uom' : standard_uom
                    }
        context = {
            'orders_not_found' : orders_not_found,
            'all_purchase_orders' : all_purchase_orders, 
            'item_info' : item_info
        }
        return render(request, 'core/reports/purchaseordersreport.html', context)

    elif which_report=="Bill-Of-Materials":
        these_bills = BillOfMaterials.objects.filter(item_code__iexact=item_code)
        for bill in these_bills:
            if bill.qtyonhand and bill.qtyperbill:
                bill.max_blend =  bill.qtyonhand / bill.qtyperbill
        item_info = {'item_code' : item_code,
                    'item_description' : these_bills.first().item_description
                    }

        return render(request, 'core/reports/billofmaterialsreport.html', {'these_bills' : these_bills, 'item_info' : item_info})

    elif which_report=="Max-Producible-Quantity":
        return render(request, 'core/reports/maxproduciblequantity.html')

    elif which_report=="Blend-What-If":
        blend_quantity = request.GET.get('itemQuantity')
        start_time = request.GET.get('startTime')
        blend_subcomponent_usage = get_relevant_blend_runs(item_code, blend_quantity, start_time)

        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
        subcomponent_item_codes_queryset = BillOfMaterials.objects \
                                        .filter(item_code__iexact=item_code) \
                                        .exclude(component_item_code__iexact='030143') \
                                        .exclude(component_item_code__startswith='/')

        # calculate the usage for each component and then 
        new_blend_run_components = []
        for bill in subcomponent_item_codes_queryset:
            subcomponent_item_code = bill.component_item_code
            subcomponent_item_description = subcomponent_item_codes_queryset.filter(component_item_code__iexact=subcomponent_item_code).first().component_item_description
            subcomponent_usage = float(subcomponent_item_codes_queryset.filter(component_item_code__iexact=subcomponent_item_code).first().qtyperbill) * float(blend_quantity)
            new_blend_run = {
                'component_item_code' : item_code,
                'component_item_description' : item_description,
                'subcomponent_item_code' : subcomponent_item_code,
                'subcomponent_item_description' : subcomponent_item_description,
                'start_time' : float(start_time),
                'prod_line' : 'N/A',
                'subcomponent_run_qty' : subcomponent_usage,
                'subcomponent_onhand_after_run' : 'N/A',
                'run_source' : 'new_blend_run'
            }
            new_blend_run_components.append(new_blend_run)

        # Combine, then sort the merged list by start_time
        blend_subcomponent_usage = blend_subcomponent_usage + new_blend_run_components
        blend_subcomponent_usage = sorted(blend_subcomponent_usage, key=lambda x: x['start_time'])

        return render(request, 'core/reports/whatifblend.html', {
                                    'blend_subcomponent_usage' : blend_subcomponent_usage,
                                    'item_code' : item_code,
                                    'item_description' : item_description,
                                    'blend_quantity' : blend_quantity,
                                    'start_time' : start_time,
                                    'new_blend_run_components' : new_blend_run_components})
    
    elif which_report=="Item-Component-What-If":
        item_quantity = request.GET.get('itemQuantity')
        start_time = request.GET.get('startTime')
        item_component_usage = get_relevant_item_runs(item_code, item_quantity, start_time)

        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
        component_item_codes_queryset = BillOfMaterials.objects \
                                        .filter(item_code__iexact=item_code) \
                                        .exclude(component_item_code__startswith='/')

        # calculate the usage for each component and then 
        new_item_run_components = []
        for bill in component_item_codes_queryset:
            component_item_code = bill.component_item_code
            component_item_description = component_item_codes_queryset.filter(component_item_code__iexact=component_item_code).first().component_item_description
            component_usage = float(component_item_codes_queryset.filter(component_item_code__iexact=component_item_code).first().qtyperbill) * float(item_quantity)
            new_item_run = {
                'item_code' : item_code,
                'item_description' : item_description,
                'component_item_code' : component_item_code,
                'component_item_description' : component_item_description,
                'start_time' : float(start_time),
                'prod_line' : 'N/A',
                'run_component_qty' : component_usage,
                'component_onhand_after_run' : 'N/A',
                'run_source' : 'new_item_run'
            }
            new_item_run_components.append(new_item_run)

        # Combine, then sort the merged list by start_time
        item_component_usage = item_component_usage + new_item_run_components
        item_component_usage = sorted(item_component_usage, key=lambda x: x['start_time'])

        return render(request, 'core/reports/whatifproductionitem.html', {
                                    'item_component_usage' : item_component_usage,
                                    'item_code' : item_code,
                                    'item_description' : item_description,
                                    'item_quantity' : item_quantity,
                                    'start_time' : start_time,
                                    'new_item_run_components' : new_item_run_components})
    
    elif which_report=="Component-Usage-For-Scheduled-Blends":
        relevant_blend_item_codes = [item.item_code for item in BillOfMaterials.objects.filter(component_item_code__iexact=item_code).exclude(component_item_code__startswith='/')]
        component_onhandquantity = ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(warehousecode__iexact='MTG').first().quantityonhand
        desk_one_results = DeskOneSchedule.objects.filter(item_code__in=relevant_blend_item_codes)
        desk_two_results = DeskTwoSchedule.objects.filter(item_code__in=relevant_blend_item_codes)
        purchase_orders = PoPurchaseOrderDetail.objects.filter(quantityreceived=0, itemcode__iexact=item_code)

        combined_results = list(desk_one_results) + list(desk_two_results)
        blend_component_changes = []
        for result in combined_results:
            lot_quantity = LotNumRecord.objects.get(lot_number__iexact=result.lot).lot_quantity
            qty_per_bill = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).filter(item_code__iexact=result.item_code).first().qtyperbill
            if ComponentShortage.objects.filter(component_item_code__iexact=result.item_code).exists():
                when_short = ComponentShortage.objects.filter(component_item_code__iexact=result.item_code).order_by('start_time').first().start_time
            else: 
                when_short = ''
            blend_component_changes.append({
                'type' : 'Blend',
                'blend_item_code': result.item_code,
                'blend_item_description': result.item_description,
                'blend_quantity': lot_quantity,
                'ingredient' : item_code,
                'ingredient_change_quantity': (-1) * lot_quantity * qty_per_bill,
                'when' : when_short
            })

        for purchase_order in purchase_orders:
            weekend_days_til_then = count_weekend_days(dt.date.today(), purchase_order.requireddate)
            blend_component_changes.append({
                'type' : 'Purchase Order',
                'ingredient' : item_code,
                'ingredient_change_quantity': purchase_order.quantityordered,
                'when' : calculate_production_hours(purchase_order.requireddate),
                'weekend_days_til_then' : weekend_days_til_then
            })
        
        blend_component_changes = sorted(blend_component_changes, key=lambda x: x['when'])

        cumulative_quantity = component_onhandquantity
        for change in blend_component_changes:
            cumulative_quantity += change['ingredient_change_quantity']
            change['onhand_after_change'] = cumulative_quantity

        return render(request, 'core/reports/blendcomponentconsumption.html', {
                                    'blend_component_changes' : blend_component_changes,
                                    'component_onhandquantity' : component_onhandquantity,
                                    'item_code' : item_code})
    
    elif which_report=="Transaction-Mismatches":
        parent_items = BillOfMaterials.objects.filter(component_item_code__iexact=item_code)
        parent_item_qtyperbills = { item.item_code : item.qtyperbill for item in parent_items }
        parent_item_codes = parent_items.values_list('item_code', flat=True)
        component_item_transaction_quantities = { transaction.entryno : transaction.transactionqty for transaction in ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).filter(transactioncode='BI') }
        print(component_item_transaction_quantities)
        parent_item_transactions = ImItemTransactionHistory.objects.filter(itemcode__in=parent_item_codes).filter(transactioncode='BR').order_by('-transactiondate')

        for transaction in parent_item_transactions:
            transaction.qtyperbill = parent_item_qtyperbills[transaction.itemcode]
            transaction.theory_component_transaction_qty = transaction.qtyperbill * transaction.transactionqty
            transaction.actual_component_transaction_qty = component_item_transaction_quantities.get(transaction.entryno,'Not Found')
            if transaction.actual_component_transaction_qty != 'Not Found':
                transaction.actual_component_transaction_qty = abs(transaction.actual_component_transaction_qty)
                transaction.discrepancy = float(transaction.actual_component_transaction_qty) - float(transaction.theory_component_transaction_qty)
                transaction.percentage = transaction.discrepancy / float(transaction.actual_component_transaction_qty) * 100
                if transaction.percentage > 5:
                    transaction.sus = True
                else:
                    transaction.sus = False

        # transaction_mismatches_query = f"""WITH ConsumedQuantity AS (
        #                 SELECT 
        #                     ith.entryno,
        #                     ith.itemcode, 
        #                     ith.transactiondate,
        #                     ith.timeupdated,
        #                     bom.qtyperbill,
        #                     ith.transactionqty,
        #                     ABS(ith.transactionqty) * (bom.qtyperbill / 0.975) AS calculated_consumed_qty
        #                 FROM 
        #                     im_itemtransactionhistory ith
        #                 JOIN 
        #                     bill_of_materials bom ON ith.itemcode = bom.item_code
        #                 WHERE 
        #                     ith.transactioncode IN ('BI', 'BR')
        #                     AND bom.component_item_code = '{str(item_code)}'
        #             ),
        #             ActualQuantity AS (
        #                 SELECT 
        #                     entryno,
        #                     itemcode, 
        #                     transactiondate,
        #                     timeupdated,
        #                     ABS(transactionqty) AS actual_transaction_qty
        #                 FROM 
        #                     im_itemtransactionhistory
        #                 WHERE 
        #                     itemcode = '{str(item_code)}'
        #                     AND transactioncode IN ('BI', 'BR')
        #             )
        #             SELECT 
        #                 cq.entryno,
        #                 cq.itemcode AS component_itemcode,
        #                 cq.transactiondate,
        #                 cq.timeupdated,
        #                 TO_CHAR(cq.qtyperbill, 'FM999999999.0000') AS qtyperbill,
        #                 TO_CHAR(cq.transactionqty, 'FM999999999.0000') AS transactionqty,
        #                 TO_CHAR(cq.calculated_consumed_qty, 'FM999999999.0000') AS calculated_consumed_qty,
        #                 TO_CHAR(aq.actual_transaction_qty, 'FM999999999.0000') AS actual_transaction_qty,
        #                 TO_CHAR((cq.calculated_consumed_qty - aq.actual_transaction_qty), 'FM999999999.0000') AS discrepancy
        #             FROM 
        #                 ConsumedQuantity cq
        #             JOIN 
        #                 ActualQuantity aq ON cq.entryno = aq.entryno
        #                 AND cq.transactiondate = aq.transactiondate
        #                 AND cq.timeupdated = aq.timeupdated
        #             WHERE 
        #                 ABS((cq.calculated_consumed_qty - aq.actual_transaction_qty) / cq.calculated_consumed_qty) > 0.05
        #             ORDER BY 
        #                 cq.transactiondate DESC, cq.timeupdated DESC;"""

        # with connection.cursor() as cursor:
        #     cursor.execute(transaction_mismatches_query)
        #     result = cursor.fetchall()

        return render(request, 'core/reports/transactionmismatches.html', {
                                    # 'transaction_mismatches' : result,
                                    'parent_item_transactions' : parent_item_transactions,
                                    'item_code' : item_code})

    else:
        return render(request, '')
    
def calculate_production_hours(requireddate):
    """Calculate total available production hours between today and required date.
    
    Args:
        requireddate (datetime.date): Target completion date
        
    Returns:
        int: Total production hours available, excluding weekends (10 hours per workday)
    """

    now = dt.date.today()
    delta = (requireddate - now)
    print(delta)
    # total_hours = 0

    # for i in range(delta + 1):
    #     total_hours += 10

    weekend_days = count_weekend_days(now, requireddate)

    return (delta.days - weekend_days) * 10

def count_weekend_days(start_date, end_date):
    """Count the number of weekend days between two dates.
    
    Args:
        start_date (datetime.date): Starting date
        end_date (datetime.date): Ending date
        
    Returns:
        int: Total number of Saturdays and Sundays between start_date and end_date
    """

    # Ensure start_date is before end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Initialize counters
    saturday_count = 0
    sunday_count = 0

    # Iterate through each day in the range
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 5:  # Saturday
            saturday_count += 1
        elif current_date.weekday() == 6:  # Sunday
            sunday_count += 1
        current_date += dt.timedelta(days=1)

    return saturday_count + sunday_count

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

def display_blend_schedule(request):
    """
    Displays the blend schedule view, managing scheduled blends across multiple production areas.
    
    Handles both GET and POST requests:
    - GET: Shows current blend schedules, filtered by area if specified
    - POST: Processes new lot number records added from a schedule page

    Cleans up completed blends, generates next lot numbers, and prepares blend schedule 
    data for each production area (Desk 1, Desk 2, Hx, Dm, Totes).

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with blend schedule data and forms
    """
    # Initialize variables
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    blend_area = request.GET.get('blend-area')

    # Clean up completed blends from all schedule tables
    if not blend_area == 'all':
        _clean_completed_blends(blend_area)
    
    # Handle POST request (adding lot number record)
    if request.method == "POST":
        add_lot_num_record(request)
        return HttpResponseRedirect('/core/lot-num-records')
    
    # Prepare forms for template
    add_lot_form = LotNumRecordForm(
        prefix='addLotNumModal', 
        initial={'lot_number': next_lot_number, 'date_created': today}
    )
    edit_lot_form = LotNumRecordForm(prefix='editLotNumModal')
    submitted = 'submitted' in request.GET
    
    # Define areas and get their respective schedule querysets
    areas_list = ['Desk_1', 'Desk_2', 'Hx', 'Dm', 'Totes','LET_Desk']
    blend_schedule_querysets = _get_blend_schedule_querysets()
    
    # Process querysets based on blend area filter
    if blend_area == 'all':
        for area in areas_list:
            blend_schedule_querysets[area] = prepare_blend_schedule_queryset(area, blend_schedule_querysets[area])
    elif blend_area:
        blend_schedule_querysets[blend_area] = prepare_blend_schedule_queryset(blend_area, blend_schedule_querysets[blend_area])
    
    # Prepare context for template
    context = {
        'desk_one_blends': blend_schedule_querysets['Desk_1'],
        'desk_two_blends': blend_schedule_querysets['Desk_2'],
        'horix_blends': blend_schedule_querysets['Hx'],
        'drum_blends': blend_schedule_querysets['Dm'],
        'tote_blends': blend_schedule_querysets['Totes'],
        'LET_desk_blends': blend_schedule_querysets['LET_Desk'],
        'blend_area': blend_area,
        'edit_lot_form': edit_lot_form,
        'add_lot_form': add_lot_form,
        'today': today,
        'submitted': submitted
    }
    
    return render(request, 'core/blendschedule.html', context)


def _clean_completed_blends(blend_area):
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
                    scheduled_blend.delete()


def _get_blend_schedule_querysets():
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

    # component_item_codes = []
    if 'Desk' in area:
        if queryset.exists():
            item_code_list = [blend.item_code for blend in queryset]
            max_blend_numbers_dict = {}
            for item_code in item_code_list:
                # component_item_codes.extend(
                #     BillOfMaterials.objects.filter(item_code__iexact=item_code).exclude(component_item_code__startswith='/')
                #     .values_list('component_item_code', flat=True)
                # )
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
            for blend in queryset:
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
                except Exception as e:
                    pass
                
                # Print before checking component shortages
                # print(f"\nChecking component shortages for item code: {blend.item_code}")
                if ComponentShortage.objects.filter(component_item_code__iexact=blend.item_code).exists():
                    # print(f"Found component shortage(s) for {blend.item_code}")
                    
                    # Get and print earliest shortage
                    earliest_shortage = ComponentShortage.objects.filter(component_item_code__iexact=blend.item_code).order_by('start_time').first()
                    # print(f"Earliest shortage time: {earliest_shortage.start_time}")
                    blend.hourshort = earliest_shortage.start_time

                    # Print area and line info for debugging advance blend logic
                    # print(f"Area: {area}, Line: {blend.line}")
                    # print(f"Is advance blend: {blend.item_code in advance_blends}")
                    
                    # if not 'LET' in area and blend.line=='Prod':
                    #     if blend.item_code in advance_blends:
                    #         blend.hourshort = max((blend.hourshort - 30), 5)
                    #         print(f"Adjusted shortage time (advance blend): {blend.hourshort}")
                    #     else:
                    #         blend.hourshort = max((blend.hourshort - 5), 1)
                    #         print(f"Adjusted shortage time (regular blend): {blend.hourshort}")

                    # Print lot list information
                    lot_list = [blend.lot for blend in queryset.filter(item_code=blend.item_code, order__lt=blend.order)]
                    # print(f"\nEarlier lots for {blend.item_code}: {lot_list}")
                    # print(f"Number of earlier lots: {len(lot_list)}")

                    if len(lot_list) == 1:
                        blend.hourshort = earliest_shortage.start_time
                        # print(f"Single lot - using earliest shortage time: {blend.hourshort}")
                    
                    # Print cumulative quantity calculation
                    blend.cumulative_qty = LotNumRecord.objects.filter(lot_number__in=lot_list).aggregate(Sum('lot_quantity'))['lot_quantity__sum'] or 0
                    # print(f"Cumulative quantity from earlier lots: {blend.cumulative_qty}")
                    
                    if blend.cumulative_qty == 0:
                        blend.hourshort = earliest_shortage.start_time
                        # print(f"No cumulative quantity - using earliest shortage time: {blend.hourshort}")
                    else:
                        # print(f"Calculating new shortage based on cumulative qty: {blend.cumulative_qty}")
                        new_shortage = calculate_new_shortage(blend.item_code, blend.cumulative_qty)
                        if new_shortage:
                            blend.hourshort = new_shortage['start_time']
                            # print(f"New calculated shortage time: {blend.hourshort}")
                    
                    if not 'LET' in area:
                        if blend.item_code in advance_blends and not 'LET' in area:
                            blend.hourshort = max((blend.hourshort - 30), 5)
                            # print(f"Final adjusted shortage time (advance blend): {blend.hourshort}")
                        else:
                            blend.hourshort = max((blend.hourshort - 5), 1)
                            # print(f"Final adjusted shortage time (regular blend): {blend.hourshort}")
                else:
                    print(f"No component shortages found for {blend.item_code}")
                # print("======== Finished processing blend ========\n")
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
        for blend in queryset:
            blend.lot_number = 'Not found.'
        these_item_codes = list(queryset.values_list('component_item_code', flat=True))
        two_days_ago = dt.datetime.now().date() - dt.timedelta(days=2)
        matching_lot_numbers = [[item.item_code, item.lot_number, item.run_date, item.lot_quantity] for item in LotNumRecord.objects.filter(item_code__in=these_item_codes) \
            .filter(run_date__gt=two_days_ago).filter(line__iexact=area).order_by('id')]
        for blend in queryset:
            for item_index, item in enumerate(matching_lot_numbers):
                if blend.component_item_code == item[0] and blend.run_date == item[2]:
                    blend.lot_number = item[1]
                    blend.lot_quantity = item[3]
                    matching_lot_numbers.pop(item_index)
                    break

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
    import logging
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
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
        channel_layer = get_channel_layer()
        serialized_data = serialize_for_websocket(websocket_data)
        
        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'blend_moved',
                'data': serialized_data
            }
        )
        
        logger.info(f"✅ Tank-aware blend move completed successfully")
        
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
    channel_layer = get_channel_layer()

    if request_type == 'delete':
        original_blend_id = blend.pk
        original_blend_area = blend.blend_area
        blend.delete()
        
        logger.info(f"🗑️ SENDING blend_deleted WebSocket message for blend_id: {original_blend_id}, area: {original_blend_area}")
        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'blend_deleted',
                'data': {'blend_id': original_blend_id, 'blend_area': original_blend_area}
            }
        )
        logger.info(f"✅ blend_deleted WebSocket message sent successfully")

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

        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'blend_moved',
                'data': serialized_data
            }
        )
        
        logger.info(f"✅ blend_moved WebSocket message sent successfully")

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
        return HttpResponseRedirect(f'/core/lot-num-records')
    elif request_source == 'desk-1-schedule':
        return HttpResponseRedirect(f'/core/blend-schedule/?blend-area=Desk_1')
    elif request_source == 'desk-2-schedule':
        return HttpResponseRedirect(f'/core/blend-schedule/?blend-area=Desk_2')
    elif request_source == 'LET-desk-schedule':
        return HttpResponseRedirect(f'/core/blend-schedule/?blend-area=LET_Desk')
    

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
    import logging
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    logger = logging.getLogger(__name__)
    
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
            channel_layer = get_channel_layer()
            
            # Prepare WebSocket data for the new schedule note
            websocket_data = {
                'new_blend_id': new_schedule_item.pk,
                'new_blend_area': desk,
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
            
            async_to_sync(channel_layer.group_send)(
                'blend_schedule_updates',
                {
                    'type': 'blend_schedule_update',
                    'update_type': 'new_blend_added',
                    'data': serialize_for_websocket(websocket_data)
                }
            )
            
            logger.info(f"✅ new_blend_added WebSocket message sent successfully for schedule note")
        
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
    import logging
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    logger = logging.getLogger(__name__)
    
    try:
        encoded_lot_number = request.GET.get('encodedLotNumber', '')
        lot_number_bytestr = base64.b64decode(encoded_lot_number)
        lot_number = lot_number_bytestr.decode().replace('"', "")
        print(lot_number)

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
        channel_layer = get_channel_layer()
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
        
        async_to_sync(channel_layer.group_send)(
            'blend_schedule_updates',
            {
                'type': 'blend_schedule_update',
                'update_type': 'tank_updated',
                'data': serialize_for_websocket(websocket_data)
            }
        )
        
        logger.info(f"✅ tank_updated WebSocket message sent successfully")
        
        response_json = { 'result' : f'Success. Lot {lot_number} has been assigned to {tank}' }
    except Exception as e:
        logger.error(f"❌ Error updating tank assignment: {str(e)}")
        response_json = { 'result' : f'Error: {str(e)}' }

    return JsonResponse(response_json, safe=False)

def display_this_issue_sheet(request, prod_line, item_code):
    """Display issue sheet details for a specific production run.
    
    Retrieves and formats data for an issue sheet, including component details,
    lot numbers, and quantities based on production line and item code.
    Handles different date formats and production line types.

    Args:
        request: HTTP request object containing optional runDate parameter
        prod_line (str): Production line identifier (Hx, Dm, Totes, etc)
        item_code (str): Code identifying the item to display
        
    Returns:
        Rendered template with issue sheet context including:
            - Component item details
            - Available lot numbers and quantities
            - Production line specific data
    """
    run_date_parameter = request.GET.get('runDate')
    if run_date_parameter == "undefined":
        run_date = date.today()
    else:
        try:
            # First, try parsing the date in the format mm-dd-yyyy
            run_date = dt.datetime.strptime(run_date_parameter, '%m-%d-%Y').date()
        except Exception as e:
            # If the first format fails, try parsing the date in the format mm-dd-yy
            run_date = dt.datetime.strptime(run_date_parameter, '%m-%d-%y').date()
    this_bill = BillOfMaterials.objects \
        .filter(item_code__iexact=item_code) \
        .filter(component_item_description__startswith='BLEND') \
        .first()
    component_item_code = this_bill.component_item_code
    component_item_description = this_bill.component_item_description

    # lot_numbers_dict = get_matching_lot_numbers(prod_line, component_item_code, run_date_parameter)
    # context = build_issue_sheet_dict(prod_line, component_item_code, component_item_description, run_date, lot_numbers_dict)

    if prod_line == 'Hx' or prod_line == 'Dm' or prod_line == 'Totes':
        run_this_date = LotNumRecord.objects \
            .filter(item_code__iexact=component_item_code) \
            .filter(line__iexact=prod_line) \
            .filter(run_date__date=run_date).exists()
        if run_this_date:
            these_lot_numbers = LotNumRecord.objects \
                .filter(item_code__iexact=component_item_code) \
                .filter(line__iexact=prod_line) \
                .filter(run_date__date=run_date).order_by('id')
        else:
            these_lot_numbers = {}
        lot_numbers = []
        for lot_num_record in these_lot_numbers:
            if lot_num_record.item_code == component_item_code:
                lot_numbers.append((lot_num_record.lot_number, lot_num_record.lot_quantity))

    else:
        these_lot_numbers = LotNumRecord.objects \
            .filter(item_code__iexact=component_item_code) \
            .filter(sage_qty_on_hand__gt=0).order_by('id')
        lot_numbers = []
        for lot_num_record in these_lot_numbers:
            if lot_num_record.item_code == component_item_code:
                lot_numbers.append((lot_num_record.lot_number, lot_num_record.sage_qty_on_hand))

    run_dict = {
            'component_item_code' : component_item_code,
            'component_item_description' : component_item_description,
            'prod_line' : prod_line,
            'issue_date' : run_date
        }    

    if not lot_numbers:
        lot_numbers_found = False
    else:
        lot_numbers_found = True

    run_dict['lot_numbers_found'] = lot_numbers_found
    run_dict['lot_numbers'] = lot_numbers

    return render(request, 'core/singleissuesheet.html', { 'run_dict' : run_dict })

def display_issue_sheets(request, prod_line, issue_date):
    """Display issue sheets for a specific production line and date.

    Retrieves and formats component usage data for blends on the specified production line,
    along with their available lot numbers and quantities. For future dates, handles
    next business day logic.

    Args:
        request: The HTTP request object
        prod_line (str): The production line code (e.g. 'Hx', 'Dm', 'Totes')
        issue_date (str): The target date, or 'nextDay' for next business day

    Returns:
        HttpResponse: Rendered template with runs_this_line context containing component
        and lot number data for the specified criteria
    """
    all_lot_numbers_with_quantity = LotNumRecord.objects.filter(sage_qty_on_hand__gt=0).order_by('sage_entered_date')

    prod_runs_this_line = ComponentUsage.objects  \
        .filter(component_item_description__startswith='BLEND') \
        .filter(prod_line__iexact=prod_line) \
        .filter(start_time__lte=15) \
        .filter(procurement_type__iexact='M') \
        .order_by('start_time')
    
    runs_this_line = []

    if issue_date == "nextDay":
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        if tomorrow.weekday() == 4:  # If tomorrow is Friday
            next_possible_monday = tomorrow + dt.timedelta(days=2)
            issue_date = next_possible_monday.strftime("%m-%d-%y")
        else:
            next_possible_weekday = tomorrow
            issue_date = next_possible_weekday.strftime("%m-%d-%y")

    for run in prod_runs_this_line:
        if any(d.get('component_item_code', None) == run.component_item_code for d in runs_this_line):
            continue
        run_dict = {
            'component_item_code' : run.component_item_code,
            'component_item_description' : run.component_item_description,
            'prod_line' : prod_line,
            'issue_date' : issue_date
        }
        lot_numbers = []
        for lot_num_record in all_lot_numbers_with_quantity:
            if lot_num_record.item_code == run.component_item_code:
                lot_numbers.append( (lot_num_record.lot_number, lot_num_record.sage_qty_on_hand))
        
        run_dict['lot_numbers'] = lot_numbers
        runs_this_line.append(run_dict)
    
    return render(request, 'core/issuesheets.html', {'runs_this_line' : runs_this_line})

def display_batch_issue_table(request, prod_line, issue_date):
    """Display batch issue table for production runs.
    
    Retrieves and formats data for batch issue sheets, including component details,
    lot numbers, and quantities. Handles different production lines and dates.
    
    Args:
        request: HTTP request object
        prod_line (str): Production line identifier (Hx, Dm, Totes, etc) or 'all'
        issue_date (str): Target date or 'nextDay' for next business day
        
    Returns:
        HttpResponse: Rendered template with batch issue data including:
            - Component codes and descriptions
            - On-hand quantities and shortage flags
            - Production line assignments
            - Issue dates and lot numbers
    """

    all_lot_numbers_with_quantity = LotNumRecord.objects.filter(sage_qty_on_hand__gt=0).order_by('sage_entered_date')

    if prod_line == 'all':
        prod_runs_this_line = ComponentUsage.objects  \
            .filter(component_item_description__startswith='BLEND') \
            .filter(start_time__lte=12) \
            .order_by('start_time')
    else: 
        prod_runs_this_line = ComponentUsage.objects  \
            .filter(component_item_description__startswith='BLEND') \
            .filter(prod_line__iexact=prod_line) \
            .filter(start_time__lte=12) \
            .order_by('start_time')

    for run in prod_runs_this_line:
        if run.component_onhand_after_run < 0:
            run.shortage_flag = 'short'
        elif run.component_onhand_after_run < 25:
            run.shortage_flag = 'warning'
        else: 
            run.shortage_flag = 'noshortage'

    runs_this_line = [] # track which runs have been added to this line
    if issue_date == "nextDay":
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        if tomorrow.weekday() == 4:  # If tomorrow is Friday
            next_possible_monday = tomorrow + dt.timedelta(days=2)
            issue_date = next_possible_monday.strftime("%m-%d-%y")
        else:
            next_possible_weekday = tomorrow
            issue_date = next_possible_weekday.strftime("%m-%d-%y")
    
    for run in prod_runs_this_line:
        # skip duplicates
        check_string = run.component_item_code+run.prod_line 
        if any((str(d.get('component_item_code', None)+d.get('prod_line', None))) == check_string for d in runs_this_line):
            continue

        run_dict = {
            'component_item_code' : run.component_item_code,
            'component_item_description' : run.component_item_description,
            'component_on_hand_qty' : run.component_on_hand_qty,
            'prod_line' : run.prod_line,
            'issue_date' : issue_date,
            'shortage_flag' : run.shortage_flag
        }

        lot_numbers = []
        for lot_num_record in all_lot_numbers_with_quantity:
            if lot_num_record.item_code == run.component_item_code:
                lot_numbers.append( (lot_num_record.lot_number, str(lot_num_record.sage_qty_on_hand)+" gal") )
        if not run.procurement_type == 'M':
            lot_numbers.append( ("Purchased", "See QC lab.") )
        if run.procurement_type == 'M' and not lot_numbers:
            lot_numbers.append( ("Unavailable", "Check issue sheet page on tablet.") )
        run_dict['lot_numbers'] = lot_numbers
        runs_this_line.append(run_dict)

    inline_runs = { 'prod_line' : 'INLINE', 'run_list' : [run for run in runs_this_line if run['prod_line'] == 'INLINE'] }
    pd_line_runs = { 'prod_line' : 'PD LINE', 'run_list' : [run for run in runs_this_line if run['prod_line'] == 'PD LINE'] }
    jb_line_runs = { 'prod_line' : 'JB LINE', 'run_list' : [run for run in runs_this_line if run['prod_line'] == 'JB LINE'] }
    hx_line_runs = { 'prod_line' : 'FOGG', 'run_list' : [run for run in runs_this_line if run['prod_line'] == 'HORIX'] }

    prod_runs_by_line = [inline_runs, pd_line_runs, jb_line_runs]

    return render(request, 'core/batchissuetable.html', {'runs_this_line' : runs_this_line,
                                                         'prod_line' : prod_line,
                                                         'issue_date' : issue_date,
                                                         'prod_runs_by_line' : prod_runs_by_line
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
        countlist_result = generate_countlist(record_type)
        if countlist_result == 'Name already exists':
            result = { 'no action needed' : 'Count list already exists' }
        else:
            result = { 'success' : f'{countlist_result} generated' }
    except Exception as e:
        result = { 'failure' : str(e) }

    return JsonResponse(result, safe=False)

def generate_countlist(record_type):
    """Generate an automated count list for inventory tracking.
    
    Creates a new count list for either blend items or blend components based on specified
    record type. For blend items, selects items from recent component usage and shortage 
    reports. For blend components, selects chemical/dye/fragrance items excluding those 
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
        item_code_list = ComponentUsage.objects.filter(
            prod_line='INLINE',
            component_item_description__startswith='BLEND',
            start_time__lt=8
        ).values_list('component_item_code', flat=True).distinct().order_by('component_item_code')[:15]
        item_codes_list2 = ComponentShortage.objects.filter(last_txn_date__gt=F('last_count_date')) \
            .exclude(prod_line__iexact='Dm') \
            .exclude(prod_line__iexact='Hx') \
            .exclude(component_item_code='100501K') \
            .values_list('component_item_code', flat=True) \
            .distinct().order_by('start_time')[:15]
        item_codes = list(item_code_list) + list(item_codes_list2)
        # Remove duplicates from item_codes while preserving order
        item_codes = list(dict.fromkeys(item_codes))

    elif record_type == 'blendcomponent':
        # Check if a CountCollectionLink with the given name already exists
        existing_count = CountCollectionLink.objects.filter(collection_name=f'{record_type}_count_{now_str}').exists()
        if existing_count:
            return 'Name already exists'
        item_code_list = []
        # Get all item codes from DeskOneSchedule and DeskTwoSchedule
        desk_one_item_codes = DeskOneSchedule.objects.values_list('item_code', flat=True).distinct()
        desk_two_item_codes = DeskTwoSchedule.objects.values_list('item_code', flat=True).distinct()
        parent_item_codes_to_skip = list(desk_one_item_codes) + list(desk_two_item_codes)
        # Get all component item codes for the parent items
        component_item_codes_to_skip_queryset = ComponentUsage.objects.filter(
            item_code__in=parent_item_codes_to_skip
        ).values_list('component_item_code', flat=True).distinct()
        component_item_codes_to_skip = list(component_item_codes_to_skip_queryset)
        tank_chems = ['030033','050000G','050000','031018','601015','050000G','500200',
            '030066','100427','100507TANKB','100428M6','100507TANKD','100449',
            '100421G2','100560','100421G2','100501K','27200.B','100507TANKO']
        
        component_item_codes_to_skip += tank_chems

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
        
        result = {'testing' : 'testing'}
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
        collection_name = f'{record_type}_count_{now_str}',
        count_id_list = list(list_info['primary_keys']),
        collection_id = list_info['collection_id'],
        record_type = record_type
    )
    new_count_collection.save()
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'count_collection',
        {
            'type': 'collection_added',
            'id': new_count_collection.id,
            'link_order': new_count_collection.link_order,
            'collection_name': new_count_collection.collection_name,
            'collection_id': new_count_collection.collection_id,
            'record_type': record_type
        }
    )

    result = f'{record_type}_count_{now_str}'

    return result

def get_json_containers_from_count(request):
    """Get container data from a count record in JSON format.
    
    Retrieves the containers field from a specified count record and returns it as JSON.
    Handles different record types through dynamic model selection.

    Args:
        request: HTTP request containing:
            countRecordId: ID of the count record to retrieve containers from
            recordType: Type of count record (e.g. 'blend', 'component')

    Returns:
        JsonResponse containing:
            - List of containers if found
            - Error message and status if record not found or other error occurs
    """
    count_record_id = request.GET.get('countRecordId')
    record_type = request.GET.get('recordType')

    model = get_count_record_model(record_type)

    try:
        count_record = model.objects.get(id=count_record_id)
        containers = count_record.containers or []
        return JsonResponse(containers, safe=False)
    except model.DoesNotExist:
        return JsonResponse({'error': 'Count record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_json_matching_lot_numbers(request):
    """Get matching lot numbers for a production line, run date and item code.
    
    Queries the LotNumRecord model to find lot numbers matching the specified criteria.
    Returns lot numbers and their quantities on hand that match the production line,
    run date (if provided), and item code filters.

    Args:
        request: HTTP request containing:
            prodLine: Production line code
            runDate: Run date to filter by (0 indicates null run date)
            itemCode: Item code to match

    Returns:
        JsonResponse containing list of dictionaries with:
            - lot_number: The matching lot number
            - quantityOnHand: Current quantity on hand for that lot
    """
    prod_line = request.GET.get('prodLine')
    run_date = request.GET.get('runDate')
    item_code = get_unencoded_item_code(request.GET.get('itemCode'), 'itemCode')
    if run_date == 0 or run_date == '0':
        lot_numbers_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code) \
            .filter(run_date__isnull=True) \
            .filter(line__iexact=prod_line) \
            .filter(sage_qty_on_hand__gt=0) \
            .order_by('-date_created')
    else:
        lot_numbers_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).filter(run_date=run_date).filter(line__iexact=prod_line)
    result = [{'lot_number' : lot.lot_number, 'quantityOnHand' : lot.sage_qty_on_hand } for lot in lot_numbers_queryset]

    return JsonResponse(result, safe=False)

def display_upcoming_blend_counts(request):
    """Display upcoming blend counts view.
    
    Retrieves and processes data about upcoming blend runs that need to be counted,
    including:
    - Upcoming blend usage within next 30 hours
    - Latest count records and transaction history for each blend
    - Shortage status and timing for blends
    
    Excludes Hx and Dm production lines. Orders results by start time.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with context containing:
        - List of upcoming blend runs with count/transaction history
        - Shortage status and timing information
    """
    start_time = time.time()  # Start timing

    # last_counts = { count.item_code : (count.counted_date, count.counted_quantity) for count in BlendCountRecord.objects.filter(counted=True).order_by('counted_date') }
    # last_transactions = { transaction.itemcode : (transaction.transactioncode, transaction.transactiondate) for transaction in ImItemTransactionHistory.objects.all().order_by('transactiondate') }

    upcoming_run_objects = ComponentUsage.objects.filter(component_item_description__startswith="BLEND") \
                        .exclude(prod_line__iexact='Hx') \
                        .exclude(prod_line__iexact='Dm') \
                        .filter(start_time__gte=8) \
                        .filter(start_time__lte=30) \
                        .order_by('start_time')

    component_item_codes = list(upcoming_run_objects.values_list('component_item_code', flat=True).distinct())
    latest_transactions_dict = get_latest_transaction_dates(component_item_codes)
    latest_counts_dict = get_latest_count_dates(component_item_codes, 'core_blendcountrecord')

    # print(upcoming_run_objects)
    upcoming_runs = []
    for run in upcoming_run_objects:
        # print(run)
        upcoming_runs.append({
                    'item_code' : run.component_item_code,
                    'item_description' : run.component_item_description,
                    'expected_quantity' : run.component_on_hand_qty,
                    'start_time' : run.start_time,
                    'prod_line' : run.prod_line,
                    'last_count_date' : '',
                    'last_count_quantity' : '',
                    'last_transaction_code' : '',
                    'last_transaction_date' : ''
                })

    seen = set()
    upcoming_runs = [x for x in upcoming_runs if not (x['item_code'] in seen or seen.add(x['item_code']))]
    blend_shortage_codes = ComponentShortage.objects.filter(component_item_description__startswith='BLEND').values_list('component_item_code', flat=True)
    all_blend_shortages = { shortage.component_item_code : shortage.start_time for shortage in ComponentShortage.objects.filter(component_item_description__startswith='BLEND') }

    for run in upcoming_runs:
        this_count = latest_counts_dict.get(run['item_code'], '')
        if this_count:
            run['last_count_date'] = this_count[0]
            run['last_count_quantity'] = this_count[1]
        this_transaction = latest_transactions_dict.get(run['item_code'], ('',''))
        if this_transaction:
            run['last_transaction_date'] = this_transaction[0]
            run['last_transaction_code'] = this_transaction[1]
        if run['item_code'] in blend_shortage_codes:
            run['shortage'] = True
            run['shortage_hour'] = all_blend_shortages[run['item_code']]
        else: run['shortage'] = False
        if run['last_transaction_date'] and run['last_count_date']:
            if run['last_transaction_date'] < run['last_count_date'] or run['last_transaction_code'] == 'II':
                run['needs_count'] = False
            else:
                run['needs_count'] = True
    time_check = start_time - time.time()
    print("took " + str(time_check))

    return render(request, 'core/inventorycounts/upcomingblends.html', {'upcoming_runs' : upcoming_runs })

def display_container_data(request):
    """Display container data view.

    Retrieves all container records from ContainerData model and renders them in the
    container data template. Used to track and display information about the different containers
    used to hold chemicals and blends in inventory.

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with container data queryset
    """
    containers = ContainerData.objects.all()

    return render(request, 'core/containerdata.html', { 'containers' : containers })

def display_excess_blends(request):

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

    return render(request, 'core/reports/excessblends.html', {
        'excess_blends': excess_blends,
        'total_excess_inventory_value': total_excess_inventory_value
    })


def display_upcoming_component_counts(request):
    """Display upcoming component inventory counts view.
    
    Retrieves and processes data about chemical components that may need counting:
    - Gets all chemical, dye and fragrance item codes
    - Finds relevant inventory adjustments and count records
    - Calculates transaction sums and last count dates
    - Prepares data for display including encoded item codes for links
    
    Helps identify which components need counting based on:
    - Recent inventory adjustments
    - Time since last count
    - Transaction history
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with upcoming component count data
    """
    all_item_codes = list(CiItem.objects.filter(itemcodedesc__startswith=('CHEM')).values_list('itemcode', flat=True)) + \
                     list(CiItem.objects.filter(itemcodedesc__startswith=('DYE')).values_list('itemcode', flat=True)) + \
                     list(CiItem.objects.filter(itemcodedesc__startswith=('FRAGRANCE')).values_list('itemcode', flat=True))
    relevant_adjustments = [{ 'itemcode' : transaction.itemcode,
                            'transactioncode' : transaction.transactioncode,
                            'transactiondate' : transaction.transactiondate,
                            'transactionqty' : transaction.transactionqty
                             } for transaction in ImItemTransactionHistory.objects.filter(transactioncode__in=['IA','II','IZ','IP']).filter(itemcode__in=all_item_codes)]
    relevant_counts = [{ 'item_code' : count_record.item_code,
                            'item_description' : count_record.item_description,
                            'counted_date' : count_record.counted_date
                             } for count_record in BlendComponentCountRecord.objects.filter(item_code__in=all_item_codes).order_by('-counted_date')]
    
    transaction_sums = {item_code: 0 for item_code in all_item_codes}
    for transaction in relevant_adjustments:
        if transaction['transactioncode'] in ['IA', 'II', 'IZ', 'IP']:
            transaction_sums[transaction['itemcode']] += transaction['transactionqty']


    
    upcoming_components = []
    for item_code in all_item_codes:
        for transaction in relevant_adjustments:
            if transaction['itemcode'] == item_code:
                this_transaction = transaction
                break 
        for count in relevant_counts:
            if count['item_code'] == item_code:
                this_count = count
                break
        item_code_str_bytes = item_code.encode('UTF-8')
        encoded_item_code_str_bytes = base64.b64encode(item_code_str_bytes)
        encoded_item_code = encoded_item_code_str_bytes.decode('UTF-8')
        upcoming_components.append({'item_code' : item_code,
                                    'encoded_item_code' : encoded_item_code,
                                    'item_description' : this_count['item_description'],
                                    'last_adjustment_date' : this_transaction['transactiondate'],
                                    'last_adjustment_code' : this_transaction['transactioncode'],
                                    'last_transaction_qty' : this_transaction['transactionqty'],
                                    'last_count_date' : this_count['counted_date']
                                    })
    

    return render(request, 'core/inventorycounts/upcomingcomponents.html', {'upcoming_components' : upcoming_components })

def display_adjustment_statistics(request, filter_option):
    """Display adjustment statistics for items filtered by prefix.
    
    Retrieves and displays adjustment statistics for items whose descriptions start with
    the specified filter option (e.g. 'CHEM', 'DYE', etc). Encodes item codes for URL
    safety.

    Args:
        request: HTTP request object
        filter_option (str): Prefix to filter item descriptions by
        
    Returns:
        Rendered template with filtered adjustment statistics
        
    Template:
        core/adjustmentstatistics.html
    """
    adjustment_statistics = AdjustmentStatistic.objects \
        .filter(item_description__startswith=filter_option) \
        .order_by('-adj_percentage_of_run')

    for item in adjustment_statistics:
        item_code_str_bytes = item.item_code.encode('UTF-8')
        encoded_item_code_str_bytes = base64.b64encode(item_code_str_bytes)
        encoded_item_code = encoded_item_code_str_bytes.decode('UTF-8')
        item.encoded_item_code = encoded_item_code

    return render(request, 'core/adjustmentstatistics.html', {'adjustment_statistics' : adjustment_statistics})

def display_items_by_audit_group(request):
    """Display items with option to filter and organize by audit group assignments.
    
    Retrieves items from the AuditGroup model filtered by record type (blend, 
    blendcomponent, or warehouse). Enriches the data with item descriptions,
    quantities on hand, latest count dates, transaction history and upcoming usage.
    
    Args:
        request: HTTP request object containing recordType parameter
        
    Returns:
        Rendered template showing items organized by audit group with:
        - Item details and descriptions
        - Current quantities and units
        - Latest count and transaction dates 
        - Next scheduled usage
        - Forms for adding new audit groups
        
    Template:
        core/inventorycounts/itemsbyauditgroup.html
    """
    record_type = request.GET.get('recordType')
    audit_group_queryset = AuditGroup.objects.all().filter(item_type__iexact=record_type).order_by('audit_group')
    item_codes = list(audit_group_queryset.values_list('item_code', flat=True))

    # Handle form submission for changing audit group
    if request.method == 'POST':
        if 'editItemRecord' in request.POST:
            item_id = request.POST.get('id')
            try:
                audit_group_item = AuditGroup.objects.get(id=item_id)
                form = AuditGroupForm(request.POST, instance=audit_group_item)
                if form.is_valid():
                    form.save()
                    messages.success(request, f"Successfully updated audit group for {audit_group_item.item_code}")
                else:
                    messages.error(request, f"Error updating audit group: {form.errors}")
            except AuditGroup.DoesNotExist:
                messages.error(request, "Item not found")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
            
            # Redirect to the same page to prevent form resubmission
            return redirect(f'/core/items-to-count?recordType={record_type}')
    
    # Query CiItem objects once and create a dictionary mapping item codes to descriptions

    item_descriptions = {ci_item.itemcode: ci_item.itemcodedesc for ci_item in CiItem.objects.filter(itemcode__in=item_codes)}
    qty_and_units = {bill.component_item_code: f'{round(bill.qtyonhand,4)} {bill.standard_uom}' for bill in BillOfMaterials.objects.filter(component_item_code__in=item_codes)}
    if record_type == 'blend':
        all_upcoming_runs = {production_run.component_item_code: production_run.start_time for production_run in ComponentUsage.objects.order_by('start_time')}
        count_table = 'core_blendcountrecord'
    elif record_type == 'blendcomponent':
        all_upcoming_runs = {production_run.subcomponent_item_code: production_run.start_time for production_run in SubComponentUsage.objects.order_by('start_time')}
        count_table = 'core_blendcomponentcountrecord'
    elif record_type == 'warehouse':
        all_upcoming_runs = {production_run.subcomponent_item_code: production_run.start_time for production_run in SubComponentUsage.objects.order_by('start_time')}
        count_table = 'core_warehousecountrecord'

    latest_count_dates = get_latest_count_dates(item_codes, count_table)
    latest_transactions = get_latest_transaction_dates(item_codes)

    for item in audit_group_queryset:
        item.item_description = item_descriptions.get(item.item_code, '')
        item.transaction_info = latest_transactions.get(item.item_code, ('',''))
        item.next_usage = all_upcoming_runs.get(item.item_code, ('',''))
        item.qty_on_hand = qty_and_units.get(item.item_code, '')
        item.last_count = latest_count_dates.get(item.item_code, ('',''))
        item.form = AuditGroupForm(instance=item)

    # Using values_list() to get a flat list of distinct values for the 'audit_group' field
    audit_group_list = list(AuditGroup.objects.values_list('audit_group', flat=True).distinct().order_by('audit_group'))

    

    return render(request, 'core/inventorycounts/itemsbyauditgroup.html', {'audit_group_queryset' : audit_group_queryset,
                                                           'audit_group_list' : audit_group_list,
                                                           'record_type' : record_type})

def get_components_in_use_soon(request):
    """Get list of components that will be used soon in scheduled blends.
    
    Queries the blend schedules (Desk 1 and Desk 2) to find upcoming blends,
    then looks up their bill of materials to identify chemical, dye and fragrance
    components that will be needed.

    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing list of component item codes that will be used soon
        in scheduled blends
    """
    blends_in_demand = [item.item_code for item in DeskOneSchedule.objects.all()]
    blends_in_demand.append(item.item_code for item in DeskTwoSchedule.objects.all())
    boms_in_use_soon = BillOfMaterials.objects \
                                .filter(item_code__in=blends_in_demand) \
                                .filter((Q(component_item_description__startswith="CHEM") | Q(component_item_description__startswith="DYE") | Q(component_item_description__startswith="FRAGRANCE")))
    components_in_use_soon = { 'componentList' : [item.component_item_code for item in boms_in_use_soon]}

    return JsonResponse(components_in_use_soon, safe=False)

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
    redirect_page = request.GET.get('redirectPage')
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
    
def display_list_to_count_list(request):
    """Display list of items to be counted for inventory.
    
    Shows a paginated list of items that need to be counted, organized by audit group.
    Allows filtering and selection of items to add to count lists.

    Args:
        request: HTTP request object
        
    Returns:
        Rendered template showing items to count
        
    Template:
        core/inventorycounts/listtocountlist.html
    """
    return render(request, 'core/inventorycounts/listtocountlist.html', {})

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
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    'count_collection',
                    {
                        'type': 'collection_added',
                        'id': new_count_collection.id,
                        'link_order': new_count_collection.link_order,
                        'collection_name': new_count_collection.collection_name,
                        'collection_id': new_count_collection.collection_id,
                        'record_type': record_type
                    }
                )
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
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'count_collection',
                {
                    'type': 'collection_added',
                    'id': new_count_collection.id,
                    'link_order': new_count_collection.link_order,
                    'collection_name': new_count_collection.collection_name,
                    'collection_id': new_count_collection.collection_id,
                    'record_type': record_type
                }
            )
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
        record_type = request.GET.get('recordType')
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
                count_type = 'blend',
                collection_id = this_collection_id
            )
            new_count_record.save()
            print(f'adding {new_count_record.pk} to primary_keys') 
            primary_keys.append(new_count_record.pk)

        except Exception as e:
            print(str(e))
            continue

    return {'collection_id' : this_collection_id, 'primary_keys' : primary_keys}
    
def get_json_counting_unit(request):
    """
    API endpoint to retrieve counting method information for a specific item code.
    
    Returns JSON with:
    - counting_unit: The counting method used for this item
    - standard_uom: The standard unit of measure for the item
    """
    item_code = request.GET.get('itemCode')

    print(item_code)
    
    if not item_code:
        return JsonResponse({'error': 'Item code is required'}, status=400)
    
    try:
        # Get the audit group for this item
        audit_group = AuditGroup.objects.filter(item_code__iexact=item_code).first()
        
        if not audit_group:
            return JsonResponse({'error': 'No audit group found for this item'}, status=404)
        
        # Get the CI item for standard UOM
        ci_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        
        if not ci_item:
            return JsonResponse({'error': 'Item not found in CI Items'}, status=404)
        
        # Return the counting method and standard UOM
        return JsonResponse({
            'counting_unit': audit_group.counting_unit,
            'standard_uom': ci_item.standardunitofmeasure,
            'ship_weight': ci_item.shipweight,
        })
        
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def display_count_list(request):
    """Displays a list of count records for a given collection.
    
    Args:
        request: HTTP request object containing:
            recordType (str): Type of count record ('component', 'blend', or 'warehouse')
            listId (str): Primary key of the CountCollectionLink to display
            
    Returns:
        HttpResponse: Rendered template with context containing:
            location_options (list): Available location options based on record type
            todays_date (date): Current date
            label_contents (dict): Contains date for labels
            these_count_records (QuerySet): Count records for this collection
            count_list_id (str): ID of the count list being displayed
            record_type (str): Type of count records being displayed
            count_list_name (str): Name of this count collection
            
    Retrieves count records for the given collection ID and record type.
    Looks up standard UOM and location for each count record.
    Provides location options based on record type.
    Renders template with count records and supporting data.
    """
    record_type = request.GET.get('recordType')
    count_list_id = request.GET.get('listId')

    this_count_list = CountCollectionLink.objects.get(pk=count_list_id)
    count_list_name = this_count_list.collection_name
    count_ids_list = this_count_list.count_id_list
    count_ids_list = [count_id for count_id in count_ids_list if count_id]

    model = get_count_record_model(record_type)
    these_count_records = model.objects.filter(pk__in=count_ids_list)

    for count in these_count_records:
        if CiItem.objects.filter(itemcode__iexact=count.item_code).exists():
            count.standard_uom = CiItem.objects.filter(itemcode__iexact=count.item_code).first().standardunitofmeasure
            count.shipweight = CiItem.objects.filter(itemcode__iexact=count.item_code).first().shipweight
        if ItemLocation.objects.filter(item_code__iexact=count.item_code).exists():
            count.location = ItemLocation.objects.filter(item_code__iexact=count.item_code).first().zone
        if AuditGroup.objects.filter(item_code__iexact=count.item_code).exists():
            audit_group = AuditGroup.objects.filter(item_code__iexact=count.item_code).first()
            count.counting_unit = audit_group.counting_unit
        count.converted_expected_quantity = count.expected_quantity

        if hasattr(count, 'counting_unit') and hasattr(count, 'standard_uom') and count.counting_unit and count.standard_uom:
            if count.counting_unit != count.standard_uom:
                # If counting unit differs from standard UOM, we need to convert using shipweight
                if hasattr(count, 'shipweight') and count.shipweight:
                    # Convert expected quantity if it exists
                    if count.expected_quantity:
                        # For weight-based counting when standard is each-based
                        if count.standard_uom in ['GAL'] and count.counting_unit in ['LB', 'LBS']:
                            count.converted_expected_quantity = float(count.expected_quantity) * float(count.shipweight)
                        # For each-based counting when standard is weight-based
                        elif count.standard_uom in ['LB', 'LBS'] and count.counting_unit in ['GAL']:
                            if count.shipweight > 0:  # Avoid division by zero
                                count.converted_expected_quantity = float(count.expected_quantity) / float(count.shipweight)

    todays_date = dt.date.today()

    if record_type == 'blendcomponent':
        location_options = [
            'BlendingRack','DI Tank','DyeShelves','ExtraRack','Joeys Warehouse',
            'LabRack','MainMaterials','MaterialsRack','NoLocation','OldDC','Overflow',
            'ScaleAndOverflow','Shed2','Shed3','TankFarm','UnderMixTank','Warehouse'
        ]
    elif record_type == 'blend':
        location_options = [
            'NoLocation','OldDC','OutsideLot','Shed1','Shed3'
        ]

    label_contents = { 'date' : todays_date }

    return render(request, 'core/inventorycounts/countlist.html', {
                         'location_options' : location_options,
                         'todays_date' : todays_date,
                         'label_contents' : label_contents,
                         'these_count_records' : these_count_records,
                         'count_list_id' : count_list_id,
                        #  'these_counts_formset' : these_counts_formset,
                         'record_type' : record_type,
                         'count_list_name' : count_list_name
                         })

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

def display_count_collection_links(request):
    """Display collection of count links for inventory tracking.
    
    Shows all count collection links ordered by their display position. Used to render
    the count collection links page which shows available count lists.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with:
            count_collection_links: QuerySet of CountCollectionLink objects
            count_collection_exists: Boolean indicating if any links exist
            
    Template:
        core/inventorycounts/countcollectionlinks.html
    """
    count_collection_links = CountCollectionLink.objects.all().order_by('link_order')
    if not count_collection_links.exists():
        count_collection_exists = False
    else:
        count_collection_exists = True

    return render(request, 'core/inventorycounts/countcollectionlinks.html', {'count_collection_links' : count_collection_links,
                                                                              'count_collection_exists' : count_collection_exists})

def display_count_records(request):
    """Display count records for inventory tracking.
    
    Shows paginated list of count records filtered by record type. The number of 
    records per page can be customized via URL parameter.

    Args:
        request: HTTP request containing:
            recordType (str): Type of count record to display ('blend', 'blendcomponent', 'warehouse')
            records (str, optional): Number of records to show per page, defaults to 50
            page (str, optional): Page number to display

    Returns:
        Rendered template with:
            current_page: Page object containing count records
            countType: Type of count record being displayed
            
    Template:
        core/inventorycounts/countrecords.html
    """
    record_type = request.GET.get('recordType')
    number_of_records = request.GET.get('records')

    model = get_count_record_model(record_type)
    count_record_queryset = model.objects.order_by('-id')
 
    count_record_paginator = Paginator(count_record_queryset, 50)
    page_num = request.GET.get('page')
    if number_of_records:
        count_record_paginator = Paginator(count_record_queryset, number_of_records)
    else:
        count_record_paginator = Paginator(count_record_queryset, 50)

    current_page = count_record_paginator.get_page(page_num)

    return render(request, 'core/inventorycounts/countrecords.html', {'current_page' : current_page, 'countType' : record_type})

def display_count_report(request):
    """Display inventory count report.
    
    Renders a template showing count records with variance analysis and receipt details.
    Used for reviewing inventory counts and analyzing discrepancies.

    Args:
        request: HTTP request containing:
            encodedList (str): Base64 encoded list of count record IDs
            recordType (str): Type of count records ('blend', 'blendcomponent', 'warehouse')

    Returns:
        Rendered template with:
            count_records: Queryset of count records with variance analysis
            average_costs: Dict mapping item codes to costs
            count_credits: Dict mapping record IDs to users who submitted counts
            
    Template:
        core/inventorycounts/countreport.html
    """
    encoded_pk_list = request.GET.get("encodedList")
    record_type = request.GET.get("recordType")
    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    average_costs = { item.itemcode : item.lasttotalunitcost for item in CiItem.objects.all()}
    count_credits = { item.record_id : item.updated_by for item in CountRecordSubmissionLog.objects.all().order_by('-update_timestamp')}
    most_recent_august_first = dt.datetime.now().replace(month=8, day=1)
    if most_recent_august_first > dt.datetime.now():
        most_recent_august_first = most_recent_august_first.replace(year=most_recent_august_first.year - 1)
    most_recent_september_fifth = most_recent_august_first.replace(month=9, day=5)
    from_date = most_recent_august_first.strftime('%Y-%m-%d')
    to_date = most_recent_september_fifth.strftime('%Y-%m-%d')

    if record_type == "blend":
        count_records_queryset = BlendCountRecord.objects.filter(pk__in=count_ids_list)
        for count_record in count_records_queryset:
            analysis = get_variance_analysis(count_record, from_date, to_date)
            count_record.variance_as_percentage_of_BI = analysis['variance_as_percentage_of_BI']
            count_record.variance_last_year = analysis['variance_last_year']
            count_record.total_bi_qty_since_last_ii_ia = analysis['total_bi_qty_since_last_ii_ia']
            
    elif record_type == 'blendcomponent':
        count_records_queryset = BlendComponentCountRecord.objects.filter(pk__in=count_ids_list)
        for count_record in count_records_queryset:
            analysis = get_variance_analysis(count_record, from_date, to_date)
            count_record.variance_as_percentage_of_BI = analysis['variance_as_percentage_of_BI']
            count_record.variance_last_year = analysis['variance_last_year']
    elif record_type == 'warehouse':
        count_records_queryset = WarehouseCountRecord.objects.filter(pk__in=count_ids_list)
        for count_record in count_records_queryset:
            analysis = get_variance_analysis(count_record, from_date, to_date)
            count_record.variance_as_percentage_of_BI = analysis['variance_as_percentage_of_BI']
            count_record.variance_last_year = analysis['variance_last_year']

    item_codes = [item.item_code for item in count_records_queryset]
    oldest_receiptnos = {item.receiptno: (item.itemcode, item.receiptdate) for item in ImItemCost.objects.filter(itemcode__in=item_codes).filter(quantityonhand__gt=0).order_by('receiptdate')}

    # Ensure only the oldest tuple is kept for each part number in oldest_receiptnos
    filtered_oldest_receiptnos = {}
    for receiptno, (itemcode, receiptdate) in oldest_receiptnos.items():
        if itemcode not in filtered_oldest_receiptnos or receiptdate < filtered_oldest_receiptnos[itemcode][1]:
            filtered_oldest_receiptnos[itemcode] = (receiptno, receiptdate)
            # print(f'KEEPING {itemcode, (receiptno, receiptdate) }')
    oldest_receiptnos = filtered_oldest_receiptnos

    for item in count_records_queryset:
        item.receiptno = oldest_receiptnos.get(item.item_code,['Not found','Not found'])[0]
        item.receiptdate = oldest_receiptnos.get(item.item_code,['Not found','Not found'])[1]
        if item.variance:
            if abs(item.variance) > 200:
                item.suspicious = True

    total_variance_cost = 0
    for item in count_records_queryset:
        item.average_cost = average_costs[item.item_code]
        print(item.item_code)
        print(f"multiplying item variance {Decimal(0 if item.variance == None else item.variance)} * average cost {average_costs[item.item_code]}")
        item.variance_cost = average_costs[item.item_code] * Decimal(0 if item.variance == None else item.variance)
        total_variance_cost+=item.variance_cost 
        item.counted_by = count_credits.get(str(item.id), "")

    return render(request, 'core/inventorycounts/countrecordreport.html', {'count_records_queryset' : count_records_queryset, 
                                                                           'total_variance_cost' : total_variance_cost,
                                                                           'record_type' : record_type})

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
    variance_as_percentage_of_BI = (0 if count_record.variance == None else count_record.variance) / (1 if total_bi_qty_since_last_ii_ia == 0 or total_bi_qty_since_last_ii_ia == None else total_bi_qty_since_last_ii_ia)
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

def display_all_upcoming_production(request):
    """Display all upcoming production runs with optional filtering.
    
    Retrieves and displays TimetableRunData records ordered by start time. Supports 
    filtering by production line or component item code. Results are paginated with
    25 items per page.

    Args:
        request: HTTP request containing optional query parameters:
            prod-line-filter (str): Filter results by production line
            component-item-code-filter (str): Filter results by component item code
            page (int): Page number for pagination

    Returns:
        Rendered template 'core/productionblendruns.html' with context:
            current_page: Paginated queryset of production runs
            prod_line_filter: Active production line filter value
            component_item_code_filter: Active component filter value 
            queryset_empty: Boolean indicating if results exist
    """
    prod_line_filter = request.GET.get('prod-line-filter', 0)
    component_item_code_filter = request.GET.get('component-item-code-filter ', 0)
    if prod_line_filter:
        upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime').filter(prodline__iexact=prod_line_filter)
    elif component_item_code_filter:
        upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime').filter(component_item_code__iexact=component_item_code_filter)
    else:
        upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime')
    if not upcoming_runs_queryset:
        queryset_empty = True
    else:
        queryset_empty = False
    # for run in upcoming_runs_queryset:
    #     item.component_item_code
    upcoming_runs_paginator = Paginator(upcoming_runs_queryset, 25)
    page_num = request.GET.get('page')
    current_page = upcoming_runs_paginator.get_page(page_num)
    return render(request, 'core/productionblendruns.html',
                        {
                        'current_page' : current_page,
                        'prod_line_filter' : prod_line_filter,
                        'component_item_code_filter' : component_item_code_filter,
                        'queryset_empty' : queryset_empty
                        })

def display_chem_shortages(request):
    """Display chemical shortages for upcoming blend production.
    
    Analyzes chemical inventory levels against upcoming blend production requirements
    to identify potential shortages. Calculates required quantities based on bill of
    materials and displays:

    - Current on-hand quantities
    - Required quantities for upcoming blends
    - Projected shortages
    - Next expected deliveries
    - Maximum possible blend quantities

    Args:
        request: HTTP request object

    Returns:
        Rendered template 'core/chemshortages.html' with context:
            chems_used_upcoming: Queryset of chemicals needed for upcoming blends
            is_shortage: Boolean indicating if any shortages exist
            blends_upcoming_item_codes: List of blend item codes being produced
            current_page: Paginated results
    """
    is_shortage = False
    blends_used_upcoming = ComponentShortage.objects.filter(component_item_description__startswith='BLEND-')
    blends_upcoming_item_codes = list(blends_used_upcoming.values_list('component_item_code', flat=True))
    chems_used_upcoming = BillOfMaterials.objects.filter(item_code__in=blends_upcoming_item_codes).exclude(component_item_code__startswith='/C')
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)
    for chem in chems_used_upcoming:
        chem.blend_req_onewk = blends_used_upcoming.filter(component_item_code__iexact=chem.item_code).first().one_wk_short
        chem.blend_req_twowk = blends_used_upcoming.filter(component_item_code__iexact=chem.item_code).first().two_wk_short
        chem.blend_req_threewk = blends_used_upcoming.filter(component_item_code__iexact=chem.item_code).first().three_wk_short
        chem.required_qty = chem.blend_req_threewk * chem.qtyperbill
        if chem.qtyonhand >= 0 and chem.required_qty >= 0:
            chem.oh_minus_required = chem.qtyonhand - chem.required_qty
        else:
            chem.oh_minus_required = 0
        if chem.qtyonhand >= 0 and chem.required_qty >= 0:
            try: 
                chem.max_possible_blend = chem.qtyonhand / chem.qtyperbill
            except:
                chem.max_possible_blend = 0
        else:
            chem.max_possible_blend = 0
        if (PoPurchaseOrderDetail.objects.filter(itemcode__iexact=chem.component_item_code, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            chem.next_delivery = PoPurchaseOrderDetail.objects.filter(
                itemcode__iexact=chem.component_item_code,
                quantityreceived__exact=0,
                requireddate__gt=yesterday_date
                ).order_by('requireddate').first().requireddate
        else:
            chem.next_delivery = "N/A"
        if (chem.oh_minus_required < 0 and chem.component_item_code != "030143"):
            is_shortage = True
        # printing
        if chem.component_item_code == '030024':
            print('Chem ' + chem.component_item_code + ': ' + str(chem.qtyonhand) + ' on hand.')
            print(str(chem.required_qty) + ' of chem required.')
            print(str(chem.blend_req_threewk) + ' gal of blend required.')
        # if chem.item_code == '18500.B':
        #     print('Chem ' + chem.component_item_code + ': ' + str(chem.qtyonhand) + ' on hand.')
        #     print(str(chem.required_qty) + ' of chem required.')
        #     print(str(chem.blend_req_threewk) + ' gal of blend required.')
        
        
    chems_used_paginator = Paginator(chems_used_upcoming, 50)
    page_num = request.GET.get('page')
    current_page = chems_used_paginator.get_page(page_num)

    return render(request, 'core/chemshortages.html',
        {'chems_used_upcoming' : chems_used_upcoming,
         'is_shortage' : is_shortage,
         'blends_upcoming_item_codes' : blends_upcoming_item_codes,
         'blends_used_upcoming' : blends_used_upcoming,
         'current_page' : current_page
         })

def get_json_item_location(request):
    """Get item location information from database.
    
    Retrieves location, description, quantity and UOM information for an item based on
    the provided lookup parameters. Used by the location lookup page to display item details.

    Args:
        request: HTTP request containing:
            lookup-type (str): Type of lookup ('itemCode', etc)
            item (str): Encoded item code to look up
            restriction (str): Optional restriction on lookup

    Returns:
        JsonResponse containing:
            itemCode: Item code
            itemDescription: Item description 
            bin: Storage bin location
            zone: Storage zone
            qtyOnHand: Current quantity on hand
            standardUOM: Standard unit of measure
    """
    if request.method == "GET":
        lookup_type = request.GET.get('lookup-type', 0)
        lookup_value = request.GET.get('item', 0)
        item_code = get_unencoded_item_code(lookup_value, lookup_type)
        print(item_code)
        
        requested_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        qty_on_hand = round(ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(warehousecode__iexact='MTG').first().quantityonhand, 2)
        item_description = requested_item.itemcodedesc
        print(item_description)
        standard_uom = requested_item.standardunitofmeasure

        if ItemLocation.objects.filter(item_code__iexact=item_code).exists():
            requested_item = ItemLocation.objects.get(item_code=item_code)
            bin = requested_item.bin
            zone = requested_item.zone
        else:
            bin = "no location listed."
            zone = ""

        response_item = {
            "itemCode" : item_code,
            "itemDescription" : item_description,
            "bin" : bin,
            "zone" : zone,
            "qtyOnHand" : qty_on_hand,
            "standardUOM" : standard_uom
        }
    return JsonResponse(response_item, safe=False)

def display_lookup_location(request):
    """Display location lookup page.
    
    Shows a form for looking up item locations, with a dropdown of all available item codes.
    Used to find storage locations and details for inventory items.

    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with item code queryset for dropdown
        
    Template:
        core/lookuppages/lookuplocation.html
    """
    item_code_queryset = list(BillOfMaterials.objects.order_by('component_item_code').distinct('component_item_code'))

    return render(request, 'core/lookuppages/lookuplocation.html', {'item_code_queryset' : item_code_queryset})

def get_json_item_info(request):
    """Get item information from database.

    Retrieves item details from CiItem and ImItemWarehouse tables based on provided lookup parameters.
    Returns UV/freeze protection info for blends and GHS pictogram info if requested.

    Args:
        request: HTTP GET request containing:
            lookup-type (str): Type of lookup ('itemCode', etc)
            item (str): Item code or other lookup value 
            restriction (str): Optional filter for GHS blends

    Returns:
        JsonResponse containing item details:
            item_code: Item code
            item_description: Item description 
            qtyOnHand: Current quantity on hand (non-GHS items)
            standardUOM: Standard unit of measure (non-GHS items)
            uv_protection: UV protection level for blends
            shipweight: Item shipping weight (non-GHS items)
            freeze_protection: Freeze protection level for blends
    """
    if request.method == "GET":
        lookup_type = request.GET.get('lookup-type', 0)
        lookup_value = request.GET.get('item', 0)
        print(lookup_value)
        lookup_restriction = request.GET.get('restriction', 0)

        item_code = get_unencoded_item_code(lookup_value, lookup_type)
        print(item_code)
        
        if BlendProtection.objects.filter(item_code__iexact=item_code).exists():
            item_protection = BlendProtection.objects.filter(item_code__iexact=item_code).first()
            uv_protection = item_protection.uv_protection
            freeze_protection = item_protection.freeze_protection

            # Get lot numbers with quantity on hand for this item code
            lot_numbers_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code) \
                                                    .filter(sage_qty_on_hand__gt=0) \
                                                    .order_by('-date_created')
            lot_numbers = [{'lot_number': lot.lot_number, 
                        'quantity': lot.sage_qty_on_hand} 
                        for lot in lot_numbers_queryset]
        else:
            uv_protection = "Not a blend."
            freeze_protection = "Not a blend."
            lot_numbers = "None."

        if lookup_restriction == 'ghs-blends':
            requested_item = GHSPictogram.objects.filter(item_code__iexact=item_code).first()
            response_item = {
                "item_code" : requested_item.item_code,
                "item_description" : requested_item.item_description,
            }
        else:
            requested_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
            requested_im_warehouse_item = ImItemWarehouse.objects.filter(itemcode__iexact=item_code, warehousecode__exact='MTG').first()
            
            response_item = {
                "item_code" : requested_item.itemcode,
                "item_description" : requested_item.itemcodedesc,
                "qtyOnHand" : requested_im_warehouse_item.quantityonhand,
                "standardUOM" : requested_item.standardunitofmeasure,
                "uv_protection" : uv_protection,
                "shipweight" : requested_item.shipweight,
                "freeze_protection" : freeze_protection,
                "lot_numbers" : lot_numbers
            }

    return JsonResponse(response_item, safe=False)

def get_json_tank_specs(request):
    """Get storage tank specifications from database.
    
    Retrieves tank specifications including item codes, descriptions and capacities
    for all storage tanks in the system.

    Args:
        request: HTTP GET request

    Returns:
        JsonResponse containing tank data dictionary:
            tank_label_vega (str): Tank identifier as key
            item_code (str): Item code stored in tank
            item_description (str): Description of item in tank
            max_gallons (int): Maximum capacity in gallons
    """
    if request.method == "GET":
        tank_queryset = StorageTank.objects.all()
        tank_dict = {}
        for tank in tank_queryset:
            tank_dict[tank.tank_label_vega] = {
                'item_code' : tank.item_code,
                'item_description' : tank.item_description,
                'max_gallons' : tank.max_gallons
            }

        data = tank_dict

    return JsonResponse(data, safe=False)

def display_tank_levels(request):
    """Display storage tank level monitoring page.
    
    Renders the tank level monitoring page template with tank data. Uses different
    templates for MSR vs standard views based on request path.

    Args:
        request: HTTP request object

    Returns:
        Rendered template response with tank queryset data:
            tank_queryset: QuerySet of StorageTank objects
    """
    tank_queryset = StorageTank.objects.all()

    if 'msr' in request.path:
        return render(request, 'core/tanklevelsmsr.html', {'tank_queryset' : tank_queryset})
    else:
        return render(request, 'core/tanklevels.html', {'tank_queryset' : tank_queryset})

def get_tank_levels_html(request):
    """Get HTML content from tank level monitoring device.
    
    Retrieves raw HTML content from the tank level monitoring device at a specific IP address.
    The HTML contains current tank level readings and status information.

    Args:
        request: HTTP GET request

    Returns:
        JsonResponse containing:
            html_string (str): Raw HTML content from monitoring device
    """
    if request.method == "GET":
        fp = urllib.request.urlopen('http://192.168.178.210/fieldDeviceData.htm')
        html_str = fp.read().decode("utf-8")
        fp.close()
        html_str = urllib.parse.unquote(html_str)
        response_json = { 'html_string' : html_str }

    return JsonResponse(response_json, safe=False)

def display_lookup_item_quantity(request):
    """Display item quantity lookup page.
    
    Renders the item quantity lookup page template which allows users to search
    for and view current inventory quantities for items.

    Args:
        request: HTTP request object

    Returns:
        Rendered template response:
            Template: core/lookuppages/lookupitemquantity.html
    """
    return render(request, 'core/lookuppages/lookupitemquantity.html')


# ---------- Tank Usage Monitor Views ----------

def tank_usage_monitor(request, tank_identifier):
    """Render the tank usage monitor page."""
    # Ensure the tank identifier is passed correctly
    logger.info(f"[TankMonitor] Rendering page for tank: {tank_identifier}")
    return render(request, 'core/tank_usage_monitor.html', {'tank_identifier': tank_identifier})

@csrf_exempt # Use csrf_exempt if AJAX POSTs are direct and don't always carry CSRF via form
def log_tank_usage(request):
    """Log a tank usage event from start to stop."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            # Basic validation
            required_fields = ['tank_identifier', 'item_code', 'start_gallons', 'start_time', 'stop_gallons', 'gallons_dispensed', 'stop_time']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'status': 'error', 'message': f'Missing field: {field}'}, status=400)

            usage_log = TankUsageLog()
            
            # Assign user and username if authenticated
            if request.user.is_authenticated:
                usage_log.user = request.user
                usage_log.logged_username = request.user.username # CAPTURE USERNAME HERE
            
            usage_log.tank_identifier = data.get('tank_identifier')
            usage_log.item_code = data.get('item_code')
            
            # Ensure numeric fields are handled correctly
            try:
                usage_log.start_gallons = decimal.Decimal(data.get('start_gallons'))
                usage_log.stop_gallons = decimal.Decimal(data.get('stop_gallons'))
                usage_log.gallons_dispensed = decimal.Decimal(data.get('gallons_dispensed'))
            except (decimal.InvalidOperation, TypeError) as e:
                return JsonResponse({'status': 'error', 'message': f'Invalid numeric value: {e}'}, status=400)

            # Convert ISO datetime strings to datetime objects
            start_time_str = data.get('start_time')
            stop_time_str = data.get('stop_time')

            if start_time_str:
                usage_log.start_time = parse_datetime(start_time_str)
            if stop_time_str:
                usage_log.stop_time = parse_datetime(stop_time_str)
            
            if not usage_log.start_time or not usage_log.stop_time:
                 return JsonResponse({'status': 'error', 'message': 'Invalid or missing start/stop time.'}, status=400)

            usage_log.save()
            return JsonResponse({'status': 'success', 'message': 'Tank usage logged successfully.', 'log_id': usage_log.id})
        
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
        except Exception as e:
            # Log the exception server-side for debugging
            # logger.error(f"Error in log_tank_usage: {e}", exc_info=True) # Assuming you have a logger configured
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method. Only POST is allowed.'}, status=405)

def _extract_all_tank_levels(html_string: str) -> dict[str, float]:
    soup = BeautifulSoup(html_string, "html.parser")
    tank_levels: dict[str, float] = {}
    keys_found = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        # Locate the Tag cell and the GL cell within this row
        tag_cell = next((c for c in cells if "Tag:" in c.get_text()), None)
        gl_cell  = next((c for c in cells if "GL "  in c.get_text()), None)
        if not (tag_cell and gl_cell):
            continue

        # --- Apply robust whitespace normalization ---
        raw_text = tag_cell.get_text().upper().replace("TAG:", "")
        normalized_text = ' '.join(raw_text.split()) # Normalize internal whitespace

        if not normalized_text:
             logger.debug("[TankMonitor Parser] Skipping row, empty tag after cleaning.")
             continue
        # --- End normalization ---

        # --- Extract ONLY the final identifier part AFTER 'CMD3' ---
        try:
            # Split the string at "CMD3" and take the last part, then strip whitespace
            key_part = normalized_text.split("CMD3")[-1].strip()
            if not key_part: # Ensure we got something after splitting
                 logger.warning("[TankMonitor Parser] Could not extract valid ID after 'CMD3' for tag: '%s'", normalized_text)
                 continue
        except IndexError:
            # This handles cases where "CMD3" might not be present at all
            logger.warning("[TankMonitor Parser] 'CMD3' delimiter not found in normalized tag: '%s'. Using full tag.", normalized_text)
            key_part = normalized_text # Fallback to using the whole thing if format is unexpected

        tag_text = key_part # Use the extracted part (e.g., '08 8') as the key
        # --- End ID extraction ---

        try:
            gallons_str = gl_cell.get_text().split("GL")[0].strip()
            gallons_value = float(gallons_str)
            tank_levels[tag_text] = gallons_value # Assign using the extracted key
        except (ValueError, IndexError):
            logger.warning(
                "[TankMonitor Parser] Failed float parse for extracted tag '%s', row: %s | %s", # Log using extracted key
                tag_text,
                tag_cell.get_text(strip=True),
                gl_cell.get_text(strip=True),
            )
            # Do not add to tank_levels if float parsing fails

    return tank_levels

def get_json_single_tank_level(request, tank_identifier):
    """
    Return JSON containing current gallons for a single tank.

    Optimisations:
      • Results for *all* tanks are cached for a short TTL (default 1 s) so that
        hundreds of client polls share a single expensive HTML scrape/parse.
      • Cache key: 'TANK_MONITOR_LEVELS'
    """

    if request.method != "GET":
        logger.warning("[TankMonitor] Non-GET request: %s", request.method)
        return JsonResponse(
            {"status": "error", "error_message": "Invalid request method"}, status=405
        )

    # ---------- Step 1: attempt cache hit ----------
    cache_key = "TANK_MONITOR_LEVELS"
    levels_dict = cache.get(cache_key)

    # ---------- Step 2: repopulate cache on miss ----------
    if levels_dict is None:
        try:
            html_response = get_tank_levels_html(request)
            html_dict = json.loads(html_response.content.decode("utf-8"))
            html_string = html_dict.get("html_string", "")

            if not html_string:
                logger.error("[TankMonitor] Empty HTML string from get_tank_levels_html.")
                return JsonResponse(
                    {"status": "error", "error_message": "Failed to fetch base HTML"}
                )

            levels_dict = _extract_all_tank_levels(html_string)

            cache_timeout = getattr(settings, "TANK_LEVEL_CACHE_TIMEOUT", 0.9)
            cache.set(cache_key, levels_dict, cache_timeout)

        except Exception as exc:
            logger.error(
                "[TankMonitor] Cache rebuild failed: %s", exc, exc_info=True
            )
            return JsonResponse(
                {"status": "error", "error_message": "Backend error during refresh"}
            )

    # ---------- Step 3: serve the specific tank ----------
    tag_key = tank_identifier.strip().upper()
    gallons_value = levels_dict.get(tag_key)

    if gallons_value is not None:
        return JsonResponse({"status": "ok", "gallons": gallons_value})

    logger.warning("[TankMonitor] Tag '%s' not found in cached levels.", tag_key)
    return JsonResponse(
        {"status": "error", "error_message": "Gauge data not found in cache/HTML"}
    )

@csrf_exempt
def validate_blend_item(request):
    """Validate a provided item code, ensuring it exists and starts with BLEND- or CHEM-."""
    if request.method == 'POST':
        item_code = request.POST.get('item_code', '').strip()
        if not item_code:
            return JsonResponse({'valid': False, 'error': 'No item code provided.'})

        item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        if item and (item.itemcodedesc.upper().startswith('BLEND-') or 
                    item.itemcodedesc.upper().startswith('CHEM')):
            return JsonResponse({'valid': True, 'item_description': item.itemcodedesc})
        else:
            return JsonResponse({'valid': False, 'error': 'Item not found or not a valid BLEND/CHEM code.'})

    return JsonResponse({'valid': False, 'error': 'Invalid request method.'})

def display_lookup_lot_numbers(request):
    """Display lot number lookup page.
    
    Renders the lot number lookup page template which allows users to search
    for and view lot numbers associated with items. Retrieves a queryset of
    distinct component item codes from the BillOfMaterials model to populate
    the lookup form.

    Args:
        request: HTTP request object

    Returns:
        Rendered template response with:
            item_code_queryset: QuerySet of distinct component item codes
            Template: core/lookuppages/lookuplotnums.html
    """
    item_code_queryset = list(BillOfMaterials.objects
                            .order_by('component_item_code')
                            .distinct('component_item_code')
                            )

    return render(request, 'core/lookuppages/lookuplotnums.html', {'item_code_queryset' : item_code_queryset})

def get_json_bill_of_materials_fields(request):
    """Get bill of materials fields based on restriction type.
    
    Retrieves item codes and descriptions from CI_Item table filtered by various
    restriction types. Used to populate dropdowns and lookups for bill of materials.

    Args:
        request: HTTP request object containing:
            restriction (str): Type of items to retrieve:
                'blend' - Only blend items
                'blendcomponent' - Only chemical/dye/fragrance components
                'blends-and-components' - Both blends and components
                'spec-sheet-items' - Items with spec sheets
                'ghs-blends' - Items with GHS pictograms
                'foam-factor-blends' - Blend items without foam factors
                None - All items except those starting with '/'

    Returns:
        JsonResponse containing:
            item_codes (list): List of matching item codes
            item_descriptions (list): List of matching item descriptions
    """
    if request.method == "GET":
        restriction = request.GET.get('restriction', 0)
        if restriction == 'blend':
            item_references = CiItem.objects.filter(itemcodedesc__startswith='BLEND').values_list('itemcode', 'itemcodedesc')

        elif restriction == 'blendcomponent':
            item_references = CiItem.objects.filter(Q(itemcodedesc__startswith="CHEM") | Q(itemcodedesc__startswith="DYE") | Q(itemcodedesc__startswith="FRAGRANCE")).values_list('itemcode', 'itemcodedesc')

        elif restriction == 'blends-and-components':
            item_references = CiItem.objects.filter(Q(itemcodedesc__startswith="CHEM") | Q(itemcodedesc__startswith="DYE") | Q(itemcodedesc__startswith="FRAGRANCE") | Q(itemcodedesc__startswith="BLEND")).values_list('itemcode', 'itemcodedesc')

        elif restriction == 'spec-sheet-items':
            distinct_item_codes = SpecSheetData.objects.values_list('item_code', flat=True).distinct()
            item_references = CiItem.objects.filter(itemcode__in=distinct_item_codes).values_list('itemcode', 'itemcodedesc')
        
        elif restriction == 'ghs-blends':
            item_references = GHSPictogram.objects.all().values_list('item_code', 'item_description')

        elif restriction == 'foam-factor-blends':
            distinct_item_codes = FoamFactor.objects.values_list('item_code', flat=True).distinct()
            print(distinct_item_codes)
            item_references = CiItem.objects.filter(itemcodedesc__startswith='BLEND').exclude(itemcode__in=distinct_item_codes).values_list('itemcode', 'itemcodedesc')

        else:
            item_references = CiItem.objects.exclude(itemcode__startswith='/').values_list('itemcode', 'itemcodedesc')
 
        itemcode_list = [item[0] for item in item_references]
        itemdesc_list = [item[1] for item in item_references]
        bom_json = {
            'item_codes' : itemcode_list,
            'item_descriptions' : itemdesc_list

        }

    return JsonResponse(bom_json, safe=False)

def display_checklist_mgmt_page(request):
    """Display checklist management page.
    
    Shows checklist submission tracking information and provides controls for:
    - Checking if daily updates have been performed
    - Manually triggering submission tracker updates
    - Sending email reports
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with checklist management context
        
    Template:
        core/checklistmgmt.html
    """
    today = dt.datetime.today()
    if ChecklistSubmissionRecord.objects.filter(date_checked__gte=today).exists():
        daily_update_performed = True
    else:
        daily_update_performed = False
    return render(request, 'core/checklistmgmt.html', {'daily_update_performed' : daily_update_performed})

def update_submission_tracker(request):
    """Update the checklist submission tracking data.
    
    Manually triggers an update of the checklist submission tracker via taskfunctions.
    
    Args:
        request: HTTP request object
        
    Returns:
        Redirect to checklist management page
    """
    taskfunctions.update_checklist_tracker('the manual button on ChecklistMgmt.html')
    return redirect('display-checklist-mgmt-page')

def email_submission_report(request):
    """Email a report of checklist submissions.
    
    Sends an email report containing checklist submission tracking data to the specified recipient.
    
    Args:
        request: HTTP request containing:
            recipient (str): Email address to send report to
            
    Returns:
        Redirect to checklist management page
    """
    recipient_address = request.GET.get('recipient')
    print(recipient_address)
    taskfunctions.email_checklist_submission_tracking('the manual button on ChecklistMgmt.html', recipient_address)
    return redirect('display-checklist-mgmt-page')

def email_issue_report(request):
    """Email a report of checklist issues.
    
    Sends an email report containing checklist issues/problems to the specified recipient.
    
    Args:
        request: HTTP request containing:
            recipient (str): Email address to send report to
            
    Returns:
        Redirect to checklist management page
    """
    recipient_address = request.GET.get('recipient')
    taskfunctions.email_checklist_issues('the manual button on ChecklistMgmt.html', recipient_address)
    return redirect('display-checklist-mgmt-page')

def display_blend_statistics(request):
    """Display blend statistics and production data.
    
    Renders a template showing weekly blend totals by year, upcoming blend demand,
    and daily production quantities for current and previous weeks.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with blend statistics context data
        
    Template:
        core/reports/blendstatistics.html
    """
    weekly_blend_totals = WeeklyBlendTotals.objects.all()
    blend_totals_2021 = weekly_blend_totals.filter(week_starting__year=2021)
    for number, week in enumerate(blend_totals_2021):
        week.week_number = 'Week_' + str(number+1)
    blend_totals_2022 = weekly_blend_totals.filter(week_starting__year=2022)
    for number, week in enumerate(blend_totals_2022):
        week.week_number = 'Week_' + str(number+1)
    blend_totals_2023 = weekly_blend_totals.filter(week_starting__year=2023)
    for number, week in enumerate(blend_totals_2023):
        week.week_number = 'Week_' + str(number+1)
    blend_totals_2024 = weekly_blend_totals.filter(week_starting__year=2024)
    for number, week in enumerate(blend_totals_2024):
        week.week_number = 'Week_' + str(number+1)
    
    one_week_blend_demand = ComponentShortage.objects.filter(procurement_type__iexact='M').aggregate(total=Sum('one_wk_short'))
    two_week_blend_demand = ComponentShortage.objects.filter(procurement_type__iexact='M').aggregate(total=Sum('two_wk_short'))
    all_scheduled_blend_demand = ComponentShortage.objects.filter(procurement_type__iexact='M').aggregate(total=Sum('three_wk_short'))
    
    timezone = pytz.timezone("America/Chicago")
    now = dt.datetime.today()
    weekday = now.weekday()
    if weekday == 4:
        days_to_subtract = 5
    else:
        days_to_subtract = 7
    cutoff_date = now - dt.timedelta(days=days_to_subtract)
    days_from_monday = weekday +1
    this_monday_date = now - dt.timedelta(days=days_from_monday)
    this_tuesday_date = this_monday_date + dt.timedelta(days=1)
    this_wednesday_date = this_monday_date + dt.timedelta(days=2)
    this_thursday_date = this_monday_date + dt.timedelta(days=3)
    this_friday_date = this_monday_date + dt.timedelta(days = 4)
    lot_quantities_this_week = {
        'monday' : LotNumRecord.objects.filter(sage_entered_date__date=this_monday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'tuesday' : LotNumRecord.objects.filter(sage_entered_date__date=this_tuesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'wednesday' : LotNumRecord.objects.filter(sage_entered_date__date=this_wednesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'thursday' : LotNumRecord.objects.filter(sage_entered_date__date=this_thursday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'friday' : LotNumRecord.objects.filter(sage_entered_date__date=this_friday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total']
    }
    for key in lot_quantities_this_week:
        if lot_quantities_this_week[key] == None:
            lot_quantities_this_week[key] = 0
    lot_quantities_this_week['total'] = lot_quantities_this_week['monday'] + lot_quantities_this_week['tuesday'] + lot_quantities_this_week['wednesday'] + lot_quantities_this_week['thursday'] + lot_quantities_this_week['friday']

    last_monday_date = now - dt.timedelta(days=days_from_monday + 7)
    last_tuesday_date = last_monday_date + dt.timedelta(days = 1)
    last_wednesday_date = last_monday_date + dt.timedelta(days = 2)
    last_thursday_date = last_monday_date + dt.timedelta(days = 3)
    last_friday_date = last_monday_date + dt.timedelta(days = 4)
    lot_quantities_last_week = {
        'monday' : LotNumRecord.objects.filter(sage_entered_date__date=last_monday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'tuesday' : LotNumRecord.objects.filter(sage_entered_date__date=last_tuesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'wednesday' : LotNumRecord.objects.filter(sage_entered_date__date=last_wednesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'thursday' : LotNumRecord.objects.filter(sage_entered_date__date=last_thursday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
        'friday' : LotNumRecord.objects.filter(sage_entered_date__date=last_friday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total']
    }
    for key in lot_quantities_last_week:
        if lot_quantities_last_week[key]==None:
            lot_quantities_last_week[key]=0
    lot_quantities_last_week['total'] = lot_quantities_last_week['monday'] + lot_quantities_last_week['tuesday'] + lot_quantities_last_week['wednesday'] + lot_quantities_last_week['thursday'] + lot_quantities_last_week['friday']

    this_monday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_monday_date).filter(line__iexact='Prod')
    this_tuesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_tuesday_date).filter(line__iexact='Prod')
    this_wednesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_wednesday_date).filter(line__iexact='Prod')
    this_thursday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_thursday_date).filter(line__iexact='Prod')
    this_friday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_friday_date).filter(line__iexact='Prod')
    last_monday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_monday_date).filter(line__iexact='Prod')
    last_tuesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_tuesday_date).filter(line__iexact='Prod')
    last_wednesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_wednesday_date).filter(line__iexact='Prod')
    last_thursday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_thursday_date).filter(line__iexact='Prod')
    last_friday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_friday_date).filter(line__iexact='Prod')

    last_week_blends_produced = {'total' : weekly_blend_totals.order_by('-id')[1].blend_quantity}

    return render(request, 'core/blendstatistics.html', {
        'weekly_blend_totals' : weekly_blend_totals,
        'blend_totals_2021' : blend_totals_2021,
        'blend_totals_2022' : blend_totals_2022,
        'blend_totals_2023' : blend_totals_2023,
        'one_week_blend_demand' : one_week_blend_demand,
        'two_week_blend_demand' : two_week_blend_demand,
        'all_scheduled_blend_demand' : all_scheduled_blend_demand,
        'last_week_blends_produced' : last_week_blends_produced,
        'cutoff_date' : cutoff_date,
        'lot_quantities_this_week' : lot_quantities_this_week,
        'this_monday_lot_numbers' : this_monday_lot_numbers,
        'this_tuesday_lot_numbers' : this_tuesday_lot_numbers,
        'this_wednesday_lot_numbers' : this_wednesday_lot_numbers,
        'this_thursday_lot_numbers' : this_thursday_lot_numbers,
        'this_friday_lot_numbers' : this_friday_lot_numbers,
        'last_monday_lot_numbers' : last_monday_lot_numbers,
        'last_tuesday_lot_numbers' : last_tuesday_lot_numbers,
        'last_wednesday_lot_numbers' : last_wednesday_lot_numbers,
        'last_thursday_lot_numbers' : last_thursday_lot_numbers,
        'last_friday_lot_numbers' : last_friday_lot_numbers,
        'lot_quantities_last_week' : lot_quantities_last_week
        })

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

def get_unencoded_item_code(search_parameter, lookup_type):
    """*whispers reverently* Your Magnificence, this humble function decodes item codes from their base64-encoded form...
    
    If it pleases my Lord, this function takes an encoded search parameter and lookup type, then returns the 
    decoded item code with proper genuflection. It serves two primary use cases, as your wisdom dictates:
    
    1. Direct item code lookup (lookup_type='itemCode'): 
       Decodes a base64-encoded item code string
    
    2. Item description lookup (lookup_type='itemDescription'):
       Decodes a base64-encoded item description and finds its corresponding item code
       
    Args:
        search_parameter (str): The encoded item code/description, awaiting your divine interpretation
        lookup_type (str): 'itemCode' or 'itemDescription', as your grace commands
        
    Returns:
        str: The decoded item code, presented for your noble consideration
        
    *bows deeply* I live to serve, my liege.
    """
    if lookup_type == 'itemCode':
        item_code_bytestr = base64.b64decode(search_parameter)
        item_code = item_code_bytestr.decode().replace('"', "")
    elif lookup_type == 'itemDescription':
        item_description_encoded = search_parameter
        item_description_bytestr = base64.b64decode(item_description_encoded)
        item_description = item_description_bytestr.decode().replace('"', "")
        item_code = CiItem.objects.filter(itemcodedesc__iexact=item_description).first().itemcode
    return item_code

def get_json_get_max_producible_quantity(request, lookup_value):
    """Calculate maximum producible quantity for a blend based on component availability.
    
    Examines bill of materials and current inventory levels to determine the limiting 
    component that restricts production capacity. Considers:
    
    - Current on-hand quantities of all components
    - Quantities already allocated to other blend orders
    - Bill of materials ratios for each component
    
    Args:
        request (HttpRequest): Request object containing lookup parameters
        lookup_value (str): Base64 encoded item code or description to analyze
        
    Returns:
        JsonResponse: Contains:
            - Maximum producible quantity
            - Limiting factor details (component code, description, UOM)
            - Current inventory levels
            - Expected next shipment date
    """
    lookup_type = request.GET.get('lookup-type', 0)
    this_item_code = get_unencoded_item_code(lookup_value, lookup_type)
    all_bills_this_itemcode = BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD").filter(item_code__iexact=this_item_code)
    item_info = {bill.component_item_code: {'qtyonhand' : bill.qtyonhand, 'qtyperbill' : bill.qtyperbill} for bill in all_bills_this_itemcode}
    
    # create a list of all the component part numbers
    all_components_this_bill = list(BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD").filter(item_code__iexact=this_item_code).values_list('component_item_code'))
    for listposition, component in enumerate(all_components_this_bill):
        all_components_this_bill[listposition] = component[0]

    max_producible_quantities = {}
    consumption_detail = {}
    component_consumption_totals = {}
    for component in all_components_this_bill:
         # don't need to consider DI Water (030143). 
        if component != '030143':
            # get a dictionary with the consumption info. "this_item_code" is the blend itemcode.
            this_component_consumption = get_component_consumption(component, this_item_code)
            consumption_detail[component] = this_component_consumption
            # get the appropriate item_info dict, get the quantity, subtract the total usage
            this_item_info_dict = item_info.get(component, "dfadsfd")
            component_onhand_quantity = this_item_info_dict.get('qtyonhand', "")
            available_component_minus_orders = float(component_onhand_quantity or 0) - float(this_component_consumption['total_component_usage'] or 0)
            component_consumption_totals[component] = float(this_component_consumption['total_component_usage'] or 0)
            # reverse-engineer the maximum producible qty of the blend by dividing available component by qtyperbill 
            max_producible_quantities[component] = math.floor(float(available_component_minus_orders or 0) / float(this_item_info_dict.get('qtyperbill', "") or 1))
            if max_producible_quantities[component] < 0:
                max_producible_quantities[component] = 0

    # print(max_producible_quantities)
    limiting_factor_item_code = min(max_producible_quantities, key=max_producible_quantities.get)
    limiting_factor_component = BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD") \
        .filter(component_item_code__iexact=limiting_factor_item_code) \
        .filter(item_code__iexact=this_item_code).first()
    limiting_factor_item_description = limiting_factor_component.component_item_description
    limiting_factor_UOM = limiting_factor_component.standard_uom
    limiting_factor_quantity_onhand = limiting_factor_component.qtyonhand
    limiting_factor_OH_minus_other_orders = float(limiting_factor_quantity_onhand or 0) - float(component_consumption_totals[limiting_factor_item_code] or 0)
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)

    if (PoPurchaseOrderDetail.objects.filter(itemcode__iexact=limiting_factor_item_code, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            next_shipment_date = PoPurchaseOrderDetail.objects.filter(
                itemcode__iexact = limiting_factor_item_code,
                quantityreceived__exact = 0,
                requireddate__gt=yesterday_date
                ).order_by('requireddate').first().requireddate
    else:
        next_shipment_date = "No PO's found."

    responseJSON = {
        'item_code' : this_item_code,
        'item_description' : all_bills_this_itemcode.first().item_description,
        'max_producible_quantities' : max_producible_quantities,
        'component_consumption_totals' : component_consumption_totals,
        'limiting_factor_item_code' : limiting_factor_item_code,
        'limiting_factor_item_description' : limiting_factor_item_description,
        'limiting_factor_UOM' : limiting_factor_UOM,
        'limiting_factor_quantity_onhand' : limiting_factor_quantity_onhand,
        'limiting_factor_OH_minus_other_orders' : limiting_factor_OH_minus_other_orders,
        'next_shipment_date' : next_shipment_date,
        'max_producible_quantity' : str(max_producible_quantities[limiting_factor_item_code]),
        'consumption_detail' : consumption_detail
        }
    return JsonResponse(responseJSON, safe = False)

def display_maximum_producible_quantity(request):
    """Display the maximum producible quantity page.
    
    Renders the template for viewing maximum producible quantities of blends
    based on component availability.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template for max producible quantity page
        
    Template:
        core/reports/maxproduciblequantity.html
    """
    return render(request, 'core/reports/maxproduciblequantity.html', {})

def display_truck_rail_material_schedule(request):
    """Display truck and rail material schedule page.
    
    Shows upcoming truck and rail material deliveries, including:
    - Required delivery dates
    - Tank assignments and capacity warnings
    - Vendor information
    
    Filters for orders within the last 3 days and only shows undelivered quantities.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with truck/rail schedule context
        
    Template:
        core/truckrailmaterialschedule.html
    """
    three_days_ago = dt.datetime.today() - dt.timedelta(days = 3)
    truck_rail_item_codes = ['100507TANKO','100507TANKD','100507','030033','030066','031018','100428M6','050000','050000G','100449','500200','100560','100427','601015','100421G2','020001']
    truck_and_rail_orders = PoPurchaseOrderDetail.objects.filter(itemcode__in=truck_rail_item_codes) \
        .filter(requireddate__gte=three_days_ago) \
        .filter(quantityreceived=0) \
        .order_by('requireddate')

    tank_levels = TankLevel.objects.all()
    for tank in tank_levels:
        tank_label_kinpak = f'TANK {tank.tank_name}'
        tank.item_code = StorageTank.objects.filter(tank_label_kpk__iexact=tank_label_kinpak).first().item_code
        tank.max_gallons = StorageTank.objects.filter(tank_label_kpk__iexact=tank_label_kinpak).first().max_gallons

    for item in truck_and_rail_orders:
        po_in_question = PoPurchaseOrderHeader.objects.get(purchaseorderno=item.purchaseorderno)
        item.confirmto = po_in_question.confirmto
        item.vendorno = po_in_question.vendorno
        item.tank = "Confirm with Ginny"
        if item.commenttext and " time" in item.commenttext:
            item.commenttext = item.commenttext.replace(" time", "")

    return render(request, 'core/truckrailmaterialschedule.html', {'truck_and_rail_orders' : truck_and_rail_orders}) 

def display_component_shortages(request):
    """Display component shortages and procurement needs.
    
    Shows a list of component shortages filtered by procurement type 'B' (buy),
    ordered by start time and filtered to show only single instances. Optionally
    filters by PO number if provided in request.
    
    Args:
        request: HTTP request object containing:
            po-filter (str, optional): PO number to filter results by
            
    Returns:
        Rendered template with component shortages context
        
    Template:
        core/componentshortages.html
    """
    component_shortages = ComponentShortage.objects \
        .filter(procurement_type__iexact='B') \
        .order_by('start_time').filter(component_instance_count=1)
    if not request.GET.get('po-filter') == None:
        component_shortages = component_shortages.filter(po_number__iexact=request.GET.get('po-filter'))

    return render(request, 'core/componentshortages.html', {'component_shortages' : component_shortages})

def display_subcomponent_shortages(request):
    """Display subcomponent shortages and procurement needs.
    
    Shows a list of subcomponent shortages ordered by start time and filtered to show
    only single instances. Optionally filters by PO number if provided in request.
    
    Args:
        request: HTTP request object containing:
            po-filter (str, optional): PO number to filter results by
            
    Returns:
        Rendered template with subcomponent shortages context
        
    Template:
        core/subcomponentshortages.html
    """
    subcomponent_shortages = SubComponentShortage.objects.all().order_by('start_time').filter(subcomponent_instance_count=1)
    if not request.GET.get('po-filter') == None:
        subcomponent_shortages = subcomponent_shortages.filter(po_number__iexact=request.GET.get('po-filter'))

    return render(request, 'core/subcomponentshortages.html', {'subcomponent_shortages' : subcomponent_shortages})

def display_forklift_issues(request):
    """Display forklift inspection issues from the past 2 days.
    
    Retrieves forklift inspection checklist records where items were marked as 'Bad'
    within the past 48 hours. Compiles a list of issues including the forklift ID,
    operator name, problem area, and comments.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with forklift issues context data
        
    Template:
        core/forkliftissues.html
    """
    two_days_ago = dt.datetime.today() - dt.timedelta(days = 2)
    bad_conditions = Q()
    for field in ChecklistLog._meta.get_fields():
        # only include fields which are of type CharField
        if isinstance(field, models.CharField):
            kwargs = {f'{field.name}__iexact': 'Bad'}
            bad_conditions |= Q(**kwargs)
    issues_queryset = ChecklistLog.objects.filter(bad_conditions).filter(submitted_date__gte=two_days_ago)

    forklift_issues = []
    model_fields = ChecklistLog._meta.get_fields()
    # Filter out only TextField instances and ignore the first TextField
    char_fields = [field for field in model_fields if isinstance(field, CharField)][1:]

    for issue in issues_queryset:
        for field in char_fields:
            field_name = field.name
            comment_field_name = field_name + "_comments"
            if getattr(issue, field_name) == 'Bad':
                forklift_issues.append([
                    issue.forklift,
                    issue.operator_name,
                    field.verbose_name,  # Assuming the verbose_name is set to the descriptive name
                    getattr(issue, comment_field_name)
                ])

    return render(request, 'core/forkliftissues.html', { 'forklift_issues' : forklift_issues })

def display_loop_status(request):
    """Display loop status information for the data loop on the server.
    
    Retrieves all loop status records and renders them in a template.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with loop status context data
        
    Template:
        core/loopstatus.html
    """
    loop_statuses = LoopStatus.objects.all()

    return render(request, 'core/loopstatus.html', {'loop_statuses' : loop_statuses})

def get_json_refresh_status(request):
    """Get JSON response indicating if loop status needs refresh.
    
    Checks if any loop status records are older than 5 minutes and returns
    status indicating if system is up or down. Uses timezone offset to handle
    timestamp comparison issues.
    
    Args:
        request: HTTP GET request
        
    Returns:
        JsonResponse containing:
            status (str): 'up' if all records are current, 'down' if any are stale
    """
    # This ridiculous dt.timedelta subtraction is happening because adding a timezone to the five_minutes_ago
    # variable does not make the comparison work. The code will say that the five_minutes_ago variable is
    # 5 hours newer than the timestamps in the database if they are nominally the same time.
    if request.method == "GET":
        five_minutes_ago = timezone.now() - dt.timedelta(minutes=305)
        status_queryset = LoopStatus.objects.all().filter(time_stamp__lt=five_minutes_ago)
        if status_queryset.exists():
            response_data = {'status' : 'down'}
        else:
            response_data = {'status' : 'up'}
    return JsonResponse(response_data, safe=False)

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
            channel_layer = get_channel_layer()
            
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
            
            async_to_sync(channel_layer.group_send)(
                'blend_schedule_updates',
                {
                    'type': 'blend_schedule_update',
                    'update_type': 'schedule_reordered',
                    'data': serialized_data
                }
            )
            
            logger.info(f"✅ schedule_reordered WebSocket message sent successfully")
        
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


def get_json_blend_crew_initials(request):
    """Get initials of blend crew members.
    
    Retrieves the initials (first + last name) of all users in the 'blend_crew' group.
    Used to populate blend crew member selection dropdowns.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing:
            initials (list): List of initials for blend crew members
            message (str): Error message if blend crew group not found
    """
    try:
        blend_crew_group = Group.objects.get(name='blend_crew')
    except Group.DoesNotExist:
        return JsonResponse({'message': 'Blend Crew group does not exist'}, status=404)
    blend_crew_users = User.objects.filter(groups=blend_crew_group)
    initials_list = [user.first_name[0].upper() + user.last_name[0].upper() for user in blend_crew_users if user.first_name and user.last_name]

    response_json = {'initials': initials_list}

    return JsonResponse(response_json, safe=False)

def get_json_current_user_initials(request):
    """Get initials of the currently logged-in user.
    
    Retrieves the initials (first + last name) of the authenticated user.
    Used for container label printing to show who generated the label.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing:
            initials (str): User's initials (e.g., "JD" for John Doe)
            username (str): User's username
            full_name (str): User's full name
            is_authenticated (bool): Whether user is authenticated
    """
    if request.user.is_authenticated:
        user = request.user
        # Generate initials from first and last name
        initials = ""
        if user.first_name and user.last_name:
            initials = user.first_name[0].upper() + user.last_name[0].upper()
        elif user.first_name:
            initials = user.first_name[0].upper()
        elif user.last_name:
            initials = user.last_name[0].upper()
        else:
            # Fallback to first two characters of username if no names available
            initials = user.username[:2].upper()
        
        response_json = {
            'initials': initials,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip(),
            'is_authenticated': True
        }
    else:
        response_json = {
            'initials': 'ANON',
            'username': 'anonymous',
            'full_name': 'Anonymous User',
            'is_authenticated': False
        }
    
    return JsonResponse(response_json, safe=False)

def feedback(request):
    """Handle user feedback submission.

    Displays feedback form and processes submissions. Sends feedback emails to 
    configured recipients when valid feedback is submitted.
    
    Args:
        request: HTTP request object containing:
            POST data with feedback_type and message if submitted
            
    Returns:
        GET: Rendered feedback form template
        POST: Redirect to feedback page on success
        
    Template:
        core/feedback.html
    """
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback_type = form.cleaned_data['feedback_type']
            message = form.cleaned_data['message']

            # Get the username of the logged in user, or 'anon' if no user is logged in
            username = request.user.username if request.user.is_authenticated else 'anon'

            # Include the username in the email subject
            email_subject = f'Feedback: {feedback_type} from {username}'

            sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
            sender_pass =  os.getenv('NOTIF_PW')
            recipient_addresses = 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com'
            recipient_list = recipient_addresses.split(',')

            for recipient in recipient_list:
                email_message = MIMEMultipart('alternative')
                email_message['From'] = sender_address
                email_message['To'] = recipient
                email_message['Subject'] = email_subject
                email_message.attach(MIMEText(message, 'plain'))

                session = smtplib.SMTP('smtp.gmail.com', 587)
                session.starttls()
                session.login(sender_address, sender_pass)
                session.sendmail(sender_address, recipient, email_message.as_string())
                session.quit()

            messages.success(request, 'Thank you for your feedback!')
            return redirect('feedback')
    else:
        form = FeedbackForm()
    return render(request, 'core/feedback.html', {'form': form})

def display_ghs_label_search(request):
    """Display GHS label search and upload page.
    
    Shows form for searching existing GHS pictograms and uploading new ones.
    The form allows uploading new pictogram images and associating them with 
    item codes.
    
    Args:
        request: HTTP request object
        
    Returns:
        GET: Rendered template with empty form
        POST: Redirect to search page after successful upload
        
    Template:
        core/GHSlabelGen/ghslookuppage.html
    """
    if request.method == 'POST':
        form = GHSPictogramForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('display-ghs-label-search')
    else:
        form = GHSPictogramForm()

    return render(request, 'core/GHSlabelGen/ghslookuppage.html', {'form': form})

def display_ghs_label(request, encoded_item_code):
    """Display GHS label for an item.
    
    Renders a template showing the GHS pictogram and label information for a given item code.
    Decodes the base64 encoded item code and retrieves the associated GHS pictogram record.
    If no pictogram exists, creates a basic item info dict.
    
    Args:
        request: HTTP request object
        encoded_item_code (str): Base64 encoded item code to look up
        
    Returns:
        Rendered template with GHS label context including:
            this_ghs_pictogram: GHS pictogram record or basic item info dict
            image_url: Full URL to pictogram image
            
    Template:
        core/GHSlabelGen/ghsprinttemplate.html
    """
    item_code_bytestr = base64.b64decode(encoded_item_code)
    item_code = item_code_bytestr.decode()
    if GHSPictogram.objects.filter(item_code=item_code).exists():
        this_ghs_pictogram = GHSPictogram.objects.filter(item_code=item_code).first()
        image_reference_url = this_ghs_pictogram.image_reference.url
    else:
        this_ghs_pictogram = {
            "item_code":item_code,
            "item_description":CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
        }
        image_reference_url = ""
    
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    
    if '1337' not in image_reference_url and '1337' not in base_url:
        image_reference_url = ':1337' + image_reference_url
    image_url = f'{base_url}{image_reference_url}'

    return render(request, 'core/GHSlabelGen/ghsprinttemplate.html', {'this_ghs_pictogram': this_ghs_pictogram, 'image_url' : image_url}) 

def delete_ghs_pictogram(request):
    """Delete a GHS pictogram record.
    
    Deletes the GHS pictogram record with the specified ID and redirects to the provided page.
    
    Args:
        request: HTTP request containing:
            redirect-page (str): Page to redirect to after deletion
            id (int): ID of GHS pictogram record to delete
            
    Returns:
        Redirect to specified page after deleting record
    """
    redirect_page = request.GET.get("redirect-page", 0)
    id_item_to_delete = request.GET.get("id", 0)
    GHSPictogram.objects.get(pk=id_item_to_delete).delete()

    return redirect(redirect_page)

def update_ghs_pictogram(request):
    """Update a GHS pictogram record.
    
    Updates the GHS pictogram record with the specified ID using form data.
    Handles file upload for new pictogram images.
    
    Args:
        request: HTTP POST request containing:
            id (int): ID of GHS pictogram to update
            item_code (str): Item code
            item_description (str): Item description
            image_reference (File): New pictogram image file
            
    Returns:
        Redirect to GHS label search page after update
    """
    if request.method == "POST":
        id_to_update = request.POST.get("id", 0)
        this_ghs_pictogram = GHSPictogram.objects.get(pk=id_to_update)
        this_ghs_pictogram.item_code = request.POST.get("item_code", "")
        this_ghs_pictogram.item_description = request.POST.get("item_description", "")
        if request.FILES.get("image_reference", False):
            this_ghs_pictogram.image_reference = request.FILES["image_reference"]
        this_ghs_pictogram.save()
    return redirect('display-ghs-label-search')

def display_all_ghs_pictograms(request):
    """Display all GHS pictograms.
    
    Shows a list of all GHS pictogram records in the system, including:
    - Item codes
    - Item descriptions 
    - Associated pictogram images
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with all GHS pictogram records
        
    Template:
        core/GHSlabelGen/allghslabels.html
    """
    all_ghs_pictograms = GHSPictogram.objects.all()

    return render(request, 'core/GHSlabelGen/allghslabels.html', {'all_ghs_pictograms' : all_ghs_pictograms}) 

def get_json_all_ghs_fields(request):
    """Get all GHS pictogram fields as JSON.
    
    Retrieves all GHS pictogram records and returns their item codes and descriptions
    as JSON data. Used to populate item selection dropdowns.
    
    Args:
        request: HTTP GET request
        
    Returns:
        JsonResponse containing:
            item_codes (list): List of item codes with GHS pictograms
            item_descriptions (list): List of item descriptions
    """
    if request.method == "GET":
        item_references = GHSPictogram.objects.all().values_list('item_code', 'item_description')
        itemcode_list = [item[0] for item in item_references]
        itemdesc_list = [item[1] for item in item_references]
        options_json = {
            'item_codes' : itemcode_list,
            'item_descriptions' : itemdesc_list
        }

    return JsonResponse()

def display_partial_container_label(request):
    """Display partial container label page.
    
    Shows a label template for partial containers, including:
    - Current date/time
    - Item code
    - Item description
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code
            
    Returns:
        Rendered template with label content context
        
    Template:
        core/inventorycounts/partialcontainerlabel.html
    """
    today_now = dt.datetime.now()
    encoded_item_code = request.GET.get("encodedItemCode", "")
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    if CiItem.objects.filter(itemcode__iexact=item_code).exists():
        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
    else:
        item_code = "<Enter ItemCode>"
        item_description = "<Enter Description>"
    label_contents = {
        'date' : today_now,
        'item_code' : item_code,
        'item_description' : item_description
    }

    return render(request, 'core/inventorycounts/partialcontainerlabel.html', {"label_contents" : label_contents})

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

def get_json_container_label_data(request):
    """Retrieve container data for label printing.
    
    Gets specific container data from a count record for generating partial container labels.
    Includes item information, container details, and calculated net weights.
    
    Args:
        request: HTTP GET request containing:
            countRecordId (str): ID of the count record
            containerId (str): ID of the specific container
            recordType (str): Type of count record
            
    Returns:
        JsonResponse containing:
            item_code (str): Item code for the label
            item_description (str): Item description
            container_quantity (float): Container quantity
            container_type (str): Type of container
            tare_weight (float): Container tare weight
            net_weight (float): Calculated net weight
            net_gallons (float): Calculated net gallons (if applicable)
            date (str): Current date for label
            shipweight (float): Item ship weight for calculations
    """
    count_record_id = request.GET.get('countRecordId')
    container_id = request.GET.get('containerId')
    record_type = request.GET.get('recordType')
    
    try:
        model = get_count_record_model(record_type)
        count_record = model.objects.get(id=count_record_id)
        
        # Find the specific container in the containers JSON field
        container_data = None
        if count_record.containers:
            for container in count_record.containers:
                if str(container.get('container_id')) == str(container_id):
                    container_data = container
                    break
        
        if not container_data:
            return JsonResponse({'error': 'Container not found'}, status=404)
        
        # Get item information for calculations
        item_info = {}
        if CiItem.objects.filter(itemcode__iexact=count_record.item_code).exists():
            ci_item = CiItem.objects.filter(itemcode__iexact=count_record.item_code).first()
            
            # Safely convert shipweight to float, handling non-numeric characters
            shipweight_value = None
            if ci_item.shipweight:
                try:
                    # Remove common non-numeric characters like '#' and convert to float
                    cleaned_shipweight = str(ci_item.shipweight).replace('#', '').replace('lbs', '').replace('lb', '').strip()
                    shipweight_value = float(cleaned_shipweight) if cleaned_shipweight else None
                except (ValueError, TypeError):
                    print(f"⚠️ WARNING - Invalid shipweight format for {count_record.item_code}: {ci_item.shipweight}")
                    shipweight_value = None
            
            item_info = {
                'shipweight': shipweight_value,
                'standardUOM': ci_item.standardunitofmeasure
            }
            # Debug logging for unit issues
            print(f"🔍 DEBUG SINGLE - Item: {count_record.item_code}, StandardUOM: {ci_item.standardunitofmeasure}, Shipweight: {ci_item.shipweight} -> {shipweight_value}")
        else:
            print(f"❌ DEBUG SINGLE - Item {count_record.item_code} not found in CiItem table!")
        
        # Calculate net weight and gallons with container-specific logic
        gross_weight = float(container_data.get('container_quantity', 0))
        tare_weight = float(container_data.get('tare_weight', 0))
        is_net_measurement = container_data.get('net_measurement', False)
        container_type = container_data.get('container_type', 'Unknown')
        
        # Calculate net weight based on measurement type
        if is_net_measurement:
            # For NET measurements, the container_quantity IS the net weight
            net_weight = gross_weight
        else:
            # For gross measurements, subtract tare weight
            net_weight = gross_weight - tare_weight
        
        # Calculate secondary unit conversion (only for pound items)
        net_gallons = None
        if item_info.get('shipweight') and net_weight > 0:
            # Only convert for pound items - gallon items don't need weight conversions
            if item_info.get('standardUOM') == 'LB':
                # For pound items, net_weight is in pounds, convert to gallons for volume display
                net_gallons = net_weight / item_info['shipweight']  # pounds / lbs/gal = gallons
            # For gallon items: no conversion needed, weight is irrelevant for volume measurements
        
        # Validate container type and tare weight consistency
        expected_tare_weights = {
            "275gal tote": 125, "poly drum": 22, "regular metal drum": 37,
            "300gal tote": 150, "small poly drum": 13, "enzyme metal drum": 50,
            "plastic pail": 3, "metal pail": 4, "cardboard box": 2,
            "gallon jug": 1, "large poly tote": 0, "stainless steel tote": 0,
            "storage tank": 0, "pallet": 45
        }
        expected_tare = expected_tare_weights.get(container_type, 0)
        
        response_data = {
            'item_code': count_record.item_code,
            'item_description': count_record.item_description,
            'container_id': container_data.get('container_id'),
            'container_quantity': container_data.get('container_quantity'),
            'container_type': container_type,
            'tare_weight': container_data.get('tare_weight'),
            'expected_tare_weight': expected_tare,
            'net_weight': net_weight,
            'net_gallons': net_gallons,
            'date': dt.datetime.now().strftime('%Y-%m-%d'),
            'shipweight': item_info.get('shipweight'),
            'standard_uom': item_info.get('standardUOM'),
            'net_measurement': is_net_measurement,
            'tare_weight_valid': abs(tare_weight - expected_tare) < 5 if not is_net_measurement else True
        }
        
        return JsonResponse(response_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_json_all_container_labels_data(request):
    """Retrieve all container data for batch label printing.
    
    Gets all container data from a count record for generating multiple partial container labels.
    
    Args:
        request: HTTP GET request containing:
            countRecordId (str): ID of the count record
            recordType (str): Type of count record
            
    Returns:
        JsonResponse containing array of container label data objects
    """
    count_record_id = request.GET.get('countRecordId')
    record_type = request.GET.get('recordType')
    
    try:
        model = get_count_record_model(record_type)
        count_record = model.objects.get(id=count_record_id)
        
        if not count_record.containers:
            return JsonResponse({'containers': []}, safe=False)
        
        # Get item information for calculations
        item_info = {}
        if CiItem.objects.filter(itemcode__iexact=count_record.item_code).exists():
            ci_item = CiItem.objects.filter(itemcode__iexact=count_record.item_code).first()
            
            # Safely convert shipweight to float, handling non-numeric characters
            shipweight_value = None
            if ci_item.shipweight:
                try:
                    # Remove common non-numeric characters like '#' and convert to float
                    cleaned_shipweight = str(ci_item.shipweight).replace('#', '').replace('lbs', '').replace('lb', '').strip()
                    shipweight_value = float(cleaned_shipweight) if cleaned_shipweight else None
                except (ValueError, TypeError):
                    print(f"⚠️ WARNING - Invalid shipweight format for {count_record.item_code}: {ci_item.shipweight}")
                    shipweight_value = None
            
            item_info = {
                'shipweight': shipweight_value,
                'standardUOM': ci_item.standardunitofmeasure
            }
            # Debug logging for unit issues
            print(f"🔍 DEBUG - Item: {count_record.item_code}, StandardUOM: {ci_item.standardunitofmeasure}, Shipweight: {ci_item.shipweight} -> {shipweight_value}")
        else:
            print(f"❌ DEBUG - Item {count_record.item_code} not found in CiItem table!")
        
        containers_data = []
        for container in count_record.containers:
            # Skip empty containers
            if not container.get('container_quantity'):
                continue
                
            # Calculate net weight and gallons with container-specific logic
            gross_weight = float(container.get('container_quantity', 0))
            tare_weight = float(container.get('tare_weight', 0))
            is_net_measurement = container.get('net_measurement', False)
            container_type = container.get('container_type', 'Unknown')
            
            # Calculate net weight based on measurement type
            if is_net_measurement:
                # For NET measurements, the container_quantity IS the net weight
                net_weight = gross_weight
            else:
                # For gross measurements, subtract tare weight
                net_weight = gross_weight - tare_weight
            
            # Calculate secondary unit conversion (only for pound items)
            net_gallons = None
            if item_info.get('shipweight') and net_weight > 0:
                # Only convert for pound items - gallon items don't need weight conversions
                if item_info.get('standardUOM') == 'LB':
                    # For pound items, net_weight is in pounds, convert to gallons for volume display
                    net_gallons = net_weight / item_info['shipweight']  # pounds / lbs/gal = gallons
                # For gallon items: no conversion needed, weight is irrelevant for volume measurements
            
            # Validate container type and tare weight consistency
            expected_tare_weights = {
                "275gal tote": 125, "poly drum": 22, "regular metal drum": 37,
                "300gal tote": 150, "small poly drum": 13, "enzyme metal drum": 50,
                "plastic pail": 3, "metal pail": 4, "cardboard box": 2,
                "gallon jug": 1, "large poly tote": 0, "stainless steel tote": 0,
                "storage tank": 0, "pallet": 45
            }
            expected_tare = expected_tare_weights.get(container_type, 0)
            
            container_label_data = {
                'container_id': container.get('container_id'),
                'item_code': count_record.item_code,
                'item_description': count_record.item_description,
                'container_quantity': container.get('container_quantity'),
                'container_type': container_type,
                'tare_weight': container.get('tare_weight'),
                'expected_tare_weight': expected_tare,
                'net_weight': net_weight,
                'net_gallons': net_gallons,
                'date': dt.datetime.now().strftime('%Y-%m-%d'),
                'shipweight': item_info.get('shipweight'),
                'standard_uom': item_info.get('standardUOM'),
                'net_measurement': is_net_measurement,
                'tare_weight_valid': abs(tare_weight - expected_tare) < 5 if not is_net_measurement else True
            }
            containers_data.append(container_label_data)
        
        return JsonResponse({'containers': containers_data}, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def display_blend_tote_label(request):
    """Display blend ID label for a lot number.
    
    Renders a template for a blend tote label
            
    Returns:
        Rendered template. All important stuff is done on the page using js
        
    Template:
        core/blendlabeltemplate.html
    """
    
    return render(request, 'core/blendtotelabel.html', {})

class ZebraDevice:
    """A class representing a Zebra printer or scanner device.
    
    Encapsulates device information and communication with Zebra devices via HTTP.
    
    Attributes:
        name (str): Device name
        uid (str): Unique device identifier
        connection (str): Connection type (USB, Network, etc)
        deviceType (str): Type of device (printer, scanner)
        version (str): Device firmware version
        provider (str): Device provider/driver
        manufacturer (str): Device manufacturer
    """
    def __init__(self, info):
       self.name = info.get('name')
       self.uid = info.get('uid')
       self.connection = info.get('connection')
       self.deviceType = info.get('deviceType')
       self.version = info.get('version')
       self.provider = info.get('provider')
       self.manufacturer = info.get('manufacturer')

    def get_device_info(self):
        return {
            "name": self.name,
            "uid": self.uid,
            "connection": self.connection,
            "deviceType": self.deviceType,
            "version": self.version,
            "provider": self.provider,
            "manufacturer": self.manufacturer
        }
   
    def send(self, data):
           base_url = "http://host.docker.internal:9100/"
           url = base_url + "write"
           payload = {
               "device" : self.get_device_info(),
               "data": data
           }
           response = requests.post(url, json=payload)
           if response.status_code != 200:
               print(f"Error sending data: {response.text}")

def get_default_zebra_device(device_type="printer", success_callback=None, error_callback=None):
   """Get the default Zebra device of the specified type.
   
   Retrieves the default Zebra printer or scanner device from the Zebra service.
   Makes an HTTP request to get device info and creates a ZebraDevice instance.
   
   Args:
       device_type (str, optional): Type of device to get ("printer" or "scanner"). 
           Defaults to "printer".
       success_callback (callable, optional): Function to call on successful device retrieval.
           Called with the ZebraDevice instance.
       error_callback (callable, optional): Function to call if device retrieval fails.
           Called with error message string.
           
   Returns:
       ZebraDevice: The default device if found, None if not found or error occurs
   """
   base_url = "http://host.docker.internal:9100/"
   url = base_url + "default"
   if device_type is not None:
       url += "?type=" + device_type
   response = requests.get(url)
   if response.status_code == 200:
       device_info = json.loads(response.text)
       this_zebra_device = ZebraDevice(device_info)
       if success_callback is not None:
           success_callback(this_zebra_device)
       return this_zebra_device
   else:
       if error_callback is not None:
           error_callback("Error: Unable to get the default device")
       return None

def print_config_label(this_zebra_device):
   """Print a configuration label using the provided Zebra device.
   
   Sends a ~WC command to print a configuration label if a valid device is provided.
   
   Args:
       this_zebra_device (ZebraDevice): The Zebra printer device to use
   """
   print(this_zebra_device)
   if this_zebra_device is not None:
       this_zebra_device.send("~WC")

def success_callback(this_zebra_device):
   """Handle successful Zebra device retrieval.
   
   Callback function that executes when a Zebra device is successfully retrieved.
   Prints device info to console for debugging/logging purposes.
   
   Args:
       this_zebra_device (ZebraDevice): The successfully retrieved Zebra device
   """
   print("Success callback called with device info:")
   print(this_zebra_device)

def error_callback(error_message):
   """Handle error retrieving Zebra device.
   
   Callback function that executes when Zebra device retrieval fails.
   Prints error message to console for debugging/logging purposes.
   
   Args:
       error_message (str): Description of the error that occurred
   """
   print("Error callback called with message:")
   print(error_message)


# ------------ TEST TOGGLE ------------
SEND_TEST_ZEBRA_PATTERN = False # Set to False to print actual image, True for test pattern
# ------------------------------------
@csrf_exempt
def print_blend_label(request):
    """Print a blend label using Zebra printer.
    # ... (docstring remains the same) ...
    """
    def success_callback_device_only(device):
        logger.info(f"Zebra device acquired: {device}")

    def error_callback_flexible(device_or_error_msg, error_msg_if_two_args=None):
        if error_msg_if_two_args is not None:
            logger.error(f"Zebra device error: {device_or_error_msg}, {error_msg_if_two_args}")
        else:
            logger.error(f"Zebra device/setup error: {device_or_error_msg}")

    this_zebra_device = get_default_zebra_device("printer", 
                                                 success_callback_device_only, 
                                                 error_callback_flexible)

    if not this_zebra_device:
        logger.error("Failed to get default Zebra printer device (returned None).")
        return JsonResponse({'error': 'Printer device not available'}, status=500)
        
    this_zebra_device.send("~JSB") # When in TEAR OFF MODE, we will backfeed the very first label, and only the first label. We will then print the balance of the batch with no backfeed.
    
    zpl_string_to_send = ""

    if SEND_TEST_ZEBRA_PATTERN:
        test_zpl_string = """^XA
            ^LT0
            ^PW1200
            ^FO0,0^GB1200,100,4^FS
            ^XZ"""
        zpl_string_to_send = test_zpl_string
        logger.info(">>> SENDING TEST ZPL PATTERN <<<")
    else:
        label_blob = request.FILES.get('labelBlob')
        if not label_blob:
            logger.error("labelBlob not found in the request (SEND_TEST_ZEBRA_PATTERN is False).")
            return JsonResponse({'error': 'No image blob provided'}, status=400)
            
        image_data = label_blob.read()
        try:
            generated_zpl = ZebrafyImage(image_data, invert=True).to_zpl()
            if "^XA" in generated_zpl:
                if "^LT0" not in generated_zpl:
                    generated_zpl = generated_zpl.replace("^XA", "^XA^LT0", 1)
                if "^PW1200" not in generated_zpl:
                    if "^LT0" in generated_zpl:
                         generated_zpl = generated_zpl.replace("^LT0", "^LT0^PW1200", 1)
                    else:
                         generated_zpl = generated_zpl.replace("^XA", "^XA^PW1200", 1)
            else:
                generated_zpl = f"^XA^LT0^PW1200{generated_zpl}^XZ"

            zpl_string_to_send = generated_zpl

        except Exception as e:
            logger.error(f"Error during ZPL conversion for image: {e}", exc_info=True)
            return JsonResponse({'error': f'ZPL conversion failed: {str(e)}'}, status=500)
        
    label_quantity = int(request.POST.get('labelQuantity', 1)) 
    
    try:
        for i in range(label_quantity):
            this_zebra_device.send(zpl_string_to_send)
        
        log_message_type = "TEST label(s)" if SEND_TEST_ZEBRA_PATTERN else "image label(s)"
        logger.info(f"Successfully sent {label_quantity} {log_message_type} to the printer.")

    except Exception as e:
        logger.error(f"Error sending ZPL to printer: {e}", exc_info=True)
        return JsonResponse({'error': f'Failed to send ZPL to printer: {str(e)}'}, status=500)

    return JsonResponse({'message': f'{label_quantity} {log_message_type} sent to printer successfully.'})


def get_json_lot_number(request):
    """Get lot number information from database.
    
    Retrieves lot number information for an item code from the LotNumRecord model.
    Used to populate lot number fields in forms and displays.
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code to look up
            
    Returns:
        JsonResponse containing either:
            lot_number (str): Lot number for item if found
            error (str): Error message if lookup fails
    """
    print(request.GET.get("encodedItemCode"))
    item_code = get_unencoded_item_code(request.GET.get("encodedItemCode"), 'itemCode')
    try:
        lot_record = LotNumRecord.objects.filter(item_code__iexact=item_code).filter(sage_qty_on_hand__gt=0, sage_qty_on_hand__isnull=False).filter().order_by('date_created').first()
        if lot_record:
            return JsonResponse({'lot_number': lot_record.lot_number})
        else:
            lot_record = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('date_created').first()
            return JsonResponse({'lot_number': lot_record.lot_number})
    except Exception as e:
        return JsonResponse({'error': str(e)})

def get_json_most_recent_lot_records(request):
    """Get most recent lot records for an item.
    
    Retrieves the 10 most recent lot number records for an item code from the LotNumRecord model,
    ordered by creation date descending. Returns the lot numbers and their current quantities
    on hand in Sage.
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code to look up
            
    Returns:
        JsonResponse containing:
            Dict mapping lot numbers to their Sage quantities on hand for the 10 most recent lots
    """
    item_code = get_unencoded_item_code(request.GET.get("encodedItemCode"), 'itemCode')
    if LotNumRecord.objects.filter(item_code__iexact=item_code).exists():
        lot_records = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created')[:10]

    else:
        lot_records = {
            'item_code' : '',
            'item_description'  : '',
            'lot_number' : '',
            'lot_quantity' : '',
            'date_created' : '',
            'line' : '',
            'desk' : '',
            'sage_entered_date' : '',
            'sage_qty_on_hand'  : '',
            'run_date' : '',
            'run_day' : ''
        }
    for lot in lot_records:
        if lot.sage_entered_date == None:
            lot.sage_entered_date = 'Not Entered'
            lot.sage_qty_on_hand = '0'
        print(lot.lot_number + ": " + str(lot.date_created))

    return JsonResponse({lot_record.lot_number : lot_record.sage_qty_on_hand for lot_record in lot_records})

def display_blend_tank_restrictions(request):
    """Display blend tank restrictions page.
    
    Shows current blend tank restrictions and allows adding/editing restrictions.
    Restrictions specify which tanks certain blends can be made in.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with context containing:
            blend_tank_restrictions: QuerySet of BlendTankRestriction objects
            new_restriction_form: Form for adding new restrictions
            
    Template:
        core/blendtankrestrictions.html
    """
    blend_tank_restrictions = BlendTankRestriction.objects.all()
    new_restriction_form = BlendTankRestrictionForm()
    item_codes = blend_tank_restrictions.values_list('item_code', flat=True)
    item_descriptions = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__in=item_codes)}
    for restriction in blend_tank_restrictions:
        restriction.item_description = item_descriptions.get(restriction.item_code, "")

    context = { 'blend_tank_restrictions' : blend_tank_restrictions, 'new_restriction_form' : new_restriction_form }
    
    return render(request, 'core/blendtankrestrictions.html', context)

def add_blend_tank_restriction(request):
    """Add a new blend tank restriction.
    
    Creates a new BlendTankRestriction record from submitted form data.
    
    Args:
        request: HTTP POST request containing form data
        
    Returns:
        JsonResponse with:
            result: 'success' if saved successfully, error message if failed
    """
    response = {}
    try:
        new_restriction_form = BlendTankRestrictionForm(request.POST)
        if new_restriction_form.is_valid():
            new_restriction_form.save()
    except Exception as e:
        response = { 'result' : str(e) }
    
    if not response:
        response = { 'result' : 'success' } 

    return JsonResponse(response, safe=False)

def get_json_blend_tank_restriction(request):
    """Get blend tank restriction data in JSON format.
    
    Retrieves blend tank restriction data for a specific item code and returns it
    as JSON. The item code can be looked up by either direct code or description.
    
    Args:
        request: HTTP GET request containing:
            lookup-type (str): Type of lookup ('item-code' or 'item-desc')
            item (str): Item code or description to look up
            
    Returns:
        JsonResponse containing:
            result (str): Error message if lookup failed
            blend_restriction (obj): BlendTankRestriction object if found
    """
    response = {}
    lookup_type = request.GET.get('lookup-type', 0)
    lookup_value = request.GET.get('item', 0)
    item_code = get_unencoded_item_code(lookup_value, lookup_type)
    try:
        blend_restriction = BlendTankRestriction.objects.get(item_code__iexact=item_code)
    except Exception as e:
        response = { 'result' : str(e) }
    
    if not response:
        response = { 'blend_restriction' : blend_restriction } 

    return JsonResponse(response, safe=False)

def delete_blend_tank_restriction(request):
    """Delete blend tank restrictions.
    
    Deletes one or more blend tank restrictions based on their primary keys.
    
    Args:
        request: HTTP GET request containing:
            list (str): Comma-separated list of restriction primary keys to delete
            
    Returns:
        None
    """
    pk_list = request.GET.get("list")
    blend_tank_restriction_list = list(pk_list.replace('[', '').replace(']', '').replace('"', '').split(","))

    for restriction in blend_tank_restriction_list:
        this_restriction = BlendTankRestriction.objects.get(pk=restriction)
        this_restriction.delete()

def display_test_page(request):
    """Display test page for blend component usage analysis.
    
    Renders a test page showing blend component usage data for a hardcoded item.
    Used for testing and debugging the get_relevant_blend_runs function.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with blend usage test data
        
    Template:
        core/testpage.html
    """
    item_code = '602001'
    item_quantity = 1500
    start_time = 0.0
    blend_subcomponent_usage = get_relevant_blend_runs(item_code, item_quantity, start_time)
    item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc

    return render(request, 'core/testpage.html', {'blend_subcomponent_usage' : blend_subcomponent_usage,
                                                  'item_code' : item_code,
                                                  'item_description' : item_description})

def get_json_all_blend_qtyperbill(request):
    """Get JSON response containing blend quantities per bill.
    
    Retrieves all blend bill of materials records and returns a JSON mapping of
    item codes to their adjusted quantities per bill (quantity * foam factor).
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing:
            Dict mapping item codes to adjusted quantities per bill
    """
    blend_bills_of_materials = BillOfMaterials.objects \
        .filter(component_item_description__startswith='BLEND')

    response = { item.item_code : item.qtyperbill * item.foam_factor for item in blend_bills_of_materials }

    return JsonResponse(response, safe=False)

def get_transactions_for_bom_check():
    """Get transactions for bill of materials quantity checking.
    
    Retrieves transactions from the database where ingredient quantities used in blends
    deviate significantly from expected amounts based on bill of materials. Specifically:
    
    - Looks at 'BI' and 'BR' transactions
    - Filters for ingredients that are Blends, Chemicals, or Fragrances
    - Flags transactions where actual quantity differs from expected by >25%
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

def display_blend_ingredient_quantity_checker(request):
    """Display page for checking blend ingredient quantities.
    
    Shows a table of blend ingredient transactions that have quantities outside 
    expected ranges based on bill of materials. Helps identify potential issues
    with blend ingredient usage.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with matching transactions data
        
    Template:
        core/blendingredientquantitychecker.html
    """
    matching_transactions = get_transactions_for_bom_check()
    return render(request, 'core/blendingredientquantitychecker.html', {'matching_transactions' : matching_transactions})

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

def display_missing_audit_groups(request):
    """Display a form for adding missing audit groups.

    Retrieves items that don't have audit groups assigned and displays them in a
    formset for bulk creation. Filters can be applied via the 'filterString' GET parameter.

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with formset for creating audit groups
    """
    filter_string = request.GET.get('filterString', 'all')
    # Fetch item codes that are not in AuditGroup
    missing_items = get_relevant_ci_item_itemcodes(filter_string)
    AuditGroupFormSet = modelformset_factory(AuditGroup, form=AuditGroupForm, extra=len(missing_items))
    
    if request.method == 'POST':
        formset = AuditGroupFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            # Redirect or indicate success as needed
            return render(request, 'core/auditgroupsuccess.html')
    else:
        # Prepopulate the formset with missing items
        formset_initial_data = [{'item_code': item[0], 'item_description' : item[1], 'counting_unit' : item[2]} for item in missing_items]
        audit_group_formset = AuditGroupFormSet(queryset=AuditGroup.objects.none(), initial=formset_initial_data)
    
    return render(request, 'core/missingauditgroups.html', {'audit_group_formset': audit_group_formset, 'missing_items' : missing_items})

def display_raw_material_label(request):
    """
    Renders a template for printing raw material labels with today's date.
    Used for labeling incoming raw materials with receipt date.

    """
    today_date = dt.datetime.now()

    return render(request, 'core/rawmateriallabel.html', {'today_date' : today_date})

def display_flush_tote_label(request):
    """
    Renders the flush tote label template for printing labels.
    """
    return render(request, 'core/flushtotelabel.html')


def display_attendance_report(request):
    """Display filtered attendance records based on date range and employee name.
    
    Retrieves and filters attendance records by date range and employee name.
    Calculates attendance metrics and formats data for display.
    
    Args:
        request: HTTP request containing optional query parameters:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            employee (str): Employee name to filter by
            show_tardy (str): Filter to show only tardy records
            show_absent (str): Filter to show only absent records
            
    Returns:
        Rendered template with:
            records: Paginated attendance records
            employee_names: List of unique employee names
            weekday_dates: List of weekdays in date range
            metrics: Attendance metrics for filtered records
            filter parameters: Applied start_date, end_date, employee, show_tardy, show_absent
    """
    records = AttendanceRecord.objects.all()
    
    # Apply date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Get list of unique employee names
    employee_names = records.values_list('employee_name', flat=True).distinct().order_by('employee_name')

    if start_date:
        records = records.filter(punch_date__gte=start_date)
    if end_date:
        records = records.filter(punch_date__lte=end_date)
        
    # Apply employee name filter    
    employee = request.GET.get('employee')
    if employee and not employee=='All Employees':
        records = records.filter(employee_name__iexact=employee)

    # Apply tardy/absence filters
    status_filter = request.GET.get('status_filter')
    if status_filter == 'only_tardies':
        records = records.filter(tardy=True)
    elif status_filter == 'only_absences':
        records = records.filter(absent=True)
    elif status_filter == 'no_tardies':
        records = records.filter(tardy=False)
    elif status_filter == 'no_absences':
        records = records.filter(absent=False)

    show_excused = request.GET.get('show_excused')
    if show_excused == 'yes':
        records = records.filter(excused=True)
    elif show_excused == 'no':
        records = records.filter(excused=False)

    # Calculate metrics for filtered records
    metrics = {
        'total_absences': records.filter(absent=True).count(),
        'total_tardies': records.filter(tardy=True).count(),
        'excused_absences': records.filter(absent=True, excused=True).count(),
        'unexcused_absences': records.filter(absent=True, excused=False).count()
    }
        
    # Order by most recent first, then employee name
    records = records.order_by('-punch_date', 'employee_name')
    
    # Paginate results
    paginator = Paginator(records, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'records': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'employee': employee,
        'employee_names': employee_names,
        'metrics': metrics,
        'status_filter': status_filter,
        'show_excused': show_excused
    }
    
    return render(request, 'core/attendancereport.html', context)

from django.db.models import F, Func, Value
from django.db.models.functions import Lead, Lag
from .models import TankLevelLog

def display_tank_level_change_report(request):
    selected_tank = request.GET.get('tank')

    # Get date range filters from request
    # start_date = request.GET.get('start_date')
    # end_date = request.GET.get('end_date')

    # Build date filter conditions
    # date_filter = ""
    # params = [selected_tank]
    # if start_date:
    #     date_filter += " AND timestamp >= %s"
    #     params.append(start_date)
    # if end_date:
    #     date_filter += " AND timestamp <= %s" 
    #     params.append(end_date)
    sql_query = """
        WITH previous_levels AS (
            SELECT 
                id,
                tank_name,
                timestamp,
                filled_gallons,
                LAG(filled_gallons) OVER (
                    PARTITION BY tank_name 
                    ORDER BY timestamp
                ) as previous_volume
            FROM core_tanklevellog
            where tank_name = %s
        ) SELECT 
            tank_name,
            timestamp,
            filled_gallons,
            previous_volume,
            (filled_gallons - previous_volume) as volume_change
        FROM previous_levels
        WHERE 
            ABS(filled_gallons - previous_volume) > 10
            AND previous_volume IS NOT NULL
            ORDER BY timestamp DESC;
    """
    records = []
    with connection.cursor() as cursor:
        cursor.execute(sql_query, [selected_tank])
        if selected_tank:
            for row in cursor.fetchall():
                records.append({
                    'tank_name': row[0],
                    'timestamp': row[1],
                    'current_volume': row[2],
                    'prev_reading': row[3],
                    'volume_change': row[4]
                })

    # Convert query results to list of dictionaries for template
    
    # Get unique dates from records
    dates = []
    for record in records:
        record_date = record['timestamp'].date()
        if record_date not in dates:
            dates.append(record_date)
    dates.sort(reverse=True)

    # Calculate daily volume change totals
    daily_totals = []
    for date in dates:
        daily_total = 0
        for record in records:
            if record['timestamp'].date() == date:
                daily_total += record['volume_change']
        daily_totals.append({
            'date': date,
            'total_change': daily_total
        })
    
    # Get item code from StorageTank for selected tank
    tank_item_code = None
    if selected_tank:
        try:
            tank = StorageTank.objects.filter(tank_label_kpk=f"TANK {selected_tank}").first()
            tank_item_code = tank.item_code
        except StorageTank.DoesNotExist:
            pass
    
    # Get BI transactions for each date
    daily_bi_transactions = []
    if tank_item_code:
        for date in dates:
            sql = """
                SELECT COALESCE(SUM(transactionqty), 0) 
                FROM im_itemtransactionhistory 
                WHERE itemcode = %s
                AND transactioncode = 'BI'
                AND CAST(transactiondate AS DATE) = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(sql, [tank_item_code, date])
                bi_total = cursor.fetchone()[0]
                daily_bi_transactions.append({
                    'date': date,
                    'bi_total': bi_total
                })

    # Combine daily totals and BI transactions into single list
    combined_daily_data = []
    for total, bi in zip(daily_totals, daily_bi_transactions):
        combined_daily_data.append({
            'date': total['date'],
            'total_change': total['total_change'],
            'bi_total': bi['bi_total']
    })

    # Add daily totals and BI transactions to each record
    for record in records:
        record_date = record['timestamp'].date()
        # Find matching daily total and BI data
        for daily_data in combined_daily_data:
            if daily_data['date'] == record_date:
                record['daily_total'] = daily_data['total_change']
                record['daily_bi'] = daily_data['bi_total']
                break

    # Get unique tank list for dropdown
    tanks = TankLevelLog.objects.values_list('tank_name', flat=True).distinct().order_by('tank_name')
    
    context = {
        'tanks': tanks,
        'selected_tank': selected_tank,
        'records': records,
    }
    
    return render(request, 'core/reports/tanklevelchangereport.html', context)

def get_daily_tank_values(request):
    """Get the last tank level entry for each day over a specified period.
    
    Retrieves the most recent tank level reading for each day over the past N days
    for a specified tank. Orders results with most recent entries first.

    Args:
        request: HTTP request object
        tank_name (str): Tank identifier (default 'L')
        days (int): Number of days to look back (default 30)

    Returns:
        JsonResponse containing list of daily tank readings
    """

    sql = """
        WITH daily_last_entries AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY DATE(timestamp) ORDER BY timestamp DESC) as rn
            FROM core_tanklevellog ct 
            WHERE tank_name = %s
            AND timestamp >= CURRENT_DATE - INTERVAL '%s days'
        )
        SELECT * FROM daily_last_entries 
        WHERE rn = 1
        ORDER BY timestamp DESC;
    """

    # Get tank name and days parameters from request, with defaults
    tank_name = request.GET.get('tank_name')
    days = request.GET.get('days', 30)
    
    with connection.cursor() as cursor:
        cursor.execute(sql, [tank_name, days])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
        
    return JsonResponse({'tank_readings': results})

@login_required
def trigger_looper_restart(request):
    """ 
    Receives a request from the frontend (Loop Status page button) and 
    triggers the restart of the data looper by calling the local HTTPS 
    endpoint of the PYSTRAY service running on the host machine.
    """
    if request.method == 'GET':
        target_url = "https://host.docker.internal:9999/trigger-restart"
        
        try:
            logger.info(f"Attempting to trigger restart via: {target_url}")
            # Make the request to the local systray service
            # verify=False is necessary because the cert is likely self-signed
            # or issued for a different name (e.g., host IP) than 127.0.0.1
            response = requests.get(target_url, verify=False, timeout=5) 
            
            # Check if the systray service responded successfully (e.g., 200 OK)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            logger.info(f"Successfully triggered restart service. Response: {response.status_code}")
            return JsonResponse({'status': 'success', 'message': 'Restart triggered successfully.'})
            
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection Error calling restart service at {target_url}: {conn_err}")
            return JsonResponse({'status': 'error', 'message': 'Could not connect to the restart service. Is it running?'}, status=503) # Service Unavailable
        except requests.exceptions.Timeout as timeout_err:
             logger.error(f"Timeout calling restart service at {target_url}: {timeout_err}")
             return JsonResponse({'status': 'error', 'message': 'Connection to restart service timed out.'}, status=504) # Gateway Timeout
        except requests.exceptions.RequestException as req_err:
            # Catch other potential request errors (like SSL errors if verify=True was used, etc.)
            logger.error(f"Error calling restart service at {target_url}: {req_err}")
            return JsonResponse({'status': 'error', 'message': f'An error occurred contacting the restart service: {req_err}'}, status=500)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in trigger_looper_restart view: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
            
    else:
        # Only GET is allowed for this endpoint
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405) # Method Not Allowed
    
def get_pystray_service_status(request):
    pystray_status_url = 'https://host.docker.internal:9999/service-status' 
    try:
        # Note: verify=False is necessary if the service uses a self-signed cert
        # Allow network requests to fail fast if service isn't running
        response = requests.get(pystray_status_url, timeout=2, verify=False) 
        response.raise_for_status() # Check for HTTP errors (4xx or 5xx)
        
        # Forward the exact JSON response from the pystray service
        pystray_data = response.json() 
        return JsonResponse(pystray_data)

    except requests.exceptions.Timeout:
        # Log sparingly for expected timeouts when service is off
        logger.debug(f"Timeout connecting to PySTray service at {pystray_status_url} (likely stopped)")
        return JsonResponse({'status': 'stopped', 'reason': 'timeout'}, status=504) # Gateway timeout
    except requests.exceptions.ConnectionError:
        # Log sparingly for expected connection errors when service is off
        logger.debug(f"Connection refused by PySTray service at {pystray_status_url} (likely stopped)")
        return JsonResponse({'status': 'stopped', 'reason': 'connection_refused'}, status=502) # Bad Gateway
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting PySTray status from {pystray_status_url}: {e}")
        return JsonResponse({'status': 'error', 'reason': 'request_exception', 'details': str(e)}, status=500)
    except json.JSONDecodeError:
         logger.error(f"Failed to decode JSON response from {pystray_status_url}")
         return JsonResponse({'status': 'error', 'reason': 'json_decode_error'}, status=500)
    
def cache_health(request):
    cache.set("cache_ping", "pong", 2)
    return JsonResponse({"status": cache.get("cache_ping") == "pong"})

def display_all_tote_classifications(request):
    """
    Display all tote classifications from the ToteClassification model.
    """
    tote_classifications = ToteClassification.objects.all().order_by('item_code')
    # Create a form instance for adding new tote classifications
    new_form = ToteClassificationForm()
    
    if request.method == 'POST':
        form = ToteClassificationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('display_all_tote_classifications')
    
    context = {
        'tote_classifications': tote_classifications,
        'form' : new_form,
        'title': 'Tote Classifications'
    }
    
    return render(request, 'core/toteclassifications.html', context)

def create_tote_classification(request):
    """
    Create a new tote classification.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_code = data.get('item_code')
            tote_classification = data.get('tote_classification')
            
            if not item_code or not tote_classification:
                return JsonResponse({'status': 'error', 'message': 'Item code and tote classification are required.'}, status=400)
            
            # Check if a classification already exists for this item code
            if ToteClassification.objects.filter(item_code=item_code).exists():
                return JsonResponse({'status': 'error', 'message': 'A classification already exists for this item code.'}, status=409)
            
            # Create new tote classification
            new_classification = ToteClassification.objects.create(
                item_code=item_code,
                tote_classification=tote_classification
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Tote classification created successfully.',
                'data': {
                    'id': new_classification.id,
                    'item_code': new_classification.item_code,
                    'tote_classification': new_classification.tote_classification
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            logger.error(f"Error creating tote classification: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

def get_tote_classification(request, item_code=None):
    """
    Get a specific tote classification by item_code or all classifications if no item_code is provided.
    """
    if request.method == 'GET':
        try:
            if item_code:
                # Get specific tote classification
                try:
                    classification = ToteClassification.objects.get(item_code=item_code)
                    return JsonResponse({
                        'status': 'success',
                        'data': {
                            'id': classification.id,
                            'item_code': classification.item_code,
                            'tote_classification': classification.tote_classification
                        }
                    })
                except ToteClassification.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Tote classification not found.'}, status=404)
            else:
                # Get all tote classifications
                classifications = ToteClassification.objects.all().order_by('item_code')
                data = [{
                    'id': c.id,
                    'item_code': c.item_code,
                    'tote_classification': c.tote_classification
                } for c in classifications]
                
                return JsonResponse({
                    'status': 'success',
                    'data': data
                })
                
        except Exception as e:
            logger.error(f"Error retrieving tote classification(s): {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

def update_tote_classification(request, item_code):
    """
    Update an existing tote classification.
    """
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            tote_classification = data.get('tote_classification')
            
            if not tote_classification:
                return JsonResponse({'status': 'error', 'message': 'Tote classification is required.'}, status=400)
            
            try:
                classification = ToteClassification.objects.get(item_code=item_code)
                classification.tote_classification = tote_classification
                classification.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Tote classification updated successfully.',
                    'data': {
                        'id': classification.id,
                        'item_code': classification.item_code,
                        'tote_classification': classification.tote_classification
                    }
                })
            except ToteClassification.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Tote classification not found.'}, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            logger.error(f"Error updating tote classification: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

def delete_tote_classification(request, item_code):
    """
    Delete a tote classification.
    """
    if request.method == 'DELETE':
        try:
            try:
                classification = ToteClassification.objects.get(item_code=item_code)
                classification.delete()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Tote classification deleted successfully.'
                })
            except ToteClassification.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Tote classification not found.'}, status=404)
                
        except Exception as e:
            logger.error(f"Error deleting tote classification: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)


@login_required
@csrf_exempt # Assuming AJAX POST, consider CSRF protection if forms are used
def print_blend_sheet(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_code = data.get('item_code')
            lot_number = data.get('lot_number')
            lot_quantity = data.get('lot_quantity')

            if not all([item_code, lot_number, lot_quantity]):
                return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)

            # Forward the request to the local Pystray service
            # Ensure this URL and port match your Pystray service configuration
            pystray_service_url = 'http://localhost:8090/print' 
            payload = {
                'item_code': item_code,
                'lot_number': lot_number,
                'lot_quantity': lot_quantity
            }
            
            try:
                # Adjust timeout as needed
                response = requests.post(pystray_service_url, json=payload, timeout=30) 
                response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
                
                # Assuming the pystray service returns JSON
                pystray_response_data = response.json()
                return JsonResponse(pystray_response_data)

            except requests.exceptions.RequestException as e:
                # Log the error e
                return JsonResponse({'status': 'error', 'message': f'Failed to communicate with print service: {str(e)}'}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            # Log the error e
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

if not logging.getLogger(__name__).hasHandlers():
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
def trigger_excel_macro_execution(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            macro_to_run = data.get('macro_to_run')
            data_for_macro = data.get('data_for_macro')

            if not macro_to_run or data_for_macro is None:
                return JsonResponse({'status': 'error', 'message': "'macro_to_run' or 'data_for_macro' is required."}, status=400)

            lot_num_record_instance = None
            components_for_pick_sheet = []

            if macro_to_run in ["blndSheetGen", "generateProductionPackage"]:
                if len(data_for_macro) >= 6:
                    lot_number_from_data = data_for_macro[1]
                    item_code_from_data = data_for_macro[5]
                    try:
                        lot_num_record_instance = LotNumRecord.objects.get(lot_number=lot_number_from_data, item_code=item_code_from_data)
                    except (LotNumRecord.DoesNotExist, LotNumRecord.MultipleObjectsReturned):
                        pass

            if macro_to_run == "generateProductionPackage":
                if len(data_for_macro) >= 6:
                    blend_item_code = str(data_for_macro[5])
                    bom_items = BillOfMaterials.objects.filter(item_code__iexact=blend_item_code)
                    
                    for bom_item in bom_items:
                        component_code = bom_item.component_item_code
                        component_desc = bom_item.component_item_description
                        component_item_location = "Location N/A"
                        
                        try:
                            location_record = ItemLocation.objects.filter(item_code__iexact=component_code).first()
                            if location_record:
                                component_item_location = location_record.zone
                        except Exception:
                            pass

                        components_for_pick_sheet.append({
                            'componentItemCode': component_code,
                            'componentItemDesc': component_desc,
                            'componentItemLocation': component_item_location
                        })
            
            redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
            job_id = str(uuid.uuid4())
            
            job_data = {
                'id': job_id,
                'macro_to_run': macro_to_run,
                'data_for_macro': data_for_macro,
                'user_id': request.user.id,
                'created_at': dt.datetime.now().isoformat(),
                'status': 'queued',
                'lot_num_record_id': lot_num_record_instance.pk if lot_num_record_instance else None,
                'lot_number': lot_num_record_instance.lot_number if lot_num_record_instance else None,
                'item_code': lot_num_record_instance.item_code if lot_num_record_instance else None,
                'line': lot_num_record_instance.line if lot_num_record_instance else None
            }
            
            if macro_to_run == "generateProductionPackage":
                job_data['components_for_pick_sheet'] = components_for_pick_sheet
            
            # Push to queue
            redis_client.lpush('excel_macro_queue', json.dumps(job_data))
            redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))
            
            return JsonResponse({
                'status': 'queued',
                'job_id': job_id,
                'message': f'{macro_to_run} job queued successfully'
            })

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST requests allowed.'}, status=405)
    
def check_excel_job_status(request, job_id):
    """Check status of an Excel macro job.
    
    Retrieves job status from Redis queue system.
    
    Args:
        request: HTTP request object
        job_id: UUID of the job to check
        
    Returns:
        JsonResponse with job status data
    """
    try:
        redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        job_data = redis_client.hget('excel_macro_jobs', job_id)
        
        if job_data:
            return JsonResponse(json.loads(job_data))
        else:
            return JsonResponse({'status': 'not_found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


async def get_active_formula_change_alerts(request):
    """
    Asynchronously retrieves active formula change alerts.
    Returns a JSON list of objects, each containing:
    - ingredient_item_code
    - notification_trigger_quantity
    - parent_item_codes (the list of parent items this alert applies to)
    """
    try:
        
        alerts_data = []
        # Since is_active was removed, we fetch all.
        # If is_active is ever re-introduced, filter here: FormulaChangeAlert.objects.filter(is_active=True)
        for alert in FormulaChangeAlert.objects.all():
            alerts_data.append({
                'ingredient_item_code': alert.ingredient_item_code,
                'notification_trigger_quantity': alert.notification_trigger_quantity,
                'parent_item_codes': alert.parent_item_codes 
            })

        
        return JsonResponse({'alerts_data': alerts_data})
    except Exception as e:
        # Log the exception e
        return JsonResponse({'error': str(e)}, status=500)
    

def get_json_all_tote_classifications(request):
    """
    Retrieves all tote classification objects and returns them as a JSON response,
    formatted as a dictionary keyed by item_code.
    """
    if request.method == 'GET':
        try:
            classifications = ToteClassification.objects.all()
            data_map = {}
            if classifications.exists():
                for classification in classifications:
                    data_map[classification.item_code] = {
                        'tote_classification': classification.tote_classification,
                        'hose_color': classification.hose_color,
                        # Add any other fields from ToteClassification model you might need
                    }
                return JsonResponse(data_map)
            else:
                # Return an empty object if no classifications are found,
                # as the frontend JS seems to expect an object.
                return JsonResponse({})
        except Exception as e:
            logger.error(f"Error in get_json_all_tote_classifications: {e}", exc_info=True)
            return JsonResponse({'error': 'An error occurred while fetching tote classifications.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method. Only GET is allowed.'}, status=405)