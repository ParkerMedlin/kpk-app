import urllib
import math
import datetime as dt
from datetime import date
import pytz
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

def display_blend_shortages(request):
    blend_shortages_queryset = ComponentShortage.objects \
        .filter(component_item_description__startswith='BLEND') \
        .filter(procurement_type__iexact='M') \
        .order_by('start_time') \
        .filter(component_instance_count=1) \
        .exclude(prod_line__iexact='Hx')
    advance_blends = ['602602','602037','602037EUR','93700.B','94700.B','93800.B','94600.B']
    for blend in blend_shortages_queryset:
        if blend.component_item_code in advance_blends:
            blend.advance_blend = 'yes'
    component_item_codes = blend_shortages_queryset.values_list('component_item_code', flat=True)

    foam_factor_is_populated = FoamFactor.objects.all().exists()
    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_one_item_codes = desk_one_queryset.values_list('item_code', flat=True)
    desk_two_queryset = DeskTwoSchedule.objects.all()
    desk_two_item_codes = desk_two_queryset.values_list('item_code', flat=True)
    
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
            blend.schedule_value = 'Desk_1'
        elif blend.component_item_code in desk_two_item_codes:
            blend.schedule_value = 'Desk_2'
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

    return render(request, 'core/blendshortages.html', {
        'blend_shortages_queryset': blend_shortages_queryset,
        'foam_factor_is_populated' : foam_factor_is_populated,
        'submitted' : submitted,
        'add_lot_form' : add_lot_form})

def create_blend_sheet_json(item_code, item_description, batch_volume):
    formatted_item_code = item_code.replace('/','-').replace('.','')
    error = ''
    if BlendInstruction.objects.filter(blend_item_code__iexact=item_code).exists():
        these_blend_instructions = BlendInstruction.objects.filter(blend_item_code__iexact=item_code)
    else:
        error = f'Instruction set for {item_code} does not exist.'
    try:
        these_blend_components = BlendFormulaComponent.objects.filter(blend_number__iexact=formatted_item_code)
    except Exception as error:
        # error = f'Formula components for {item_code} do not exist.'
        return (error, {})

    
    item_weights = {ci_item.itemcode: ci_item.shipweight for ci_item in CiItem.objects.filter(Q(itemcodedesc__startswith="CHEM") | Q(itemcodedesc__startswith="DYE") | Q(itemcodedesc__startswith="FRAGRANCE") | Q(itemcodedesc__startswith="BLEND"))}
    item_descriptions = {ci_item.itemcode: ci_item.shipweight for ci_item in CiItem.objects.filter(Q(itemcodedesc__startswith="CHEM") | Q(itemcodedesc__startswith="DYE") | Q(itemcodedesc__startswith="FRAGRANCE") | Q(itemcodedesc__startswith="BLEND"))}

    product_density = these_blend_components.first().product_density
    total_batch_weight = batch_volume * product_density

    # construct the steps out of the instructions.
    # STEPS are like an instantiation of instructions: Instructions are the blueprint, 
    # while steps are the actual construct. 
    steps = {}
    for instruction in these_blend_instructions:
        component_quantity = 0
        if instruction.component_item_code:
            print(f'looking up percent weight of total for {instruction.component_item_code}')
            try:
                component_quantity = these_blend_components.filter(component_item_code__iexact=instruction.component_item_code).first().percent_weight_of_total * total_batch_weight
            except Exception as error:
                return (error, {})

        steps[instruction.step_number] = {
            "notes": "",
            "start_time": "",
            "end_time": "",
            "component_quantity": component_quantity,
            "completed": "",
            "component_item_code": instruction.component_item_code,
            "component_item_description" : item_descriptions.get(instruction.component_item_code,''),
            "quantity": "",
            "step_description": instruction.step_description,
            "weight_per_gallon": item_weights.get(instruction.component_item_code,'')
        }
    
    blend_sheet_json = {
        "item_code" : item_code,
        "item_description" : item_description,
        "product_density" : product_density,
        "batch_volume" : batch_volume,
        "total_batch_weight" : total_batch_weight
    }

    return (error, blend_sheet_json)

    # return render(request, 'core/lotnumerrorform.html', {'add_lot_form' : add_lot_form, 'error' : error})

def add_lot_num_record(request):
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    redirect_page = request.GET.get('redirect-page', 0)
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
                next_duplicate_lot_number = generate_next_lot_number()
                next_duplicate_lot_num_record = LotNumRecord(
                    item_code = add_lot_form.cleaned_data['item_code'],
                    item_description = add_lot_form.cleaned_data['item_description'],
                    lot_number = next_duplicate_lot_number,
                    lot_quantity = add_lot_form.cleaned_data['lot_quantity'],
                    date_created = add_lot_form.cleaned_data['date_created'],
                    line = add_lot_form.cleaned_data['line'],
                    desk = this_lot_desk,
                    run_date = add_lot_form.cleaned_data['run_date']
                )
                next_duplicate_lot_num_record.save()
                if not this_lot_prodline == 'Hx':
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
            elif redirect_page == 'blend-shortages':
                return HttpResponseRedirect('/core/blend-shortages')
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
            selected_schedule_item = DeskOneSchedule.objects.get(lot__icontains=lot_number)
            selected_schedule_item.delete()
        except DeskOneSchedule.DoesNotExist as e:
            print(str(e))
            continue
        try:
            selected_schedule_item = DeskTwoSchedule.objects.get(lot__icontains=lot_number)
            selected_schedule_item.delete()
        except DeskTwoSchedule.DoesNotExist as e:
            print(str(e))
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

def display_all_chemical_locations(request):
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
        this_lot_number = LotNumRecord.objects.get(lot_number__icontains=data['blelot_number'])
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

def create_report(request, which_report):
    encoded_item_code = request.GET.get('itemCode')
    item_code_bytestr = base64.b64decode(encoded_item_code)
    item_code = item_code_bytestr.decode()
    if which_report=="Lot-Numbers":
        no_lots_found = False
        lot_num_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created', '-lot_number')
        lot_num_paginator = Paginator(lot_num_queryset, 25)
        page_num = request.GET.get('page')
        current_page = lot_num_paginator.get_page(page_num)

        im_itemcost_queryset = ImItemCost.objects.filter(itemcode__iexact=item_code)
        for lot in current_page:
            if im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).exists():
                total_qty_so_far = float(0.0000)
                for item in im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number):
                    print(item.quantityonhand)
                    total_qty_so_far = total_qty_so_far + float(item.quantityonhand)
                    print(lot.lot_number + ' ' + str(total_qty_so_far))
                lot.qty_on_hand = round(total_qty_so_far,4)
                lot.date_entered = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().transactiondate)
            else:
                lot.qty_on_hand = None
                lot.date_entered = None
        if lot_num_queryset.exists():
            item_description = lot_num_queryset.first().item_description
        else:
            no_lots_found = True
            item_description = ''
        blend_info = {'item_code' : item_code, 'item_description' : item_description}

        return render(request, 'core/reports/lotnumsreport.html', {'no_lots_found' : no_lots_found, 'current_page' : current_page, 'blend_info': blend_info})

    elif which_report=="All-Upcoming-Runs":
        no_runs_found = False
        report_type = ''
        this_bill = BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first()
        component_prefixes = ['BLEND','ADAPTER','APPLICATOR','BAG','BAIL','BASE','BILGE PAD','BOTTLE',
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
            upcoming_runs = ComponentUsage.objects.filter(component_item_code__icontains=item_code).order_by('start_time')
            report_type = 'Component'
        else:
            upcoming_runs = SubComponentUsage.objects.filter(subcomponent_item_code__icontains=item_code).order_by('start_time')
            report_type = 'SubComponent'
        # upcoming_runs = TimetableRunData.objects.filter(component_item_code__icontains=item_code).order_by('starttime')
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
                        .filter(component_item_code__icontains=item_code) \
                        .first().component_item_description
                    }
        context = {'counts_not_found' : counts_not_found,
            'blend_count_records' : count_records,
            'item_info' : item_info
            }
        return render(request, 'core/reports/inventorycountsreport.html', context)

    elif which_report=="Counts-And-Transactions":
        if BlendCountRecord.objects.filter(item_code__iexact=item_code).exists():
            blend_count_records = BlendCountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
            item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(blend_count_records):
                count.blend_count_order = str(order) + "counts"
        else:
            counts_not_found = True
            blend_count_records = {}
        if ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).exists():
            transactions_list = ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).order_by('-transactiondate')
            for order, count in enumerate(transactions_list):
                count.transaction_order = str(order) + "txns"
        else:
            no_transactions_found = True
            transactions_list = {}
        
        counts_and_transactions = {}
        for iteration, item in enumerate(blend_count_records):
            item.iteration = iteration
            item.ordering_date = str(item.counted_date) + 'b' + str(item.iteration)
            counts_and_transactions[item.ordering_date] = item
            item.transactioncode = 'Count'
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

    else:
        return render(request, '')
    
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
    submitted=False
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    # blend_instruction_queryset = BlendInstruction.objects.order_by('item_code', 'step_no')
    
    if request.method == "POST":
        add_lot_num_record(request)
        return HttpResponseRedirect('/core/lot-num-records')
    else:
        add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number': next_lot_number, 'date_created':today,})
        if 'submitted' in request.GET:
            submitted=True

    desk_one_blends = DeskOneSchedule.objects.all().order_by('order')
    if desk_one_blends.exists():
        for blend in desk_one_blends:
            try:
                blend.quantity = LotNumRecord.objects.get(lot_number=blend.lot).lot_quantity
                blend.line = LotNumRecord.objects.get(lot_number=blend.lot).line
            except LotNumRecord.DoesNotExist:
                blend.delete()
            try:
                blend.when_entered = ImItemCost.objects.filter(receiptno__iexact=blend.lot).first()
            except ImItemCost.DoesNotExist:
                blend.when_entered = "Not Entered"
            if BlendThese.objects.filter(component_item_code__iexact=blend.item_code).exists():
                blend.threewkshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().three_wk_short
                blend.hourshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().starttime
            else:
                blend.threewkshort = ""
            
    desk_two_blends = DeskTwoSchedule.objects.all().order_by('order')
    if desk_two_blends.exists():
        for blend in desk_two_blends:
            try:
                blend.quantity = LotNumRecord.objects.get(lot_number=blend.lot).lot_quantity
                blend.line = LotNumRecord.objects.get(lot_number=blend.lot).line
            except LotNumRecord.DoesNotExist:
                blend.delete()
            try:
                blend.when_entered = ImItemCost.objects.filter(receiptno__iexact=blend.lot).first()
            except ImItemCost.DoesNotExist:
                blend.when_entered = "Not Entered"
            if BlendThese.objects.filter(component_item_code__iexact=blend.item_code).exists():
                blend.threewkshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().three_wk_short
                blend.hourshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().starttime
            else: 
                blend.threewkshort = "No Shortage"
    
    horix_blends = ComponentUsage.objects \
        .filter(prod_line__icontains='Hx') \
        .filter(component_item_description__startswith='BLEND-') \
        .order_by('start_time')
    drum_blends = ComponentUsage.objects \
        .filter(prod_line__icontains='Dm') \
        .filter(component_item_description__startswith='BLEND-') \
        .order_by('start_time')
    tote_blends = ComponentUsage.objects \
        .filter(prod_line__icontains='Totes') \
        .filter(component_item_description__startswith='BLEND-') \
        .order_by('start_time')


    blend_area = request.GET.get('blend-area', 0)
    return render(request, 'core/blendschedule.html', {'desk_one_blends': desk_one_blends,
                                                        'desk_two_blends': desk_two_blends,
                                                        'horix_blends': horix_blends,
                                                        'drum_blends': drum_blends,
                                                        'tote_blends': tote_blends,
                                                        'blend_area': blend_area,
                                                        'add_lot_form' : add_lot_form,
                                                        'today' : today,
                                                        'submitted' : submitted})

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
        .filter(item_code__icontains=item_code) \
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
            these_lot_numbers = LotNumRecord.objects \
                .filter(item_code__iexact=component_item_code) \
                .filter(sage_qty_on_hand__gt=0).order_by('id')[:1]
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
    all_lot_numbers_with_quantity = LotNumRecord.objects.filter(sage_qty_on_hand__gt=0).order_by('sage_entered_date')

    prod_runs_this_line = ComponentUsage.objects  \
        .filter(component_item_description__startswith='BLEND') \
        .filter(prod_line__iexact=prod_line) \
        .filter(start_time__lte=12) \
        .order_by('start_time')

    if prod_line == 'all':
        prod_runs_this_line = ComponentUsage.objects  \
        .filter(component_item_description__startswith='BLEND') \
        .filter(start_time__lte=12) \
        .order_by('start_time')

    for run in prod_runs_this_line:
        if run.component_onhand_after_run < 0:
            run.shortage_flag = 'short'
        elif run.component_onhand_after_run < 25:
            run.shortage_flag = 'warning'
        else: 
            run.shortage_flag = 'noshortage'

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
        # skip duplicates
        if any(d.get('component_item_code', None) == run.component_item_code for d in runs_this_line):
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


def display_upcoming_blend_counts(request):
    last_counts = { count.item_code : (count.counted_date, count.counted_quantity) for count in BlendCountRecord.objects.filter(counted=True).order_by('counted_date') }
    last_transactions = { transaction.itemcode : (transaction.transactioncode, transaction.transactiondate) for transaction in ImItemTransactionHistory.objects.all().order_by('transactiondate') }

    upcoming_run_objects = ComponentUsage.objects.filter(component_item_description__startswith="BLEND") \
                        .exclude(prod_line__iexact='Hx') \
                        .exclude(prod_line__iexact='Dm') \
                        .filter(start_time__gte=8) \
                        .order_by('start_time')
    
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
        this_count = last_counts.get(run['item_code'], '')
        if this_count:
            run['last_count_date'] = this_count[0]
            run['last_count_quantity'] = this_count[1]
        this_transaction = last_transactions.get(run['item_code'], '')
        if this_transaction:
            run['last_transaction_code'] = this_transaction[0]
            run['last_transaction_date'] = this_transaction[1]
        if run['item_code'] in blend_shortage_codes:
            run['shortage'] = True
            run['shortage_hour'] = all_blend_shortages[run['item_code']]
        else: run['shortage'] = False
        if run['last_transaction_date'] and run['last_count_date']:
            if run['last_transaction_date'] < run['last_count_date'] or run['last_transaction_code'] == 'II':
                run['needs_count'] = False
            else:
                run['needs_count'] = True

    return render(request, 'core/inventorycounts/upcomingblends.html', {'upcoming_runs' : upcoming_runs })

def display_upcoming_component_counts(request):
    upcoming_run_objects = SubComponentUsage.objects.filter(component_item_description__startswith="BLEND") \
                        .exclude(prod_line__iexact='Hx') \
                        .exclude(prod_line__iexact='Dm') \
                        .exclude(subcomponent_item_description__startswith="BLEND") \
                        .exclude(subcomponent_item_description__startswith="VOLUME") \
                        .exclude(subcomponent_item_code__startswith="/C") \
                        .order_by('start_time')

    upcoming_runs = []
    for run in upcoming_run_objects:
        upcoming_runs.append({
                    'item_code' : run.subcomponent_item_code,
                    'item_description' : run.subcomponent_item_description,
                    'expected_quantity' : run.subcomponent_onhand_qty,
                    'start_time' : run.start_time,
                    'prod_line' : run.prod_line,
                    'last_count_date' : '',
                    'last_count_quantity' : '',
                    'last_transaction_code' : '',
                    'last_transaction_date' : ''
                })

    seen = set()
    upcoming_runs = [x for x in upcoming_runs if not (x['item_code'] in seen or seen.add(x['item_code']))]

    last_counts = { count.item_code : (count.counted_date, count.counted_quantity) for count in BlendComponentCountRecord.objects.all().order_by('counted_date') }
    last_transactions = { transaction.itemcode : (transaction.transactioncode, transaction.transactiondate) for transaction in ImItemTransactionHistory.objects.all().order_by('transactiondate') }

    for run in upcoming_runs:
        this_count = last_counts.get(run['item_code'], '')
        if this_count:
            run['last_count_date'] = this_count[0]
            run['last_count_quantity'] = this_count[1]
        this_transaction = last_transactions.get(run['item_code'], '')
        if this_transaction:
            run['last_transaction_code'] = this_transaction[0]
            run['last_transaction_date'] = this_transaction[1]
        else: run['shortage'] = False
        if run['last_transaction_date'] and run['last_count_date']:
            if run['last_transaction_date'] < run['last_count_date']:
                run['needs_count'] = True
            else: 
                run['needs_count'] = False

    return render(request, 'core/inventorycounts/upcomingcomponents.html', {'upcoming_runs' : upcoming_runs })

def display_adjustment_statistics(request, filter_option):
    submitted=False
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
    # need to filter this by recordtype eventually
    audit_group_queryset = AuditGroup.objects.all().order_by('audit_group')
    item_codes = audit_group_queryset.values_list('item_code', flat=True)

    
    # Query CiItem objects once and create a dictionary mapping item codes to descriptions

    item_descriptions = {ci_item.itemcode: ci_item.itemcodedesc for ci_item in CiItem.objects.filter(itemcode__in=item_codes)}
    qty_and_units = {bill.component_item_code: f'{round(bill.qtyonhand,4)} {bill.standard_uom}' for bill in BillOfMaterials.objects.filter(component_item_code__in=item_codes)}
    if record_type == 'blend':
        audit_group_queryset = [item for item in audit_group_queryset if item_descriptions.get(item.item_code, '').startswith('BLEND')]
        all_upcoming_runs = {production_run.component_item_code: production_run.start_time for production_run in ComponentUsage.objects.order_by('start_time')}
        all_counts = {count_record.item_code: count_record.counted_date.strftime("%m/%d/%Y") for count_record in BlendCountRecord.objects.all()}
    elif record_type == 'blendcomponent':
        audit_group_queryset = [item for item in audit_group_queryset if not item_descriptions.get(item.item_code, '').startswith('BLEND')]
        all_upcoming_runs = {production_run.subcomponent_item_code: production_run.start_time for production_run in SubComponentUsage.objects.order_by('start_time')}
        all_counts = {count_record.item_code: count_record.counted_date.strftime("%m/%d/%Y") for count_record in BlendComponentCountRecord.objects.all()}
        
    all_transactions = {
        im_itemtransaction.itemcode : (im_itemtransaction.transactioncode + ' - ', im_itemtransaction.transactiondate.strftime("%m/%d/%Y")) 
        for im_itemtransaction in ImItemTransactionHistory.objects.exclude(transactioncode__iexact='PO').order_by('transactiondate')
    }

    # from core.models import ImItemTransactionHistory, ComponentUsage, SubComponentShortage, AuditGroup, CiItem

    # for item in audit_group_queryset:
    latest_transactions = {}
    for item_code, (transactioncode, transactiondate) in all_transactions.items():
        if item_code not in latest_transactions:
            latest_transactions[item_code] = (transactioncode, transactiondate)
        else:
            existing_date = latest_transactions[item_code][0]
            if transactiondate > existing_date:
                latest_transactions[item_code] = (transactioncode, transactiondate)

    earliest_usages = {}
    for item_code, hour in all_counts.items():
        if item_code not in earliest_usages:
            earliest_usages[item_code] = hour
        else:
            existing_hour = latest_transactions[item_code]
            if hour > existing_hour:
                existing_hour[item_code] = hour

    for item in audit_group_queryset:
        item.item_description = item_descriptions.get(item.item_code, '')
        item.transaction_info = all_transactions.get(item.item_code, '')
        item.next_usage = all_upcoming_runs.get(item.item_code, '')
        item.qty_on_hand = qty_and_units.get(item.item_code, '')
        item.last_count = earliest_usages.get(item.item_code, '')
        # if item.item_description == '':
        #     item.delete()

    # Using values_list() to get a flat list of distinct values for the 'audit_group' field
    audit_group_list = list(AuditGroup.objects.values_list('audit_group', flat=True).distinct().order_by('audit_group'))

    new_audit_group_form = AuditGroupForm()

    return render(request, 'core/inventorycounts/itemsbyauditgroup.html', {'audit_group_queryset' : audit_group_queryset,
                                                           'audit_group_list' : audit_group_list,
                                                           'all_transactions' : all_transactions,
                                                           'new_audit_group_form' : new_audit_group_form})

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

def add_count_list(request):
    encoded_item_code_list = request.GET.get('itemsToAdd')
    encoded_pk_list = request.GET.get('encodedPkList')
    record_type = request.GET.get('recordType')
    submitted = False
    item_codes_bytestr = base64.b64decode(encoded_item_code_list)
    item_codes_str = item_codes_bytestr.decode()
    item_codes_list = list(item_codes_str.replace('[', '').replace(']', '').replace('"', '').split(","))

    primary_keys_bytestr = base64.b64decode(encoded_pk_list)
    primary_key_str = primary_keys_bytestr.decode()
    primary_key_list = list(primary_key_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    if (primary_key_list[0] == "No_Item_Codes"):
        primary_key_str = ''
    else:
        primary_key_str = primary_key_str.replace('[', '').replace(']', '').replace('"', '')
        primary_key_str += ','

    if record_type == 'blend':
        today_string = dt.date.today().strftime("%Y%m%d")
        unique_values_count = BlendCountRecord.objects.filter(counted_date=dt.date.today()) \
                                            .values('collection_id') \
                                            .distinct() \
                                            .count()
        this_collection_id = f'B{unique_values_count+1}-{today_string}'
        for item_code in item_codes_list:
            this_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
            this_item_onhandquantity = ImItemWarehouse.objects.filter(itemcode__iexact=item_code).first().quantityonhand
            try:
                new_count_record = BlendCountRecord(
                    item_code = item_code,
                    item_description = this_description,
                    expected_quantity = this_item_onhandquantity,
                    counted_quantity = 0,
                    counted_date = dt.date.today(),
                    variance = 0,
                    count_type = 'blend',
                    collection_id = this_collection_id
                )
                new_count_record.save()
                primary_key_str+=str(new_count_record.pk) + ','
            except Exception as e:
                print(str(e))
                continue

    elif record_type == 'blendcomponent':
        today_string = dt.date.today().strftime("%Y%m%d")
        unique_values_count = BlendComponentCountRecord.objects.filter(counted_date=dt.date.today()) \
                                        .values('collection_id') \
                                        .distinct() \
                                        .count()
        this_collection_id = f'C{unique_values_count+1}-{today_string}'
        for item_code in item_codes_list:
            this_bill = BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first()
            new_count_record = BlendComponentCountRecord(
                item_code = item_code,
                item_description = this_bill.component_item_description,
                expected_quantity = this_bill.qtyonhand,
                counted_quantity = 0,
                counted_date = dt.date.today(),
                variance = 0,
                count_type = 'blendcomponent',
                collection_id = this_collection_id
            )
            new_count_record.save()
            primary_key_str+=str(new_count_record.pk) + ','
    elif record_type == 'warehouse':
        today_string = dt.date.today().strftime("%Y%m%d")
        unique_values_count = WarehouseCountRecord.objects.filter(counted_date=dt.date.today()) \
                                            .values('collection_id') \
                                            .distinct() \
                                            .count()
        this_collection_id = f'W{unique_values_count+1}-{today_string}'
        for item_code in item_codes_list:
            this_bill = BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first()
            new_count_record = WarehouseCountRecord(
                item_code = item_code,
                item_description = this_bill.component_item_description,
                expected_quantity = this_bill.qtyonhand,
                counted_quantity = 0,
                counted_date = dt.date.today(),
                variance = 0,
                count_type = 'warehouse',
                collection_id = this_collection_id
            )
            new_count_record.save()
            primary_key_str+=str(new_count_record.pk) + ','

    primary_key_str = primary_key_str[:-1]
    primary_key_str_bytes = primary_key_str.encode('UTF-8')
    encoded_primary_key_bytes = base64.b64encode(primary_key_str_bytes)
    encoded_primary_key_str = encoded_primary_key_bytes.decode('UTF-8')

    return HttpResponseRedirect(f'/core/count-list/display/{encoded_primary_key_str}?recordType={record_type}')

@login_required
def display_count_list(request, encoded_pk_list):
    record_type = request.GET.get('recordType')
    submitted=False
    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))

    if record_type == 'blend':
        these_count_records = BlendCountRecord.objects.filter(pk__in=count_ids_list)
    elif record_type == 'blendcomponent':
        these_count_records = BlendComponentCountRecord.objects.filter(pk__in=count_ids_list)
    elif record_type == 'warehouse':
        these_count_records = WarehouseCountRecord.objects.filter(pk__in=count_ids_list)

    expected_quantities = {}
    for count_record in these_count_records:
        item_unit_of_measure = CiItem.objects.filter(itemcode__iexact=count_record.item_code).first().standardunitofmeasure
        count_record.standard_uom = item_unit_of_measure
        expected_quantities[count_record.id] = count_record.expected_quantity

    todays_date = dt.date.today()
    
    if record_type == 'blend':
        formset_instance = modelformset_factory(BlendCountRecord, form=BlendCountRecordForm, extra=0)
        these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)
    elif record_type == 'blendcomponent':
        formset_instance = modelformset_factory(BlendComponentCountRecord, form=BlendComponentCountRecordForm, extra=0)
        these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)
    elif record_type == 'warehouse':
        formset_instance = modelformset_factory(WarehouseCountRecord, form=WarehouseCountRecordForm, extra=0)
        these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)

    if request.method == 'POST':
        # If the form is valid: submit changes, log who made them,
        # then redirect to the same page but with the success message.
        # Otherwise redirect to same page with errors.
        if these_counts_formset.is_valid():
            these_counts_formset.save()
            for form in these_counts_formset:
                this_submission_log = CountRecordSubmissionLog(
                    record_id = form.instance.pk,
                    count_type = record_type,
                    updated_by = f'{request.user.first_name} {request.user.last_name}',
                    update_timestamp = dt.datetime.now()
                )
                print(f'''making submission log like so: 
                      \nrecord_id = {form.instance.pk},
                      \ncount_type = {record_type},
                      \nupdated_by = {request.user.first_name} {request.user.last_name},
                      \nupdate_timestamp = dt.datetime.now()''')
                this_submission_log.save()
            
            return render(request, 'core/inventorycounts/countlist.html', {
                         'submitted' : submitted,
                         'todays_date' : todays_date,
                         'these_counts_formset' : these_counts_formset,
                         'encoded_list' : encoded_pk_list,
                         'expected_quantities' : expected_quantities,
                         'record_type' : record_type,
                         'result' : 'success'
                         })
        else:
            return render(request, 'core/inventorycounts/countlist.html', {
                         'submitted' : submitted,
                         'todays_date' : todays_date,
                         'these_counts_formset' : these_counts_formset,
                         'encoded_list' : encoded_pk_list,
                         'expected_quantities' : expected_quantities,
                         'record_type' : record_type
                         })
    else:
        these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)
        if 'submitted' in request.GET:
            submitted=True
    if not CountCollectionLink.objects.filter(collection_link=f'{request.path}?recordType={record_type}'):
        now_str = dt.datetime.now().strftime('%m-%d-%Y_%H:%M')
        new_collection_link = CountCollectionLink(
            collection_id = f'{record_type}_count_{now_str}',
            collection_link = f'{request.path}?recordType={record_type}'
        )
        new_collection_link.save()

    return render(request, 'core/inventorycounts/countlist.html', {
                         'submitted' : submitted,
                         'todays_date' : todays_date,
                         'these_counts_formset' : these_counts_formset,
                         'encoded_list' : encoded_pk_list,
                         'expected_quantities' : expected_quantities,
                         'record_type' : record_type
                         })

def display_count_records(request):
    record_type = request.GET.get('recordType')
    number_of_records = request.GET.get('records')
    if record_type == 'blend':
        count_record_queryset = BlendCountRecord.objects.order_by('-id')
    elif record_type == 'blendcomponent':
        count_record_queryset = BlendComponentCountRecord.objects.order_by('-id')
    elif record_type == 'warehouse':
        count_record_queryset = WarehouseCountRecord.objects.order_by('-id')
    count_record_paginator = Paginator(count_record_queryset, 50)
    page_num = request.GET.get('page')
    if number_of_records:
        count_record_paginator = Paginator(count_record_queryset, number_of_records)
    else:
        count_record_paginator = Paginator(count_record_queryset, 50)

    current_page = count_record_paginator.get_page(page_num)

    return render(request, 'core/inventorycounts/countrecords.html', {'current_page' : current_page, 'countType' : record_type})

def delete_count_record(request):
    redirect_page = request.GET.get('redirectPage')
    items_to_delete = request.GET.get('listToDelete')
    all_items = request.GET.get('fullList')
    record_type = request.GET.get('recordType')
    items_to_delete_bytestr = base64.b64decode(items_to_delete)
    items_to_delete_str = items_to_delete_bytestr.decode()
    items_to_delete_list = list(items_to_delete_str.replace('[', '').replace(']', '').replace('"', '').split(","))

    all_items_bytestr = base64.b64decode(all_items)
    all_items_str = all_items_bytestr.decode()
    all_items_list = list(all_items_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    
    if record_type == 'blend':
        for item in items_to_delete_list:
            if BlendCountRecord.objects.filter(pk=item).exists():
                selected_count = BlendCountRecord.objects.get(pk=item)
                selected_count.delete()
            if item in all_items_list:
                all_items_list.remove(item)
    elif record_type == 'blendcomponent':
        for item in items_to_delete_list:
            if BlendComponentCountRecord.objects.filter(pk=item).exists():
                selected_count = BlendComponentCountRecord.objects.get(pk=item)
                selected_count.delete()
            if item in all_items_list:
                all_items_list.remove(item)
    elif record_type == 'warehouse':
        for item in items_to_delete_list:
            if WarehouseCountRecord.objects.filter(pk=item).exists():
                selected_count = WarehouseCountRecord.objects.get(pk=item)
                selected_count.delete()
            if item in all_items_list:
                all_items_list.remove(item)

    if (redirect_page == 'count-records'):
        return HttpResponseRedirect(f'/core/count-records?recordType={record_type}')

    if (redirect_page == 'count-list'):
        all_items_str = ''
        for count_id in all_items_list:
            all_items_str += count_id + ','
        all_items_str = all_items_str[:-1]
        all_items_str_bytes = all_items_str.encode('UTF-8')
        encoded_all_items_bytes = base64.b64encode(all_items_str_bytes)
        encoded_all_items_str = encoded_all_items_bytes.decode('UTF-8')
        if all_items_str == '':
            return HttpResponseRedirect(f'/core/count-records?recordType={record_type}')
        else:
            return HttpResponseRedirect(f'/core/count-list/display/{encoded_all_items_str}?recordType={record_type}')

def display_count_report(request):
    encoded_pk_list = request.GET.get("encodedList")
    record_type = request.GET.get("recordType")
    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    average_costs = { item.itemcode : item.averageunitcost for item in CiItem.objects.all()}
    count_credits = { item.record_id : item.updated_by for item in CountRecordSubmissionLog.objects.all().order_by('-update_timestamp')}

    if record_type == "blend":
        count_records_queryset = BlendCountRecord.objects.filter(pk__in=count_ids_list)
    elif record_type == 'blendcomponent':
        count_records_queryset = BlendComponentCountRecord.objects.filter(pk__in=count_ids_list)
    elif record_type == 'warehouse':
        count_records_queryset = WarehouseCountRecord.objects.filter(pk__in=count_ids_list)

    total_variance_cost = 0
    for item in count_records_queryset:
        item.average_cost = average_costs[item.item_code]
        item.variance_cost = average_costs[item.item_code] * item.variance
        total_variance_cost+=item.variance_cost 
        item.counted_by = count_credits.get(str(item.id), "")


    return render(request, 'core/inventorycounts/countrecordreport.html', {'count_records_queryset' : count_records_queryset, 'total_variance_cost' : total_variance_cost})

def display_count_collection_links(request):
    count_collection_links = CountCollectionLink.objects.all()
    if not count_collection_links.exists():
        count_collection_exists = False
    else:
        count_collection_exists = True

    return render(request, 'core/inventorycounts/countcollectionlinks.html', {'count_collection_links' : count_collection_links,
                                                                              'count_collection_exists' : count_collection_exists})

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
    blends_used_upcoming = BlendThese.objects.all()
    blends_upcoming_item_codes = list(BlendThese.objects.values_list('component_item_code', flat=True))
    chems_used_upcoming = BillOfMaterials.objects.filter(item_code__in=blends_upcoming_item_codes).exclude(component_item_code__startswith='/C')
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)
    for chem in chems_used_upcoming:
        chem.blend_req_onewk = blends_used_upcoming.filter(component_item_code__icontains=chem.item_code).first().one_wk_short
        chem.blend_req_twowk = blends_used_upcoming.filter(component_item_code__icontains=chem.item_code).first().two_wk_short
        chem.blend_req_threewk = blends_used_upcoming.filter(component_item_code__icontains=chem.item_code).first().three_wk_short
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
        if (PoPurchaseOrderDetail.objects.filter(itemcode__icontains=chem.component_item_code, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            chem.next_delivery = PoPurchaseOrderDetail.objects.filter(
                itemcode__icontains=chem.component_item_code,
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
        
        if ItemLocation.objects.filter(component_item_code=item_code).exists():
            requested_item = ItemLocation.objects.get(component_item_code=item_code)
            specific_location = requested_item.specific_location
            general_location = requested_item.general_location
        else:
            specific_location = "no location listed."
            general_location = "Check with Parker"

        response_item = {
            "itemCode" : item_code,
            "itemDescription" : item_description,
            "specificLocation" : specific_location,
            "generalLocation" : general_location,
            "qtyOnHand" : qty_on_hand,
            "standardUOM" : standard_uom
        }
    return JsonResponse(response_item, safe=False)

def display_lookup_location(request):
    item_code_queryset = list(BillOfMaterials.objects
                            .order_by('component_item_code')
                            .distinct('component_item_code')
                            )

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
    
    one_week_blend_demand = BlendThese.objects.filter(procurementtype__iexact='M').aggregate(total=Sum('one_wk_short'))
    two_week_blend_demand = BlendThese.objects.filter(procurementtype__iexact='M').aggregate(total=Sum('two_wk_short'))
    all_scheduled_blend_demand = BlendThese.objects.filter(procurementtype__iexact='M').aggregate(total=Sum('three_wk_short'))
    
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
    shortages_using_this_component = BlendThese.objects.filter(component_item_code__in=item_codes_using_this_component).exclude(component_item_code__iexact=blend_item_code_to_exclude)
    total_component_usage = 0
    component_consumption = {}
    for shortage in shortages_using_this_component:
        this_bill = BillOfMaterials.objects.filter(item_code__iexact=shortage.component_item_code) \
            .filter(component_item_code__iexact=component_item_code) \
            .exclude(item_code__startswith="/") \
            .first()
        shortage.component_usage = shortage.adjustedrunqty * this_bill.qtyperbill
        total_component_usage += float(shortage.component_usage)
        component_consumption[shortage.component_item_code] = {
            'blend_item_code' : shortage.component_item_code,
            'blend_item_description' : shortage.component_item_description,
            'blend_total_qty_needed' : shortage.three_wk_short,
            'blend_first_shortage' : shortage.starttime,
            'component_usage' : shortage.component_usage
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

    if (PoPurchaseOrderDetail.objects.filter(itemcode__icontains=limiting_factor_item_code, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            next_shipment_date = PoPurchaseOrderDetail.objects.filter(
                itemcode__icontains = limiting_factor_item_code,
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
        .filter(quantityreceived=0)

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

def display_partial_tote_label(request):
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
    label_blob = request.FILES.get('labelBlob')
    zpl_string = ZebrafyImage(label_blob.read(),invert=True).to_zpl()
    label_quantity = int(request.POST.get('labelQuantity', 0))
    # zpl_command = build_zpl_command(request)
    # print(zpl_string)
    # Send ZPL command to Zebra device
    if this_zebra_device is not None:
        for i in range(label_quantity):
            this_zebra_device.send(zpl_string)
    print("uwu")

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
