import urllib
import datetime as dt
from datetime import date
from django.shortcuts import render
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
import requests


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
    return render(request, 'core/blendthese.html', {'blend_these_queryset': blend_these_queryset,})

def display_lot_num_records(request):
    lot_num_queryset = LotNumRecord.objects.order_by('-date_created')
    lot_num_paginator = Paginator(lot_num_queryset, 25)
    page_num = request.GET.get('page')
    current_page = lot_num_paginator.get_page(page_num)

    return render(request, 'core/lotnumrecords.html', {'current_page' : current_page})

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

def get_json_item_description(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_item = CiItem.objects.get(itemcode=item_code)
    return JsonResponse(requested_item.itemcodedesc, safe=False)

@login_required
def display_blend_sheet(request, lot):
    submitted=False
    this_lot = LotNumRecord.objects.get(lot_number=lot)
    blend_steps = BlendingStep.objects.filter(blend_lot_number__icontains=lot)
    first_step = blend_steps.first()

    blend_components = BlendBillOfMaterials.objects.filter(bill_pn=this_lot.part_number)
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
    ci_item_queryset = CiItem.objects.filter(itemcodedesc__startswith="BLEND-") | CiItem.objects.filter(itemcodedesc__startswith="CHEM") | CiItem.objects.filter(itemcodedesc__startswith="FRAGRANCE") | CiItem.objects.filter(itemcodedesc__startswith="DYE")
    report_form = ReportForm
    blends_needed = BlendThese.objects.all()
    part_nums_blends_needed = []
    for blend in blends_needed:
        part_nums_blends_needed.append(blend.blend_pn)
    bom_blends_needed = BlendBillOfMaterials.objects.filter(bill_pn__in=part_nums_blends_needed)
    for component in bom_blends_needed:
        component.blendQtyShortThreeWk = blends_needed.filter(blend_pn__icontains=component.bill_pn).first().three_wk_short
        component.chemRequiredThreeWk = float(component.blendQtyShortThreeWk) * float(component.qtyperbill)
        component.chemShortThreeWk = float(component.qtyonhand) - component.chemRequiredThreeWk
    blends_needed_components = bom_blends_needed
    return render(request, 'core/reportcenter.html', {'report_form' : report_form, 'ci_item_queryset' : ci_item_queryset, 'blends_needed_components' : blends_needed_components})

def display_report(request, which_report, part_number):
    if which_report=="Lot-Numbers":
        no_lots_found = False
        lot_nums = LotNumRecord.objects.filter(part_number__icontains=part_number)
        if lot_nums.exists():
            description = lot_nums.first().description
        else:
            no_lots_found = True    
            description = ''
        blend_info = {'part_number' : part_number, 'description' : description}
        return render(request, 'core/reports/lotnumsreport.html', {'no_lots_found' : no_lots_found, 'lot_nums' : lot_nums, 'blend_info': blend_info})

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
            blend_pn_list.append(item.bill_pn)
        prod_run_list = TimetableRunData.objects.filter(blend_pn__in=blend_pn_list,oh_after_run__lt=0).order_by('starttime')
        running_chem_total = 0.0
        for run in prod_run_list:
            single_bill = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number,bill_pn__icontains=run.blend_pn).first()
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
    
def display_upcoming_counts(request):
    submitted=False
    upcoming_blends = UpcomingBlendCount.objects.all().order_by('starttime')
    blend_these_table = BlendThese.objects.all()
    for blend in upcoming_blends:
        if BlendThese.objects.filter(blend_pn__icontains = blend.blend_pn).exists():
            blend.short_hour = blend_these_table.get(blend_pn = blend.blend_pn).starttime
        else:
            blend.short_hour = 0
    eight_months_past = dt.date.today() - dt.timedelta(weeks = 36)
    transactions_list = ImItemTransactionHistory.objects.filter(transactiondate__gt=eight_months_past).order_by('-transactiondate')
    for blend in upcoming_blends:
        if CountRecord.objects.filter(part_number__icontains=blend.blend_pn).order_by('-counted_date').exists():
            blend.last_count = CountRecord.objects.filter(part_number__icontains=blend.blend_pn).order_by('-counted_date').first().counted_quantity
            blend.last_count_date = CountRecord.objects.filter(part_number__icontains=blend.blend_pn).order_by('-counted_date').first().counted_date
        else:
            blend.last_count = "n/a"
            blend.last_count_date = "n/a"
        if transactions_list.filter(itemcode__icontains=blend.blend_pn).exists():
            blend.last_transaction_type = transactions_list.filter(itemcode__icontains=blend.blend_pn).first().transactioncode
            blend.last_transaction_date = transactions_list.filter(itemcode__icontains=blend.blend_pn).first().transactiondate
        else:
            blend.last_transaction_type = "n/a"
            blend.last_transaction_date = "n/a"

    return render(request, 'core/upcomingblndcounts.html', {'upcoming_blends' : upcoming_blends})

def add_lot_to_schedule(request, lotnum, partnum, blendarea):
    submitted=False
    thisLot = LotNumRecord.objects.get(lot_number=lotnum)
    description = thisLot.description
    qty = thisLot.quantity
    totesNeeded = round((qty/250),0)
    blendarea = blendarea
    if request.method == "POST":
        msg = ""
        if blendarea == 'Desk1':
            form = DeskOneScheduleForm(request.POST)
        if blendarea == 'Desk2':
            form = DeskTwoScheduleForm(request.POST)
        if form.is_valid():
            newScheduleSubmission = form.save(commit=False)
            newScheduleSubmission.save()
        return HttpResponseRedirect('/core/blendschedule/'+blendarea)
    else:
        msg = ""
        if blendarea == 'Desk1':
            form = DeskOneScheduleForm(initial={'blend_pn': partnum,
                                                'description': description,
                                                'lot': lotnum,
                                                'quantity': qty,
                                                'totes_needed': totesNeeded,
                                                'blend_area': blendarea, 
                                                })
        elif blendarea == 'Desk2':
            form = DeskTwoScheduleForm(initial={'blend_pn': partnum,
                                                'description': description,
                                                'lot': lotnum,
                                                'quantity': qty,
                                                'totes_needed': totesNeeded,
                                                'blend_area': blendarea, 
                                                })
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/thisLotToSched.html', {'form':form, 'submitted':submitted, "msg": msg})

def display_blend_schedule(request, blendarea):
    desk_one_blends = DeskOneSchedule.objects.all().order_by('order')
    for blend in desk_one_blends:
        try:
            blend.when_entered = ImItemCost.objects.get(receiptno=blend.blend_pn)
        except ImItemCost.DoesNotExist:
            blend.when_entered = "Not Entered"
    desk_two_blends = DeskTwoSchedule.objects.all()
    for blend in desk_two_blends:
        try:
            blend.when_entered = ImItemCost.objects.get(receiptno=blend.blend_pn)
        except ImItemCost.DoesNotExist:
            blend.when_entered = "Not Entered"
    horix_blends = HorixBlendThese.objects.filter(line__icontains='Hx')
    drum_blends = HorixBlendThese.objects.filter(line__icontains='Dm')
    tote_blends = HorixBlendThese.objects.filter(line__icontains='Totes')

    blend_area = blendarea
    return render(request, 'core/blendschedule.html', {'desk_one_blends': desk_one_blends,
                                                        'desk_two_blends': desk_two_blends,
                                                        'horix_blends': horix_blends,
                                                        'drum_blends': drum_blends,
                                                        'tote_blends': tote_blends,
                                                        'blend_area': blend_area})

def manage_blend_schedule(request, request_type, blend_area, blend_id, blend_list_position):
    if blend_area == 'Desk1':
        blend = DeskOneSchedule.objects.get(pk=blend_id)
    elif blend_area == 'Desk2':
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

def add_count_list(request, encoded_list):
    submitted=False
    # https://stackoverflow.com/questions/3470546/how-do-you-decode-base64-data-in-python
    part_numbers_bytestr = base64.b64decode(encoded_list)
    # https://stackoverflow.com/questions/38586586/how-to-convert-class-bytes-to-array-or-string-in-python
    part_numbers_str = part_numbers_bytestr.decode()
    part_numbers_list = list(part_numbers_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    primary_key_str = ''

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
    primary_key_dict = { 'primary_keys_here' : primary_key_str }
    # primary_key_str_bytes = primary_key_str.encode('utf-8')
    # encoded_primary_key_str = base64.b64encode(primary_key_str_bytes)

    return HttpResponseRedirect('/core/countlist/display/' + primary_key_str)

def display_count_list(request, primary_key_str):
    submitted=False
    primary_key_list = list(primary_key_str.split(','))
    these_count_records = CountRecord.objects.filter(pk__in=primary_key_list)
    for count_record in these_count_records:
        item_unit_of_measure = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=count_record.part_number).first().standard_uom
        count_record.standard_uom = item_unit_of_measure

    todays_date = dt.date.today()
    
    formset_instance = modelformset_factory(CountRecord, form=CountRecordForm, extra=0)
    these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)

    if request.method == 'POST':
        print(these_counts_formset)
        if these_counts_formset.is_valid():
            these_counts_formset.save()
            return HttpResponseRedirect('/core/countrecords/?page=1')
    else:
        these_counts_formset = formset_instance(request.POST or None, queryset=these_count_records)
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/countlist.html', {
                         'submitted' : submitted,
                         'todays_date' : todays_date,
                         'these_counts_formset' : these_counts_formset,
                         })

def display_count_records(request):
    count_record_queryset = CountRecord.objects.order_by('-counted_date')
    count_record_paginator = Paginator(count_record_queryset, 25)
    page_num = request.GET.get('page')
    current_page = count_record_paginator.get_page(page_num)

    return render(request, 'core/countrecords.html', {'current_page' : current_page})

def display_all_upcoming_production(request):
    upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime')
    upcoming_runs_paginator = Paginator(upcoming_runs_queryset, 25)
    page_num = request.GET.get('page')
    current_page = upcoming_runs_paginator.get_page(page_num)
    return render(request, 'core/allupcomingproduction.html', {'current_page' : current_page})

def display_chem_shortages(request):
    is_shortage = False
    blends_used_upcoming = BlendThese.objects.all()
    blends_upcoming_partnums = list(BlendThese.objects.values_list('blend_pn', flat=True))
    chems_used_upcoming = BlendBillOfMaterials.objects.filter(bill_pn__in=blends_upcoming_partnums)

    for chem in chems_used_upcoming:
        chem.blend_req_onewk = blends_used_upcoming.filter(blend_pn__icontains=chem.bill_pn).first().one_wk_short
        chem.blend_req_twowk = blends_used_upcoming.filter(blend_pn__icontains=chem.bill_pn).first().two_wk_short
        chem.blend_req_threewk = blends_used_upcoming.filter(blend_pn__icontains=chem.bill_pn).first().three_wk_short
        chem.required_qty = chem.blend_req_threewk * chem.qtyperbill
        chem.oh_minus_required = chem.qtyonhand - chem.required_qty
        chem.max_possible_blend = chem.qtyonhand / chem.qtyperbill
        if (PoPurchaseOrderDetail.objects.filter(itemcode__icontains=chem.component_itemcode).exists()):
            chem.next_delivery = PoPurchaseOrderDetail.objects.filter(itemcode__icontains=chem.component_itemcode).order_by('-requireddate').first().requireddate
        else:
            chem.next_delivery = "N/A"
        if (chem.oh_minus_required < 0 and chem.component_itemcode != "030143"):
            is_shortage = True
        

    return render(request, 'core/chemshortages.html',
        {'chems_used_upcoming' : chems_used_upcoming,
         'is_shortage' : is_shortage,
         'blends_upcoming_partnums' : blends_upcoming_partnums,
         'blends_used_upcoming' : blends_used_upcoming
         })

def get_json_chemloc_from_itemcode(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_item = ChemLocation.objects.get(part_number=item_code)
        response_item = {
            "description" : requested_item.description,
            "specific_location" : requested_item.specificlocation,
            "general_location" : requested_item.generallocation
        }
    return JsonResponse(response_item, safe=False)

def get_json_chemloc_from_itemdesc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_item = ChemLocation.objects.get(description=item_desc)
        responseData = {
            "reqItemCode" : requested_item.part_number,
            "specific_location" : requested_item.specificlocation,
            "general_location" : requested_item.generallocation
            }
    return JsonResponse(responseData, safe=False)

def display_lookup_location(request):
    itemcode_queryset = list(BlendBillOfMaterials.objects
                            .order_by('component_itemcode')
                            .distinct('component_itemcode')
                            )

    return render(request, 'core/lookuplocation.html', {'itemcode_queryset' : itemcode_queryset})

def display_lookup_location(request):
    itemcode_queryset = list(BlendBillOfMaterials.objects
                            .order_by('component_itemcode')
                            .distinct('component_itemcode')
                            )

    return render(request, 'core/lookuplocation.html', {'itemcode_queryset' : itemcode_queryset})

def display_tank_levels(request):
    tank_info = StorageTank.objects.all()
    
    return render(request, 'core/tanklevels.html', {'tank_info' : tank_info})

def get_tank_levels_html(request):
    if request.method == "GET":
        fp = urllib.request.urlopen('http://192.168.178.210/fieldDeviceData.htm')
        html_str = fp.read().decode("utf-8")
        fp.close()
        html_str = urllib.parse.unquote(html_str)
        response_json = { 'html_string' : html_str }

    return JsonResponse(response_json, safe=False)

def get_json_lotnums_from_itemcode(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        possible_batches = list(CiItem.objects.filter(quantityonhand__gt=0).only('receiptno'))
        all_lots_this_item = LotNumRecord.objects.filter(part_number=item_code)
        
        response_batches = {}
        this_item = []
        for lot in all_lots_this_item:
            this_item.append(lot.part_number)
            this_item.append(lot.description)
            this_item.append(lot.quantity)
            this_item.append(lot.date_created)
            response_batches[lot.lot_number] = this_item
            this_item = []
    return JsonResponse(response_batches, safe=False)

def get_json_lotnums_from_itemdesc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_item = ChemLocation.objects.get(description=item_desc)
        responseData = {
            "reqItemCode" : requested_item.part_number,
            "specific_location" : requested_item.specificlocation,
            "general_location" : requested_item.generallocation
            }
    return JsonResponse(responseData, safe=False)

def display_lookup_lotnums(request):

    return render(request, 'core/testpage.html', {})

def display_test_page(request):
    
    return render(request, 'core/testpage.html', {})
   