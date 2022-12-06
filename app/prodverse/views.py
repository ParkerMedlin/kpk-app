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
    return render(request, 'prodverse/lookupitemqty.html')

def display_excel_inline(request):
    return render(request, 'prodverse/excelinline.html')

def get_json_from_item_code(request):
    if request.method == "GET":
        item_code = request.GET.get('item', 0)
        requested_BOM_item = ProdBillOfMaterials.objects.filter(component_itemcode__iexact=item_code).first()
        response_item = {
            "itemcode" : requested_BOM_item.component_itemcode,
            "description" : requested_BOM_item.component_desc,
            "qtyOnHand" : requested_BOM_item.qtyonhand,
            "standardUOM" : requested_BOM_item.standard_uom
            }
    return JsonResponse(response_item, safe=False)

def get_json_from_item_desc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_BOM_item = ProdBillOfMaterials.objects.filter(component_desc__iexact=item_desc).first()
        response_item = {
            "itemcode" : requested_BOM_item.component_itemcode,
            "description" : requested_BOM_item.component_desc,
            "qtyOnHand" : requested_BOM_item.qtyonhand,
            "standardUOM" : requested_BOM_item.standard_uom
            }
    return JsonResponse(response_item, safe=False)