from django.shortcuts import render
from .models import safetyChecklistForm,lotnumrecordForm,checklistlog,blendthese,lotnumrecord,blendInstruction,PoPurchaseorderdetail,ImItemwarehouse,ImItemtransactionhistory,ImItemcost,CiItem,BmBillheader,BmBilldetail
from .models import blendthese
from django.http import HttpResponseRedirect
from datetime import datetime
from rest_framework import viewsets
from .serializers import checklistlogSerializer,blendtheseSerializer,lotnumrecordSerializer,blendInstructionSerializer,PoPurchaseorderdetailSerializer,ImItemwarehouseSerializer,ImItemtransactionhistorySerializer,ImItemcostSerializer,CiItemSerializer,BmBillheaderSerializer,BmBilldetailSerializer


#API Ser
###VIEWSETS THAT CALL THE APPROPRIATE SERIALIZER CLASS FROM serializers.py### 
###Edit these ViewSets to dictate how table is queried###
class checklistlogViewSet(viewsets.ModelViewSet):
    queryset = checklistlog.objects.all()
    serializer_class = checklistlogSerializer
class blendtheseViewSet(viewsets.ModelViewSet):
    queryset = blendthese.objects.all()
    serializer_class = blendtheseSerializer
class lotnumrecordViewSet(viewsets.ModelViewSet):
    queryset = lotnumrecord.objects.all()
    serializer_class = lotnumrecordSerializer
class blendInstructionViewSet(viewsets.ModelViewSet):
    queryset = blendInstruction.objects.all()
    serializer_class = blendInstructionSerializer
class PoPurchaseorderdetailViewSet(viewsets.ModelViewSet):
    queryset = PoPurchaseorderdetail.objects.all()
    serializer_class = PoPurchaseorderdetailSerializer
class ImItemwarehouseViewSet(viewsets.ModelViewSet):
    queryset = ImItemwarehouse.objects.all()
    serializer_class = ImItemwarehouseSerializer
class ImItemtransactionhistoryViewSet(viewsets.ModelViewSet):
    queryset = ImItemtransactionhistory.objects.all()
    serializer_class = ImItemtransactionhistorySerializer
class ImItemcostViewSet(viewsets.ModelViewSet):
    queryset = ImItemcost.objects.all()
    serializer_class = ImItemcostSerializer
class CiItemViewSet(viewsets.ModelViewSet):
    queryset = CiItem.objects.all()
    serializer_class = CiItemSerializer
class BmBillheaderViewSet(viewsets.ModelViewSet):
    queryset = BmBillheader.objects.all()
    serializer_class = BmBillheaderSerializer
class BmBilldetailViewSet(viewsets.ModelViewSet):
    queryset = BmBilldetail.objects.all()
    serializer_class = BmBilldetailSerializer



def safetychecklist(request):
    submitted = False
    if request.method == "POST":
        form = safetyChecklistForm(request.POST)
        if form.is_valid():
            checklistSubmission = form.save(commit=False)
            today = datetime.now()
            checklistSubmission.date = today
            current_user = request.user
            checklistSubmission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklistSubmission.save()
            return HttpResponseRedirect('/core/safetychecklist?submitted=True')
    else:
        form = safetyChecklistForm
        if 'submitted' in request.GET:
            submitted=True
    return render(request, 'core/forkliftsafetylist.html', {'form':form, 'submitted':submitted})


def blendsforthese(request):
    get_blends = blendthese.objects.all()
    return render(request, 'core/blendthese.html', {'blendlist': get_blends,})


def lotnumrecords(request):
    get_lotnums = lotnumrecord.objects.order_by('-date')
    return render(request, 'core/lotnumrecords.html', {'lotnumlist': get_lotnums})


def lotnumform(request):
    submitted=False
    nextLotNum = chr(64 + datetime.now().month)+str(datetime.now().year % 100)+str(int(str(lotnumrecord.objects.order_by('-date')[0])[-4:])+1).zfill(4)
    itemCodes = CiItem.objects.values_list('itemcode', flat=True)
    if request.method == "POST":
        form = lotnumrecordForm(request.POST)
        if form.is_valid():
            newLotNumSubmission = form.save(commit=False)
            today = datetime.now()
            newLotNumSubmission.date = today
            newLotNumSubmission.lot_number = nextLotNum
            newLotNumSubmission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        form = lotnumrecordForm
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/lotnumform.html', {'form':form, 'submitted':submitted, 'nextLotNum':nextLotNum, 'itemCodes':itemCodes})


def blendsheet(request, part_number, lot_number, quantity, description):
    procQ = blendInstruction.objects.filter()
    ingrQ = BmBillheader.objects.all()
    current_user = request.user
    blendDict = {'part_number': part_number,
                 'description': description,
                 'formulaRef': '',
                 'lbPerGal': '',
                 'quantity': quantity,
                 'lot_number': lot_number,
                 }
    
    return render(request, 'core/blendsheet.html', {'procedurelist': procQ, 'blendinfo': blendDict,})