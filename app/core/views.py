from django.shortcuts import render
from .models import *
from django.forms.models import model_to_dict
from .forms import *
from django.http import HttpResponseRedirect, JsonResponse
from datetime import datetime
import datetime
from datetime import date
from rest_framework import viewsets
from .serializers import *
import json


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
    get_lotnums = LotNumRecord.objects.order_by('-date_created')
    return render(request, 'core/lotnumrecords.html', {'lotnumlist': get_lotnums})


def lotnumform(request):
    submitted=False
    today = datetime.datetime.now()
    nextLotNum = chr(64 + datetime.datetime.now().month)+str(datetime.datetime.now().year % 100)+str(int(str(LotNumRecord.objects.order_by('-date_created')[0])[-4:])+1).zfill(4)
    BlendInstructionDB = BlendInstruction.objects.order_by('blend_part_num', 'step_no')
    CiItemDB = CiItem.objects.filter(itemcodedesc__startswith="BLEND-")
    if request.method == "POST":
        form = LotNumRecordForm(request.POST)
        if form.is_valid():
            newLotNumSubmission = form.save(commit=False)
            newLotNumSubmission.date_created = today
            newLotNumSubmission.lot_number = nextLotNum
            newLotNumSubmission.save()
            ourBlendSteps = BlendInstructionDB.filter(blend_part_num__icontains=newLotNumSubmission.part_number)
            numSteps = ourBlendSteps.count()
            emptyStringList = [''] # generate a list with as many empty strings as there are steps in the procedure
            for count in range(numSteps-1): 
                emptyStringList.append('')
            stepQtyFactorList = list(ourBlendSteps.all().values_list('step_qty', flat=True))
            stepQtyList = ['']
            for count in range(numSteps-1): 
                stepQtyList.append('')
            funIterator = 0
            for stepQtyFactor in stepQtyFactorList: 
                if stepQtyFactorList[funIterator] != "":
                    stepQtyList[funIterator] = float(newLotNumSubmission.quantity) * float(stepQtyFactor)
                funIterator+=1
            thisLotDict = {
                'step_no' : list(ourBlendSteps.all().values_list('step_no', flat=True)),
                'step_desc' : list(ourBlendSteps.all().values_list('step_desc', flat=True)),
                'step_qty' : stepQtyList,
                'step_unit' : list(ourBlendSteps.all().values_list('step_unit', flat=True)),
                'component_item_code' : list(ourBlendSteps.all().values_list('component_item_code', flat=True)),
                'chem_lot_no' : emptyStringList,
                'qty_added' : emptyStringList,
                'start_time' : emptyStringList,
                'end_time' : emptyStringList,
                'chkd_by' : emptyStringList,
                'mfg_chkd_by' : emptyStringList,
            }
            thisLotStepsJSON = json.dumps(thisLotDict)
            newLotNumSubmission.steps = thisLotStepsJSON
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

def blendsheet(request, lot):
    # If the lot steps don't exist yet, create them
    # Get info about this batch from the lot number table
    lotInfoQuery = LotNumRecord.objects.get(lot_number=lot)
    instructionQuery = BlendInstruction.objects.filter(blend_part_num=lotInfoQuery.part_number)
    
    blendInfo = {'part_number': lotInfoQuery.part_number,
                    'description': lotInfoQuery.description,
                    'lot_number': lotInfoQuery.lot_number,
                    'quantity': lotInfoQuery.quantity,
                    'ref_no': instructionQuery.first().ref_no,
                    'prepared_by': instructionQuery.first().prepared_by,
                    'prepared_date': instructionQuery.first().prepared_date,
                    'lbs_per_gal': instructionQuery.first().lbs_per_gal}
    
    # Get info about the chems from BlendBillofMaterials ChemLocation tables.
    chemList = BlendBillOfMaterials.objects.filter(bill_pn=lotInfoQuery.part_number)
    for chemical in chemList:
        quantityRequired = 0
        for step in instructionQuery.filter(component_item_code__icontains=chemical.component_itemcode):
            quantityRequired+=float(step.step_qty)*float(lotInfoQuery.quantity)
        chemical.qtyreq = quantityRequired
        chemLocQuery = ChemLocation.objects.filter(part_number=chemical.component_itemcode)
        chemical.area = chemLocQuery.first().specificlocation
        chemical.location = chemLocQuery.first().generallocation
        
    return render(request, 'core/blendsheet.html', 
                    { 'lotInfoQuery': lotInfoQuery,
                    'instructionQuery': instructionQuery,
                    'ingredients': chemList, 
                    'blendInfo' : blendInfo, 
                    })


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
