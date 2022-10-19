from django.shortcuts import render
from django.http import JsonResponse

from core.models import ProdBillOfMaterials, CiItem, ImItemWarehouse
from .models import *

def display_lookup_item(request):
    CiItem_data = list(CiItem.objects.only('itemcode'))
    
    return render(request, 'prodverse/lookupitem.html', {'CiItem_data' : CiItem_data})

def get_json_item_info(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_item = CiItem.objects.get(itemcode=item_code)
        if ProdBillOfMaterials.objects.filter(component_itemcode__icontains=item_code).exists():
            requested_item_qty = ProdBillOfMaterials.objects.filter(component_itemcode__icontains=item_code).first()
        else: 
            requested_item_qty = "No."
        responseData = {
            "reqItemDesc" : requested_item.itemcodedesc,
            "reqQty" : requested_item_qty.qtyonhand,
            }
    return JsonResponse(responseData, safe=False)