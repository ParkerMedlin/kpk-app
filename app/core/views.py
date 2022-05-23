from django.shortcuts import render
from .models import ChecklistLogForm,LotNumRecordForm,ChecklistLog,BlendThese,LotNumRecord,BlendInstruction,PoPurchaseOrderDetail,ImItemWarehouse,ImItemTransactionHistory,ImItemCost,CiItem,BmBillHeader,BmBillDetail,ChemLocation
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from datetime import datetime
from rest_framework import viewsets
from .serializers import BlendInstructionSerializer,BlendTheseSerializer,BmBillDetailSerializer,BmBillHeaderSerializer,ChecklistLogSerializer,CiItemSerializer,ImItemCostSerializer,ImItemTransactionHistorySerializer,ImItemWarehouseSerializer,LotNumRecordSerializer,PoPurchaseOrderDetailSerializer


#API Ser
###VIEWSETS THAT CALL THE APPROPRIATE SERIALIZER CLASS FROM serializers.py### 
###Edit these ViewSets to dictate how table is queried###
class BlendInstructionViewSet(viewsets.ModelViewSet):
    queryset = BlendInstruction.objects.all()
    serializer_class = BlendInstructionSerializer
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

def safetychecklist(request):
    submitted = False
    if request.method == "POST":
        form = ChecklistLogForm(request.POST)
        if form.is_valid():
            checklistSubmission = form.save(commit=False)
            today = datetime.now()
            checklistSubmission.date = today
            current_user = request.user
            checklistSubmission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklistSubmission.save()
            return HttpResponseRedirect('/core/safetychecklist?submitted=True')
    else:
        form = ChecklistLogForm
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/forkliftsafetylist.html', {'form':form, 'submitted':submitted})


def blendsforthese(request):
    get_blends = BlendThese.objects.all()
    return render(request, 'core/blendthese.html', {'blendlist': get_blends,})


def lotnumrecords(request):
    get_lotnums = LotNumRecord.objects.order_by('-date')
    return render(request, 'core/lotnumrecords.html', {'lotnumlist': get_lotnums})


def lotnumform(request):
    submitted=False
    today = datetime.now()
    nextLotNum = chr(64 + datetime.now().month)+str(datetime.now().year % 100)+str(int(str(LotNumRecord.objects.order_by('-date')[0])[-4:])+1).zfill(4)
    CiItemDB = CiItem.objects.filter(itemcodedesc__startswith="BLEND-")
    if request.method == "POST":
        form = LotNumRecordForm(request.POST)
        if form.is_valid():
            newLotNumSubmission = form.save(commit=False)
            newLotNumSubmission.date = today
            newLotNumSubmission.lot_number = nextLotNum
            newLotNumSubmission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        form = LotNumRecordForm(initial={'lot_number': nextLotNum, 'date': today,})
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/lotnumform.html', {'form':form, 'submitted':submitted, 'nextLotNum':nextLotNum, 'CiItemDB':CiItemDB})

def itemcodedesc_request(request):
    if request.method == "GET":
        gotItemCode = request.GET.get('item', 0)
        desc = CiItem.objects.get(itemcode=gotItemCode)
    return JsonResponse(desc.itemcodedesc, safe=False)

def blendsheet(request, lot):
    # If the lot steps don't exist yet, create them


    # Get info about this batch from the lot number table
    lotInfoQuery = LotNumRecord.objects.get(lot_number=lot)
    blend_part_number = lotInfoQuery.part_number
    instructionQuery = BlendInstruction.objects.filter(blend_part_num=blend_part_number)

    blendInfo = {'part_number': blend_part_number,
                    'description': lotInfoQuery.description,
                    'lot_number': lotInfoQuery.lot_number,
                    'quantity': lotInfoQuery.quantity,
                    'ref_no': instructionQuery.first().ref_no,
                    'prepared_by': instructionQuery.first().prepared_by,
                    'prepared_date': instructionQuery.first().prepared_date,
                    'lbs_per_gal': instructionQuery.first().lbs_per_gal}
    
    # Get info about the chems and their from the BmBillDetail, CiItem, and ChemLocation tables.
    allIngredientsPNList = BmBillDetail.objects.exclude(componentitemcode__startswith='/').filter(billno=blend_part_number).values_list('componentitemcode', flat=True)
    allIngredientsQtyFactorList =  BmBillDetail.objects.exclude(componentitemcode__startswith='/').filter(billno=blend_part_number).values_list('quantityperbill', flat=True)
    ingredientsQtyFactorDict = dict(((modicterator['componentitemcode'], modicterator['quantityperbill']) for modicterator in allIngredientsQtyFactorList.values('componentitemcode', 'quantityperbill')))
    allUOMList =  BmBillDetail.objects.exclude(componentitemcode__startswith='/').filter(billno=blend_part_number).values_list('unitofmeasure', flat=True)
    uomDict = dict(((modicterator['componentitemcode'], modicterator['unitofmeasure']) for modicterator in allUOMList.values('componentitemcode', 'unitofmeasure')))
    CiItemDict = dict(((modicterator['itemcode'], modicterator['itemcodedesc']) for modicterator in CiItem.objects.values('itemcode', 'itemcodedesc')))
    ChemGenLocationDict = dict(((modicterator['part_number'], modicterator['generallocation']) for modicterator in ChemLocation.objects.values('part_number', 'generallocation')))
    ChemSpecLocationDict = dict(((modicterator['part_number'], modicterator['specificlocation']) for modicterator in ChemLocation.objects.values('part_number', 'specificlocation')))
    ingredientsDict = {}
    for partNum in allIngredientsPNList:
        ingredientsDict[partNum] = (CiItemDict[partNum], 
                                    ingredientsQtyFactorDict[partNum]*round(lotInfoQuery.quantity),
                                    uomDict[partNum], ChemGenLocationDict[partNum],
                                    ChemSpecLocationDict[partNum]
                                    )
    ingredients = [(ingredientPN, ingredientsDict.get(ingredientPN)) for ingredientPN in allIngredientsPNList]

    return render(request, 'core/blendsheet.html', { 'instructionQuery': instructionQuery, 'ingredients': ingredients, 'blendInfo': blendInfo})