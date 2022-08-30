from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import *
from django.forms.models import modelformset_factory
from django.db.models.signals import pre_save
from django.dispatch import receiver    
from .forms import *
from django.http import HttpResponseRedirect, JsonResponse
from datetime import datetime
import datetime
from datetime import date
from rest_framework import viewsets
from .serializers import *

#API Ser
###VIEWSETS THAT CALL THE APPROPRIATE SERIALIZER CLASS FROM serializers.py### 
###Edit these ViewSets to dictate how table is queried###
class BlendBillOfMaterialsViewSet(viewsets.ModelViewSet):
    queryset = BlendBillOfMaterials.objects.all()
    serializer_class = BlendBillOfMaterialsSerializer
class BlendInstructionViewSet(viewsets.ModelViewSet):
    queryset = BlendInstruction.objects.all()
    serializer_class = BlendInstructionSerializer
class BlendInvLogViewSet(viewsets.ModelViewSet):
    queryset = BlendInvLog.objects.all()
    serializer_class = BlendInvLogSerializer
class BlendTheseViewSet(viewsets.ModelViewSet):
    queryset = BlendThese.objects.all()
    serializer_class = BlendTheseSerializer
class BmBillDetailViewSet(viewsets.ModelViewSet):
    queryset = BmBillDetail.objects.all()
    serializer_class = BmBillDetailSerializer
class BmBillHeaderViewSet(viewsets.ModelViewSet):
    queryset = BmBillHeader.objects.all()
    serializer_class = BmBillHeaderSerializer
class ChecklistSubmissionTrackerViewSet(viewsets.ModelViewSet):
    queryset = ChecklistSubmissionTracker.objects.all()
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
    return render(request, 'core/lotnumrecords.html', {'lot_num_queryset': lot_num_queryset})

def display_new_lot_form(request):
    submitted=False
    today = datetime.datetime.now()
    next_lot_number = chr(64 + datetime.datetime.now().month)+str(datetime.datetime.now().year % 100)+str(int(str(LotNumRecord.objects.order_by('-date_created')[0])[-4:])+1).zfill(4)
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
    
    # Get info about the chems from BlendBillofMaterials ChemLocation tables.
    blend_components = BlendBillOfMaterials.objects.filter(bill_pn=blend_steps.part_number)
    for component in blend_components:
        quantity_required = 0
        for step in this_lot.filter(component_item_code__icontains=component.component_itemcode):
            quantity_required+=float(step.step_qty)
        component.qtyreq = quantity_required
        component_locations = ChemLocation.objects.filter(part_number=component.component_itemcode)
        component.area = component_locations.first().generallocation
        component.location = component_locations.first().specificlocation


    steps_formset = modelformset_factory(BlendingStep, form=BlendingStepModelForm, extra=0)
    this_lot_Formset = steps_formset(request.POST or None, queryset=blend_steps)
    
    if request.method == 'POST':
        print(this_lot_Formset)
        if this_lot_Formset.is_valid():
            this_lot_Formset.save()
            
            return HttpResponseRedirect('/core/blendsheetcomplete')
        else:
            this_lot_Formset = steps_formset(request.POST or None, queryset=blend_steps)
            if 'submitted' in request.GET:
                submitted=True

    return render(request, 'core/blendsheet.html', 
                { 'blend_steps': blend_steps,
                'submitted': submitted,
                'this_lot': this_lot,
                'blend_components': blend_components, 
                'first_step': first_step,
                'this_lot_Formset': this_lot_Formset
                })

def blendsheetcomplete(request):
    return render(request, 'core/blendsheetcomplete.html')

def reportcenter(request):
    CiItemDB = CiItem.objects.filter(itemcodedesc__startswith="BLEND-") | CiItem.objects.filter(itemcodedesc__startswith="CHEM") | CiItem.objects.filter(itemcodedesc__startswith="FRAGRANCE") | CiItem.objects.filter(itemcodedesc__startswith="DYE")
    reportform = ReportForm
    shortBlends = BlendThese.objects.all()
    shortBlends_pnList = []
    for blend in shortBlends:
        shortBlends_pnList.append(blend.blend_pn)
    bomForShortBlends = BlendBillOfMaterials.objects.filter(bill_pn__in=shortBlends_pnList)
    for component in bomForShortBlends:
        component.blendQtyShortThreeWk = shortBlends.filter(blend_pn__icontains=component.bill_pn).first().three_wk_short
        component.chemNeededThreeWk = float(component.blendQtyShortThreeWk) * float(component.qtyperbill)
        component.chemShortThreeWk = float(component.qtyonhand) - component.chemNeededThreeWk
    chemsShort = bomForShortBlends
    return render(request, 'core/reportcenter.html', {'reportform':reportform, 'CiItemDB':CiItemDB, 'chemsShort':chemsShort})

def reportmaker(request, which_report, part_number):
    if which_report=="Lot-Numbers":
        lotnumsFiltered = LotNumRecord.objects.filter(part_number__icontains=part_number)
        blenddesc = lotnumsFiltered.first().description
        blendinfo = {'part_number':part_number, 'desc':blenddesc}
        return render(request, 'core/reports/lotnumsreport.html', {'lotnums':lotnumsFiltered, 'blendinfo': blendinfo})

    elif which_report=="All-Upcoming-Runs":
        timetableFiltered = TimetableRunData.objects.filter(blend_pn__icontains=part_number).order_by('starttime')
        blenddesc = timetableFiltered.first().blend_desc
        blendinfo = {'part_number':part_number, 'desc':blenddesc}
        return render(request, 'core/reports/upcomingrunsreport.html', {'upcomingruns':timetableFiltered, 'blendinfo': blendinfo})

    elif which_report=="Chem-Shortage":
        blend_list = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number) # all blends containing the chem PN provided
        blend_pn_list = [] 
        for item in blend_list: # insert each part number into blend_pn_list
            blend_pn_list.append(item.bill_pn)
        run_list = TimetableRunData.objects.filter(blend_pn__in=blend_pn_list,oh_after_run__lt=0).order_by('starttime') # filter for runs that will be short of blend
        runningTotalChemNeed = 0.0 # keep track of the running total of chemical needed regardless of what blend it's being used for 
        for run in run_list:
            singleBOMobject = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number,bill_pn__icontains=run.blend_pn).first()
            run.chemFactor = singleBOMobject.qtyperbill # grab the factor for this chemical in this blend from the BOM
            run.chemNeededForRun = float(run.chemFactor) * float(run.adjustedrunqty)
            runningTotalChemNeed = runningTotalChemNeed + float(run.chemFactor * run.adjustedrunqty) # update the total amount of our chemical that is needed so far
            run.chemOHafterRun = float(singleBOMobject.adjusted_qtyonhand) - runningTotalChemNeed # chemical on hand minus cumulative amount of the chemical needed 
            run.chemUnit = singleBOMobject.standard_uom # unit of measure for display purposes
        item_info = {
                    'item_pn': BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_itemcode, 
                    'item_desc': BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_desc
                    }
        return render(request, 'core/reports/chemshortagereport.html', {'run_list':run_list, 'item_info':item_info})

    elif which_report=="Startron-Runs":
        filterList = ["14000.B", "14308.B", "14308AMBER.B", "93100DSL.B", "93100GAS.B", "93100TANK.B", "93100GASBLUE.B", "93100GASAMBER.B"]
        timetableStartron = TimetableRunData.objects.filter(blend_pn__in=filterList)
        return render(request, 'core/reports/startronreport.html', {'startronruns':timetableStartron})

    elif which_report=="Transaction-History":
        txnsFiltered = ImItemTransactionHistory.objects.filter(itemcode__icontains=part_number).order_by('-transactiondate')
        itemdesc = BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_desc
        for item in txnsFiltered:
            item.description = itemdesc
        iteminfo = {'part_number':part_number, 'desc':itemdesc}
        return render(request, 'core/reports/transactionsreport.html', {'txns':txnsFiltered, 'iteminfo': iteminfo})
        
    elif which_report=="Physical-Count-History":
        blndCountsFiltered = BlendInvLog.objects.filter(blend_pn__icontains=part_number)
        part_info = {'part_number': part_number,
                        'part_desc': BlendBillOfMaterials.objects.filter(component_itemcode__icontains=part_number).first().component_desc
                    }
        return render(request, 'core/reports/inventorycountsreport.html', {'blndCountsFiltered':blndCountsFiltered, 'part_info':part_info})

    elif which_report=="Counts-And-Transactions":
        ctsAndTrxns = { 'currentstatus': 'workin on it'}
        return render(request, 'core/reports/countsandtransactionsreport.html', {'ctsAndTrxns':ctsAndTrxns})
    else:
        return render(request, '')
    
def upcomingblendcounts(request):
    upcomingBlndCounts = UpcomingBlendCount.objects.all()
    today = datetime.date.today()
    eightMonthsAgo = today - datetime.timedelta(weeks=36)
    txnsSortedDistinct = ImItemTransactionHistory.objects.filter(transactiondate__gt=eightMonthsAgo).order_by('-transactiondate')
    for run in upcomingBlndCounts:
        run.lastCount = BlendInvLog.objects.filter(blend_pn__icontains=run.blend_pn).order_by('-count_date').first().count
        run.lastCtDate = BlendInvLog.objects.filter(blend_pn__icontains=run.blend_pn).order_by('-count_date').first().count_date
        run.lastTxn = txnsSortedDistinct.filter(itemcode__icontains=run.blend_pn).first().transactioncode
        run.lastTxnDate = txnsSortedDistinct.filter(itemcode__icontains=run.blend_pn).first().transactiondate
        
    return render(request, 'core/upcomingblndcounts.html', {'upcomingBlndCounts': upcomingBlndCounts})

def thisLotToSchedule(request, lotnum, partnum, blendarea):
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

def blendSchedule(request, blendarea):
    desk1Blends = DeskOneSchedule.objects.all().order_by('order')
    for blend in desk1Blends:
        try:
            blend.when_entered = ImItemCost.objects.get(receiptno=blend.blend_pn)
        except ImItemCost.DoesNotExist:
            blend.when_entered = "Not Entered"
    desk2Blends = DeskTwoSchedule.objects.all()
    for blend in desk2Blends:
        try:
            blend.when_entered = ImItemCost.objects.get(receiptno=blend.blend_pn)
        except ImItemCost.DoesNotExist:
            blend.when_entered = "Not Entered"
    hxBlends = HorixBlendThese.objects.filter(line__icontains='Hx')
    dmBlends = HorixBlendThese.objects.filter(line__icontains='Dm')
    toteBlends = HorixBlendThese.objects.filter(line__icontains='Totes')

    blend_area = blendarea
    return render(request, 'core/blendschedule.html', {'desk1Blends': desk1Blends,
                                                        'desk2Blends': desk2Blends, 
                                                        'hxBlends': hxBlends, 
                                                        'dmBlends': dmBlends, 
                                                        'toteBlends': toteBlends,
                                                        'blend_area': blend_area})

def blndSchedMgmt(request, reqType, blend_area, blend_id, blend_listposition):
    if blend_area == 'Desk1':
        blend = DeskOneSchedule.objects.get(pk=blend_id)
    elif blend_area == 'Desk2':
        blend = DeskTwoSchedule.objects.get(pk=blend_id)

    if reqType == 'moveupone':
        blend.up()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if reqType == 'movedownone':
        blend.down()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if reqType == 'movetotop':
        blend.top()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if reqType == 'movetobottom':
        blend.bottom()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)
    if reqType == 'delete':
        blend.delete()
        return HttpResponseRedirect('/core/blendschedule/'+blend_area)

def batchIssueTable(request, line):
    allRunsQS = IssueSheetNeeded.objects.all()
    if line == 'INLINE':
        lineRunsQS = allRunsQS.filter(prodline__icontains='INLINE').order_by('starttime')
    if line == 'PDLINE':
        lineRunsQS = allRunsQS.filter(prodline__icontains='PD LINE').order_by('starttime')
    if line == 'JBLINE':
        lineRunsQS = allRunsQS.filter(prodline__icontains='JB LINE').order_by('starttime')
    if line == 'all':
        lineRunsQS = allRunsQS.order_by('prodline','starttime')
    dateToday = date.today().strftime('%m/%d/%Y')

    return render(request, 'core/batchissuetable.html', {'lineRunsQS':lineRunsQS, 'line':line, 'dateToday':dateToday})

def issueSheets(request, prodLine, issueDate):
    allRunsQS = IssueSheetNeeded.objects.all()
    thisLineRunsQS = allRunsQS.filter(prodline__icontains=prodLine).order_by('starttime')
    
    return render(request, 'core/issuesheets.html', {'thisLineRunsQS':thisLineRunsQS, 'prodLine':prodLine, 'issueDate': issueDate})

def testPageFunction(request, prodLine, issueDate):
    allRunsQS = IssueSheetNeeded.objects.all()
    thisLineRunsQS = allRunsQS.filter(prodline__icontains=prodLine).order_by('starttime')
    pdLineRunsQS = allRunsQS.filter(prodline__icontains='PD LINE').order_by('starttime')
    jbLineRunsQS = allRunsQS.filter(prodline__icontains='JB LINE').order_by('starttime')
    
    
    return render(request, 'core/testpage.html', {'thisLineRunsQS':thisLineRunsQS, 'prodLine':prodLine, 'issueDate': issueDate})