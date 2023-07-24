import requests
from datetime import datetime
import json
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from core.models import BillOfMaterials, CiItem, ImItemWarehouse
from prodverse.models import *
from django.db import transaction
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect

def display_item_qc(request):
    return render(request, 'prodverse/item-qc.html')

def display_pickticket_detail(request, item_code):
    bom = BillOfMaterials.objects.all().filter(item_code__iexact=item_code)
    bom.item_description = BillOfMaterials.objects.only("item_description").filter(item_code__iexact=item_code).first().item_description
    schedule_qty = request.GET.get('schedule-quantity', 0)
    for bill in bom:
        if float(request.GET.get('schedule-quantity', 0)) * float(bill.qtyperbill) != 0:
            bill.total_qty = float(request.GET.get('schedule-quantity', 0)) * float(bill.qtyperbill)
        else:
            bill.total_qty = 0.0

    context = {
        'bill_of_materials': bom,
        'item_code': item_code,
        'schedule_qty': schedule_qty,
    }
    
    return render(request, 'prodverse/pickticket.html', context)

def display_production_schedule(request):
    return render(request, 'prodverse/productionschedule.html')

@transaction.atomic
def display_specsheet_detail(request, item_code, po_number, juliandate):
    if request.method == 'POST':
        data = json.loads(request.body)
        state, created = SpecsheetState.objects.update_or_create(
            item_code=item_code, 
            po_number=po_number, 
            juliandate=juliandate,
            defaults={'state_json': data}
        )
        return JsonResponse({'status': 'success'})

    try: 
        specsheet = SpecSheetData.objects.get(item_code__iexact=item_code)
        item_code_description = CiItem.objects.only("itemcodedesc").get(itemcode__iexact=item_code).itemcodedesc
        bom = BillOfMaterials.objects.filter(item_code__iexact=item_code)
        label_component_item_codes = list(SpecSheetLabels.objects.values_list('item_code', flat=True))
        label_items = SpecSheetLabels.objects.all()
        try:
            state = SpecsheetState.objects.get(item_code=item_code, po_number=po_number, juliandate=juliandate)
            state_json = state.state_json
        except SpecsheetState.DoesNotExist:
            state_json = None
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
            'state_json': state_json,
        }
    except SpecSheetData.DoesNotExist:
        return redirect('/prodverse/specsheet/specsheet-lookup/?redirect=true')
    
    return render(request, 'prodverse/specsheet.html', context)

def display_specsheet_lookup_page(request):
    redirect_message = request.GET.get('redirect', None)
    context = {'redirect_message': redirect_message}
    return render(request, 'prodverse/specsheetlookup.html', context)

def get_last_modified(request, file_name):
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    file_url = f'{base_url}:1337/dynamic/html/{file_name}'
    
    response = requests.head(file_url)
    
    if response.status_code == 200:
        last_modified = response.headers.get('Last-Modified')
        if last_modified:
            last_modified_date = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
            return JsonResponse({'last_modified': last_modified_date.strftime('%Y-%m-%d %H:%M:%S')})
        else:
            return JsonResponse({'error': 'Last-Modified header not found'})
    else:
        return JsonResponse({'error': f'File not found: {file_url}'})

def display_items_to_count(request):
    record_type = request.GET.get('recordType')
    audit_group_queryset = AuditGroup.objects.all()
    for item in audit_group_queryset:
        item.item_description = CiItem.objects.filter(itemcode__iexact=item.item_code).first().itemcodedesc
    # Using values_list() to get a flat list of distinct values for the 'audit_group' field
    audit_group_list = list(AuditGroup.objects.values_list('audit_group', flat=True).distinct())

    return render(request, 'prodverse/itemstocount.html', {'audit_group_queryset' : audit_group_queryset, 
                                                           'audit_group_list' : audit_group_list})

def add_item_to_new_group(request):
    record_type = request.GET.get('recordType')
    new_audit_group = request.GET.get('auditGroup')
    redirect_page = request.GET.get('redirectPage')
    item_id = request.GET.get('itemID')
    this_item = get_object_or_404(AuditGroup, id = item_id)
    this_item.audit_group = new_audit_group

    return HttpResponseRedirect(f'/prodverse/items-to-count?recordType={record_type}')
