from django.shortcuts import render
from django.http import JsonResponse

from core.models import ProdBillOfMaterials, CiItem, ImItemWarehouse
from .models import *

import urllib.parse

def display_lookup_item(request):
    ci_item_queryset = CiItem.objects.exclude(itemcode__startswith="/C")
    context = {
        'ci_item_queryset' : ci_item_queryset,
        }
    
    return render(request, 'prodverse/lookupitem.html', context)

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

def get_json_item_from_desc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_item = CiItem.objects.get(itemcodedesc=item_desc)
        bom_item = ProdBillOfMaterials.objects.filter(component_desc__icontains=item_desc)
        if bom_item.exists():
            requested_item_qty = bom_item.first()
        else: 
            requested_item_qty = "No."
        responseData = {
            "reqItemCode" : requested_item.itemcode,
            "reqQty" : requested_item_qty.qtyonhand,
            }
    return JsonResponse(responseData, safe=False)