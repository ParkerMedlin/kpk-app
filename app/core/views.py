import urllib
import math
import datetime as dt
import time
from datetime import date
import pytz
from django.db import connection
import json
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core.paginator import Paginator
from django.conf import settings
import base64
from core.models import *
from prodverse.models import *
from core.forms import *
from prodverse.forms import *
from django.db.models import Sum, Subquery, OuterRef, Q, CharField, Max, F
from core import taskfunctions
from .forms import FeedbackForm
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from django.template.loader import get_template
import os
from django.views.decorators.csrf import csrf_exempt
import requests
from PIL import Image
import io
import sys
from .zebrafy_image import ZebrafyImage
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

advance_blends = ['602602','602037US','602011','602037EUR','93700.B','94700.B','93800.B','94600.B','94400.B','602067']

def get_json_forklift_serial(request):
    if request.method == "GET":
        forklift_unit_number = request.GET.get('unit-number', 0)
        forklift = Forklift.objects.get(unit_number=forklift_unit_number)
    return JsonResponse(forklift.serial_no, safe=False)

def generate_next_lot_number():
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    
    # Get the latest lot number
    latest_lot = LotNumRecord.objects.latest('id').lot_number
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

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def display_attendance_records(request):
    # Get all attendance records
    attendance_records = AttendanceRecord.objects.all().order_by('-punch_date', 'employee_name')

    context = {
        'attendance_records': attendance_records
    }

    return render(request, 'core/attendance_records.html', context)

def display_forklift_checklist(request):
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

    all_item_codes = list(set(desk_one_item_codes) | set(desk_two_item_codes))
    lot_quantities = { lot.lot_number : lot.lot_quantity for lot in LotNumRecord.objects.filter(item_code__in=all_item_codes) }
    
    bom_objects = BillOfMaterials.objects.filter(item_code__in=component_item_codes)

    component_shortage_queryset = SubComponentShortage.objects \
        .filter(component_item_code__in=component_item_codes)
    if component_shortage_queryset.exists():
        subcomponentshortage_item_code_list = list(component_shortage_queryset.distinct('component_item_code').values_list('component_item_code', flat=True))
        component_shortages_exist = True
    else:
        component_shortages_exist = False

    for blend in blend_shortages_queryset:
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
        if blend.component_item_code in desk_one_item_codes:
            this_lot_number = desk_one_queryset.filter(item_code__iexact=blend.component_item_code).first().lot
            lot_quantity = lot_quantities[this_lot_number]
            blend.schedule_value = f'Desk_1: {lot_quantity}'
        elif blend.component_item_code in desk_two_item_codes:
            this_lot_number = desk_two_queryset.filter(item_code__iexact=blend.component_item_code).first().lot
            lot_quantity = lot_quantities[this_lot_number]
            blend.schedule_value = f'Desk_2: {lot_quantity}'
        else:
            blend.schedule_value = 'Not Scheduled'
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
        
    submitted = False
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()

    add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number':next_lot_number, 'date_created':today,})
    
    # Fetch the latest transaction date for each item code
    today = dt.datetime.now().date()
    rare_date = today - dt.timedelta(days=179)
    epic_date = today - dt.timedelta(days=359)

    return render(request, 'core/blendshortages.html', {
        'blend_shortages_queryset': blend_shortages_queryset,
        'foam_factor_is_populated' : foam_factor_is_populated,
        'submitted' : submitted,
        'add_lot_form' : add_lot_form,
        'latest_transactions_dict': latest_transactions_dict,
        'rare_date' : rare_date,
        'epic_date' : epic_date })

def add_lot_num_record(request):
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
            # this_lot_record = LotNumRecord.objects.get(lot_number=new_lot_submission)

            # this_blend_sheet_template = BlendSheetTemplate.objects.get(item_code=new_lot_submission.item_code)

            # this_lot_blend_sheet = this_blend_sheet_template.blend_sheet_template
            # this_lot_blend_sheet['lot_number'] = new_lot_submission.lot_number
            # this_lot_blend_sheet['total_weight'] = new_lot_submission.lot_quantity * this_lot_blend_sheet['lbs_per_gallon']

            # need to set quantities and date here
            # new_blend_sheet = BlendSheet(lot_number = this_lot_record,
            #                              blend_sheet = this_blend_sheet_template.blend_sheet_template
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
    items_to_delete_bytestr = base64.b64decode(records_to_delete)
    items_to_delete_str = items_to_delete_bytestr.decode()
    items_to_delete_list = list(items_to_delete_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    
    for item in items_to_delete_list:
        lot_number = LotNumRecord.objects.get(pk=item).lot_number
        selected_lot = LotNumRecord.objects.get(pk=item)
        selected_lot.delete()
        try:
            selected_schedule_item = DeskOneSchedule.objects.get(lot__iexact=lot_number)
            selected_schedule_item.delete()
        except DeskOneSchedule.DoesNotExist as e:
            print(str(e))
            print(f'Error processing lot {lot_number}')
            continue
        try:
            selected_schedule_item = DeskTwoSchedule.objects.get(lot__iexact=lot_number)
            selected_schedule_item.delete()
        except DeskTwoSchedule.DoesNotExist as e:
            print(str(e))
            print(f'Error processing lot {lot_number}')
            continue

    return redirect('display-lot-num-records')

def display_lot_num_records(request):
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

    lot_num_queryset = LotNumRecord.objects.order_by('-id')
    for lot in lot_num_queryset:
        item_code_str_bytes = lot.item_code.encode('UTF-8')
        encoded_item_code_str_bytes = base64.b64encode(item_code_str_bytes)
        encoded_item_code = encoded_item_code_str_bytes.decode('UTF-8')
        lot.encoded_item_code = encoded_item_code

    lot_num_paginator = Paginator(lot_num_queryset, 50)
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
    if request.method == "POST":
        request.GET.get('edit-yes-no', 0)
        lot_num_record = get_object_or_404(LotNumRecord, id = lot_num_id)
        edit_lot_form = LotNumRecordForm(request.POST or None, instance=lot_num_record, prefix='editLotNumModal')

        if edit_lot_form.is_valid():
            edit_lot_form.save()

        return HttpResponseRedirect('/core/lot-num-records')
    
def update_foam_factor(request, foam_factor_id):
    if request.method == "POST":
        print(foam_factor_id)
        request.GET.get('edit-yes-no', 0)
        foam_factor = get_object_or_404(FoamFactor, id = foam_factor_id)
        edit_foam_factor = FoamFactorForm(request.POST or None, instance=foam_factor, prefix='editFoamFactorModal')

        if edit_foam_factor.is_valid():
            edit_foam_factor.save()

        return HttpResponseRedirect('/core/foam-factors')

def delete_foam_factor(request, foam_factor_id):
    try:
        foam_factor_to_delete = FoamFactor.objects.get(pk=foam_factor_id)
        foam_factor_to_delete.delete()
    except Exception as e:
        print(str(e))

    return redirect('display-foam-factors')

def display_foam_factors(request):
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
    duplicates = request.GET.get('duplicates', 0)

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

def display_all_item_locations(request):
    chemical_locations = ItemLocation.objects.all()
    component_item_codes = chemical_locations.values_list('component_item_code', flat=True)

    # Query BillOfMaterials objects once and create a dictionary mapping component item codes to lists of (qtyonhand, standard_uom) tuples
    bom_data = {}
    for bom in BillOfMaterials.objects.filter(component_item_code__in=component_item_codes):
        if bom.component_item_code not in bom_data:
            bom_data[bom.component_item_code] = []
        bom_data[bom.component_item_code].append((bom.qtyonhand, bom.standard_uom))

    for item in chemical_locations:
        bom_info_list = bom_data.get(item.component_item_code, [])
        if bom_info_list:
            # Here you'll need to decide how to handle multiple BillOfMaterials objects for the same component_item_code
            # For example, you might want to sum the qtyonhand and take the first standard_uom
            item.qtyonhand = sum(info[0] for info in bom_info_list)
            item.standard_uom = bom_info_list[0][1]
        else:
            print(f"No BillOfMaterials object found for component_item_code: {item.component_item_code}")
            continue

    return render(request, 'core/allItemLocations.html', {'chemical_locations': chemical_locations})

def add_lot_to_schedule(this_lot_desk, add_lot_form):
    if this_lot_desk == 'Desk_1':
        max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskOneSchedule(
            item_code = add_lot_form.cleaned_data['item_code'],
            item_description = add_lot_form.cleaned_data['item_description'],
            lot = add_lot_form.cleaned_data['lot_number'],
            blend_area = add_lot_form.cleaned_data['desk'],
            order = max_number + 1
            )
        new_schedule_item.save()
    if this_lot_desk == 'Desk_2':
        max_number = DeskTwoSchedule.objects.aggregate(Max('order'))['order__max']
        if not max_number:
            max_number = 0
        new_schedule_item = DeskTwoSchedule(
            item_code = add_lot_form.cleaned_data['item_code'],
            item_description = add_lot_form.cleaned_data['item_description'],
            lot = add_lot_form.cleaned_data['lot_number'],
            blend_area = add_lot_form.cleaned_data['desk'],
            order = max_number + 1
            )
        new_schedule_item.save()

@login_required
def display_blend_sheet(request):
    # This function does not retrieve the blendsheet information
    # because that json is fetched directly by the javascript on
    # the page.
    
    if request.method == 'POST':
        data = json.loads(request.body)
        this_lot_number = LotNumRecord.objects.get(lot_number__iexact=data['lot_number'])
        this_blend_sheet = BlendSheet.objects.get(lot_number=this_lot_number)
        this_blend_sheet.blend_sheet = data
        this_blend_sheet.save()
        return JsonResponse({'status': 'success'})

    user_full_name = request.user.get_full_name()

    return render(request, 'core/blendsheet.html', {'user_full_name'  : user_full_name})

def get_json_blend_sheet(request, lot_number):
    this_lot_record = LotNumRecord.objects.get(lot_number=lot_number)
    this_blend_sheet = BlendSheet.objects.get(lot_number=this_lot_record.id)
    response_item = this_blend_sheet.blend_sheet

    return JsonResponse(response_item, safe=False)

def display_conf_blend_sheet_complete(request):
    return render(request, 'core/blendsheetcomplete.html')

def display_blend_run_order(request):
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
    return render(request, 'core/reportcenter.html', {})

def get_lot_number_quantities(item_code):
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

        # im_itemcost_queryset = ImItemCost.objects.filter(itemcode__iexact=item_code)
        # for lot in current_page:
        #     if im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).exists():
        #         total_qty_so_far = float(0.0000)
        #         for item in im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number):
        #             print(item.quantityonhand)
        #             total_qty_so_far = total_qty_so_far + float(item.quantityonhand)
        #             print(lot.lot_number + ' ' + str(total_qty_so_far))
        #         lot.qty_on_hand = round(total_qty_so_far,4)
        #         lot.date_entered = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().transactiondate)
        #     else:
        #         lot.qty_on_hand = None
        #         lot.date_entered = None
        # if lot_num_queryset.exists():
        #     item_description = lot_num_queryset.first().item_description
        # else:
        #     no_lots_found = True
        #     item_description = ''
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
            item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
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
    now = dt.date.today()
    delta = (requireddate - now)
    print(delta)
    # total_hours = 0

    # for i in range(delta + 1):
    #     total_hours += 10

    weekend_days = count_weekend_days(now, requireddate)

    return (delta.days - weekend_days) * 10

def count_weekend_days(start_date, end_date):
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
    for scheduled_blend in DeskOneSchedule.objects.all():
        if scheduled_blend.item_code == 'INVENTORY':
            continue
        if ImItemCost.objects.filter(receiptno__iexact=scheduled_blend.lot).exists():
            scheduled_blend.delete()
    for scheduled_blend in DeskTwoSchedule.objects.all():
        if scheduled_blend.item_code == 'INVENTORY':
            continue
        if ImItemCost.objects.filter(receiptno__iexact=scheduled_blend.lot).exists():
            scheduled_blend.delete()

    submitted=False
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()

    blend_area = request.GET.get('blend-area')

    if request.method == "POST":
        add_lot_num_record(request)
        return HttpResponseRedirect('/core/lot-num-records')
    else:
        add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number': next_lot_number, 'date_created':today,})
        if 'submitted' in request.GET:
            submitted=True

    areas_list = ['Desk_1','Desk_2','Hx','Dm','Totes']
    blend_schedule_querysets = {
        'Desk_1' : DeskOneSchedule.objects.all().order_by('order'),
        'Desk_2' : DeskTwoSchedule.objects.all().order_by('order'),
        'Hx' : HxBlendthese.objects \
                .filter(prod_line__iexact='Hx') \
                .filter(component_item_description__startswith='BLEND-') \
                .order_by('run_date'),
        'Dm' : HxBlendthese.objects \
                .filter(prod_line__iexact='Dm') \
                .filter(component_item_description__startswith='BLEND-') \
                .order_by('run_date'),
        'Totes' : HxBlendthese.objects \
                .filter(prod_line__iexact='Totes') \
                .filter(component_item_description__startswith='BLEND-') \
                .order_by('run_date')
    }

    if blend_area == 'all':
        for area in areas_list:
            modified_queryset = prepare_blend_schedule_queryset(area, blend_schedule_querysets[area])
            blend_schedule_querysets[area] = modified_queryset
    else:
        blend_schedule_querysets[blend_area] = prepare_blend_schedule_queryset(blend_area, blend_schedule_querysets[blend_area])
    
    # pack_dict (Amazing the difference an inch can make. Thinking a lot about this)
    context = {'desk_one_blends': blend_schedule_querysets['Desk_1'],
                'desk_two_blends': blend_schedule_querysets['Desk_2'],
                'horix_blends': blend_schedule_querysets['Hx'],
                'drum_blends': blend_schedule_querysets['Dm'],
                'tote_blends': blend_schedule_querysets['Totes'],
                'blend_area': blend_area,
                'add_lot_form' : add_lot_form,
                'today' : today,
                'submitted' : submitted}

    blend_area = request.GET.get('blend-area', 0)
    return render(request, 'core/blendschedule.html', context)

def prepare_blend_schedule_queryset(area, queryset):
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
                for item in max_blend_numbers_dict:
                    print(item)

            for blend in queryset:
                try:
                    blend.quantity = LotNumRecord.objects.get(lot_number=blend.lot).lot_quantity
                    blend.line = LotNumRecord.objects.get(lot_number=blend.lot).line
                    blend.run_date = LotNumRecord.objects.get(lot_number=blend.lot).run_date
                except LotNumRecord.DoesNotExist:
                    if not blend.item_code == 'INVENTORY':
                        blend.delete()
                        continue
                if ComponentShortage.objects.filter(component_item_code__iexact=blend.item_code).exists():
                    blend.hourshort = ComponentShortage.objects.filter(component_item_code__iexact=blend.item_code).order_by('start_time').first().start_time
                    if blend.item_code in advance_blends:
                        blend.hourshort = max((blend.hourshort - 30), 5)
                else:
                    blend.threewkshort = ""
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


def manage_blend_schedule(request, request_type, blend_area, blend_id):
    request_source = request.GET.get('request-source', 0)
    if blend_area == 'Desk_1':
        blend = DeskOneSchedule.objects.get(pk=blend_id)
    elif blend_area == 'Desk_2':
        blend = DeskTwoSchedule.objects.get(pk=blend_id)
    if request_type == 'delete':
        blend.delete()
    if request_type == 'switch-schedules':
        if blend.blend_area == 'Desk_1':
            max_number = DeskTwoSchedule.objects.aggregate(Max('order'))['order__max']
            if not max_number:
                max_number = 0
            new_schedule_item = DeskTwoSchedule(
                item_code = blend.item_code,
                item_description = blend.item_description,
                lot = blend.lot,
                blend_area = 'Desk_2',
                order = max_number + 1
                )
            new_schedule_item.save()
        elif blend.blend_area == 'Desk_2':
            max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
            if not max_number:
                max_number = 0
            new_schedule_item = DeskOneSchedule(
                item_code = blend.item_code,
                item_description = blend.item_description,
                lot = blend.lot,
                blend_area = 'Desk_1',
                order = max_number + 1
                )
            new_schedule_item.save()
        blend.delete()
    if request_source == 'lot-num-records':
        return HttpResponseRedirect(f'/core/lot-num-records')
    elif request_source == 'desk-1-schedule':
        return HttpResponseRedirect(f'/core/blend-schedule/?blend-area=Desk_1')
    elif request_source == 'desk-2-schedule':
        return HttpResponseRedirect(f'/core/blend-schedule/?blend-area=Desk_2')

def add_inventory_line_to_schedule(request):
    try:
        desk = request.GET.get('desk','')
        print(desk)
        if desk == 'Desk_1':
            max_number = DeskOneSchedule.objects.aggregate(Max('order'))['order__max']
            if not max_number:
                max_number = 0
            new_schedule_item = DeskOneSchedule(
                item_code = "INVENTORY",
                item_description = "DO NOT BLEND PAST HERE",
                lot = "INVENTORY",
                blend_area = "Desk_1",
                order = max_number + 1
                )
            new_schedule_item.save()
        elif desk == 'Desk_2':
            max_number = DeskTwoSchedule.objects.aggregate(Max('order'))['order__max']
            if not max_number:
                max_number = 0
            new_schedule_item = DeskTwoSchedule(
                item_code = "INVENTORY",
                item_description = "DO NOT BLEND PAST HERE",
                lot = "INVENTORY",
                blend_area = "Desk_2",
                order = max_number + 1
                )
            new_schedule_item.save()
        response_json = { 'status' : 'success' }
        
    except Exception as e:
        response_json = { 'status' : 'failure',
                            'error' : str(e)}

    return JsonResponse(response_json, safe=False)

def clear_entered_blends(request):
    blend_area = request.GET.get('blend-area', 0)
    if blend_area == 'Desk_1':
        for scheduled_blend in DeskOneSchedule.objects.all():
            if ImItemCost.objects.filter(receiptno__iexact=scheduled_blend.lot).exists():
                scheduled_blend.delete()
    if blend_area == 'Desk_2':
        for scheduled_blend in DeskTwoSchedule.objects.all():
            if ImItemCost.objects.filter(receiptno__iexact=scheduled_blend.lot).exists():
                scheduled_blend.delete()

    return HttpResponseRedirect(f'/core/blend-schedule?blend-area={blend_area}')

def update_scheduled_blend_tank(request):
    try:
        encoded_lot_number = request.GET.get('encodedLotNumber', '')
        lot_number_bytestr = base64.b64decode(encoded_lot_number)
        lot_number = lot_number_bytestr.decode().replace('"', "")
        print(lot_number)

        encoded_tank = request.GET.get('encodedTank', '')
        tank_bytestr = base64.b64decode(encoded_tank)
        tank = tank_bytestr.decode().replace('"', "")

        blend_area = request.GET.get('blendArea', '')        

        if blend_area == 'Desk_1':
            this_schedule_item = DeskOneSchedule.objects.get(lot__iexact=lot_number)
        elif blend_area == 'Desk_2':
            this_schedule_item = DeskTwoSchedule.objects.get(lot__iexact=lot_number)

        this_schedule_item.tank = tank
        this_schedule_item.save()
        response_json = { 'result' : f'Success. Lot {lot_number} has been assigned to {tank}' }
    except Exception as e:
        response_json = { 'result' : f'Error: {str(e)}' }

    return JsonResponse(response_json, safe=False)
    

def display_this_issue_sheet(request, prod_line, item_code):
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
    print("ok")
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
    print("ok")
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
    containers = ContainerData.objects.all()

    return render(request, 'core/containerdata.html', { 'containers' : containers })

def display_upcoming_component_counts(request):
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
    submitted = False
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
    record_type = request.GET.get('recordType')
    audit_group_queryset = AuditGroup.objects.all().filter(item_type__iexact=record_type).order_by('audit_group')
    item_codes = list(audit_group_queryset.values_list('item_code', flat=True))
    
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

    # Using values_list() to get a flat list of distinct values for the 'audit_group' field
    audit_group_list = list(AuditGroup.objects.values_list('audit_group', flat=True).distinct().order_by('audit_group'))

    new_audit_group_form = AuditGroupForm()

    return render(request, 'core/inventorycounts/itemsbyauditgroup.html', {'audit_group_queryset' : audit_group_queryset,
                                                           'audit_group_list' : audit_group_list,
                                                           'new_audit_group_form' : new_audit_group_form,
                                                           'record_type' : record_type})

def get_components_in_use_soon(request):
    blends_in_demand = [item.item_code for item in DeskOneSchedule.objects.all()]
    blends_in_demand.append(item.item_code for item in DeskTwoSchedule.objects.all())
    boms_in_use_soon = BillOfMaterials.objects \
                                .filter(item_code__in=blends_in_demand) \
                                .filter((Q(component_item_description__startswith="CHEM") | Q(component_item_description__startswith="DYE") | Q(component_item_description__startswith="FRAGRANCE")))
    components_in_use_soon = { 'componentList' : [item.component_item_code for item in boms_in_use_soon]}

    return JsonResponse(components_in_use_soon, safe=False)

def add_item_to_new_group(request):
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
    if 'addNewAuditGroup' in request.POST:
        add_audit_group_form = AuditGroupForm(request.POST)
        if add_audit_group_form.is_valid():
            new_audit_group = add_audit_group_form.save()
        else:
            return render(request, {'add_audit_group_form' : add_audit_group_form})
    else:
        return HttpResponseRedirect('/')
    
def display_list_to_count_list(request):
    return render(request, 'core/inventorycounts/listtocountlist.html', {})

def get_count_record_model(record_type):
    if record_type == 'blend':
        model = BlendCountRecord
    elif record_type == 'blendcomponent':
        model = BlendComponentCountRecord
    elif record_type == 'warehouse':
        model = WarehouseCountRecord
    return model

def add_count_list(request):
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
    

@login_required
def display_count_list(request):
    record_type = request.GET.get('recordType')
    count_list_id = request.GET.get('listId')

    this_count_list = CountCollectionLink.objects.get(pk=count_list_id)
    count_list_name = this_count_list.collection_name
    count_ids_list = this_count_list.count_id_list
    print(count_ids_list)
    count_ids_list = [count_id for count_id in count_ids_list if count_id]

    model = get_count_record_model(record_type)
    these_count_records = model.objects.filter(pk__in=count_ids_list)
    print(these_count_records)

    for count in these_count_records:
        if CiItem.objects.filter(itemcode__iexact=count.item_code).exists():
            count.standard_uom = CiItem.objects.filter(itemcode__iexact=count.item_code).first().standardunitofmeasure
        if ItemLocation.objects.filter(item_code__iexact=count.item_code).exists():
            count.location = ItemLocation.objects.filter(item_code__iexact=count.item_code).first().zone

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
    count_collection_links = CountCollectionLink.objects.all().order_by('link_order')
    if not count_collection_links.exists():
        count_collection_exists = False
    else:
        count_collection_exists = True

    return render(request, 'core/inventorycounts/countcollectionlinks.html', {'count_collection_links' : count_collection_links,
                                                                              'count_collection_exists' : count_collection_exists})

def display_count_records(request):
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
    pk_list = request.GET.get("list")
    # record_type = request.GET.get("recordType")
    # collection_ids_bytestr = base64.b64decode(encoded_pk_list)
    # collection_ids_str = collection_ids_bytestr.decode()
    collection_ids_list = list(pk_list.replace('[', '').replace(']', '').replace('"', '').split(","))

    for collection_id in collection_ids_list:
        this_collection_link = CountCollectionLink.objects.get(pk=collection_id)
        this_collection_link.delete()
    
    return HttpResponseRedirect("/core/display-count-collection-links/")

def update_count_collection_link(request):
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
    if request.method == "GET":
        lookup_type = request.GET.get('lookup-type', 0)
        lookup_value = request.GET.get('item', 0)
        item_code = get_unencoded_item_code(lookup_value, lookup_type)
        requested_BOM_item = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first()
        item_description = requested_BOM_item.component_item_description
        qty_on_hand = round(requested_BOM_item.qtyonhand, 2)
        standard_uom = requested_BOM_item.standard_uom

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
    item_code_queryset = list(BillOfMaterials.objects.order_by('component_item_code').distinct('component_item_code'))

    return render(request, 'core/lookuppages/lookuplocation.html', {'item_code_queryset' : item_code_queryset})

def get_json_item_info(request):
    if request.method == "GET":
        lookup_type = request.GET.get('lookup-type', 0)
        lookup_value = request.GET.get('item', 0)
        lookup_restriction = request.GET.get('restriction', 0)
        item_code = get_unencoded_item_code(lookup_value, lookup_type)
        if BlendProtection.objects.filter(item_code__iexact=item_code).exists():
            item_protection = BlendProtection.objects.filter(item_code__iexact=item_code).first()
            uv_protection = item_protection.uv_protection
            freeze_protection = item_protection.freeze_protection
        else:
            uv_protection = "Not a blend."
            freeze_protection = "Not a blend."
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
                "freeze_protection" : freeze_protection
            }

    return JsonResponse(response_item, safe=False)

def get_json_tank_specs(request):
    if request.method == "GET":
        tank_queryset = StorageTank.objects.all()
        for tank in tank_queryset:
            print(tank.tank_label_vega)
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
    tank_queryset = StorageTank.objects.all()

    if 'msr' in request.path:
        return render(request, 'core/tanklevelsmsr.html', {'tank_queryset' : tank_queryset})
    else:
        return render(request, 'core/tanklevels.html', {'tank_queryset' : tank_queryset})

def get_tank_levels_html(request):
    if request.method == "GET":
        fp = urllib.request.urlopen('http://192.168.178.210/fieldDeviceData.htm')
        html_str = fp.read().decode("utf-8")
        fp.close()
        html_str = urllib.parse.unquote(html_str)
        response_json = { 'html_string' : html_str }

    return JsonResponse(response_json, safe=False)

def display_lookup_item_quantity(request):
    return render(request, 'core/lookuppages/lookupitemquantity.html')

def display_lookup_lot_numbers(request):
    item_code_queryset = list(BillOfMaterials.objects
                            .order_by('component_item_code')
                            .distinct('component_item_code')
                            )

    return render(request, 'core/lookuppages/lookuplotnums.html', {'item_code_queryset' : item_code_queryset})

def get_json_bill_of_materials_fields(request):
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
    today = dt.datetime.today()
    if ChecklistSubmissionRecord.objects.filter(date_checked__gte=today).exists():
        daily_update_performed = True
    else:
        daily_update_performed = False
    return render(request, 'core/checklistmgmt.html', {'daily_update_performed' : daily_update_performed})

def update_submission_tracker(request):
    taskfunctions.update_checklist_tracker('the manual button on ChecklistMgmt.html')
    return redirect('display-checklist-mgmt-page')

def email_submission_report(request):
    recipient_address = request.GET.get('recipient')
    print(recipient_address)
    taskfunctions.email_checklist_submission_tracking('the manual button on ChecklistMgmt.html', recipient_address)
    return redirect('display-checklist-mgmt-page')

def email_issue_report(request):
    recipient_address = request.GET.get('recipient')
    taskfunctions.email_checklist_issues('the manual button on ChecklistMgmt.html', recipient_address)
    return redirect('display-checklist-mgmt-page')

def display_blend_statistics(request):
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
    return render(request, 'core/reports/maxproduciblequantity.html', {})

def display_truck_rail_material_schedule(request):
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

        # for tank in tank_levels:
        #     tank_capacity = float(tank.max_gallons) - float(tank.filled_gallons)
        #     if tank_capacity > item.quantityordered:
        #         if tank.item_code == item.itemcode:
        #             item.tank = f'TANK {tank.tank_name}'
        #     elif (float(tank_capacity) - float(item.quantityordered)) < 100 and (float(tank_capacity) - float(item.quantityordered)) > 0:
        #         if tank.item_code == item.itemcode:
        #             item.tank = f'TANK {tank.tank_name}'
        #         item.space_warning_level = 'warning'
        #     elif tank_capacity < item.quantityordered or tank_capacity == item.quantityordered:
        #         if tank.item_code == item.itemcode:
        #             item.tank = f'TANK {tank.tank_name}'
        #         item.space_warning_level = 'critical'

    return render(request, 'core/truckrailmaterialschedule.html', {'truck_and_rail_orders' : truck_and_rail_orders}) 

def display_component_shortages(request):
    component_shortages = ComponentShortage.objects \
        .filter(procurement_type__iexact='B') \
        .order_by('start_time').filter(component_instance_count=1)
    if not request.GET.get('po-filter') == None:
        component_shortages = component_shortages.filter(po_number__iexact=request.GET.get('po-filter'))

    return render(request, 'core/componentshortages.html', {'component_shortages' : component_shortages})

def display_subcomponent_shortages(request):
    subcomponent_shortages = SubComponentShortage.objects.all().order_by('start_time').filter(subcomponent_instance_count=1)
    if not request.GET.get('po-filter') == None:
        subcomponent_shortages = subcomponent_shortages.filter(po_number__iexact=request.GET.get('po-filter'))

    return render(request, 'core/subcomponentshortages.html', {'subcomponent_shortages' : subcomponent_shortages})

def display_forklift_issues(request):
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
    loop_statuses = LoopStatus.objects.all()

    return render(request, 'core/loopstatus.html', {'loop_statuses' : loop_statuses})

def get_json_refresh_status(request):
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
    base64_schedule_order = request.GET.get('encodedDeskScheduleOrder')
    json_schedule_order = base64.b64decode(base64_schedule_order).decode()
    schedule_order = json.loads(json_schedule_order)
    for key, value in schedule_order.items():
        if not key == 'desk':
            if schedule_order['desk'] == 'Desk_1':
                print(f'setting lot number {key} to position {value}')
                this_item = DeskOneSchedule.objects.get(lot=key)
                this_item.order = value
                this_item.save()
            elif schedule_order['desk'] == 'Desk_2':
                print(f'setting lot number {key} to position {value}')
                this_item = DeskTwoSchedule.objects.get(lot=key)
                this_item.order = value
                this_item.save()
    
    response_json = {'' : ''}
    return JsonResponse(response_json, safe=False)

def get_json_blend_crew_initials(request):

    # Get the 'blend_crew' group
    try:
        blend_crew_group = Group.objects.get(name='blend_crew')
    except Group.DoesNotExist:
        # Handle if the group doesn't exist
        return JsonResponse({'message': 'Blend Crew group does not exist'}, status=404)
    blend_crew_users = User.objects.filter(groups=blend_crew_group)
    initials_list = [user.first_name[0].upper() + user.last_name[0].upper() for user in blend_crew_users if user.first_name and user.last_name]

    # Create the JSON response with the flat list of initials
    response_json = {'initials': initials_list}

    return JsonResponse(response_json, safe=False)

def feedback(request):
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
    if request.method == 'POST':
        form = GHSPictogramForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('display-ghs-label-search')
    else:
        form = GHSPictogramForm()

    return render(request, 'core/GHSlabelGen/ghslookuppage.html', {'form': form})

def display_ghs_label(request, encoded_item_code):
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
    redirect_page = request.GET.get("redirect-page", 0)
    id_item_to_delete = request.GET.get("id", 0)
    GHSPictogram.objects.get(pk=id_item_to_delete).delete()

    return redirect(redirect_page)

def update_ghs_pictogram(request):

    return redirect('display-ghs-label-search')

def display_all_ghs_pictograms(request):
    all_ghs_pictograms = GHSPictogram.objects.all()

    return render(request, 'core/GHSlabelGen/allghslabels.html', {'all_ghs_pictograms' : all_ghs_pictograms}) 

def get_json_all_ghs_fields(request):
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
    encoded_item_code = request.GET.get("encodedItemCode", "")
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    response_json = {'result' : 'success'}
    try: 
        new_log = PartialContainerLabelLog(item_code=item_code)
        new_log.save()
    except Exception as e:
        response_json = { 'result' : 'error: ' + str(e)}
    return JsonResponse(response_json, safe=False)

def display_blend_id_label(request):
    lot_number  = request.GET.get("lotNumber", 0)
    encoded_item_code  = request.GET.get("encodedItemCode", 0)
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    if CiItem.objects.filter(itemcode__iexact=item_code).exists():
        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
    else:
        item_description = ""
    if BlendProtection.objects.filter(item_code__iexact=item_code).exists():
        item_protect = BlendProtection.objects.filter(item_code__iexact=item_code).first()
        if item_protect.uv_protection == 'yes' and item_protect.freeze_protection == 'yes':
            item_protection = "UV and Freeze"
        elif item_protect.uv_protection == 'no' and item_protect.freeze_protection == 'yes':
            item_protection = "Freeze"
        elif item_protect.uv_protection == 'yes' and item_protect.freeze_protection == 'no':
            item_protection = "UV"
        else:
            item_protection = "No"    
    else:
        item_protection = "No"

    label_contents = {
        "item_code" : item_code,
        "item_description" : item_description,
        "lot_number" : lot_number,
        "item_protection" : item_protection
    }
    
    return render(request, 'core/blendlabeltemplate.html', {"label_contents" : label_contents})

def display_blend_instruction_links(request):
    distinct_blend_item_codes = BlendInstruction.objects.all().values_list('blend_item_code', flat=True).distinct()
    context = []
    item_descriptions = {ci_item.itemcode: ci_item.itemcodedesc for ci_item in CiItem.objects.filter(itemcode__in=distinct_blend_item_codes)}
    for item_code in distinct_blend_item_codes:
        encoded_item_code = base64.b64encode(item_code.encode()).decode()
        context.append({'url' : f'/core/display-blend-instruction-editor?itemCode={encoded_item_code}',
                        'item_code' : item_code,
                        'item_description' : item_descriptions.get(item_code, "")})
    for item in context:
        print(item['url'])

    return render(request, 'core/blendinstructions/blendinstructionlinks.html', {'context' : context})

def display_blend_instruction_editor(request):
    submitted=False
    encoded_item_code = request.GET.get("itemCode", 0)
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    these_blend_instructions = BlendInstruction.objects.filter(blend_item_code__iexact=item_code).order_by('step_number')
    formset_instance = modelformset_factory(BlendInstruction, form=BlendInstructionForm, extra=0)
    these_blend_instructions_formset = formset_instance(request.POST or None, queryset=these_blend_instructions)

    if request.method == 'POST':
        # If the form is valid: submit changes, redirect to the same page but with the success message.
        if these_blend_instructions_formset.is_valid():
            these_blend_instructions_formset.save()
            submitted = True
            these_blend_instructions = BlendInstruction.objects.filter(blend_item_code__iexact=item_code).order_by('step_number')
            formset_instance = modelformset_factory(BlendInstruction, form=BlendInstructionForm, extra=0)
            these_blend_instructions_formset = formset_instance(request.POST or None, queryset=these_blend_instructions)
            return render(request, 'core/blendinstructions/blendinstructioneditor.html', {
                            'submitted' : submitted,
                            'these_blend_instructions_formset' : these_blend_instructions_formset,
                            'result' : 'success'
                            })
        else:
            return render(request, 'core/blendinstructions/blendinstructioneditor.html', {
                        'submitted' : submitted,
                        'these_blend_instructions_formset' : these_blend_instructions_formset
                        })
    else:
        return render(request, 'core/blendinstructions/blendinstructioneditor.html', {
                        'submitted' : submitted,
                        'these_blend_instructions_formset' : these_blend_instructions_formset
                        })

def update_instructions_order(request):
    base64_instructions_order = request.GET.get('encodedInstructionsOrder')
    json_instructions_order = base64.b64decode(base64_instructions_order).decode()
    instructions_order = json.loads(json_instructions_order)
    for key, value in instructions_order.items():
        print(f'setting step {key} to position {value}')
        this_item = BlendInstruction.objects.get(id=key)
        this_item.step_number = value
        this_item.save()

    response_json = {'' : ''}
    return JsonResponse(response_json, safe=False)

def delete_blend_instruction(request):
    instruction_id = request.GET.get('objectID')
    blend_item_code = request.GET.get('encodedItemCode')

    if BlendInstruction.objects.filter(pk=instruction_id).exists():
        selected_instruction = BlendInstruction.objects.get(pk=instruction_id)
        selected_instruction.delete()

    return HttpResponseRedirect(f'/core/display-blend-instruction-editor/?itemCode={blend_item_code}')
    
def add_blend_instruction(request):

    return JsonResponse()

def get_json_new_blend_instruction_form_info(request):
    encoded_item_code = request.GET.get("encodedItemCode", 0)
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    max_id = BlendInstruction.objects.aggregate(Max('id'))['id__max']
    max_instruction_number = BlendInstruction.objects.filter(blend_item_code__iexact=item_code).order_by('-step_number').first().step_number
    
    response = { 
                'next_id' : max_id + 1,
                'next_instruction_number' : max_instruction_number + 1 
                }

    return JsonResponse(response, safe=False)


# Zebra
class ZebraDevice:
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
   print(this_zebra_device)
   if this_zebra_device is not None:
       this_zebra_device.send("~WC")

def success_callback(this_zebra_device):
   print("Success callback called with device info:")
   print(this_zebra_device)

def error_callback(error_message):
   print("Error callback called with message:")
   print(error_message)

@csrf_exempt
def print_blend_label(request):
    this_zebra_device = get_default_zebra_device("printer", success_callback, error_callback)
    this_zebra_device.send("~JSO")
    label_blob = request.FILES.get('labelBlob')
    zpl_string = ZebrafyImage(label_blob.read(),invert=True).to_zpl()
    label_quantity = int(request.POST.get('labelQuantity', 0))
    if this_zebra_device is not None:
        for i in range(label_quantity):
            this_zebra_device.send(zpl_string)

    return JsonResponse({})

def get_json_lot_number(request):
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
    blend_tank_restrictions = BlendTankRestriction.objects.all()
    new_restriction_form = BlendTankRestrictionForm()
    item_codes = blend_tank_restrictions.values_list('item_code', flat=True)
    item_descriptions = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__in=item_codes)}
    for restriction in blend_tank_restrictions:
        restriction.item_description = item_descriptions.get(restriction.item_code, "")

    context = { 'blend_tank_restrictions' : blend_tank_restrictions, 'new_restriction_form' : new_restriction_form }
    
    return render(request, 'core/blendtankrestrictions.html', context)

def add_blend_tank_restriction(request):
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
    pk_list = request.GET.get("list")
    # record_type = request.GET.get("recordType")
    # collection_ids_bytestr = base64.b64decode(encoded_pk_list)
    # collection_ids_str = collection_ids_bytestr.decode()
    blend_tank_restriction_list = list(pk_list.replace('[', '').replace(']', '').replace('"', '').split(","))

    for restriction in blend_tank_restriction_list:
        this_restriction = BlendTankRestriction.objects.get(pk=restriction)
        this_restriction.delete()

def display_test_page(request):
    item_code = '602001'
    item_quantity = 1500
    start_time = 0.0
    blend_subcomponent_usage = get_relevant_blend_runs(item_code, item_quantity, start_time)
    item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc

    return render(request, 'core/testpage.html', {'blend_subcomponent_usage' : blend_subcomponent_usage,
                                                  'item_code' : item_code,
                                                  'item_description' : item_description})

def get_json_all_blend_qtyperbill(request):
    blend_bills_of_materials = BillOfMaterials.objects \
        .filter(component_item_description__startswith='BLEND')
    # for item in blend_bills_of_materials.filter(component_item_code__iexact='87700.B'):
    #     print(f'{item.component_item_code} - {item.component_item_description}: {item.qtyperbill}')

    response = { item.item_code : item.qtyperbill * item.foam_factor for item in blend_bills_of_materials }

    return JsonResponse(response, safe=False)

def get_transactions_for_bom_check():
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
    matching_transactions = get_transactions_for_bom_check()
    return render(request, 'core/blendingredientquantitychecker.html', {'matching_transactions' : matching_transactions})

def get_relevant_ci_item_itemcodes(filter_string):
    if filter_string == 'blend_components':
        sql_query = """
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (itemcodedesc like 'BLEND%' 
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
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand FROM ci_item ci
            JOIN im_itemwarehouse iw ON ci.itemcode = iw.itemcode
            WHERE (itemcodedesc like 'BLEND%')
            AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)
            AND ci.itemcode NOT IN ('030143', '030182')
            and ci.itemcode not like '/%'
            and iw.QuantityOnHand > 0
            """
    elif filter_string == 'non_blend':
        sql_query = """
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand FROM ci_item ci
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
            SELECT ci.itemcode, ci.itemcodedesc, iw.QuantityOnHand FROM ci_item ci
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
        missing_items = [(item[0], item[1]) for item in cursor.fetchall()]

    return missing_items

def display_missing_audit_groups(request):
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
        formset_initial_data = [{'item_code': item[0], 'item_description' : item[1]} for item in missing_items]
        audit_group_formset = AuditGroupFormSet(queryset=AuditGroup.objects.none(), initial=formset_initial_data)
    
    return render(request, 'core/missingauditgroups.html', {'audit_group_formset': audit_group_formset, 'missing_items' : missing_items})

def display_raw_material_label(request):
    today_date = dt.datetime.now()

    return render(request, 'core/rawmateriallabel.html', {'today_date' : today_date})