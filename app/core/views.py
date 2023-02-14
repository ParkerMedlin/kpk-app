import urllib
import math
import datetime as dt
from datetime import date
import pytz
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core.paginator import Paginator
import base64
from .models import *
from prodverse.models import *
from .forms import *
from django.db.models import Sum, Subquery, OuterRef
from core import taskfunctions


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
    blend_these_queryset = BlendThese.objects.filter(procurementtype__iexact='M').order_by('starttime')
    foam_factor_is_populated = FoamFactor.objects.all().exists()
    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()
    for blend in blend_these_queryset:
        this_blend_bom = BillOfMaterials.objects.filter(item_code__iexact=blend.component_item_code)
        blend.ingredients_list = f'Sage OH for blend {blend.component_item_code}:\n{str(round(blend.qtyonhand, 0))} gal \n\nINGREDIENTS:\n'
        for item in this_blend_bom:
            blend.ingredients_list += item.component_item_code + ': ' + item.component_item_description + '\n'
        if blend.last_txn_date and blend.last_count_date:
            if blend.last_txn_date > blend.last_count_date:
                blend.needs_count = True
        else:
            blend.needs_count = False
        if desk_one_queryset.filter(item_code__iexact=blend.component_item_code).exists():
            blend.schedule_value = 'Desk_1'
        elif desk_two_queryset.filter(item_code__iexact=blend.component_item_code).exists():
            blend.schedule_value = 'Desk_2'
        else:
            blend.schedule_value = 'Not Scheduled'


    submitted=False
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number

    add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number':next_lot_number, 'date_created':today,})

    return render(request, 'core/blendshortages.html', {
        'blend_these_queryset': blend_these_queryset,
        'foam_factor_is_populated' : foam_factor_is_populated,
        'submitted' : submitted,
        'desk_one_queryset' : desk_one_queryset,
        'add_lot_form' : add_lot_form})

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
    # May need to revisit the logic of load_edit_modal/edit_yesno. I think
    # the proper way to handle this would be ajax. As we stand, you have to reload
    # the entire page in order to populate the editLotNumModal with the LotNumRecord
    # instance you wanted to edit. I don't want to dive into that right now though.
    submitted = False
    load_edit_modal = False
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number

    if request.method == "GET":
        edit_yesno = request.GET.get('edit_yesno', 0)
        load_add_modal = request.GET.get('load_add_modal', 0)
        lot_id = request.GET.get('lot_id', 0)
        lot_number_to_edit = ""
        add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number' : next_lot_number, 'date_created' : today})
        if edit_yesno == 'yes' and LotNumRecord.objects.filter(pk=lot_id).exists():
            load_edit_modal = True
            lot_number_to_edit = LotNumRecord.objects.get(pk=lot_id)
            edit_lot_form = LotNumRecordForm(instance=lot_number_to_edit, prefix='editLotNumModal')
        else:
            edit_lot_form = LotNumRecordForm(instance=LotNumRecord.objects.all().first(), prefix='editLotNumModal')
        if 'submitted' in request.GET:
            submitted=True

    lot_num_queryset = LotNumRecord.objects.order_by('-date_created', '-lot_number')

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
            lot.schedule_order = desk_one_queryset.filter(lot__iexact=lot.lot_number).first().order
        elif desk_two_queryset.filter(lot__iexact=lot.lot_number).exists():
            lot.schedule_value = 'Desk_2'
            lot.schedule_id = desk_two_queryset.filter(lot__iexact=lot.lot_number).first().id
            lot.schedule_order = desk_two_queryset.filter(lot__iexact=lot.lot_number).first().order
        elif lot.line != 'Prod':
            lot.schedule_value = lot.line
        else:
            lot.schedule_value = 'Not Scheduled'

    add_to_deskone = DeskOneScheduleForm(prefix="deskone")
    add_to_desktwo = DeskTwoScheduleForm(prefix="desktwo")

    context = {
        'add_to_deskone' : add_to_deskone,
        'add_to_desktwo' : add_to_desktwo,
        'add_lot_form' : add_lot_form,
        'edit_lot_form' : edit_lot_form,
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

def add_lot_num_record(request, redirect_page):
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number
    # blend_instruction_queryset = BlendInstruction.objects.order_by('item_code', 'step_no')

    if 'addNewLotNumRecord' in request.POST:
        add_lot_form = LotNumRecordForm(request.POST, prefix='addLotNumModal', )
        if add_lot_form.is_valid():
            new_lot_submission = add_lot_form.save(commit=False)
            new_lot_submission.date_created = today
            new_lot_submission.lot_number = next_lot_number
            new_lot_submission.save()
            this_lot_desk = add_lot_form.cleaned_data['desk']
            if this_lot_desk == 'Desk_1':
                new_schedule_item = DeskOneSchedule(
                    item_code = add_lot_form.cleaned_data['item_code'],
                    item_description = add_lot_form.cleaned_data['item_description'],
                    lot = add_lot_form.cleaned_data['lot_number'],
                    quantity = add_lot_form.cleaned_data['lot_quantity'],
                    totes_needed = math.ceil(add_lot_form.cleaned_data['lot_quantity']/250),
                    blend_area = add_lot_form.cleaned_data['desk']
                    )
                new_schedule_item.save()
            if this_lot_desk == 'Desk_2':
                new_schedule_item = DeskTwoSchedule(
                    item_code = add_lot_form.cleaned_data['item_code'],
                    item_description = add_lot_form.cleaned_data['item_description'],
                    lot = add_lot_form.cleaned_data['lot_number'],
                    quantity = add_lot_form.cleaned_data['lot_quantity'],
                    totes_needed = math.ceil(add_lot_form.cleaned_data['lot_quantity']/250),
                    blend_area = add_lot_form.cleaned_data['desk']
                    )
                new_schedule_item.save()
            # these_blend_instructions = blend_instruction_queryset.filter(item_code__icontains=new_lot_submission.item_code)
            # for step in these_blend_instructions:
            #     if step.step_qty == '':
            #         this_step_qty = ''
            #     else:
            #         this_step_qty = float(step.step_qty) * float(new_lot_submission.quantity)
            #     new_step = BlendingStep(
            #         step_no = step.step_no,
            #         step_desc = step.step_desc,
            #         step_qty = this_step_qty,
            #         step_unit = step.step_unit,
            #         qty_added = "",
            #         component_item_code = step.component_item_code,
            #         notes_1 = step.notes_1,
            #         notes_2 = step.notes_2,
            #         item_code = step.item_code,
            #         item_description = new_lot_submission.description,
            #         ref_no = step.ref_no,
            #         prepared_by = step.prepared_by,
            #         prepared_date = step.prepared_date,
            #         lbs_per_gal = step.lbs_per_gal,
            #         blend_lot_number = new_lot_submission.lot_number,
            #         lot = new_lot_submission
            #         )
            #     new_step.save()
            # new_lot_submission.save()
            if redirect_page == 'blendschedule':
                return HttpResponseRedirect('/core/blendschedule?blend_area=all')
            elif redirect_page == 'blendshortages':
                return HttpResponseRedirect('/core/blendshortages')
            else:
                return HttpResponseRedirect('/core/lotnumrecords')
        else:
            return
    else: 
        return HttpResponseRedirect('/')

@login_required
def display_blend_sheet(request, lot):
    submitted=False
    this_lot = LotNumRecord.objects.get(lot_number=lot)
    blend_steps = BlendingStep.objects.filter(blend_lot_number__icontains=lot)
    first_step = blend_steps.first()

    blend_components = BillOfMaterials.objects.filter(item_code=this_lot.item_code)
    for component in blend_components:
        quantity_required = 0
        for step in blend_steps.filter(component_item_code__icontains=component.component_item_code):
            quantity_required+=float(step.step_qty)
        component.qtyreq = quantity_required
        component_locations = ChemLocation.objects.filter(component_item_code=component.component_item_code)
        component.area = component_locations.first().general_location
        component.location = component_locations.first().specific_location

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
        part_nums_blends_needed.append(blend.component_item_code)
    bom_blends_needed = BillOfMaterials.objects.filter(item_code__in=part_nums_blends_needed)
    for component in bom_blends_needed:
        component.blendQtyShortThreeWk = blends_needed.filter(component_item_code__icontains=component.item_code).first().three_wk_short
        component.chemRequiredThreeWk = float(component.blendQtyShortThreeWk) * float(component.qtyperbill)
        component.chemShortThreeWk = float(component.qtyonhand) - component.chemRequiredThreeWk
    blends_needed_components = bom_blends_needed
    return render(request, 'core/reportcenter.html', {'blends_needed_components' : blends_needed_components})

def display_report(request, which_report, item_code):
    if which_report=="Lot-Numbers":
        no_lots_found = False
        lot_num_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created', '-lot_number')

        lot_num_paginator = Paginator(lot_num_queryset, 25)
        page_num = request.GET.get('page')
        current_page = lot_num_paginator.get_page(page_num)

        im_itemcost_queryset = ImItemCost.objects.filter(itemcode__iexact=item_code)
        for lot in current_page:
            if im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).exists():
                lot.qty_on_hand = (im_itemcost_queryset.filter(receiptno__iexact=lot.lot_number).first().quantityonhand)
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
        upcoming_runs = TimetableRunData.objects.filter(component_item_code__icontains=item_code).order_by('starttime')
        if upcoming_runs.exists():
            item_description = upcoming_runs.first().component_item_description
        else:
            no_runs_found = True
            item_description = ''
        blend_info = {'item_code' : item_code, 'item_description' : item_description}
        return render(request, 'core/reports/upcomingrunsreport.html', {'no_runs_found' : no_runs_found, 'upcoming_runs' : upcoming_runs, 'blend_info' : blend_info})

    elif which_report=="Chem-Shortage":
        no_shortage_found = False
        blend_list = BillOfMaterials.objects.filter(component_item_code__icontains=item_code)
        component_item_code_list = []
        for item in blend_list:
            component_item_code_list.append(item.item_code)
        prod_run_list = TimetableRunData.objects.filter(component_item_code__in=component_item_code_list,oh_after_run__lt=0).order_by('starttime')
        running_chem_total = 0.0
        for run in prod_run_list:
            single_bill = BillOfMaterials.objects.filter(component_item_code__icontains=item_code,item_code__icontains=run.component_item_code).first()
            run.chem_factor = single_bill.qtyperbill
            run.chem_needed_for_run = float(run.chem_factor) * float(run.adjustedrunqty)
            running_chem_total = running_chem_total + float(run.chem_factor * run.adjustedrunqty)
            run.chem_oh_after_run = float(single_bill.qtyonhand) - running_chem_total
            run.chemUnit = single_bill.standard_uom
        
        if BillOfMaterials.objects.filter(component_item_code__icontains=item_code).exists():
            item_info = {
                    'item_code' : BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first().component_item_code,
                    'item_description' : BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first().component_item_description
                    }
        else:
            no_shortage_found = True
            item_info = {}
        return render(request, 'core/reports/chemshortagereport.html', {'no_shortage_found' : no_shortage_found, 'prod_run_list' : prod_run_list, 'item_info' : item_info})

    elif which_report=="Startron-Runs":
        startron_item_codes = ["14000.B", "14308.B", "14308AMBER.B", "93100DSL.B", "93100GAS.B", "93100TANK.B", "93100GASBLUE.B", "93100GASAMBER.B"]
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
        if CountRecord.objects.filter(item_code__iexact=item_code).exists():
            blend_count_records = CountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
        else:
            counts_not_found = True
            blend_count_records = {}
        item_info = {
                    'item_code' : item_code,
                    'item_description' : BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first().component_item_description
                    }
        return render(request, 'core/reports/inventorycountsreport.html', {'counts_not_found' : counts_not_found, 'blend_count_records' : blend_count_records, 'item_info' : item_info})

    elif which_report=="Counts-And-Transactions":
        if CountRecord.objects.filter(item_code__iexact=item_code).exists():
            blend_count_records = CountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
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

        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        item_info = {
                    'item_code' : item_code,
                    'item_description' : item_description
                    }

        
        return render(request, 'core/reports/countsandtransactionsreport.html', {'counts_and_transactions_list' : counts_and_transactions_list, 'item_info' : item_info})
    elif which_report=="Where-Used":
        all_bills_where_used = BillOfMaterials.objects.filter(component_item_code__iexact=item_code)
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        item_info = {
                    'item_code' : item_code,
                    'item_description' : item_description
                    }
        # may want to do pagination if this gets ugly
        return render(request, 'core/reports/whereusedreport.html', {'all_bills_where_used' : all_bills_where_used, 'item_info' : item_info})


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

def display_blend_schedule(request):
    submitted=False
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number
    # blend_instruction_queryset = BlendInstruction.objects.order_by('item_code', 'step_no')

    if request.method == "POST":
        add_lot_form = LotNumRecordForm(request.POST, prefix="addLotNumModal")
    
        if add_lot_form.is_valid():
            new_lot_submission = add_lot_form.save(commit=False)
            new_lot_submission.date_created = today
            new_lot_submission.lot_number = next_lot_number
            new_lot_submission.save()
            # these_blend_instructions = blend_instruction_queryset.filter(item_code__icontains=new_lot_submission.item_code)
            # for step in these_blend_instructions:
            #     if step.step_qty == '':
            #         this_step_qty = ''
            #     else:
            #         this_step_qty = float(step.step_qty) * float(new_lot_submission.quantity)
            #     new_step = BlendingStep(
            #         step_no = step.step_no,
            #         step_desc = step.step_desc,
            #         step_qty = this_step_qty,
            #         step_unit = step.step_unit,
            #         qty_added = "",
            #         component_item_code = step.component_item_code,
            #         notes_1 = step.notes_1,
            #         notes_2 = step.notes_2,
            #         item_code = step.item_code,
            #         component_item_description = new_lot_submission.item_description,
            #         ref_no = step.ref_no,
            #         prepared_by = step.prepared_by,
            #         prepared_date = step.prepared_date,
            #         lbs_per_gal = step.lbs_per_gal,
            #         blend_lot_number = new_lot_submission.lot_number,
            #         lot = new_lot_submission
            #         )
            #     new_step.save()
            new_lot_submission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number':next_lot_number, 'date_created':today,})
        if 'submitted' in request.GET:
            submitted=True

    desk_one_blends = DeskOneSchedule.objects.all().order_by('order')
    if desk_one_blends.exists():
        for blend in desk_one_blends:
            try:
                blend.when_entered = ImItemCost.objects.filter(receiptno__iexact=blend.lot).first()
            except ImItemCost.DoesNotExist:
                blend.when_entered = "Not Entered"
            if BlendThese.objects.filter(component_item_code__iexact=blend.item_code).exists():
                blend.threewkshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().three_wk_short
                blend.hourshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().starttime
            else:
                blend.threewkshort = ""
            
    desk_two_blends = DeskTwoSchedule.objects.all()
    if desk_two_blends.exists():
        for blend in desk_two_blends:
            try:
                blend.when_entered = ImItemCost.objects.filter(receiptno__iexact=blend.lot).first()
            except ImItemCost.DoesNotExist:
                blend.when_entered = "Not Entered"
            if BlendThese.objects.filter(component_item_code__iexact=blend.item_code).exists():
                blend.threewkshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().three_wk_short
                blend.hourshort = BlendThese.objects.filter(component_item_code__iexact=blend.item_code).first().starttime
            else: 
                blend.threewkshort = "No Shortage"
    
    blend_BOM = BillOfMaterials.objects.all()
    horix_blends = HorixBlendThese.objects.filter(line__icontains='Hx')
    if horix_blends:
        for item in horix_blends:
            this_blend = blend_BOM.filter(item_code__iexact=item.item_code).filter(component_item_description__icontains="BLEND-").first()
            item.component_item_description = this_blend.component_item_description
    drum_blends = HorixBlendThese.objects.filter(line__icontains='Dm')
    if drum_blends:
        for item in drum_blends:
            this_blend = blend_BOM.filter(item_code__iexact=item.item_code).filter(component_item_description__icontains="BLEND-").first()
            item.component_item_description = this_blend.component_item_description
    tote_blends = HorixBlendThese.objects.filter(line__icontains='Totes')
    if tote_blends:
        for item in tote_blends:
            this_blend = blend_BOM.filter(item_code__iexact=item.item_code).filter(component_item_description__icontains="BLEND-").first()
            item.component_item_description = this_blend.component_item_description

    blend_area = request.GET.get('blend_area', 0)
    return render(request, 'core/blendschedule.html', {'desk_one_blends': desk_one_blends,
                                                        'desk_two_blends': desk_two_blends,
                                                        'horix_blends': horix_blends,
                                                        'drum_blends': drum_blends,
                                                        'tote_blends': tote_blends,
                                                        'blend_area': blend_area,
                                                        'add_lot_form' : add_lot_form,
                                                        'today' : today,
                                                        'submitted' : submitted})

def manage_blend_schedule(request, request_type, blend_area, blend_id, blend_list_position):
    if blend_area == 'Desk_1':
        blend = DeskOneSchedule.objects.get(pk=blend_id)
    elif blend_area == 'Desk_2':
        blend = DeskTwoSchedule.objects.get(pk=blend_id)

    if request_type == 'moveupone':
        blend.up()
        return HttpResponseRedirect(f'/core/blendschedule?={blend_area}')
    if request_type == 'movedownone':
        blend.down()
        return HttpResponseRedirect(f'/core/blendschedule?={blend_area}')
    if request_type == 'movetotop':
        blend.top()
        return HttpResponseRedirect(f'/core/blendschedule?={blend_area}')
    if request_type == 'movetobottom':
        blend.bottom()
        return HttpResponseRedirect(f'/core/blendschedule?={blend_area}')
    if request_type == 'delete':
        blend.delete()
        return HttpResponseRedirect(f'/core/blendschedule?={blend_area}')
    if request_type == 'switchschedules':
        # print(blend_area)
        if blend.blend_area == 'Desk_1':
                new_schedule_item = DeskTwoSchedule(
                    item_code = blend.item_code,
                    item_description = blend.item_description,
                    lot = blend.lot,
                    quantity = blend.quantity,
                    totes_needed = blend.totes_needed,
                    blend_area = 'Desk_2'
                    )
                new_schedule_item.save()
        elif blend.blend_area == 'Desk_2':
                new_schedule_item = DeskOneSchedule(
                    item_code = blend.item_code,
                    item_description = blend.item_description,
                    lot = blend.lot,
                    quantity = blend.quantity,
                    totes_needed = blend.totes_needed,
                    blend_area = 'Desk_1'
                    )
                new_schedule_item.save()
        blend.delete()
        return HttpResponseRedirect(f'/core/lotnumrecords')


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
        if BlendThese.objects.filter(component_item_code__icontains = blend.item_code).exists():
            blend.short_hour = blend_these_table.get(component_item_code = blend.item_code).starttime
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

def add_count_list(request, encoded_item_code_list, encoded_pk_list):
    submitted=False
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

    for item_code in item_codes_list:
        this_bill = BillOfMaterials.objects.filter(component_item_code__icontains=item_code).first()
        new_count_record = CountRecord(
            item_code = item_code,
            item_description = this_bill.component_item_description,
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
        item_unit_of_measure = BillOfMaterials.objects.filter(component_item_code__icontains=count_record.item_code).first().standard_uom
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
        if item in all_items_list:
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
    #for blend in upcoming_runs_queryset:
    #    this_blend_bom = BillOfMaterials.objects.filter(item_code__iexact=blend.component_item_code)
    #    blend.ingredients_list = f'Ingredients for blend {blend.component_item_code}:\n'
    #    for item in this_blend_bom:
    #        blend.ingredients_list += item.component_item_code + ': ' + item.component_item_description + '\n'
    upcoming_runs_paginator = Paginator(upcoming_runs_queryset, 25)
    page_num = request.GET.get('page')
    current_page = upcoming_runs_paginator.get_page(page_num)
    return render(request, 'core/productionblendruns.html', {'current_page' : current_page})

def display_chem_shortages(request):
    is_shortage = False
    blends_used_upcoming = BlendThese.objects.all()
    blends_upcoming_item_codes = list(BlendThese.objects.values_list('component_item_code', flat=True))
    chems_used_upcoming = BillOfMaterials.objects.filter(item_code__in=blends_upcoming_item_codes)
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)
    for chem in chems_used_upcoming:
        chem.blend_req_onewk = blends_used_upcoming.filter(component_item_code__icontains=chem.item_code).first().one_wk_short
        chem.blend_req_twowk = blends_used_upcoming.filter(component_item_code__icontains=chem.item_code).first().two_wk_short
        chem.blend_req_threewk = blends_used_upcoming.filter(component_item_code__icontains=chem.item_code).first().three_wk_short
        chem.required_qty = chem.blend_req_threewk * chem.qtyperbill
        chem.oh_minus_required = chem.qtyonhand - chem.required_qty
        chem.max_possible_blend = chem.qtyonhand / chem.qtyperbill
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
        
    chems_used_paginator = Paginator(chems_used_upcoming, 5)
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
        lookup_type = request.GET.get('lookupType', 0)
        if lookup_type == 'itemCode':
            item_code_encoded = request.GET.get('item', 0)
            item_code_bytestr = base64.b64decode(item_code_encoded)
            item_code = item_code_bytestr.decode()
            item_code = item_code.replace('"', "")
            item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        elif lookup_type == 'itemDescription':
            item_description_encoded = request.GET.get('item', 0)
            item_description_bytestr = base64.b64decode(item_description_encoded)
            item_description = item_description_bytestr.decode()
            item_description = item_description.replace('"', "")
            item_code = BillOfMaterials.objects.filter(component_item_description__iexact=item_description).first().component_item_code
        
        requested_BOM_item = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first()
        qty_on_hand = round(requested_BOM_item.qtyonhand, 2)
        standard_uom = requested_BOM_item.standard_uom
        
        if ChemLocation.objects.filter(component_item_code=item_code).exists():
            requested_item = ChemLocation.objects.get(component_item_code=item_code)
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
    print(response_item)
    return JsonResponse(response_item, safe=False)

def display_lookup_location(request):
    item_code_queryset = list(BillOfMaterials.objects
                            .order_by('component_item_code')
                            .distinct('component_item_code')
                            )

    return render(request, 'core/lookuppages/lookuplocation.html', {'item_code_queryset' : item_code_queryset})

def get_json_item_info(request):
    if request.method == "GET":
        lookup_type = request.GET.get('lookupType', 0)
        if lookup_type == 'itemCode':
            item_code_encoded = request.GET.get('item', 0)
            item_code_bytestr = base64.b64decode(item_code_encoded)
            item_code = item_code_bytestr.decode()
            item_code = item_code.replace('"', "")
            print(item_code)
        elif lookup_type == 'itemDescription':
            item_description_encoded = request.GET.get('item', 0)
            item_description_bytestr = base64.b64decode(item_description_encoded)
            item_description = item_description_bytestr.decode()
            item_description = item_description.replace('"', "")
            item_code = CiItem.objects.filter(itemcodedesc__iexact=item_description).first().itemcode
            print(item_code)
        requested_ci_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        requested_im_warehouse_item = ImItemWarehouse.objects.filter(itemcode__iexact=item_code, warehousecode__exact='MTG').first()
        response_item = {
            "item_code" : requested_ci_item.itemcode,
            "item_description" : requested_ci_item.itemcodedesc,
            "qtyOnHand" : requested_im_warehouse_item.quantityonhand,
            "standardUOM" : requested_ci_item.standardunitofmeasure
            }
        print(response_item)
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

def display_lookup_lotnums(request):
    item_code_queryset = list(BillOfMaterials.objects
                            .order_by('component_item_code')
                            .distinct('component_item_code')
                            )

    return render(request, 'core/lookuppages/lookuplotnums.html', {'item_code_queryset' : item_code_queryset})

def get_json_bill_of_materials_fields(request):
    if request.method == "GET":
        bom_queryset = BillOfMaterials.objects.all().distinct('component_item_code')
        if request.GET.get('restriction', 0)=='blends-only':
            bom_queryset = bom_queryset.filter(component_item_description__startswith="BLEND")
        if request.GET.get('restriction', 0)=='chem-dye-frag':
            bom_queryset = bom_queryset.filter(
                component_item_description__startswith='DYE') | bom_queryset.filter(
                component_item_description__startswith='FRAGRANCE') | bom_queryset.filter(
                component_item_description__startswith='CHEM')
        if request.GET.get('restriction', 0)=='specsheet-items':
            bom_queryset = SpecSheetData.objects.distinct('item_code')
            item_codes = bom_queryset.values_list('item_code', flat=True).distinct()
            bom_map = {bom.item_code.lower(): bom for bom in BillOfMaterials.objects.filter(item_code__in=item_codes)}
            for bill in bom_queryset:
                bill.component_item_code = bill.item_code
                bom = bom_map.get(bill.item_code.lower())
                bill.component_item_description = bom.item_description if bom else 'guh'
        itemcode_list = []
        itemdesc_list = []
        for item in bom_queryset:
            itemcode_list.append(item.component_item_code)
            itemdesc_list.append(item.component_item_description)

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
    print(recipient_address)
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


def display_test_page(request):
    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()

    return render(request, 'core/testpage.html',
        {'desk_one_queryset' : desk_one_queryset, 'desk_two_queryset' : desk_two_queryset }
        )