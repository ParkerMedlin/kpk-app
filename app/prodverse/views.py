from django.shortcuts import render
from django.http import JsonResponse

from core.models import ProdBillOfMaterials, CiItem, ImItemWarehouse
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
        requested_ci_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        requested_im_warehouse_item = ImItemWarehouse.objects.filter(itemcode__iexact=item_code, warehousecode__exact='MTG').first()
        response_item = {
            "itemcode" : requested_ci_item.itemcode,
            "description" : requested_ci_item.itemcodedesc,
            "qtyOnHand" : requested_im_warehouse_item.quantityonhand,
            "standardUOM" : requested_ci_item.standardunitofmeasure
            }
    return JsonResponse(response_item, safe=False)

def get_json_from_item_desc(request):
    if request.method == "GET":
        item_desc = request.GET.get('item', 0)
        item_desc = urllib.parse.unquote(item_desc)
        requested_ci_item = CiItem.objects.filter(itemcodedesc__iexact=item_desc).first()
        item_code = requested_ci_item.itemcode
        requested_im_warehouse_item = ImItemWarehouse.objects.filter(itemcode__iexact=item_code, warehousecode__exact='MTG').first()
        response_item = {
            "itemcode" : requested_ci_item.itemcode,
            "description" : requested_ci_item.itemcodedesc,
            "qtyOnHand" : requested_im_warehouse_item.quantityonhand,
            "standardUOM" : requested_ci_item.standardunitofmeasure
            }
    return JsonResponse(response_item, safe=False)

def get_json_prodBOM_fields(request):
    if request.method == "GET":
        prod_bom_queryset = ProdBillOfMaterials.objects.all().distinct('component_itemcode')
        itemcode_list = []
        itemcodedesc_list = []
        for item in prod_bom_queryset:
            itemcode_list.append(item.component_itemcode)
            itemcodedesc_list.append(item.component_desc)

        prod_bom_json = {
            'itemcodes' : itemcode_list,
            'itemcodedescs' : itemcodedesc_list
        }

    return JsonResponse(prod_bom_json, safe=False)