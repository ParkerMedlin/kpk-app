from django.shortcuts import render
from django.http import JsonResponse

from core.models import ProdBillOfMaterials, CiItem, ImItemWarehouse
from .models import *

def display_lookup_item(request):
    CiItem_data = CiItem.objects.all()
    
    return render(request, 'prodverse/lookupitem.html', {'CiItem_data' : CiItem_data})

def get_json_item_info(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_item = CiItem.objects.get(itemcode=item_code)
        requested_item_qty = ProdBillOfMaterials.objects.get(component_itemcode=item_code)
        responseData = {
            "reqItemDesc" : requested_item.itemcodedesc,
            "reqQty" : requested_item_qty.qtyonhand,
        }
    return JsonResponse(responseData, safe=False)