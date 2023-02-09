from django.shortcuts import render, redirect
from django.http import JsonResponse

from core.models import BillOfMaterials, CiItem, ImItemWarehouse
from .models import *

import urllib.parse

def get_json_ciItem_fields(request):
    if request.method == "GET":
        ciItem_queryset = CiItem.objects.all().distinct('component_item_code')
        itemcode_list = []
        itemcodedesc_list = []
        for item in ciItem_queryset:
            itemcode_list.append(item.itemcode)
            itemcodedesc_list.append(item.itemcodedesc)

        ciItem_json = {
            'item_codes' : itemcode_list,
            'itemcodedescs' : itemcodedesc_list
        }

    return JsonResponse(ciItem_json, safe=False)

def display_lookup_item(request):
    return render(request, 'prodverse/lookupitemqty.html')

def display_production_schedule(request):
    return render(request, 'prodverse/productionschedule.html')

def get_json_item_info(request):
    if request.method == "GET":
        lookup_type = request.GET.get('lookupType', 0)
        if lookup_type == 'itemCode':
            item_code = request.GET.get('item', 0)
        elif lookup_type == 'itemDescription':
            item_description = request.GET.get('item', 0)
            item_description = urllib.parse.unquote(item_description)
            item_code = CiItem.objects.filter(itemcodedesc__iexact=item_description).first().itemcode
        requested_ci_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        requested_im_warehouse_item = ImItemWarehouse.objects.filter(itemcode__iexact=item_code, warehousecode__exact='MTG').first()
        response_item = {
            "item_code" : requested_ci_item.itemcode,
            "item_description" : requested_ci_item.itemcodedesc,
            "qtyOnHand" : requested_im_warehouse_item.quantityonhand,
            "standardUOM" : requested_ci_item.standardunitofmeasure
            }
    return JsonResponse(response_item, safe=False)

def get_json_prodBOM_fields(request):
    if request.method == "GET":
        prod_bom_queryset = BillOfMaterials.objects.all().distinct('component_item_code')
        itemcode_list = []
        itemcodedesc_list = []
        for item in prod_bom_queryset:
            itemcode_list.append(item.component_item_code)
            itemcodedesc_list.append(item.component_item_description)

        prod_bom_json = {
            'itemcodes' : itemcode_list,
            'itemcodedescs' : itemcodedesc_list
        }

    return JsonResponse(prod_bom_json, safe=False)

def display_specsheet_detail(request, item_code):
    try: 
        specsheet = SpecSheetData.objects.get(item_code__iexact=item_code)
        item_code_description = CiItem.objects.only("itemcodedesc").get(itemcode__iexact=item_code).itemcodedesc
        bom = BillOfMaterials.objects.filter(item_code__iexact=item_code)
        label_component_item_codes = list(SpecSheetLabels.objects.values_list('item_code', flat=True))
        label_items = SpecSheetLabels.objects.all()
        for bill in bom:
            if bill.component_item_code in label_component_item_codes:
                bill.weight_code = label_items.filter(item_code__iexact=bill.component_item_code).first().weight_code
                bill.location = label_items.filter(item_code__iexact=bill.component_item_code).first().location

        context = {
            'item_code': specsheet.item_code,
            'item_description': item_code_description,
            'component_item_code': specsheet.component_item_code,
            'product_class': specsheet.product_class,
            'water_flush': specsheet.water_flush,
            'solvent_flush': specsheet.solvent_flush,
            'soap_flush': specsheet.soap_flush,
            'oil_flush': specsheet.oil_flush,
            'polish_flush': specsheet.polish_flush,
            'package_retain': specsheet.package_retain,
            'uv_protect': specsheet.uv_protect,
            'freeze_protect': specsheet.freeze_protect,
            'min_weight': specsheet.min_weight,
            'target_weight': specsheet.target_weight,
            'max_weight': specsheet.max_weight,
            'upc': specsheet.upc,
            'scc': specsheet.scc,
            'us_dot': specsheet.us_dot,
            'special_notes': specsheet.special_notes,
            'eu_haz': specsheet.eu_case_marking,
            'haz_symbols': specsheet.haz_symbols,
            'pallet_footprint': specsheet.pallet_footprint,
            'notes': specsheet.notes,
            'bill_of_materials': bom,
        }
    except SpecSheetData.DoesNotExist:
            return redirect('specsheet_error_page')
    
    return render(request, 'prodverse/specsheet.html', context)

def display_specsheet_error_page(request):
    return render(request, 'prodverse/specsheet-error.html')