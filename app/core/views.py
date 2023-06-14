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
from django.db.models import Sum, Min, Subquery, OuterRef
from core import taskfunctions
from django.db.models import Q, CharField


def get_json_forklift_serial(request):
    if request.method == "GET":
        forklift_unit_number = request.GET.get('unit-number', 0)
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
            return HttpResponseRedirect('/core/forklift-checklist?submitted=True')
        else:
            return render(request, 'core/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})
    else:
        checklist_form = ChecklistLogForm
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})

def display_blend_these(request):
    blend_these_queryset = ComponentShortage.objects \
        .filter(component_item_description__startswith='BLEND') \
        .filter(procurement_type__iexact='M') \
        .order_by('start_time') \
        .filter(component_instance_count=1) \
        .exclude(prod_line__iexact='Hx')

    foam_factor_is_populated = FoamFactor.objects.all().exists()
    desk_one_queryset = DeskOneSchedule.objects.all()
    desk_two_queryset = DeskTwoSchedule.objects.all()
    for blend in blend_these_queryset:
        item_code_str_bytes = blend.component_item_code.encode('UTF-8')
        encoded_item_code_bytes = base64.b64encode(item_code_str_bytes)
        blend.encoded_component_item_code = encoded_item_code_bytes.decode('UTF-8')
        this_blend_bom = BillOfMaterials.objects.filter(item_code__iexact=blend.component_item_code)
        blend.ingredients_list = f'Sage OH for blend {blend.component_item_code}:\n{str(round(blend.component_on_hand_qty, 0))} gal \n\nINGREDIENTS:\n'
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
        try:
            component_shortage_queryset = SubComponentShortage.objects \
                .filter(component_item_code=blend.component_item_code) \
                .exclude(prod_line__icontains='UNSCHEDULED')
        except SubComponentShortage.DoesNotExist:
            component_shortage_queryset = None
            blend.shortage_flag = None
            continue
        if component_shortage_queryset:
            shortage_component_item_codes = []
            for item in component_shortage_queryset:
                if item.subcomponent_item_code not in shortage_component_item_codes:
                    shortage_component_item_codes.append(item.subcomponent_item_code)
            blend.shortage_flag_list = shortage_component_item_codes
        
    submitted = False
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
        print(item)
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
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number

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

    lot_num_queryset = LotNumRecord.objects.order_by('-date_created', '-lot_number')
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

def update_lot_num_record(request, lot_num_id):
    if request.method == "POST":
        request.GET.get('edit-yes-no', 0)
        lot_num_record = get_object_or_404(LotNumRecord, id = lot_num_id)
        edit_lot_form = LotNumRecordForm(request.POST or None, instance=lot_num_record, prefix='editLotNumModal')

        if edit_lot_form.is_valid():
            edit_lot_form.save()

        return HttpResponseRedirect('/core/lot-num-records')

def display_all_chemical_locations(request):
    chemical_locations = ChemLocation.objects.all()
    for item in chemical_locations:
        try:
            item.qtyonhand = BillOfMaterials.objects.filter(component_item_code__iexact=item.component_item_code).first().qtyonhand
            item.standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item.component_item_code).first().standard_uom
        except Exception as e:
            print(str(e))
            continue
    
    return render(request, 'core/allchemlocations.html', {'chemical_locations': chemical_locations})

def add_lot_num_record(request):
    today = dt.datetime.now()
    monthletter_and_year = chr(64 + dt.datetime.now().month) + str(dt.datetime.now().year % 100)
    four_digit_number = str(int(str(LotNumRecord.objects.order_by('-id').first().lot_number)[-4:]) + 1).zfill(4)
    next_lot_number = monthletter_and_year + four_digit_number
    redirect_page = request.GET.get('redirect-page', 0)
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
                    blend_area = add_lot_form.cleaned_data['desk']
                    )
                new_schedule_item.save()
            if this_lot_desk == 'Desk_2':
                new_schedule_item = DeskTwoSchedule(
                    item_code = add_lot_form.cleaned_data['item_code'],
                    item_description = add_lot_form.cleaned_data['item_description'],
                    lot = add_lot_form.cleaned_data['lot_number'],
                    blend_area = add_lot_form.cleaned_data['desk']
                    )
                new_schedule_item.save()
           
            if redirect_page == 'blend-schedule':
                return HttpResponseRedirect('/core/blend-schedule?blend-area=all')
            elif redirect_page == 'blend-shortages':
                return HttpResponseRedirect('/core/blend-shortages')
            else:
                return HttpResponseRedirect('/core/lot-num-records')
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
            
            return HttpResponseRedirect('/core/blend-sheet-complete')
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
    item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
    standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
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
        print(this_bill.item_description)
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
        print(report_type)
        context = {
            'report_type' : report_type,
            'no_runs_found' : no_runs_found,
            'upcoming_runs' : upcoming_runs,
            'item_info' : item_info
        }
        return render(request, 'core/reports/upcomingrunsreport/upcomingrunsreport.html', context)

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
            blend_count_records = CountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
        else:
            counts_not_found = True
            blend_count_records = {}
        item_info = {'item_code' : item_code,
                    'item_description' : BillOfMaterials.objects \
                        .filter(component_item_code__icontains=item_code) \
                        .first().component_item_description
                    }
        context = {'counts_not_found' : counts_not_found,
            'blend_count_records' : blend_count_records,
            'item_info' : item_info
            }
        return render(request, 'core/reports/inventorycountsreport.html', context)

    elif which_report=="Counts-And-Transactions":
        if CountRecord.objects.filter(item_code__iexact=item_code).exists():
            blend_count_records = CountRecord.objects.filter(item_code__iexact=item_code).filter(counted=True).order_by('-counted_date')
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
        three_months_ago = dt.datetime.today() - dt.timedelta(weeks = 24)
        orders_not_found = False
        procurementtype = BillOfMaterials.objects \
            .filter(component_item_code__iexact=item_code) \
            .first().procurementtype
        if not procurementtype == 'M':
            all_purchase_orders = PoPurchaseOrderDetail.objects \
                    .filter(itemcode=item_code) \
                    .filter(requireddate__gte=three_months_ago) \
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
            return HttpResponseRedirect('/core/lot-num-records')
    else:
        add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial={'lot_number':next_lot_number, 'date_created':today,})
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
            
    desk_two_blends = DeskTwoSchedule.objects.all()
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

def manage_blend_schedule(request, request_type, blend_area, blend_id, blend_list_position):
    if blend_area == 'Desk_1':
        blend = DeskOneSchedule.objects.get(pk=blend_id)
    elif blend_area == 'Desk_2':
        blend = DeskTwoSchedule.objects.get(pk=blend_id)

    if request_type == 'move-up-one':
        blend.up()
        return HttpResponseRedirect(f'/core/blend-schedule?blend-area={blend_area}')
    if request_type == 'move-down-one':
        blend.down()
        return HttpResponseRedirect(f'/core/blend-schedule?blend-area={blend_area}')
    if request_type == 'move-to-top':
        blend.top()
        return HttpResponseRedirect(f'/core/blend-schedule?blend-area={blend_area}')
    if request_type == 'move-to-bottom':
        blend.bottom()
        return HttpResponseRedirect(f'/core/blend-schedule?blend-area={blend_area}')
    if request_type == 'delete':
        blend.delete()
        return HttpResponseRedirect(f'/core/blend-schedule?blend-area={blend_area}')
    if request_type == 'switch-schedules':
        # print(blend_area)
        if blend.blend_area == 'Desk_1':
                new_schedule_item = DeskTwoSchedule(
                    item_code = blend.item_code,
                    item_description = blend.item_description,
                    lot = blend.lot,
                    blend_area = 'Desk_2'
                    )
                new_schedule_item.save()
        elif blend.blend_area == 'Desk_2':
                new_schedule_item = DeskOneSchedule(
                    item_code = blend.item_code,
                    item_description = blend.item_description,
                    lot = blend.lot,
                    blend_area = 'Desk_1'
                    )
                new_schedule_item.save()
        blend.delete()
        return HttpResponseRedirect('/core/lot-num-records')

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

def display_batch_issue_table(request, line):
    all_prod_runs = IssueSheetNeeded.objects.all()
    if line == 'INLINE':
        prod_runs_this_line = all_prod_runs.filter(prod_line__icontains='INLINE').order_by('start_time')
    if line == 'PDLINE':
        prod_runs_this_line = all_prod_runs.filter(prod_line__icontains='PD LINE').order_by('start_time')
    if line == 'JBLINE':
        prod_runs_this_line = all_prod_runs.filter(prod_line__icontains='JB LINE').order_by('start_time')
    if line == 'all':
        prod_runs_this_line = all_prod_runs.order_by('prod_line','start_time')
    date_today = date.today().strftime('%m/%d/%Y')

    return render(request, 'core/batchissuetable.html', {'prod_runs_this_line' : prod_runs_this_line, 'line' : line, 'dateToday' : date_today})

def display_this_issue_sheet(request, prod_line, item_code):
    date_today = date.today().strftime('%m/%d/%Y')
    run_date_parameter = request.GET.get('runDate')
    run_date = dt.datetime.strptime(run_date_parameter, '%m-%d-%y').date()
    total_gallons = Decimal(request.GET.get('totalGal'))
    this_bill = BillOfMaterials.objects \
        .filter(item_code__icontains=item_code) \
        .filter(component_item_description__startswith='BLEND') \
        .first()
    component_item_code = this_bill.component_item_code
    run_exists = IssueSheetNeeded.objects \
        .filter(prod_line__icontains=prod_line) \
        .filter(component_item_code__icontains=component_item_code) \
        .exists()
    lot_num_run_date_exists = LotNumRecord.objects \
                .filter(item_code__iexact=component_item_code) \
                .filter(run_date__date=run_date) \
                .filter(line__iexact=prod_line).exists()
    if prod_line == 'Hx' or prod_line == 'Dm' or prod_line == 'Totes':
        print(f'prod line == {prod_line}')
        print(f'lot_num_run_date_exists == {lot_num_run_date_exists}')
        if total_gallons < this_bill.qtyonhand and run_exists and not lot_num_run_date_exists:
            print(f'{this_bill.qtyonhand} gal on hand for {component_item_code}.')
            print('Using the existing IssueSheetNeeded row.')
            issue_sheet = IssueSheetNeeded.objects \
                .filter(prod_line__icontains=prod_line) \
                .filter(component_item_code__icontains=component_item_code) \
                .first()
        else:
            run_date = dt.datetime.strptime(run_date_parameter, '%m-%d-%y').date()
            print(f'prod line == {prod_line}')
            print(f'component_item_code == {component_item_code}')
            print(f'run_date == {str(run_date)}')
            lot_numbers = LotNumRecord.objects \
                .filter(item_code__iexact=component_item_code) \
                .filter(run_date__date=run_date) \
                .filter(line__iexact=prod_line)
            lot_num_sets = []
            for lot in lot_numbers:
                lot_num_sets.append((lot.lot_number, lot.lot_quantity))
            while len(lot_num_sets) < 9: #add tuples until there are 9
                lot_num_sets.append(("", ""))
            print(f'lot numbers: {lot_num_sets}')
            deletion_necessary = IssueSheetNeeded.objects \
                .filter(item_code = item_code) \
                .filter(prod_line = prod_line).exists()
                # .filter(component_item_code = this_bill.component_item_code) \
                
            if deletion_necessary:
                this_pk = IssueSheetNeeded.objects \
                    .filter(item_code = item_code) \
                    .filter(prod_line = prod_line).first().pk
                    # .filter(component_item_code = this_bill.component_item_code) \
                row_to_delete = IssueSheetNeeded.objects.get(pk=this_pk)
                print(f'deleting {row_to_delete}')
                row_to_delete.delete()

            new_issuesheetneeded = IssueSheetNeeded(
                id2 = 69,
                item_code = item_code,
                component_item_code = this_bill.component_item_code,
                component_item_description = this_bill.component_item_description,
                run_component_qty = 69.0,
                component_on_hand_qty = 69.0,
                start_time = 0,
                prod_line = prod_line,
                procurement_type = 'M',
                component_onhand_after_run = 69.0,
                batchnum1 = lot_num_sets[0][0],
                batchqty1 = lot_num_sets[0][1],
                batchnum2 = lot_num_sets[1][0],
                batchqty2 = lot_num_sets[1][1],
                batchnum3 = lot_num_sets[2][0],
                batchqty3 = lot_num_sets[2][1],
                batchnum4 = lot_num_sets[3][0],
                batchqty4 = lot_num_sets[3][1],
                batchnum5 = lot_num_sets[4][0],
                batchqty5 = lot_num_sets[4][1],
                batchnum6 = lot_num_sets[5][0],
                batchqty6 = lot_num_sets[5][1],
                batchnum7 = lot_num_sets[6][0],
                batchqty7 = lot_num_sets[6][1],
                batchnum8 = lot_num_sets[7][0],
                batchqty8 = lot_num_sets[7][1],
                batchnum9 = lot_num_sets[8][0],
                batchqty9 = lot_num_sets[8][1],
                uniqchek = item_code + prod_line,
                nonstandard_total = 420,
                row_number = 69.0,
            )
            new_issuesheetneeded.save()
            issue_sheet = new_issuesheetneeded
    else:
        issue_sheet = IssueSheetNeeded.objects \
            .filter(prod_line__icontains=prod_line) \
            .filter(component_item_code__icontains=component_item_code) \
            .first()
        run_date = date_today
    issue_sheet_found = True
    if not issue_sheet:
        issue_sheet_found = False
    # if issue_sheet:
    #     for field in issue_sheet._meta.fields:
    #         if not getattr(issue_sheet, field.attname):
    #             setattr(issue_sheet, field.attname, '')

    context = {
        'issue_sheet' : issue_sheet,
        'issue_sheet_found' : issue_sheet_found,
        'date_today' : date_today,
        'run_date' : run_date,
        'prod_line' : prod_line
    }

    return render(request, 'core/singleissuesheet.html', context)

def display_issue_sheets(request, prod_line, issue_date):
    prod_runs_this_line = IssueSheetNeeded.objects \
        .filter(prod_line__icontains=prod_line) \
        .filter(start_time__lte=15) \
        .order_by('start_time')
    
    return render(request, 'core/issuesheets.html', {'prod_runs_this_line' : prod_runs_this_line, 'prod_line' : prod_line, 'issue_date' : issue_date})

def display_upcoming_blend_counts(request):
    submitted=False
    upcoming_blends = UpcomingBlendCount.objects.exclude(last_transaction_code__iexact='BR').order_by('start_time')
    blends_made_recently = UpcomingBlendCount.objects.filter(last_transaction_code__iexact='BR')
    blend_these_table = BlendThese.objects.all()
    these_querysets = [upcoming_blends, blends_made_recently]
    for this_set in these_querysets:
        for blend in this_set:
            if blend_these_table.filter(component_item_code__iexact = blend.item_code).first():
                blend.short_hour = blend_these_table.filter(component_item_code__iexact = blend.item_code).first().starttime
            else:
                blend.short_hour = 0

        two_weeks_past = dt.date.today() - dt.timedelta(weeks = 2)
        for blend in this_set:
            if (blend.last_count_date) and (blend.last_transaction_date):
                if blend.last_count_date <= blend.last_transaction_date:
                    blend.needs_count = True
                elif blend.last_count_date <= two_weeks_past:
                    blend.needs_count = True
                else:
                    blend.needs_count = False

    return render(request, 'core/inventorycounts/upcomingblends.html', {'upcoming_blends' : upcoming_blends, 'blends_made_recently' : blends_made_recently})

def display_upcoming_component_counts(request):
    submitted=False
    upcoming_components = UpcomingComponentCount.objects.all().order_by('-last_transaction_date')

    two_weeks_past = dt.date.today() - dt.timedelta(weeks = 2)
    for component in upcoming_components:
        item_code_str_bytes = component.item_code.encode('UTF-8')
        encoded_item_code_str_bytes = base64.b64encode(item_code_str_bytes)
        encoded_item_code = encoded_item_code_str_bytes.decode('UTF-8')
        component.encoded_item_code = encoded_item_code
        if (component.last_count_date) and (component.last_transaction_date):
            if component.last_count_date < component.last_transaction_date:
                component.needs_count = True
            elif component.last_count_date < two_weeks_past:
                component.needs_count = True
            else:
                component.needs_count = False
        

    return render(request, 'core/inventorycounts/upcomingcomponents.html', {'upcoming_components' : upcoming_components})

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

    return HttpResponseRedirect('/core/count-list/display/' + encoded_primary_key_str)

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
            return HttpResponseRedirect('/core/count-records/?page=1')
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
    count_record_paginator = Paginator(count_record_queryset, 50)
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
    
    if (redirect_page == 'count-records'):
        return redirect('display-count-records')

    if (redirect_page == 'count-list'):
        all_items_str = ''
        for count_id in all_items_list:
            all_items_str += count_id + ','
        all_items_str = all_items_str[:-1]
        all_items_str_bytes = all_items_str.encode('UTF-8')
        encoded_all_items_bytes = base64.b64encode(all_items_str_bytes)
        encoded_all_items_str = encoded_all_items_bytes.decode('UTF-8')
        if encoded_all_items_str == '':
            return HttpResponseRedirect('/core/count-records')
        else:
            return HttpResponseRedirect('/core/count-list/display/' + encoded_all_items_str)

def display_count_report(request, encoded_pk_list):
    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    count_records_queryset = CountRecord.objects.filter(pk__in=count_ids_list)

    return render(request, 'core/inventorycounts/finishedcounts.html', {'count_records_queryset' : count_records_queryset})

def display_all_upcoming_production(request):
    prod_line_filter = request.GET.get('prod-line-filter', 0)
    component_item_code_filter = request.GET.get('component-item-code-filter', 0)
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
    for run in upcoming_runs_queryset:
        item.component_item_code
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
        item_code = get_unencoded_item_code(lookup_value, lookup_type)
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

def display_lookup_lot_numbers(request):
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
                component_item_description__startswith='DYE') | \
                bom_queryset.filter(component_item_description__startswith='FRAGRANCE') | \
                bom_queryset.filter(component_item_description__startswith='CHEM')
        if request.GET.get('restriction', 0)=='blends-and-components':
            bom_queryset = bom_queryset.filter(
                component_item_description__startswith="BLEND") | \
                bom_queryset.filter(component_item_description__startswith='DYE') | \
                bom_queryset.filter(component_item_description__startswith='FRAGRANCE') | \
                bom_queryset.filter(component_item_description__startswith='CHEM')
        if request.GET.get('restriction', 0)=='spec-sheet-items':
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

def get_component_consumption(component_item_code, blend_item_code_to_exclude):
    item_codes_using_this_component = []
    for bill in BillOfMaterials.objects.filter(component_item_code__iexact=component_item_code).exclude(item_code__iexact=blend_item_code_to_exclude):
        item_codes_using_this_component.append(bill.item_code)
    shortages_using_this_component = BlendThese.objects.filter(component_item_code__in=item_codes_using_this_component).exclude(component_item_code__iexact=blend_item_code_to_exclude)
    total_component_usage = 0
    component_consumption = {}
    for shortage in shortages_using_this_component:
        this_bill = BillOfMaterials.objects.filter(item_code__iexact=shortage.component_item_code).filter(component_item_code__iexact=component_item_code).first()
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
    all_bills_this_itemcode = BillOfMaterials.objects.filter(item_code__iexact=this_item_code)
    
    all_components_this_bill = list(BillOfMaterials.objects.filter(item_code__iexact=this_item_code).values_list('component_item_code'))
    for listposition, component in enumerate(all_components_this_bill):
        all_components_this_bill[listposition] = component[0]

    max_producible_quantities = {}
    consumption_detail = {}
    component_consumption_totals = {}
    for component in all_components_this_bill:
        if component != '030143':
            this_component_consumption = get_component_consumption(component, this_item_code)
            component_onhand_quantity = all_bills_this_itemcode.filter(component_item_code__iexact=component).first().qtyonhand
            available_component_minus_orders = float(component_onhand_quantity) - float(this_component_consumption['total_component_usage'])
            component_consumption_totals[component] = float(this_component_consumption['total_component_usage'])
            max_producible_quantities[component] = math.floor(float(available_component_minus_orders) / float(all_bills_this_itemcode.filter(component_item_code__iexact=component).first().qtyperbill))
            consumption_detail[component] = this_component_consumption

    limiting_factor_item_code = min(max_producible_quantities, key=max_producible_quantities.get)
    limiting_factor_component = BillOfMaterials.objects.filter(component_item_code__iexact=limiting_factor_item_code).filter(item_code__iexact=this_item_code).first()
    limiting_factor_item_description = limiting_factor_component.component_item_description
    limiting_factor_UOM = limiting_factor_component.standard_uom
    limiting_factor_quantity_onhand = limiting_factor_component.qtyonhand
    limiting_factor_OH_minus_other_orders = float(limiting_factor_quantity_onhand) - float(component_consumption_totals[limiting_factor_item_code])
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

def display_test_page(request):
    countrecord_queryset = CountRecord.objects.all()
    countrecord_itemcodes = list(countrecord_queryset.values_list('item_code', flat=True))
    im_transactionhistory_queryset = ImItemTransactionHistory.objects.filter(transactioncode__iexact='II').filter(transactiondate__gt='2021-01-01').order_by('-transactiondate')
    for transaction in im_transactionhistory_queryset:
        print(transaction.transactiondate)
        if countrecord_queryset.filter(variance=abs(transaction.transactionqty)).filter(item_code__iexact=transaction.itemcode).exists():
            transaction.counted_variance = countrecord_queryset.filter(variance=abs(transaction.transactionqty)).filter(item_code__iexact=transaction.itemcode).first().variance

    return render(request, 'core/testpage.html',
        { 'im_transactionhistory_queryset' : im_transactionhistory_queryset }
        )