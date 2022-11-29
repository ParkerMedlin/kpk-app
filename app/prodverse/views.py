from django.shortcuts import render
from django.http import JsonResponse

from core.models import ProdBillOfMaterials, CiItem
from .models import *

import urllib.parse

def get_json_ciItem_fields(request):
    if request.method == "GET":
        ciItem_queryset = CiItem.objects.all().distinct('component_itemcode')
        itemcode_list = []
        itemcodedesc_list = []
        for item in ciItem_queryset:
            itemcode_list.append(item.itemcode)
            itemcodedesc_list.append(item.itemcodedesc)

        ciItem_json = {
            'itemcodes' : itemcode_list,
            'itemcodedescs' : itemcodedesc_list
        }

    return JsonResponse(ciItem_json, safe=False)

def display_lookup_item(request):
    
    return render(request, 'prodverse/lookupitem.html')

def display_excel_inline(request):

    return render(request, 'prodverse/exceline.html')

def get_json_item_info(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_item = CiItem.objects.get(itemcode=item_code)
        if ProdBillOfMaterials.objects.filter(component_itemcode__icontains=item_code).exists():
            requested_item_bom = ProdBillOfMaterials.objects.filter(component_itemcode__icontains=item_code).first()
        else:
            requested_item_bom.qtyonhand = "No."
            requested_item_bom.standard_uom = "No."
        responseData = {
            "reqItemDesc" : requested_item.itemcodedesc,
            "reqQty" : requested_item_bom.qtyonhand,
            "standardUOM" : requested_item_bom.standard_uom
            }
    return JsonResponse(responseData, safe=False)

def get_json_item_from_desc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_item = CiItem.objects.get(itemcodedesc=item_desc)
        bom_item = ProdBillOfMaterials.objects.filter(component_desc__icontains=item_desc)
        if bom_item.exists():
            requested_item_bom = bom_item.first()
        else:
            requested_item_bom.qtyonhand = "No."
            requested_item_bom.standard_uom = "No."
        responseData = {
            "reqItemCode" : requested_item.itemcode,
            "reqQty" : requested_item_bom.qtyonhand,
            "standardUOM" : requested_item_bom.standard_uom
            }
    return JsonResponse(responseData, safe=False)