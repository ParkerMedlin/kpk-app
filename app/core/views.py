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

def forkliftserial_request(request):
    if request.method == "GET":
        gotNum = request.GET.get('unit_number', 0)
        print(gotNum)
        forklift = Forklift.objects.get(unit_number=gotNum)
        print(forklift.serial_no)
    return JsonResponse(forklift.serial_no, safe=False)

@login_required
def forkliftchecklist(request):
    submitted = False
    forkliftQuery = Forklift.objects.all()
    if request.method == "POST":
        form = ChecklistLogForm(request.POST or None)
        if form.is_valid():
            checklistSubmission = form.save(commit=False)
            current_user = request.user
            checklistSubmission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklistSubmission.save()
            return HttpResponseRedirect('/core/forkliftchecklist?submitted=True')
        else:
            return render(request, 'core/forkliftchecklist.html', {'form':form, 'submitted':submitted, 'forkliftQuery': forkliftQuery})
    else:
        form = ChecklistLogForm
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/forkliftchecklist.html', {'form':form, 'submitted':submitted, 'forkliftQuery': forkliftQuery})

def blendsforthese(request):
    get_blends = BlendThese.objects.all().order_by('starttime')
    return render(request, 'core/blendthese.html', {'blendlist': get_blends,})

def lotnumrecords(request):
    lotNumQS = LotNumRecord.objects.order_by('-date_created')
    return render(request, 'core/lotnumrecords.html', {'lotnumlist': lotNumQS})

@login_required
def lotnumform(request):
    submitted=False
    today = datetime.datetime.now()
    nextLotNum = chr(64 + datetime.datetime.now().month)+str(datetime.datetime.now().year % 100)+str(int(str(LotNumRecord.objects.order_by('-date_created')[0])[-4:])+1).zfill(4)
    BlendInstructionQS = BlendInstruction.objects.order_by('blend_part_num', 'step_no')
    CiItemDB = CiItem.objects.filter(itemcodedesc__startswith="BLEND-")
    if request.method == "POST":
        form = LotNumRecordForm(request.POST)
        if form.is_valid():
            newLotNumSubmission = form.save(commit=False)
            newLotNumSubmission.date_created = today
            newLotNumSubmission.lot_number = nextLotNum
            newLotNumSubmission.save()
            ourBlendSteps = BlendInstructionQS.filter(blend_part_num__icontains=newLotNumSubmission.part_number)
            for blndStep in ourBlendSteps:
                if blndStep.step_qty == '': 
                    this_step_qty = ''
                else:
                    this_step_qty = float(blndStep.step_qty) * float(newLotNumSubmission.quantity)
                newStep = BlendingStep(
                    step_no = blndStep.step_no,
                    step_desc = blndStep.step_desc,
                    step_qty = this_step_qty,
                    step_unit = blndStep.step_unit,
                    qty_added = "",
                    component_item_code = blndStep.component_item_code,
                    notes_1 = blndStep.notes_1,
                    notes_2 = blndStep.notes_2,
                    blend_part_num = blndStep.blend_part_num,
                    blend_desc = newLotNumSubmission.description,
                    ref_no = blndStep.ref_no,
                    prepared_by = blndStep.prepared_by,
                    prepared_date = blndStep.prepared_date,
                    lbs_per_gal = blndStep.lbs_per_gal,
                    blend_lot_number = newLotNumSubmission.lot_number,
                    lot = newLotNumSubmission
                    )
                newStep.save()
            newLotNumSubmission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        form = LotNumRecordForm(initial={'lot_number':nextLotNum, 'date_created':today,})
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/lotnumform.html', {'form':form, 'submitted':submitted, 'nextLotNum':nextLotNum, 'CiItemDB':CiItemDB,})

def itemcodedesc_request(request):
    if request.method == "GET":
        gotItemCode = request.GET.get('item', 0)
        desc = CiItem.objects.get(itemcode=gotItemCode)
    return JsonResponse(desc.itemcodedesc, safe=False)

# @login_required
def blendsheet(request, lot):
    submitted=False
    thisLot = LotNumRecord.objects.get(lot_number=lot)
    stepsQS = BlendingStep.objects.filter(blend_lot_number__icontains=lot)
    stepOne = stepsQS.first()
    
    # Get info about the chems from BlendBillofMaterials ChemLocation tables.
    chemList = BlendBillOfMaterials.objects.filter(bill_pn=thisLot.part_number)
    for chemical in chemList:
        quantityRequired = 0
        for step in stepsQS.filter(component_item_code__icontains=chemical.component_itemcode):
            quantityRequired+=float(step.step_qty)
        chemical.qtyreq = quantityRequired
        chemLocQS = ChemLocation.objects.filter(part_number=chemical.component_itemcode)
        chemical.area = chemLocQS.first().specificlocation
        chemical.location = chemLocQS.first().generallocation


    BlendingStepFormset = modelformset_factory(BlendingStep, form=BlendingStepModelForm, extra=0)
    thisLotFormset = BlendingStepFormset(request.POST or None, queryset=stepsQS)
    
    if request.method == 'POST':
        print(thisLotFormset)
        if thisLotFormset.is_valid():
            thisLotFormset.save()
            
            return HttpResponseRedirect('/core/blendsheetcomplete')
        else:
            thisLotFormset = BlendingStepFormset(request.POST or None, queryset=stepsQS)
            if 'submitted' in request.GET:
                submitted=True

        

    return render(request, 'core/blendsheet.html', 
                    { 'thisLot': thisLot,
                    'submitted': submitted,
                    'stepsQS': stepsQS,
                    'ingredients': chemList, 
                    'stepOne': stepOne,
                    'thisLotFormset': thisLotFormset
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
        component.chemShortThreeWk = float(component.adjusted_qtyonhand) - component.chemNeededThreeWk
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

def testPageFunction(request):
    logsQs = ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        engine_oil__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        propane_tank__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        radiator_leaks__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        tires__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        mast_and_forks__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        leaks__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        horn__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        driver_compartment__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        seatbelt__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        battery__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        safety_equipment__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        steering__contains='Bad') | ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
        brakes__contains='Bad').order_by('unit_number')
    
   
    allIssuesDict = {}
    for object in logsQs:
        if object.engine_oil == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_engine_oil_issue'] = object.engine_oil_comments
        if object.propane_tank == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_propane_tank_issue'] = object.propane_tank_comments
        if object.radiator_leaks == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_radiator_leaks_issue'] = object.radiator_leaks_comments
        if object.tires == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_tires_issue'] = object.tires_comments
        if object.mast_and_forks == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_mast_and_forks_issue'] = object.mast_and_forks_comments
        if object.leaks == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_leaks_issue'] = object.leaks_comments
        if object.horn == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_horn_issue'] = object.horn_comments
        if object.driver_compartment == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_driver_compartment_issue'] = object.driver_compartment_comments
        if object.seatbelt == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_seatbelt_issue'] = object.seatbelt_comments
        if object.battery == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_battery_issue'] = object.battery_comments
        if object.safety_equipment == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_safety_equipment_issue'] = object.safety_equipment_comments
        if object.steering == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_steering_issue'] = object.steering_comments
        if object.brakes == 'Bad':
            allIssuesDict[object.unit_number.unit_number + '_brakes_issue'] = object.brakes_comments
    
    html_table = ''
    for key, value in allIssuesDict.items():
        html_table += '''<tr>
                            <td>''' + (key[:2]).replace('_','') + '''</td>
                            <td>''' + value  + '''</td>
                            </tr>'''
    dd = {}
    dd['a'] = html_table

    # logsQs = ChecklistLog.objects.filter(submitted_date__gte=date.today()).filter(
    #     propane_tank__contains='Bad')
    return render(request, 'core/testpage.html', {'logsQs': logsQs, 'allIssuesDict':allIssuesDict, 'dd':dd})