from django.shortcuts import render
from .models import ChecklistLogForm,LotNumRecordForm,ChecklistLog,BlendThese,LotNumRecord,BlendInstruction,PoPurchaseOrderDetail,ImItemWarehouse,ImItemTransactionHistory,ImItemCost,CiItem,BmBillHeader,BmBillDetail
from django.http import HttpResponseRedirect
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
    CiItemDB = CiItem.objects.all()
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


def blendsheet(request, lot):
    lotInfoQ = LotNumRecord.objects.get(lot_number=lot)
    blend_part_number = lotInfoQ.part_number
    procQ = BlendInstruction.objects.filter(blend_part_num=blend_part_number)
    procOne = procQ[0]
    ingrQ = BmBillHeader.objects.all()
    current_user = request.user
    
    return render(request, 'core/blendsheet.html', {'lotInfo': lotInfoQ, 'procInfo': procQ, 'stepOne': procOne})