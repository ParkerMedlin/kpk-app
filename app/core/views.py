import urllib
import math
import datetime as dt
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms.models import modelformset_factory, inlineformset_factory
from django.http import HttpResponseRedirect, JsonResponse, StreamingHttpResponse
from rest_framework import viewsets
from django.utils.http import urlencode
from django.core.paginator import Paginator
import base64
from .models import *
from .forms import *
from .serializers import *
from django.db.models import Q
from lxml import html
from django.core.serializers import json
import requests
from core import taskfunctions
from django_q.tasks import async_task, result



class BlendBillOfMaterialsViewSet(viewsets.ModelViewSet):
    queryset = BlendBillOfMaterials.objects.all()
    serializer_class = BlendBillOfMaterialsSerializer
class BlendInstructionViewSet(viewsets.ModelViewSet):
    queryset = BlendInstruction.objects.all()
    serializer_class = BlendInstructionSerializer
class CountRecordViewSet(viewsets.ModelViewSet):
    queryset = CountRecord.objects.all()
    serializer_class = CountRecordSerializer
class BlendTheseViewSet(viewsets.ModelViewSet):
    queryset = BlendThese.objects.all()
    serializer_class = BlendTheseSerializer
class BmBillDetailViewSet(viewsets.ModelViewSet):
    queryset = BmBillDetail.objects.all()
    serializer_class = BmBillDetailSerializer
class BmBillHeaderViewSet(viewsets.ModelViewSet):
    queryset = BmBillHeader.objects.all()
    serializer_class = BmBillHeaderSerializer
class ChecklistSubmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = ChecklistSubmissionRecord.objects.all()
    serializer_class = ChecklistSubmissionTrackerSerializer
class ChecklistLogViewSet(viewsets.ModelViewSet):
    queryset = ChecklistLog.objects.all()
    serializer_class = ChecklistLogSerializer
class CiItemViewSet(viewsets.ModelViewSet):
    queryset = CiItem.objects.all()
    serializer_class = CiItemSerializer
class ImItemCostViewSet(viewsets.ModelViewSet):
    queryset = ImItemCost.objects.all()
    serializer_class = ImItemCostSerializer
class ImItemTransactionHistoryViewSet(viewsets.ModelViewSet):
    queryset = ImItemTransactionHistory.objects.all()
    serializer_class = ImItemTransactionHistorySerializer
class ImItemWarehouseViewSet(viewsets.ModelViewSet):
    queryset = ImItemWarehouse.objects.all()
    serializer_class = ImItemWarehouseSerializer
class LotNumRecordViewSet(viewsets.ModelViewSet):
    queryset = LotNumRecord.objects.all()
    serializer_class = LotNumRecordSerializer
class PoPurchaseOrderDetailViewSet(viewsets.ModelViewSet):
    queryset = PoPurchaseOrderDetail.objects.all()
    serializer_class = PoPurchaseOrderDetailSerializer
class ProdBillOfMaterialsViewSet(viewsets.ModelViewSet):
    queryset = ProdBillOfMaterials.objects.all()
    serializer_class = ProdBillOfMaterialsSerializer 
class TimetableRunDataViewSet(viewsets.ModelViewSet):
    queryset = TimetableRunData.objects.all()
    serializer_class = TimetableRunDataSerializer 
class UpcomingBlendCountViewSet(viewsets.ModelViewSet):
    queryset = UpcomingBlendCount.objects.all()
    serializer_class = UpcomingBlendCountSerializer

def get_json_forklift_serial(request):
    if request.method == "GET":
        forklift_unit_number = request.GET.get('unit_number', 0)
        forklift = Forklift.objects.get(unit_number=forklift_unit_number)
    return JsonResponse(forklift.serial_no, safe=False)

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
            return HttpResponseRedirect('/core/forkliftchecklist?submitted=True')
        else:
            return render(request, 'core/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})
    else:
        checklist_form = ChecklistLogForm
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})

def display_blend_these(request):
    blend_these_queryset = BlendThese.objects.all().order_by('starttime')
    foam_factor_is_populated = FoamFactor.objects.all().exists()
    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()
    for blend in blend_these_queryset:
        if desk_one_queryset.filter(blend_pn__iexact=blend.blend_pn).exists():
            blend.schedule_value = 'Desk 1'
        elif desk_two_queryset.filter(blend_pn__iexact=blend.blend_pn).exists():
            blend.schedule_value = 'Desk 2'
        else:
            blend.schedule_value = 'Not Scheduled'

    submitted=False
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number

    lot_form = LotNumRecordForm(initial={'lot_number':next_lot_number, 'date_created':today,})

    return render(request, 'core/blendshortages.html', {
        'blend_these_queryset': blend_these_queryset,
        'foam_factor_is_populated' : foam_factor_is_populated,
        'submitted' : submitted,
        'lot_form' : lot_form})

def delete_lot_num_records(request, records_to_delete):
    items_to_delete_bytestr = base64.b64decode(records_to_delete)
    items_to_delete_str = items_to_delete_bytestr.decode()
    items_to_delete_list = list(items_to_delete_str.replace('[', '').replace(']', '').replace('"', '').split(","))

    for item in items_to_delete_list:
        if LotNumRecord.objects.filter(pk=item).exists():
            selected_count = LotNumRecord.objects.get(pk=item)
            selected_count.delete()

    return redirect('display-lot-num-records')

def display_lot_num_records(request):
    submitted=False
    load_edit_modal = False
    load_add_modal = False
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number

    if request.method == "GET":
        edit_yesno = request.GET.get('edit_yesno', 0)
        lot_id = request.GET.get('lot_id', 0)
        if request.GET.get('load_add_modal', 0)=="True":
            load_add_modal = True
        lot_number_to_edit = ""
        lot_form = LotNumRecordForm(initial={'lot_number' : next_lot_number, 'date_created' : today})

        if edit_yesno == 'yes' and LotNumRecord.objects.filter(pk=lot_id).exists():
            load_edit_modal = True
            lot_number_to_edit = LotNumRecord.objects.get(pk=lot_id)
            lot_form = LotNumRecordForm(instance=lot_number_to_edit)
        else:
            edit_yesno = 'no'

        if 'submitted' in request.GET:
            submitted=True

    lot_num_queryset = LotNumRecord.objects.order_by('-date_created', '-lot_number')

    lot_num_paginator = Paginator(lot_num_queryset, 25)
    page_num = request.GET.get('page')
    current_page = lot_num_paginator.get_page(page_num)
    lotnum_list = []
    for lot in current_page:
        lotnum_list.append(lot.lot_number)
    im_itemcost_queryset = ImItemCost.objects.filter(receiptno__in=lotnum_list)
    for lot in current_page:
        if im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).exists():
            lot.qty_on_hand = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().quantityonhand)
            lot.date_entered = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().transactiondate)
        else:
            lot.qty_on_hand = None
            lot.date_entered = None

    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()
    for lot in current_page:
        if desk_one_queryset.filter(lot__iexact=lot.lot_number).exists():
            lot.schedule_value = 'Desk_1'
        elif desk_two_queryset.filter(lot__iexact=lot.lot_number).exists():
            lot.schedule_value = 'Desk_2'
        elif lot.line != 'Prod':
            lot.schedule_value = lot.line
        else:
            lot.schedule_value = 'Not Scheduled'

    add_to_deskone = DeskOneScheduleForm(prefix="deskone")
    add_to_desktwo = DeskTwoScheduleForm(prefix="desktwo")

    context = {
        'add_to_deskone' : add_to_deskone,
        'add_to_desktwo' : add_to_desktwo,
        'lot_form' : lot_form,
        'edit_yesno' : edit_yesno,
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

def update_lot_num_record(request, lot_num_id):
    if request.method == "POST":
        lot_num_record = get_object_or_404(LotNumRecord, id = lot_num_id)
        edit_lot_form = LotNumRecordForm(request.POST or None, instance=lot_num_record)

        if edit_lot_form.is_valid():
            edit_lot_form.save()

        return HttpResponseRedirect('/core/lotnumrecords')

def add_lot_num_record(request):
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number
    blend_instruction_queryset = BlendInstruction.objects.order_by('blend_part_num', 'step_no')

    if 'addNewLotNumRecord' in request.POST:
        new_lot_form = LotNumRecordForm(request.POST)
        if new_lot_form.is_valid():
            new_lot_submission = new_lot_form.save(commit=False)
            new_lot_submission.date_created = today
            new_lot_submission.lot_number = next_lot_number
            new_lot_submission.save()
            these_blend_instructions = blend_instruction_queryset.filter(blend_part_num__icontains=new_lot_submission.part_number)
            for step in these_blend_instructions:
                if step.step_qty == '':
                    this_step_qty = ''
                else:
                    this_step_qty = float(step.step_qty) * float(new_lot_submission.quantity)
                new_step = BlendingStep(
                    step_no = step.step_no,
                    step_desc = step.step_desc,
                    step_qty = this_step_qty,
                    step_unit = step.step_unit,
                    qty_added = "",
                    component_item_code = step.component_item_code,
                    notes_1 = step.notes_1,
                    notes_2 = step.notes_2,
                    blend_part_num = step.blend_part_num,
                    blend_desc = new_lot_submission.description,
                    ref_no = step.ref_no,
                    prepared_by = step.prepared_by,
                    prepared_date = step.prepared_date,
                    lbs_per_gal = step.lbs_per_gal,
                    blend_lot_number = new_lot_submission.lot_number,
                    lot = new_lot_submission
                    )
                new_step.save()
            new_lot_submission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
        else: 
            return HttpResponseRedirect('/')

def display_new_lot_form(request):
    submitted=False
    today = dt.datetime.now()
    next_lot_number = chr(64 + dt.datetime.now().month)+str(dt.datetime.now().year % 100)+str(int(str(LotNumRecord.objects.order_by('-date_created')[0])[-4:])+1).zfill(4)
    blend_instruction_queryset = BlendInstruction.objects.order_by('blend_part_num', 'step_no')
    ci_item_queryset = CiItem.objects.filter(itemcodedesc__startswith="BLEND-")
    if request.method == "POST":
        new_lot_form = LotNumRecordForm(request.POST)
        if new_lot_form.is_valid():
            new_lot_submission = new_lot_form.save(commit=False)
            new_lot_submission.date_created = today
            new_lot_submission.lot_number = next_lot_number
            new_lot_submission.save()
            these_blend_instructions = blend_instruction_queryset.filter(blend_part_num__icontains=new_lot_submission.part_number)
            for step in these_blend_instructions:
                if step.step_qty == '':
                    this_step_qty = ''
                else:
                    this_step_qty = float(step.step_qty) * float(new_lot_submission.quantity)
                new_step = BlendingStep(
                    step_no = step.step_no,
                    step_desc = step.step_desc,
                    step_qty = this_step_qty,
                    step_unit = step.step_unit,
                    qty_added = "",
                    component_item_code = step.component_item_code,
                    notes_1 = step.notes_1,
                    notes_2 = step.notes_2,
                    blend_part_num = step.blend_part_num,
                    blend_desc = new_lot_submission.description,
                    ref_no = step.ref_no,
                    prepared_by = step.prepared_by,
                    prepared_date = step.prepared_date,
                    lbs_per_gal = step.lbs_per_gal,
                    blend_lot_number = new_lot_submission.lot_number,
                    lot = new_lot_submission
                    )
                new_step.save()
            new_lot_submission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        new_lot_form = LotNumRecordForm(initial={'lot_number':next_lot_number, 'date_created':today,})
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/lotnumform.html', {'new_lot_form':new_lot_form, 'submitted':submitted, 'next_lot_number':next_lot_number, 'ci_item_queryset':ci_item_queryset,})

def get_json_from_item_code(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_BOM_item = BlendBillOfMaterials.objects.filter(component_itemcode__iexact=item_code).first()
        response_item = {
            "itemcode" : requested_BOM_item.component_itemcode,
            "description" : requested_BOM_item.component_desc
            }
    return JsonResponse(response_item, safe=False)

def get_json_from_item_desc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_BOM_item = BlendBillOfMaterials.objects.filter(component_desc__iexact=item_desc).first()
        response_item = {
            "itemcode" : requested_BOM_item.component_itemcode,
            "description" : requested_BOM_item.component_desc
            }
    return JsonResponse(response_item, safe=False)

@login_required
def display_blend_sheet(request, lot):
    submitted=False
    this_lot = LotNumRecord.objects.get(lot_number=lot)
    blend_steps = BlendingStep.objects.filter(blend_lot_number__icontains=lot)
    first_step = blend_steps.first()

    blend_components = BlendBillOfMaterials.objects.filter(bill_no=this_lot.part_number)
    for component in blend_components:
        quantity_required = 0
        for step in blend_steps.filter(component_item_code__icontains=component.component_itemcode):
            quantity_required+=float(step.step_qty)
        component.qtyreq = quantity_required
        component_locations = ChemLocation.objects.filter(part_number=component.component_itemcode)
        component.area = component_locations.first().generallocation
        component.location = component_locations.first().specificlocation

    formset_instance = modelformset_factory(BlendingStep, form=BlendingStepForm, extra=0)
    this_lot_formset = formset_instance(request.POST or None, queryset=blend_steps)
    
    if request.method == 'POST':
        print(this_lot_formset)
        if this_lot_formset.is_valid():
            this_lot_formset.save()
            
            return HttpResponseRedirect('/core/blendsheetcomplete')
        else:
            this_lot_formset = formset_instance(request.POST or None, queryset=blend_steps)
            if 'submitted' in request.GET:
                submitted=True

    return render(request, 'core/blendsheet.html',
                { 'blend_steps': blend_steps,
                'submitted': submitted,
                'this_lot': this_lot,
                'blend_components': blend_components,
                'first_step': first_step,
                'this_lot_formset': this_lot_formset
                })

def display_conf_blend_sheet_complete(request):
    return render(request, 'core/blendsheetcomplete.html')

def display_report_center(request):
    blends_needed = BlendThese.objects.all()
    part_nums_blends_needed = []
    for blend in blends_needed:
        part_nums_blends_needed.append(blend.blend_pn)
    bom_blends_needed = BlendBillOfMaterials.objects.filter(bill_no__in=part_nums_blends_needed)
    for component in bom_blends_needed:
        component.blendQtyShortThreeWk = blends_needed.filter(blend_pn__icontains=component.bill_no).first().three_wk_short
        component.chemRequiredThreeWk = float(component.blendQtyShortThreeWk) * float(component.qtyperbill)
        component.chemShortThreeWk = float(component.qtyonhand) - component.chemRequiredThreeWk
    blends_needed_components = bom_blends_needed
    return render(request, 'core/reportcenter.html', {'blends_needed_components' : blends_needed_components})

def display_report(request, which_report, part_number):
    if which_report=="Lot-Numbers":
        no_lots_found = False
        lot_num_queryset = LotNumRecord.objects.filter(part_number__iexact=part_number).order_by('-date_created', '-lot_number')

        lot_num_paginator = Paginator(lot_num_queryset, 25)
        page_num = request.GET.get('page')
        current_page = lot_num_paginator.get_page(page_num)

        im_itemcost_queryset = ImItemCost.objects.filter(itemcode__iexact=part_number)
        for lot in current_page:
            if im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).exists():
                lot.qty_on_hand = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().quantityonhand)
                lot.date_entered = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().transactiondate)
            else:
                lot.qty_on_hand = None
                lot.date_entered = None

        if lot_num_queryset.exists():
            description = lot_num_queryset.first().description
        else:
            no_lots_found = True
            description = ''

        blend_info = {'part_number' : part_number, 'description' : description}

        return render(request, 'core/reports/lotnumsreport.html', {'no_lots_found' : no_lots_found, 'current_page' : current_page, 'blend_info': blend_info})

    elif which_report=="All-Upcoming-Runs":
        no_runs_found = False
        upcoming_runs = TimetableRunData.objects.filter(blend_pn__icontains=part_number).order_by('starttime')
        if upcoming_runs.exists():
            description = upcoming_runs.first().blend_desc
        else:
            no_runs_found = True
            description = ''
        blend_info = {'part_number' : part_number, 'desc' : description}
        return render(request, 'core/reports/upcomingrunsreport.html', {'no_runs_found' : no_runs_found, 'upcoming_runs' : upcoming_runs, 'blend_info' : blend_info})

    elif which_report=="Chem-Shortage":
        no_shortage_found = False
        blend_list = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number)
        blend_pn_list = []
        for item in blend_list:
            blend_pn_list.append(item.bill_no)
        prod_run_list = TimetableRunData.objects.filter(blend_pn__in=blend_pn_list,oh_after_run__lt=0).order_by('starttime')
        running_chem_total = 0.0
        for run in prod_run_list:
            single_bill = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number,bill_no__icontains=run.blend_pn).first()
            run.chem_factor = single_bill.qtyperbill
            run.chem_needed_for_run = float(run.chem_factor) * float(run.adjustedrunqty)
            running_chem_total = running_chem_total + float(run.chem_factor * run.adjustedrunqty)
            run.chem_oh_after_run = float(single_bill.qtyonhand) - running_chem_total
            run.chemUnit = single_bill.standard_uom
        
        if BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).exists():
            item_info = {
                    'item_pn' : BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_itemcode,
                    'item_desc' : BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_desc
                    }
        else:
            no_shortage_found = True
            item_info = {}
        return render(request, 'core/reports/chemshortagereport.html', {'no_shortage_found' : no_shortage_found, 'prod_run_list' : prod_run_list, 'item_info' : item_info})

    elif which_report=="Startron-Runs":
        startron_blend_part_nums = ["14000.B", "14308.B", "14308AMBER.B", "93100DSL.B", "93100GAS.B", "93100TANK.B", "93100GASBLUE.B", "93100GASAMBER.B"]
        startron_runs = TimetableRunData.objects.filter(blend_pn__in=startron_blend_part_nums)
        return render(request, 'core/reports/startronreport.html', {'startron_runs' : startron_runs})

    elif which_report=="Transaction-History":
        no_transactions_found = False
        if ImItemTransactionHistory.objects.filter(itemcode__icontains=part_number).exists():
            transactions_list = ImItemTransactionHistory.objects.filter(itemcode__icontains=part_number).order_by('-transactiondate')
            description = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_desc
        else: 
            no_transactions_found = True
            transactions_list = {}
            description = ''
        for item in transactions_list:
            item.description = description
        iteminfo = {'part_number' : part_number, 'description' : description}
        return render(request, 'core/reports/transactionsreport.html', {'no_transactions_found' : no_transactions_found, 'transactions_list' : transactions_list, 'iteminfo': iteminfo})
        
    elif which_report=="Count-History":
        counts_not_found = False
        if CountRecord.objects.filter(part_number__icontains=part_number).exists():
            blend_count_records = CountRecord.objects.filter(part_number__icontains=part_number)
        else:
            counts_not_found = True
            blend_count_records = {}
        item_info = {
                    'part_number' : part_number,
                    'part_desc' : BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_desc
                    }
        return render(request, 'core/reports/inventorycountsreport.html', {'counts_not_found' : counts_not_found, 'blend_count_records' : blend_count_records, 'item_info' : item_info})

    elif which_report=="Counts-And-Transactions":
        counts_and_transactions = { 'currentstatus': 'workin on it'}
        return render(request, 'core/reports/countsandtransactionsreport.html', {'counts_and_transactions' : counts_and_transactions})
    
    else:
        return render(request, '')

def add_deskone_schedule_item(request):
    if request.method == "POST":
        new_schedule_item_form = DeskOneScheduleForm(request.POST, prefix='deskone')
        if new_schedule_item_form.is_valid():
            new_schedule_item_form.save()

    return redirect('display-lot-num-records')

def add_desktwo_schedule_item(request):
    if request.method == "POST":
        new_schedule_item_form = DeskTwoScheduleForm(request.POST, prefix='desktwo')
        if new_schedule_item_form.is_valid():
            new_schedule_item_form.save()

    return redirect('display-lot-num-records')

def display_blend_schedule(request, blendarea):
    submitted=False
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number
    blend_instruction_queryset = BlendInstruction.objects.order_by('blend_part_num', 'step_no')

    if request.method == "POST":
        lot_form = LotNumRecordForm(request.POST)
    
        if lot_form.is_valid():
            new_lot_submission = lot_form.save(commit=False)
            new_lot_submission.date_created = today
            new_lot_submission.lot_number = next_lot_number
            new_lot_submission.save()
            these_blend_instructions = blend_instruction_queryset.filter(blend_part_num__icontains=new_lot_submission.part_number)
            for step in these_blend_instructions:
                if step.step_qty == '':
                    this_step_qty = ''
                else:
                    this_step_qty = float(step.step_qty) * float(new_lot_submission.quantity)
                new_step = BlendingStep(
                    step_no = step.step_no,
                    step_desc = step.step_desc,
                    step_qty = this_step_qty,
                    step_unit = step.step_unit,
                    qty_added = "",
                    component_item_code = step.component_item_code,
                    notes_1 = step.notes_1,
                    notes_2 = step.notes_2,
                    blend_part_num = step.blend_part_num,
                    blend_desc = new_lot_submission.description,
                    ref_no = step.ref_no,
                    prepared_by = step.prepared_by,
                    prepared_date = step.prepared_date,
                    lbs_per_gal = step.lbs_per_gal,
                    blend_lot_number = new_lot_submission.lot_number,
                    lot = new_lot_submission
                    )
                new_step.save()
            new_lot_submission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        lot_form = LotNumRecordForm(initial={'lot_number':next_lot_number, 'date_created':today,})
        if 'submitted' in request.GET:
            submitted=True

    desk_one_blends = DeskOneSchedule.objects.all().order_by('order')
    if desk_one_blends.exists():
        for blend in desk_one_blends:
            try:
                blend.when_entered = ImItemCost.objects.get(receiptno=blend.blend_pn)
            except ImItemCost.DoesNotExist:
                blend.when_entered = "Not Entered"
            if BlendThese.objects.filter(blend_pn__iexact=blend.blend_pn).exists():
                blend.threewkshort = BlendThese.objects.filter(blend_pn__iexact=blend.blend_pn).first().three_wk_short
                blend.hourshort = BlendThese.objects.filter(blend_pn__iexact=blend.blend_pn).first().starttime
            else:
                blend.threewkshort = ""
            
    desk_two_blends = DeskTwoSchedule.objects.all()
    if desk_two_blends.exists():
        for blend in desk_two_blends:
            try:
                blend.when_entered = ImItemCost.objects.get(receiptno=blend.blend_pn)
            except ImItemCost.DoesNotExist:
                blend.when_entered = "Not Entered"
            if BlendThese.objects.filter(blend_pn__iexact=blend.blend_pn).exists():
                blend.threewkshort = BlendThese.objects.filter(blend_pn__iexact=blend.blend_pn).first().three_wk_short
                blend.hourshort = BlendThese.objects.filter(blend_pn__iexact=blend.blend_pn).first().starttime
            else: 
                blend.threewkshort = "No Shortage"
    
    blend_BOM = BlendBillOfMaterials.objects.all()
    horix_blends = HorixBlendThese.objects.filter(line__icontains='Hx')
    if horix_blends:
        for item in horix_blends:
            this_blend = blend_BOM.filter(bill_no__iexact=item.pn).filter(component_desc__icontains="BLEND-").first()
            item.itemcode = this_blend.component_itemcode
            item.blend_desc = this_blend.component_desc
    drum_blends = HorixBlendThese.objects.filter(line__icontains='Dm')
    if drum_blends:
        for item in drum_blends:
            this_blend = blend_BOM.filter(bill_no__iexact=item.pn).filter(component_desc__icontains="BLEND-").first()
            item.itemcode = this_blend.component_itemcode
            item.blend_desc = this_blend.component_desc
    tote_blends = HorixBlendThese.objects.filter(line__icontains='Totes')
    if tote_blends:
        for item in tote_blends:
            this_blend = blend_BOM.filter(bill_no__iexact=item.pn).filter(component_desc__icontains="BLEND-").first()
            item.itemcode = this_blend.component_itemcode
            item.blend_desc = this_blend.component_desc

    blend_area = blendarea
    return render(request, 'core/blendschedule.html', {'desk_one_blends': desk_one_blends,
                                                        'desk_two_blends': desk_two_blends,
                                                        'horix_blends': horix_blends,
                                                        'drum_blends': drum_blends,
                                                        'tote_blends': tote_blends,
                                                        'blend_area': blend_area,
                                                        'lot_form' : lot_form,
                                                        'submitted' : submitted})

def manage_blend_schedule(request, request_type, blend_area, blend_id, blend_list_position):
    if blend_area == 'Desk_1':
        blend = DeskOneSchedule.objects.get(pk=blend_id)
    elif blend_area == 'Desk_2':
        blend = DeskTwoSchedule.objects.get(pk=blend_id)

    if request_type == 'moveupone':
        blend.up()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if request_type == 'movedownone':
        blend.down()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if request_type == 'movetotop':
        blend.top()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if request_type == 'movetobottom':
        blend.bottom()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if request_type == 'delete':
        blend.delete()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)

def display_batch_issue_table(request, line):
    all_prod_runs = IssueSheetNeeded.objects.all()
    if line == 'INLINE':
        prod_runs_this_line = all_prod_runs.filter(prodline__icontains='INLINE').order_by('starttime')
    if line == 'PDLINE':
        prod_runs_this_line = all_prod_runs.filter(prodline__icontains='PD LINE').order_by('starttime')
    if line == 'JBLINE':
        prod_runs_this_line = all_prod_runs.filter(prodline__icontains='JB LINE').order_by('starttime')
    if line == 'all':
        prod_runs_this_line = all_prod_runs.order_by('prodline','starttime')
    date_today = date.today().strftime('%m/%d/%Y')

    return render(request, 'core/batchissuetable.html', {'prod_runs_this_line' : prod_runs_this_line, 'line' : line, 'dateToday' : date_today})

def display_issue_sheets(request, prod_line, issue_date):
    all_prod_runs = IssueSheetNeeded.objects.all()
    prod_runs_this_line = all_prod_runs.filter(prodline__icontains=prod_line).order_by('starttime')
    
    return render(request, 'core/issuesheets.html', {'prod_runs_this_line' : prod_runs_this_line, 'prod_line' : prod_line, 'issue_date' : issue_date})

def display_upcoming_counts(request):
    submitted=False
    upcoming_blends = UpcomingBlendCount.objects.all().order_by('starttime')
    blend_these_table = BlendThese.objects.all()
    for blend in upcoming_blends:
        if BlendThese.objects.filter(blend_pn__icontains = blend.itemcode).exists():
            blend.short_hour = blend_these_table.get(blend_pn = blend.itemcode).starttime
        else:
            blend.short_hour = 0

    two_weeks_past = dt.date.today() - dt.timedelta(weeks = 2)
    for blend in upcoming_blends:
        if (blend.last_count_date) and (blend.last_transaction_date):
            if blend.last_count_date < blend.last_transaction_date:
                blend.needs_count = True
            elif blend.last_count_date < two_weeks_past:
                blend.needs_count = True
            else:
                blend.needs_count = False

    return render(request, 'core/inventorycounts/upcomingblends.html', {'upcoming_blends' : upcoming_blends})

def add_count_list(request, encoded_partnumber_list, encoded_pk_list):
    submitted=False
    part_numbers_bytestr = base64.b64decode(encoded_partnumber_list)
    part_numbers_str = part_numbers_bytestr.decode()
    part_numbers_list = list(part_numbers_str.replace('[', '').replace(']', '').replace('"', '').split(","))

    primary_keys_bytestr = base64.b64decode(encoded_pk_list)
    primary_key_str = primary_keys_bytestr.decode()
    primary_key_list = list(primary_key_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    if (primary_key_list[0] == "No_Part_Numbers"):
        primary_key_str = ''
    else:
        primary_key_str = primary_key_str.replace('[', '').replace(']', '').replace('"', '')
        primary_key_str += ','

    for part_num in part_numbers_list:
        this_bill = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_num).first()
        new_count_record = CountRecord(
            part_number = part_num,
            part_description = this_bill.component_desc,
            expected_quantity = this_bill.qtyonhand,
            counted_quantity = 0,
            counted_date = dt.date.today(),
            variance = 0
        )
        new_count_record.save()
        primary_key_str+=str(new_count_record.pk) + ','

    primary_key_str = primary_key_str[:-1]
    primary_key_str_bytes = primary_key_str.encode('UTF-8')
    encoded_primary_key_bytes = base64.b64encode(primary_key_str_bytes)
    encoded_primary_key_str = encoded_primary_key_bytes.decode('UTF-8')

    return HttpResponseRedirect('/core/countlist/display/' + encoded_primary_key_str)

def display_count_list(request, encoded_pk_list):
    submitted=False
    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    
    these_count_records = CountRecord.objects.filter(pk__in=count_ids_list)
    expected_quantities = {}
    for count_record in these_count_records:
        item_unit_of_measure = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=count_record.part_number).first().standard_uom
        count_record.standard_uom = item_unit_of_measure
        expected_quantities[count_record.id] = count_record.expected_quantity

    todays_date = dt.date.today()
    
    formset_instance = modelformset_factory(CountRecord, form=CountRecordForm, extra=0)
    these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)

    if request.method == 'POST':
        if these_counts_formset.is_valid():
            these_counts_formset.save()
            return HttpResponseRedirect('/core/countrecords/?page=1')
    else:
        these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/inventorycounts/countlist.html', {
                         'submitted' : submitted,
                         'todays_date' : todays_date,
                         'these_counts_formset' : these_counts_formset,
                         'encoded_list' : encoded_pk_list,
                         'expected_quantities' : expected_quantities
                         })

def display_count_records(request):
    count_record_queryset = CountRecord.objects.order_by('-id')
    count_record_paginator = Paginator(count_record_queryset, 25)
    page_num = request.GET.get('page')
    current_page = count_record_paginator.get_page(page_num)

    return render(request, 'core/inventorycounts/countrecords.html', {'current_page' : current_page})

def delete_count_record(request, redirect_page, items_to_delete, all_items):
    items_to_delete_bytestr = base64.b64decode(items_to_delete)
    items_to_delete_str = items_to_delete_bytestr.decode()
    items_to_delete_list = list(items_to_delete_str.replace('[', '').replace(']', '').replace('"', '').split(","))

    all_items_bytestr = base64.b64decode(all_items)
    all_items_str = all_items_bytestr.decode()
    all_items_list = list(all_items_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    
    for item in items_to_delete_list:
        if CountRecord.objects.filter(pk=item).exists():
            selected_count = CountRecord.objects.get(pk=item)
            selected_count.delete()
        all_items_list.remove(item)
    
    if (redirect_page=='countrecords'):
        return redirect('display-count-records')

    if (redirect_page=='countlist'):
        all_items_str=''
        for count_id in all_items_list:
            all_items_str+=count_id + ','
        all_items_str = all_items_str[:-1]
        all_items_str_bytes = all_items_str.encode('UTF-8')
        encoded_all_items_bytes = base64.b64encode(all_items_str_bytes)
        encoded_all_items_str = encoded_all_items_bytes.decode('UTF-8')
        if encoded_all_items_str == '':
            return HttpResponseRedirect('/core/countrecords')
        else:
            return HttpResponseRedirect('/core/countlist/display/' + encoded_all_items_str)

def display_count_report(request, encoded_pk_list):

    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    count_records_queryset = CountRecord.objects.filter(pk__in=count_ids_list)

    return render(request, 'core/inventorycounts/finishedcounts.html', {'count_records_queryset' : count_records_queryset})

def display_all_upcoming_production(request):
    upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime')
    upcoming_runs_paginator = Paginator(upcoming_runs_queryset, 25)
    page_num = request.GET.get('page')
    current_page = upcoming_runs_paginator.get_page(page_num)
    return render(request, 'core/productionblendruns.html', {'current_page' : current_page})

def display_chem_shortages(request):
    is_shortage = False
    blends_used_upcoming = BlendThese.objects.all()
    blends_upcoming_partnums = list(BlendThese.objects.values_list('blend_pn', flat=True))
    chems_used_upcoming = BlendBillOfMaterials.objects.filter(bill_no__in=blends_upcoming_partnums)
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)
    for chem in chems_used_upcoming:
        chem.blend_req_onewk = blends_used_upcoming.filter(blend_pn__icontains=chem.bill_no).first().one_wk_short
        chem.blend_req_twowk = blends_used_upcoming.filter(blend_pn__icontains=chem.bill_no).first().two_wk_short
        chem.blend_req_threewk = blends_used_upcoming.filter(blend_pn__icontains=chem.bill_no).first().three_wk_short
        chem.required_qty = chem.blend_req_threewk * chem.qtyperbill
        chem.oh_minus_required = chem.qtyonhand - chem.required_qty
        chem.max_possible_blend = chem.qtyonhand / chem.qtyperbill
        if (PoPurchaseOrderDetail.objects.filter(itemcode__icontains=chem.component_itemcode, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            chem.next_delivery = PoPurchaseOrderDetail.objects.filter(
                itemcode__icontains=chem.component_itemcode,
                quantityreceived__exact=0,
                requireddate__gt=yesterday_date
                ).order_by('requireddate').first().requireddate
        else:
            chem.next_delivery = "N/A"
        if (chem.oh_minus_required < 0 and chem.component_itemcode != "030143"):
            is_shortage = True
        
    chems_used_paginator = Paginator(chems_used_upcoming, 5)
    page_num = request.GET.get('page')
    current_page = chems_used_paginator.get_page(page_num)

    return render(request, 'core/chemshortages.html',
        {'chems_used_upcoming' : chems_used_upcoming,
         'is_shortage' : is_shortage,
         'blends_upcoming_partnums' : blends_upcoming_partnums,
         'blends_used_upcoming' : blends_used_upcoming,
         'current_page' : current_page
         })

def get_json_chemloc_from_itemcode(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_BOM_item = BlendBillOfMaterials.objects.filter(component_itemcode__iexact=item_code).first()
        itemcode = requested_BOM_item.component_itemcode
        description = requested_BOM_item.component_desc
        qty_on_hand = round(requested_BOM_item.qtyonhand, 2)
        standard_uom = requested_BOM_item.standard_uom
        
        if ChemLocation.objects.filter(part_number=item_code).exists():
            requested_item = ChemLocation.objects.get(part_number=item_code)
            specific_location = requested_item.specificlocation
            general_location = requested_item.generallocation
        else:
            specific_location = "no location listed."
            general_location = "Check with Parker"

        response_item = {
            "itemcode" : itemcode,
            "description" : description,
            "specific_location" : specific_location,
            "general_location" : general_location,
            "qtyonhand" : qty_on_hand,
            "standard_uom" : standard_uom
        }
    return JsonResponse(response_item, safe=False)

def get_json_chemloc_from_itemdesc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_BOM_item = BlendBillOfMaterials.objects.filter(component_desc__iexact=item_desc).first()
        itemcode = requested_BOM_item.component_itemcode
        description = requested_BOM_item.component_desc
        qty_on_hand = round(requested_BOM_item.qtyonhand, 2)
        standard_uom = requested_BOM_item.standard_uom
        
        if ChemLocation.objects.filter(part_number=itemcode).exists():
            requested_item = ChemLocation.objects.get(part_number=itemcode)
            specific_location = requested_item.specificlocation
            general_location = requested_item.generallocation
        else:
            specific_location = "no location listed."
            general_location = "Check with Parker"

        response_item = {
            "itemcode" : itemcode,
            "description" : description,
            "specific_location" : specific_location,
            "general_location" : general_location,
            "qtyonhand" : qty_on_hand,
            "standard_uom" : standard_uom
        }
    return JsonResponse(response_item, safe=False)

def display_lookup_location(request):
    itemcode_queryset = list(BlendBillOfMaterials.objects
                            .order_by('component_itemcode')
                            .distinct('component_itemcode')
                            )

    return render(request, 'core/lookuppages/lookuplocation.html', {'itemcode_queryset' : itemcode_queryset})

def get_json_tank_specs(request):
    if request.method == "GET":
        tank_queryset = StorageTank.objects.all()
        tank_dict = {}
        for tank in tank_queryset:
            tank_dict[tank.tank_label_vega] = {
                'part_number' : tank.part_number,
                'part_desc' : tank.part_desc,
                'max_gallons' : tank.max_gallons
            }

        data = tank_dict

    return JsonResponse(data, safe=False)

def display_tank_levels(request):
    tank_queryset = StorageTank.objects.all()
    
    return render(request, 'core/tanklevels.html', {'tank_queryset' : tank_queryset})

def get_tank_levels_html(request):
    if request.method == "GET":
        fp = urllib.request.urlopen('http://192.168.178.210/fieldDeviceData.htm')
        html_str = fp.read().decode("utf-8")
        fp.close()
        html_str = urllib.parse.unquote(html_str)
        response_json = { 'html_string' : html_str }

    return JsonResponse(response_json, safe=False)

def display_lookup_lotnums(request):
    itemcode_queryset = list(BlendBillOfMaterials.objects
                            .order_by('component_itemcode')
                            .distinct('component_itemcode')
                            )

    return render(request, 'core/lookuppages/lookuplotnums.html', {'itemcode_queryset' : itemcode_queryset})

def get_json_blendBOM_fields(request):
    if request.method == "GET":
        blend_bom_queryset = BlendBillOfMaterials.objects.all().distinct('component_itemcode')
        if request.GET.get('restriction', 0)=='blends-only':
            blend_bom_queryset = blend_bom_queryset.filter(component_desc__icontains="BLEND")
        if request.GET.get('restriction', 0)=='no-blends':
            blend_bom_queryset = blend_bom_queryset.exclude(component_desc__icontains="BLEND")
        itemcode_list = []
        itemdesc_list = []
        for item in blend_bom_queryset:
            itemcode_list.append(item.component_itemcode)
            itemdesc_list.append(item.component_desc)

        blend_bom_json = {
            'itemcodes' : itemcode_list,
            'itemdescs' : itemdesc_list
        }

    return JsonResponse(blend_bom_json, safe=False)

def display_test_page(request):
    #taskfunctions.email_checklist_submission_tracking('views.py')
    taskfunctions.email_checklist_issues('views.py')
    #taskfunctions.update_checklist_tracker('views.py')
    today_date = date.today()
    wekdy = today_date.weekday()

    return render(request, 'core/testpage.html', {'wekdy' : wekdy})