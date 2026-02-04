import datetime as dt
from datetime import date
import time
import pytz
import os
import base64
import json
import logging
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.db import connection
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Sum, Subquery, OuterRef, Q, CharField
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.serializers.json import DjangoJSONEncoder
from core.models import TankLevelLog
from core.models import *
from core.forms import *
from prodverse.models import *
from prodverse.forms import *
from core.kpkapp_utils.string_utils import *
from core.services.lot_numbers_services import *
from core.services.reports_services import *
from core.selectors.lot_numbers_selectors import (
    get_orphaned_lots,
    get_schedule_assignments_for_lots,
    get_blend_timestudy_report,
)
from core.selectors.function_toggle_selectors import get_all_function_toggles
from core.services.blend_scheduling_services import clean_completed_blends
from core.services.production_planning_services import build_schedule_snapshot, annotate_blend_shortage_records
from core.services.inventory_services import (
    get_item_recency_thresholds,
    get_tintpaste_needs,
    build_audit_group_display_items,
    build_count_list_display_data,
    build_uncounted_items_display,
)
from core.selectors.production_planning_selectors import get_schedulable_blend_shortages
from core.selectors.inventory_selectors import *
from core.selectors.reports_selectors import *
from core.selectors import get_sampling_personnel_options, list_discharge_tests
from core.kpkapp_utils.string_utils import get_unencoded_item_code
from core.services.lot_numbers_services import generate_next_lot_number
from core.services.blend_scheduling_services import get_blend_schedule_querysets, prepare_blend_schedule_queryset
from core.services.purchasing_alias_services import normalize_supply_type
from core.services.discharge_testing_services import is_lab_user
from django.core.paginator import Paginator
from core.selectors.batch_issue_selectors import (
    get_batch_issue_runs,
    get_positive_lot_numbers,
)
from core.services.batch_issue_services import (
    build_batch_issue_data,
    resolve_issue_date,
)
from core.services.blend_count_services import build_upcoming_blend_runs
from core.services.component_count_services import build_upcoming_component_counts

logger = logging.getLogger(__name__)

advance_blends = ['602602','602037US','602037','602011','602037EUR','93700.B','94700.B','93800.B','94600.B','94400.B','602067']

_SUPPLY_TYPE_LOOKUP = dict(PurchasingAlias.SUPPLY_TYPE_CHOICES)


@login_required
def display_timestudy_entry(request):
    """Render the timestudy entry page for tracking blend batch timing."""
    lots_queryset = LotNumRecord.objects.order_by('-id').values(
        'id',
        'lot_number',
        'desk',
        'item_code',
        'item_description',
        'start_time',
        'stop_time',
    )

    paginator = Paginator(lots_queryset, 300)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    elided_page_range = paginator.get_elided_page_range(page_obj.number) if paginator.num_pages else []

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'elided_page_range': elided_page_range,
        'current_page_number': page_obj.number if paginator.num_pages else 0,
        'timezone_label': timezone.get_current_timezone_name(),
    }
    return render(request, 'core/timestudies/timestudy_entry.html', context)


@login_required
def display_timestudy_report(request):
    """Render aggregated timestudy statistics grouped by blend item code."""

    report_data = get_blend_timestudy_report()

    context = {
        'rows': report_data['rows'],
        'generated_at': timezone.localtime(),
    }

    return render(request, 'core/timestudies/timestudy_report.html', context)

def display_forklift_checklist(request):
    """
    Displays forklift checklist form for operators to complete daily inspections.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with checklist form context
        
    Template:
        core/forkliftchecklist/forkliftchecklist.html
    """
    submitted = False
    forklift_queryset = Forklift.objects.all()
    if request.method == "POST":
        checklist_form = ChecklistLogForm(request.POST)
        if checklist_form.is_valid():
            checklist_submission = checklist_form.save(commit=False)
            current_user = request.user
            checklist_submission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklist_submission.save()
            return HttpResponseRedirect('/core/forklift-checklist?submitted=True')
    else:
        checklist_form = ChecklistLogForm()
    if 'submitted' in request.GET:
        submitted=True
    return render(request, 'core/forkliftchecklist/forkliftchecklist.html', {'checklist_form':checklist_form, 'submitted':submitted, 'forklift_queryset': forklift_queryset})

@login_required
@ensure_csrf_cookie
def display_bom_cost_tool(request):
    """Render the BOM cost estimator UI."""
    return render(request, 'core/reports/bom_cost_tool.html')


@login_required
@ensure_csrf_cookie
def display_sales_order_vs_bom_cost_report(request):
    """Render the Sales Order vs BOM Cost report UI."""
    return render(request, 'core/reports/sales_order_vs_bom_cost.html')


@login_required
@ensure_csrf_cookie
def display_production_value_forecast_report(request):
    """Render the Production Value Forecast report UI."""
    return render(request, 'core/reports/production_value_forecast.html')


@login_required
@ensure_csrf_cookie
def display_cost_impact_report(request):
    """Render the Cost Impact Analysis report UI."""
    return render(request, 'core/reports/cost_impact_report.html')


@login_required
def display_blend_costing_report(request):
    """Render blend costing report comparing actual labor hours to standard costs."""
    report_data = get_blend_costing_report_data()

    context = {
        'rows': report_data['rows'],
    }

    return render(request, 'core/reports/blendcostingreport.html', context)

def display_blend_shortages(request):
    """
    Displays a page showing blend shortages and related information.
    
    Fetches blend shortages from ComponentShortage model, filtering for items that:
    - Start with 'BLEND', have procurement type 'M' 
    - Are the first instance of that blend
    - Are not on Horix production line
    
    For each blend shortage:
    - Checks if it's an advance blend (needs a lead time of 30 production hours)
    - Gets latest transaction dates
    - Gets scheduling info from desk schedules
    - Gets the bill of materials so we can list all ingredients in the tooltips
    - Checks for component shortages for all ingredients found in bill of materials
    - Finds max producible quantity if components are short (DOES NOT account for usage on other blends)
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with context containing:
        - blend_shortages_queryset: QuerySet of filtered ComponentShortage objects
        - foam_factor_is_populated: Boolean if FoamFactor table has data (to make sure decisions aren't being made on incorrect calculations)
        - add_lot_form: Form for adding lot numbers
        - latest_transactions_dict: Dict of latest transaction dates per item
        - rare_date: Date threshold for rare items (180 days ago)
        - epic_date: Date threshold for epic items (360 days ago)
    """
    blend_shortages_queryset = get_schedulable_blend_shortages()

    component_item_codes = list(blend_shortages_queryset.values_list('component_item_code', flat=True).distinct())
    latest_transactions_dict = get_latest_transaction_dates(component_item_codes)

    schedule_snapshot = build_schedule_snapshot()
    bom_objects = BillOfMaterials.objects.filter(item_code__in=component_item_codes)
    component_shortage_queryset = SubComponentShortage.objects \
        .filter(component_item_code__in=component_item_codes) \
        .exclude(component_item_code__startswith='TOTE')

    annotate_blend_shortage_records(
        blend_shortages_queryset,
        blend_item_codes=component_item_codes,
        latest_transactions_dict=latest_transactions_dict,
        bom_queryset=bom_objects,
        component_shortage_queryset=component_shortage_queryset,
        schedule_snapshot=schedule_snapshot,
        advance_blends=advance_blends,
    )

    foam_factor_is_populated = FoamFactor.objects.all().exists()

    timestamp_now = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    add_lot_form = LotNumRecordForm(
        prefix='addLotNumModal',
        initial={'lot_number': next_lot_number, 'date_created': timestamp_now},
    )

    thresholds = get_item_recency_thresholds()
    tintpaste_needs = get_tintpaste_needs()

    return render(request, 'core/productionplanning/blendshortages.html', {
        'need_black_tintpaste': tintpaste_needs['need_black_tintpaste'],
        'need_white_tintpaste': tintpaste_needs['need_white_tintpaste'],
        'blend_shortages_queryset': blend_shortages_queryset,
        'foam_factor_is_populated': foam_factor_is_populated,
        'add_lot_form': add_lot_form,
        'latest_transactions_dict': latest_transactions_dict,
        'rare_date': thresholds['rare_date'],
        'epic_date': thresholds['epic_date'],
    })

def display_orphaned_lots(request):
    orphaned_lots = get_orphaned_lots()
    edit_lot_form = LotNumRecordForm(prefix='editLotNumModal')

    return render(request, 'core/lotnumbers/orphanedlots.html', {
        'orphaned_lots': orphaned_lots,
        'edit_lot_form': edit_lot_form
    })

def display_lot_num_records(request):
    """
    Displays paginated lot number records with editing capabilities.
    
    Handles displaying lot number records in a paginated table view with options to:
    - Add new lot numbers via modal form
    - Edit existing lot numbers via modal form
    - Delete lot numbers
    - View schedule assignments
    
    Returns:
        Rendered template with context containing:
        - Paginated lot number records
        - Add/edit forms
        - Modal state flags
        - Schedule information

    Template:
        core/lotnumrecords.html
    """

    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    add_lot_form_initial = {'lot_number': next_lot_number, 'date_created': today}
    add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial=add_lot_form_initial)
    edit_lot_form = LotNumRecordForm(prefix='editLotNumModal')

    submitted = 'submitted' in request.GET
    load_add_modal_param = (request.GET.get('load-add-modal') or '').lower()
    load_add_modal = load_add_modal_param in ('true', '1', 'yes')

    lot_num_queryset = LotNumRecord.objects.order_by('-date_created')
    lot_num_paginator = Paginator(lot_num_queryset, 100)
    page_num = request.GET.get('page')
    current_page = lot_num_paginator.get_page(page_num)

    lot_numbers_on_page = [lot.lot_number for lot in current_page if lot.lot_number]
    schedule_assignments = get_schedule_assignments_for_lots(lot_numbers_on_page)

    for lot in current_page:
        schedule_data = schedule_assignments.get(lot.lot_number)
        if schedule_data:
            lot.schedule_value = schedule_data['schedule_value']
            lot.schedule_id = schedule_data['schedule_id']
        elif lot.line != 'Prod':
            lot.schedule_value = lot.line
            lot.schedule_id = None
        else:
            lot.schedule_value = 'Not Scheduled'
            lot.schedule_id = None

    context = {
        'add_lot_form': add_lot_form,
        'edit_lot_form': edit_lot_form,
        'submitted': submitted,
        'next_lot_number': next_lot_number,
        'current_page': current_page,
        'load_add_modal': load_add_modal,
    }

    return render(request, 'core/lotnumbers/lotnumrecords.html', context)

def display_foam_factors(request):
    """
    Displays foam factor records with forms for adding/editing.
    
    Handles displaying all foam factor records in a paginated view, along with forms
    for adding new records and editing existing ones. Includes logic for showing
    edit/add modals based on request parameters.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with foam factor records and forms context

    Template:
        core/foamfactor/foamfactors.html
    """
    submitted = False
    load_edit_modal = False

    if request.method == "GET":
        edit_yes_no = request.GET.get('edit-yes-no', 0)
        load_add_modal = request.GET.get('load-add-modal', 0)
        foam_factor_id = request.GET.get('foam-factor-id', 0)
        foam_factor_to_edit = ""
        add_foam_factor_form = FoamFactorForm(prefix='addFoamFactorModal')
        if edit_yes_no == 'yes' and FoamFactor.objects.filter(pk=foam_factor_id).exists():
            load_edit_modal = True
            foam_factor_to_edit = FoamFactor.objects.get(pk=foam_factor_id)
            edit_foam_factor_form = FoamFactorForm(instance=foam_factor_to_edit, prefix='editFoamFactorModal')
        else:
            edit_foam_factor_form = FoamFactorForm(instance=FoamFactor.objects.all().first(), prefix='editFoamFactorModal')
        if 'submitted' in request.GET:
            submitted=True

    foam_factor_queryset = FoamFactor.objects.order_by('item_code')

    context = {
        'foam_factor_queryset' : foam_factor_queryset,
        'add_foam_factor_form' : add_foam_factor_form,
        'edit_foam_factor_form' : edit_foam_factor_form,
        'edit_yes_no' : edit_yes_no,
        'submitted' : submitted,
        'load_edit_modal' : load_edit_modal,
        'load_add_modal' : load_add_modal,
        'foam_factor_to_edit' : foam_factor_to_edit,
        'foam_factor_id' : foam_factor_id
        }
    
    return render(request, 'core/foamfactor/foamfactors.html', context)

def display_all_item_locations(request):
    """
    Displays all item locations with their current quantities on hand.
    
    Retrieves ItemLocation records and joins with BillOfMaterials to get current
    quantities and units. Handles cases where multiple BOM records exist for an item
    by summing quantities.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with item locations and quantities
        
    Template:
        core/inventorycounts/allItemLocations.html
    """
    item_type_filter = request.GET.get('item-type', None)

    item_locations = ItemLocation.objects.all().order_by('item_code')
    if item_type_filter:
        item_locations = item_locations.filter(item_type__iexact=item_type_filter)
    
    item_codes = item_locations.values_list('item_code', flat=True)

    # Create an instance of the ItemLocationForm for editing item locations
    edit_item_location_form = ItemLocationForm(prefix='editItemLocationModal')

    # Query BillOfMaterials objects once and create a dictionary mapping component item codes to lists of (qtyonhand, standard_uom) tuples
    bom_data = {}
    for bom in BillOfMaterials.objects.filter(component_item_code__in=item_codes):
        if bom.component_item_code not in bom_data:
            bom_data[bom.component_item_code] = []
        bom_data[bom.component_item_code].append((bom.qtyonhand, bom.standard_uom))

    for item in item_locations:
        bom_info_list = bom_data.get(item.item_code, [])
        if bom_info_list:
            # Here you'll need to decide how to handle multiple BillOfMaterials objects for the same component_item_code
            # For example, you might want to sum the qtyonhand and take the first standard_uom
            item.qtyonhand = sum(info[0] for info in bom_info_list)
            item.standard_uom = bom_info_list[0][1]
        else:
            print(f"No BillOfMaterials object found for component_item_code: {item.item_code}")
            continue

    return render(request, 'core/inventorycounts/itemlocations.html', {'item_locations': item_locations, 
                                                        'edit_item_location_form' : edit_item_location_form})

def display_report_center(request):
    """
    Displays the report center page where users can generate available reports.
    The list of options is contained in the html of the page.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template for report center
        
    Template:
        core/reports/reportcenter.html
    """

    return render(request, 'core/reports/reportcenter.html', {})


@ensure_csrf_cookie
def display_blend_protection_audit(request):
    missing_blends = get_active_blends_missing_blend_protection()
    uv_freeze_unmatched = get_uv_freeze_sheet_unmatched()
    last_uv_refresh = uv_freeze_unmatched[0].get('sheet_refreshed_at') if uv_freeze_unmatched else None

    context = {
        'missing_blends': missing_blends,
        'missing_blends_count': len(missing_blends),
        'uv_freeze_unmatched': uv_freeze_unmatched,
        'uv_freeze_unmatched_count': len(uv_freeze_unmatched),
        'uv_last_refreshed': last_uv_refresh,
    }
    return render(request, 'core/reports/blend_protection_audit.html', context)


@login_required
@ensure_csrf_cookie
def trigger_uv_freeze_audit(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    target_url = "https://host.docker.internal:9999/run-uv-freeze-audit"
    try:
        response = requests.get(target_url, timeout=20, verify=False)
        response.raise_for_status()
        return JsonResponse({'status': 'queued', 'message': 'Requested host to run UV & Freeze audit.'})
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to trigger UV/Freeze audit: %s", exc)
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=502)

def display_report(request, which_report):
    """
    Displays a report based on the specified report type and item code.
    
    Args:
        request: HTTP request object containing encoded item code
        which_report (str): Type of report to generate ('Lot-Numbers' or 'All-Upcoming-Runs')
    """
    item_code = get_unencoded_item_code(request.GET.get('itemCode'))
    render_payload = create_report(request, which_report, item_code)

    return render(request, render_payload['template_string'], render_payload['context'])

def display_blend_schedule(request):
    """
    Displays the blend schedule view, managing scheduled blends across multiple production areas.
    
    Handles both GET and POST requests:
    - GET: Shows current blend schedules, filtered by area if specified
    - POST: Processes new lot number records added from a schedule page

    Cleans up completed blends, generates next lot numbers, and prepares blend schedule 
    data for each production area (Desk 1, Desk 2, Hx, Dm, Totes).

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with blend schedule data and forms
    """
    # Initialize variables
    today = dt.datetime.now()
    next_lot_number = generate_next_lot_number()
    blend_area = request.GET.get('blend-area')

    # Clean up completed blends from all schedule tables
    if not blend_area == 'all':
        clean_completed_blends(blend_area)

    # Prepare default forms
    add_lot_form_initial = {'lot_number': next_lot_number, 'date_created': today}
    add_lot_form = LotNumRecordForm(prefix='addLotNumModal', initial=add_lot_form_initial)
    edit_lot_form = LotNumRecordForm(prefix='editLotNumModal')
    submitted = 'submitted' in request.GET

    # Handle POST request (adding lot number record)
    if request.method == "POST":
        submission_result = process_lot_num_form_submission(request)
        if submission_result.get('success'):
            return HttpResponseRedirect('/core/lot-num-records')
        add_lot_form = submission_result.get('form', add_lot_form)
        submitted = False
    
    # Define areas and get their respective schedule querysets
    areas_list = ['Desk_1', 'Desk_2', 'Hx', 'Dm', 'Totes','LET_Desk']
    blend_schedule_querysets = get_blend_schedule_querysets()
    
    # Process querysets based on blend area filter
    if blend_area == 'all':
        for area in areas_list:
            blend_schedule_querysets[area] = prepare_blend_schedule_queryset(area, blend_schedule_querysets[area])
    elif blend_area:
        blend_schedule_querysets[blend_area] = prepare_blend_schedule_queryset(blend_area, blend_schedule_querysets[blend_area])
    
    # Prepare context for template
    context = {
        'desk_one_blends': blend_schedule_querysets['Desk_1'],
        'desk_two_blends': blend_schedule_querysets['Desk_2'],
        'horix_blends': blend_schedule_querysets['Hx'],
        'drum_blends': blend_schedule_querysets['Dm'],
        'tote_blends': blend_schedule_querysets['Totes'],
        'LET_desk_blends': blend_schedule_querysets['LET_Desk'],
        'blend_area': blend_area,
        'edit_lot_form': edit_lot_form,
        'add_lot_form': add_lot_form,
        'today': today,
        'submitted': submitted
    }
    
    return render(request, 'core/blendscheduling/main/blendschedule.html', context)

def display_this_issue_sheet(request, prod_line, item_code):
    """Display issue sheet details for a specific production run.
    
    Retrieves and formats data for an issue sheet, including component details,
    lot numbers, and quantities based on production line and item code.
    Handles different date formats and production line types.

    Args:
        request: HTTP request object containing optional runDate parameter
        prod_line (str): Production line identifier (Hx, Dm, Totes, etc)
        item_code (str): Code identifying the item to display
        
    Returns:
        Rendered template with issue sheet context including:
            - Component item details
            - Available lot numbers and quantities
            - Production line specific data
    """
    run_date_parameter = request.GET.get('runDate')
    if run_date_parameter == "undefined":
        run_date = date.today()
    else:
        try:
            # First, try parsing the date in the format mm-dd-yyyy
            run_date = dt.datetime.strptime(run_date_parameter, '%m-%d-%Y').date()
        except Exception as e:
            # If the first format fails, try parsing the date in the format mm-dd-yy
            run_date = dt.datetime.strptime(run_date_parameter, '%m-%d-%y').date()
    this_bill = BillOfMaterials.objects \
        .filter(item_code__iexact=item_code) \
        .filter(component_item_description__startswith='BLEND') \
        .first()
    component_item_code = this_bill.component_item_code
    component_item_description = this_bill.component_item_description

    # lot_numbers_dict = get_matching_lot_numbers(prod_line, component_item_code, run_date_parameter)
    # context = build_issue_sheet_dict(prod_line, component_item_code, component_item_description, run_date, lot_numbers_dict)

    if prod_line == 'Hx' or prod_line == 'Dm' or prod_line == 'Totes':
        run_this_date = LotNumRecord.objects \
            .filter(item_code__iexact=component_item_code) \
            .filter(line__iexact=prod_line) \
            .filter(run_date__date=run_date).exists()
        if run_this_date:
            these_lot_numbers = LotNumRecord.objects \
                .filter(item_code__iexact=component_item_code) \
                .filter(line__iexact=prod_line) \
                .filter(run_date__date=run_date).order_by('id')
        else:
            these_lot_numbers = {}
        lot_numbers = []
        for lot_num_record in these_lot_numbers:
            if lot_num_record.item_code == component_item_code:
                lot_numbers.append((lot_num_record.lot_number, lot_num_record.lot_quantity))

    else:
        these_lot_numbers = LotNumRecord.objects \
            .filter(item_code__iexact=component_item_code) \
            .filter(sage_qty_on_hand__gt=0).order_by('id')
        lot_numbers = []
        for lot_num_record in these_lot_numbers:
            if lot_num_record.item_code == component_item_code:
                lot_numbers.append((lot_num_record.lot_number, lot_num_record.sage_qty_on_hand))

    run_dict = {
            'component_item_code' : component_item_code,
            'component_item_description' : component_item_description,
            'prod_line' : prod_line,
            'issue_date' : run_date
        }    

    if not lot_numbers:
        lot_numbers_found = False
    else:
        lot_numbers_found = True

    run_dict['lot_numbers_found'] = lot_numbers_found
    run_dict['lot_numbers'] = lot_numbers

    return render(request, 'core/lotnumbers/singleissuesheet.html', { 'run_dict' : run_dict })

def display_issue_sheets(request, prod_line, issue_date):
    """Display issue sheets for a specific production line and date.

    Retrieves and formats component usage data for blends on the specified production line,
    along with their available lot numbers and quantities. For future dates, handles
    next business day logic.

    Args:
        request: The HTTP request object
        prod_line (str): The production line code (e.g. 'Hx', 'Dm', 'Totes')
        issue_date (str): The target date, or 'nextDay' for next business day

    Returns:
        HttpResponse: Rendered template with runs_this_line context containing component
        and lot number data for the specified criteria
    """
    all_lot_numbers_with_quantity = LotNumRecord.objects.filter(sage_qty_on_hand__gt=0).order_by('sage_entered_date')

    prod_runs_this_line = ComponentUsage.objects  \
        .filter(component_item_description__startswith='BLEND') \
        .filter(prod_line__iexact=prod_line) \
        .filter(start_time__lte=15) \
        .filter(procurement_type__iexact='M') \
        .order_by('start_time')
    
    runs_this_line = []

    if issue_date == "nextDay":
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        if tomorrow.weekday() == 4:  # If tomorrow is Friday
            next_possible_monday = tomorrow + dt.timedelta(days=2)
            issue_date = next_possible_monday.strftime("%m-%d-%y")
        else:
            next_possible_weekday = tomorrow
            issue_date = next_possible_weekday.strftime("%m-%d-%y")

    for run in prod_runs_this_line:
        if any(d.get('component_item_code', None) == run.component_item_code for d in runs_this_line):
            continue
        run_dict = {
            'component_item_code' : run.component_item_code,
            'component_item_description' : run.component_item_description,
            'prod_line' : prod_line,
            'issue_date' : issue_date
        }
        lot_numbers = []
        for lot_num_record in all_lot_numbers_with_quantity:
            if lot_num_record.item_code == run.component_item_code:
                lot_numbers.append( (lot_num_record.lot_number, lot_num_record.sage_qty_on_hand))
        
        run_dict['lot_numbers'] = lot_numbers
        runs_this_line.append(run_dict)
    
    return render(request, 'core/lotnumbers/issuesheets.html', {'runs_this_line' : runs_this_line})

def display_batch_issue_table(request, prod_line, issue_date):
    """Display batch issue table for production runs.
    
    Retrieves and formats data for batch issue sheets, including component details,
    lot numbers, and quantities. Handles different production lines and dates.
    
    Args:
        request: HTTP request object
        prod_line (str): Production line identifier (Hx, Dm, Totes, etc) or 'all'
        issue_date (str): Target date or 'nextDay' for next business day
        
    Returns:
        HttpResponse: Rendered template with batch issue data including:
            - Component codes and descriptions
            - On-hand quantities and shortage flags
            - Production line assignments
            - Issue dates and lot numbers
    """

    resolved_issue_date = resolve_issue_date(issue_date)
    lot_numbers_with_qty = get_positive_lot_numbers()
    prod_runs_this_line = get_batch_issue_runs(prod_line)
    runs_this_line, prod_runs_by_line = build_batch_issue_data(
        prod_runs_this_line,
        lot_numbers_with_qty,
        resolved_issue_date,
    )

    return render(request, 'core/lotnumbers/batchissuetable.html', {'runs_this_line' : runs_this_line,
                                                         'prod_line' : prod_line,
                                                         'issue_date' : resolved_issue_date,
                                                         'prod_runs_by_line' : prod_runs_by_line
                                                         })

def display_upcoming_blend_counts(request):
    """Display upcoming blend counts view.
    
    Retrieves and processes data about upcoming blend runs that need to be counted,
    including:
    - Upcoming blend usage within next 30 hours
    - Latest count records and transaction history for each blend
    - Shortage status and timing for blends
    
    Excludes Hx and Dm production lines. Orders results by start time.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template with context containing:
        - List of upcoming blend runs with count/transaction history
        - Shortage status and timing information
    """

    upcoming_runs = build_upcoming_blend_runs()

    return render(
        request,
        "core/inventorycounts/upcomingblends.html",
        {"upcoming_runs": upcoming_runs},
    )

def display_container_data(request):
    """Display container data view.

    Retrieves all container records from ContainerData model and renders them in the
    container data template. Used to track and display information about the different containers
    used to hold chemicals and blends in inventory.

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with container data queryset
    """
    containers = ContainerData.objects.all()

    return render(request, 'core/containerdata.html', { 'containers' : containers })

def display_excess_blends(request):

    excess_blends = get_excess_blends()

    return render(request, 'core/reports/excessblends.html', {
        'excess_blends': excess_blends['query_results'],
        'total_excess_inventory_value': excess_blends['total_excess_inventory_value']
    })

def display_blend_item_status(request):
    """Display report showing whether blend items are active or dead."""
    use_deeptime = request.GET.get('deeptime', '').lower() in ('true', '1', 'yes')
    data = get_blend_item_status_data(use_deeptime=use_deeptime)
    return render(request, 'core/reports/blenditemstatus.html', {
        'blend_items': data['rows'],
        'dead_count': data['dead_count'],
        'active_count': data['active_count'],
        'total_count': data['total_count'],
        'use_deeptime': use_deeptime,
    })


@login_required
def display_xmr_tank_control_limits(request):
    """
    Display XmR (Wheeler's) statistical process control limits for tank leak detection.

    Shows a table of current control limits for each tank plus XmR charts
    visualizing recent tank level changes against control limits.
    """
    # Handle recalculation request
    if request.method == 'POST' and request.POST.get('action') == 'recalculate':
        result = recalculate_and_store_control_limits(lookback_days=60)
        messages.success(
            request,
            f"Recalculated control limits: {result['updated']} tanks updated, {result['skipped']} skipped."
        )
        return redirect('xmr-tank-control-limits')

    # Get current limits and chart data
    limits = get_current_control_limits()
    all_tank_data = get_all_tanks_xmr_data()

    # Prepare chart data as JSON for JavaScript (just the tanks dict)
    chart_data_json = json.dumps(all_tank_data['tanks'], cls=DjangoJSONEncoder)

    return render(request, 'core/reports/xmr_tank_control_limits.html', {
        'limits': limits,
        'chart_data_json': chart_data_json,
        'period_label': all_tank_data['period_label'],
        'tank_count': len(limits),
    })


def display_upcoming_component_counts(request):
    """Render the upcoming component count queue built by the service layer."""
    upcoming_components = build_upcoming_component_counts()
    return render(
        request,
        "core/inventorycounts/upcomingcomponents.html",
        {"upcoming_components": upcoming_components},
    )

def display_adjustment_statistics(request, filter_option):
    """Display adjustment statistics for items filtered by prefix.
    
    Retrieves and displays adjustment statistics for items whose descriptions start with
    the specified filter option (e.g. 'CHEM', 'DYE', etc). Encodes item codes for URL
    safety.

    Args:
        request: HTTP request object
        filter_option (str): Prefix to filter item descriptions by
        
    Returns:
        Rendered template with filtered adjustment statistics
        
    Template:
        core/reports/adjustmentstatistics.html
    """
    
    adjustment_statistics = AdjustmentStatistic.objects \
        .filter(item_description__startswith=filter_option) \
        .order_by('-adj_percentage_of_run')

    for item in adjustment_statistics:
        item_code_str_bytes = item.item_code.encode('UTF-8')
        encoded_item_code_str_bytes = base64.b64encode(item_code_str_bytes)
        encoded_item_code = encoded_item_code_str_bytes.decode('UTF-8')
        item.encoded_item_code = encoded_item_code

    return render(request, 'core/reports/adjustmentstatistics.html', {'adjustment_statistics' : adjustment_statistics})

def display_items_by_audit_group(request):
    """Display items with option to filter and organize by audit group assignments."""

    valid_record_types = {'blend', 'blendcomponent', 'warehouse', 'all'}
    record_type = (request.GET.get('recordType') or 'blendcomponent').lower()
    if record_type not in valid_record_types:
        record_type = 'blendcomponent'

    search_query = request.GET.get('filter_criteria') or request.GET.get('search') or ''
    search_query = search_query.strip()
    selected_audit_group = request.GET.get('auditGroupLinks') or request.GET.get('auditGroup') or ''

    service_record_type = None if record_type == 'all' else record_type
    audit_items, audit_group_list = build_audit_group_display_items(
        service_record_type,
        search_query=search_query,
        audit_group_filter=selected_audit_group,
    )
    return render(request, 'core/inventorycounts/itemsbyauditgroup.html', {
        'audit_group_queryset': audit_items,
        'audit_group_list': audit_group_list,
        'record_type': record_type,
        'search_query': search_query,
        'selected_audit_group': selected_audit_group,
    })


def display_uncounted_items(request):
    """Display uncounted items report with filters."""
    days_param = request.GET.get('days', 3)
    try:
        days_value = int(days_param)
    except (TypeError, ValueError):
        days_value = 3
    if days_value < 0:
        days_value = 3

    raw_item_type = (request.GET.get('itemType') or request.GET.get('item_type') or 'all').strip().lower()
    allowed_types = {'all', 'blend', 'component', 'warehouse'}
    if raw_item_type not in allowed_types:
        raw_item_type = 'all'

    search_query = (request.GET.get('search') or '').strip()

    uncounted_items = build_uncounted_items_display(
        days=days_value,
        item_type=None if raw_item_type == 'all' else raw_item_type,
        search_query=search_query,
    )

    return render(request, 'core/inventorycounts/uncounted_items.html', {
        'uncounted_items': uncounted_items,
        'days': days_value,
        'item_type': raw_item_type,
        'search_query': search_query,
        'audit_group_choices': get_distinct_audit_groups(),
    })

def display_list_to_count_list(request):
    """Display list of items to be counted for inventory.
    
    Shows a paginated list of items that need to be counted, organized by audit group.
    Allows filtering and selection of items to add to count lists.

    Args:
        request: HTTP request object
        
    Returns:
        Rendered template showing items to count
        
    Template:
        core/inventorycounts/listtocountlist.html
    """
    return render(request, 'core/inventorycounts/listtocountlist.html', {})

@login_required
def display_count_list(request):
    """Displays a list of count records for a given collection.
    
    Args:
        request: HTTP request object containing:
            recordType (str): Type of count record ('component', 'blend', or 'warehouse')
            listId (str): Primary key of the CountCollectionLink to display
            
    Returns:
        HttpResponse: Rendered template with context containing:
            location_options (list): Available location options based on record type
            todays_date (date): Current date
            label_contents (dict): Contains date for labels
            these_count_records (QuerySet): Count records for this collection
            count_list_id (str): ID of the count list being displayed
            record_type (str): Type of count records being displayed
            count_list_name (str): Name of this count collection
            
    Retrieves count records for the given collection ID and record type.
    Looks up standard UOM and location for each count record.
    Provides location options based on record type.
    Renders template with count records and supporting data.
    """
    record_type = request.GET.get('recordType')
    count_list_id = request.GET.get('listId')

    count_list_data = build_count_list_display_data(
        record_type=record_type,
        count_list_id=count_list_id,
    )

    todays_date = dt.date.today()

    if record_type == 'blendcomponent':
        location_options = [
            'BlendingRack', 'DI Tank', 'DyeShelves', 'ExtraRack', 'Joeys Warehouse',
            'LabRack', 'MainMaterials', 'MaterialsRack', 'NoLocation', 'OldDC', 'Overflow',
            'ScaleAndOverflow', 'Shed2', 'Shed3', 'TankFarm', 'UnderMixTank', 'Warehouse'
        ]
    elif record_type == 'blend':
        location_options = [
            'NoLocation', 'OldDC', 'OutsideLot', 'Shed1', 'Shed3'
        ]
    else:
        location_options = []

    label_contents = {'date': todays_date}

    context = {
        'location_options': location_options,
        'todays_date': todays_date,
        'label_contents': label_contents,
        'these_count_records': count_list_data['count_records'],
        'count_list_id': count_list_data['count_list_id'],
        'record_type': count_list_data['record_type'],
        'count_list_name': count_list_data['count_list_name'],
    }

    return render(request, 'core/inventorycounts/countlist.html', context)

def display_count_collection_links(request):
    """Display collection of count links for inventory tracking.
    
    Shows all count collection links ordered by their display position. Used to render
    the count collection links page which shows available count lists.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with:
            count_collection_links: QuerySet of CountCollectionLink objects
            count_collection_exists: Boolean indicating if any links exist
            
    Template:
        core/inventorycounts/countcollectionlinks.html
    """
    count_collection_links = CountCollectionLink.objects.all().order_by('link_order')
    if not count_collection_links.exists():
        count_collection_exists = False
    else:
        count_collection_exists = True

    return render(request, 'core/inventorycounts/countcollectionlinks.html', {'count_collection_links' : count_collection_links,
                                                                              'count_collection_exists' : count_collection_exists})

def display_count_records(request):
    """Display count records for inventory tracking.
    
    Shows paginated list of count records filtered by record type. The number of 
    records per page can be customized via URL parameter.

    Args:
        request: HTTP request containing:
            recordType (str): Type of count record to display ('blend', 'blendcomponent', 'warehouse')
            records (str, optional): Number of records to show per page, defaults to 50
            page (str, optional): Page number to display

    Returns:
        Rendered template with:
            current_page: Page object containing count records
            countType: Type of count record being displayed
            
    Template:
        core/inventorycounts/countrecords.html
    """
    record_type = request.GET.get('recordType')
    number_of_records = request.GET.get('records')

    model = get_count_record_model(record_type)
    count_record_queryset = model.objects.order_by('-id')
 
    count_record_paginator = Paginator(count_record_queryset, 750)
    page_num = request.GET.get('page')
    if number_of_records:
        count_record_paginator = Paginator(count_record_queryset, number_of_records)
    else:
        count_record_paginator = Paginator(count_record_queryset, 750)

    current_page = count_record_paginator.get_page(page_num)

    return render(request, 'core/inventorycounts/countrecords.html', {'current_page' : current_page, 'countType' : record_type})

def display_count_report(request):
    """Display inventory count report.
    
    Renders a template showing count records with variance analysis and receipt details.
    Used for reviewing inventory counts and analyzing discrepancies.

    Args:
        request: HTTP request containing:
            encodedList (str): Base64 encoded list of count record IDs
            recordType (str): Type of count records ('blend', 'blendcomponent', 'warehouse')

    Returns:
        Rendered template with:
            count_records: Queryset of count records with variance analysis
            average_costs: Dict mapping item codes to costs
            count_credits: Dict mapping record IDs to users who submitted counts
            
    Template:
        core/inventorycounts/countreport.html
    """
    encoded_pk_list = request.GET.get("encodedList")
    record_type = request.GET.get("recordType")
    count_ids_bytestr = base64.b64decode(encoded_pk_list)
    count_ids_str = count_ids_bytestr.decode()
    count_ids_list = list(count_ids_str.replace('[', '').replace(']', '').replace('"', '').split(","))
    average_costs = { item.itemcode : item.lasttotalunitcost for item in CiItem.objects.all()}
    count_credits = { item.record_id : item.updated_by for item in CountRecordSubmissionLog.objects.all().order_by('-update_timestamp')}
    most_recent_august_first = dt.datetime.now().replace(month=8, day=1)
    if most_recent_august_first > dt.datetime.now():
        most_recent_august_first = most_recent_august_first.replace(year=most_recent_august_first.year - 1)
    most_recent_september_fifth = most_recent_august_first.replace(month=9, day=5)
    from_date = most_recent_august_first.strftime('%Y-%m-%d')
    to_date = most_recent_september_fifth.strftime('%Y-%m-%d')

    if record_type == "blend":
        count_records_queryset = BlendCountRecord.objects.filter(pk__in=count_ids_list)
    #     for count_record in count_records_queryset:
    #         analysis = get_variance_analysis(count_record, from_date, to_date)
    #         count_record.variance_as_percentage_of_BI = analysis['variance_as_percentage_of_BI']
    #         count_record.variance_last_year = analysis['variance_last_year']
    #         count_record.total_bi_qty_since_last_ii_ia = analysis['total_bi_qty_since_last_ii_ia']
            
    elif record_type == 'blendcomponent':
        count_records_queryset = BlendComponentCountRecord.objects.filter(pk__in=count_ids_list)
    #     for count_record in count_records_queryset:
    #         analysis = get_variance_analysis(count_record, from_date, to_date)
    #         count_record.variance_as_percentage_of_BI = analysis['variance_as_percentage_of_BI']
    #         count_record.variance_last_year = analysis['variance_last_year']
    elif record_type == 'warehouse':
        count_records_queryset = WarehouseCountRecord.objects.filter(pk__in=count_ids_list)
    #     for count_record in count_records_queryset:
    #         analysis = get_variance_analysis(count_record, from_date, to_date)
    #         count_record.variance_as_percentage_of_BI = analysis['variance_as_percentage_of_BI']
    #         count_record.variance_last_year = analysis['variance_last_year']

    item_codes = [item.item_code for item in count_records_queryset]
    oldest_receiptnos = {item.receiptno: (item.itemcode, item.receiptdate) for item in ImItemCost.objects.filter(itemcode__in=item_codes).filter(quantityonhand__gt=0).order_by('receiptdate')}

    # Ensure only the oldest tuple is kept for each part number in oldest_receiptnos
    filtered_oldest_receiptnos = {}
    for receiptno, (itemcode, receiptdate) in oldest_receiptnos.items():
        if itemcode not in filtered_oldest_receiptnos or receiptdate < filtered_oldest_receiptnos[itemcode][1]:
            filtered_oldest_receiptnos[itemcode] = (receiptno, receiptdate)
            # print(f'KEEPING {itemcode, (receiptno, receiptdate) }')
    oldest_receiptnos = filtered_oldest_receiptnos

    for item in count_records_queryset:
        item.receiptno = oldest_receiptnos.get(item.item_code,['Not found','Not found'])[0]
        item.receiptdate = oldest_receiptnos.get(item.item_code,['Not found','Not found'])[1]
        if item.variance:
            if abs(item.variance) > 200:
                item.suspicious = True

    total_variance_cost = 0
    for item in count_records_queryset:
        item.average_cost = average_costs[item.item_code]
        print(item.item_code)
        print(f"multiplying item variance {Decimal(0 if item.variance == None else item.variance)} * average cost {average_costs[item.item_code]}")
        item.variance_cost = average_costs[item.item_code] * Decimal(0 if item.variance == None else item.variance)
        total_variance_cost+=item.variance_cost 
        item.counted_by = count_credits.get(str(item.id), "")

    return render(request, 'core/inventorycounts/countrecordreport.html', {'count_records_queryset' : count_records_queryset, 
                                                                           'total_variance_cost' : total_variance_cost,
                                                                           'record_type' : record_type})

def display_all_upcoming_production(request):
    """Display all upcoming production runs with optional filtering.
    
    Retrieves and displays TimetableRunData records ordered by start time. Supports 
    filtering by production line or component item code. Results are paginated with
    25 items per page.

    Args:
        request: HTTP request containing optional query parameters:
            prod-line-filter (str): Filter results by production line
            component-item-code-filter (str): Filter results by component item code
            page (int): Page number for pagination

    Returns:
        Rendered template 'core/productionplanning/productionblendruns.html' with context:
            current_page: Paginated queryset of production runs
            prod_line_filter: Active production line filter value
            component_item_code_filter: Active component filter value 
            queryset_empty: Boolean indicating if results exist
    """
    prod_line_filter = request.GET.get('prod-line-filter', 0)
    component_item_code_filter = request.GET.get('component-item-code-filter ', 0)
    if prod_line_filter:
        upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime').filter(prodline__iexact=prod_line_filter)
    elif component_item_code_filter:
        upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime').filter(component_item_code__iexact=component_item_code_filter)
    else:
        upcoming_runs_queryset = TimetableRunData.objects.order_by('starttime')
    if not upcoming_runs_queryset:
        queryset_empty = True
    else:
        queryset_empty = False
    # for run in upcoming_runs_queryset:
    #     item.component_item_code
    upcoming_runs_paginator = Paginator(upcoming_runs_queryset, 25)
    page_num = request.GET.get('page')
    current_page = upcoming_runs_paginator.get_page(page_num)
    return render(request, 'core/productionplanning/productionblendruns.html',
                        {
                        'current_page' : current_page,
                        'prod_line_filter' : prod_line_filter,
                        'component_item_code_filter' : component_item_code_filter,
                        'queryset_empty' : queryset_empty
                        })

def display_chem_shortages(request):
    """Display chemical shortages for upcoming blend production.
    
    Analyzes chemical inventory levels against upcoming blend production requirements
    to identify potential shortages. Calculates required quantities based on bill of
    materials and displays:

    - Current on-hand quantities
    - Required quantities for upcoming blends
    - Projected shortages
    - Next expected deliveries
    - Maximum possible blend quantities

    Args:
        request: HTTP request object

    Returns:
        Rendered template 'core/productionplanning/chemshortages.html' with context:
            chems_used_upcoming: Queryset of chemicals needed for upcoming blends
            is_shortage: Boolean indicating if any shortages exist
            blends_upcoming_item_codes: List of blend item codes being produced
            current_page: Paginated results
    """
    is_shortage = False
    blends_used_upcoming = ComponentShortage.objects.filter(component_item_description__startswith='BLEND-')
    blends_upcoming_item_codes = list(blends_used_upcoming.values_list('component_item_code', flat=True))
    chems_used_upcoming = BillOfMaterials.objects.filter(item_code__in=blends_upcoming_item_codes).exclude(component_item_code__startswith='/C')
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)
    for chem in chems_used_upcoming:
        chem.blend_req_onewk = blends_used_upcoming.filter(component_item_code__iexact=chem.item_code).first().one_wk_short
        chem.blend_req_twowk = blends_used_upcoming.filter(component_item_code__iexact=chem.item_code).first().two_wk_short
        chem.blend_req_threewk = blends_used_upcoming.filter(component_item_code__iexact=chem.item_code).first().three_wk_short
        chem.required_qty = chem.blend_req_threewk * chem.qtyperbill
        if chem.qtyonhand >= 0 and chem.required_qty >= 0:
            chem.oh_minus_required = chem.qtyonhand - chem.required_qty
        else:
            chem.oh_minus_required = 0
        if chem.qtyonhand >= 0 and chem.required_qty >= 0:
            try: 
                chem.max_possible_blend = chem.qtyonhand / chem.qtyperbill
            except:
                chem.max_possible_blend = 0
        else:
            chem.max_possible_blend = 0
        if (PoPurchaseOrderDetail.objects.filter(itemcode__iexact=chem.component_item_code, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            chem.next_delivery = PoPurchaseOrderDetail.objects.filter(
                itemcode__iexact=chem.component_item_code,
                quantityreceived__exact=0,
                requireddate__gt=yesterday_date
                ).order_by('requireddate').first().requireddate
        else:
            chem.next_delivery = "N/A"
        if (chem.oh_minus_required < 0 and chem.component_item_code != "030143"):
            is_shortage = True
        # printing
        if chem.component_item_code == '030024':
            print('Chem ' + chem.component_item_code + ': ' + str(chem.qtyonhand) + ' on hand.')
            print(str(chem.required_qty) + ' of chem required.')
            print(str(chem.blend_req_threewk) + ' gal of blend required.')
        # if chem.item_code == '18500.B':
        #     print('Chem ' + chem.component_item_code + ': ' + str(chem.qtyonhand) + ' on hand.')
        #     print(str(chem.required_qty) + ' of chem required.')
        #     print(str(chem.blend_req_threewk) + ' gal of blend required.')
        
        
    chems_used_paginator = Paginator(chems_used_upcoming, 50)
    page_num = request.GET.get('page')
    current_page = chems_used_paginator.get_page(page_num)

    return render(request, 'core/productionplanning/chemshortages.html',
        {'chems_used_upcoming' : chems_used_upcoming,
         'is_shortage' : is_shortage,
         'blends_upcoming_item_codes' : blends_upcoming_item_codes,
         'blends_used_upcoming' : blends_used_upcoming,
         'current_page' : current_page
         })

def display_lookup_location(request):
    """Display location lookup page.
    
    Shows a form for looking up item locations, with a dropdown of all available item codes.
    Used to find storage locations and details for inventory items.

    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with item code queryset for dropdown
        
    Template:
        core/lookuppages/lookuplocation.html
    """
    item_code_queryset = list(BillOfMaterials.objects.order_by('component_item_code').distinct('component_item_code'))

    return render(request, 'core/lookuppages/lookuplocation.html', {'item_code_queryset' : item_code_queryset})

def display_tank_levels(request):
    """Display storage tank level monitoring page.
    
    Renders the tank level monitoring page template with tank data. Uses different
    templates for MSR vs standard views based on request path.

    Args:
        request: HTTP request object

    Returns:
        Rendered template response with tank queryset data:
            tank_queryset: QuerySet of StorageTank objects
    """
    tank_queryset = StorageTank.objects.all()

    if 'msr' in request.path:
        return render(request, 'core/tanklevels/tanklevelsmsr.html', {'tank_queryset' : tank_queryset})
    else:
        return render(request, 'core/tanklevels/tanklevels.html', {'tank_queryset' : tank_queryset})


@login_required
@ensure_csrf_cookie
def display_manual_gauge_entries(request):
    """Render manual gauge entry page for storage tanks."""

    storage_tanks = list(StorageTank.objects.order_by('tank_label_kpk'))

    tank_rows = []
    for tank in storage_tanks:
        label = tank.tank_label_kpk or ''
        display_label = label[5:] if label[:5].upper() == 'TANK ' else label
        tank_rows.append(
            {
                'tank_id': tank.id,
                'tank_label_kpk': label,
                'tank_label_display': display_label,
                'max_inches': tank.max_inches,
                'gallons_per_inch': tank.gallons_per_inch,
                'max_gallons': tank.max_gallons,
                'dead_space': None,
                'full_space': None,
                'gallons': None,
            }
        )

    context = {
        'tank_rows': tank_rows,
    }

    return render(request, 'core/storage/manual_gauges.html', context)


@login_required
def display_manual_gauge_overview(request):
    """Render a read-only summary of manual gauge measurements."""

    gauges = list(ManualGauge.objects.order_by('-created_at'))
    storage_tanks = {
        tank.tank_label_kpk: tank
        for tank in StorageTank.objects.filter(
            tank_label_kpk__in=[gauge.tank_label_kpk for gauge in gauges]
        )
    }

    rows = []
    for gauge in gauges:
        tank = storage_tanks.get(gauge.tank_label_kpk)

        max_inches = getattr(tank, 'max_inches', None)
        gallons_per_inch = getattr(tank, 'gallons_per_inch', None)
        max_gallons = getattr(tank, 'max_gallons', None)

        gallons = None
        if gauge.full_space is not None and gallons_per_inch is not None:
            gallons = gauge.full_space * gallons_per_inch

        rows.append(
            {
                'tank_label_kpk': gauge.tank_label_kpk,
                'dead_space': gauge.dead_space,
                'full_space': gauge.full_space,
                'gallons': gallons,
                'max_inches': max_inches,
                'max_gallons': max_gallons,
                'gallons_per_inch': gallons_per_inch,
                'recorded_by': gauge.recorded_by,
                'created_at': gauge.created_at,
            }
        )

    context = {
        'records': rows,
    }

    return render(request, 'core/storage/manual_gauge_overview.html', context)

def display_lookup_item_quantity(request):
    """Display item quantity lookup page.
    
    Renders the item quantity lookup page template which allows users to search
    for and view current inventory quantities for items.

    Args:
        request: HTTP request object

    Returns:
        Rendered template response:
            Template: core/lookuppages/lookupitemquantity.html
    """
    return render(request, 'core/lookuppages/lookupitemquantity.html')

def display_tank_usage_monitor(request, tank_identifier):
    """Render the tank usage monitor page."""
    # Ensure the tank identifier is passed correctly
    logger.info(f"[TankMonitor] Rendering page for tank: {tank_identifier}")
    return render(request, 'core/tanklevels/tankusagemonitor.html', {'tank_identifier': tank_identifier})

def display_lookup_lot_numbers(request):
    """Display lot number lookup page.
    
    Renders the lot number lookup page template which allows users to search
    for and view lot numbers associated with items. Retrieves a queryset of
    distinct component item codes from the BillOfMaterials model to populate
    the lookup form.

    Args:
        request: HTTP request object

    Returns:
        Rendered template response with:
            item_code_queryset: QuerySet of distinct component item codes
            Template: core/lookuppages/lookuplotnums.html
    """
    item_code_queryset = list(BillOfMaterials.objects
                            .order_by('component_item_code')
                            .distinct('component_item_code')
                            )

    return render(request, 'core/lookuppages/lookuplotnums.html', {'item_code_queryset' : item_code_queryset})

def display_checklist_mgmt_page(request):
    """Display checklist management page.
    
    Shows checklist submission tracking information and provides controls for:
    - Checking if daily updates have been performed
    - Manually triggering submission tracker updates
    - Sending email reports
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with checklist management context
        
    Template:
        core/forkliftchecklist/checklistmgmt.html
    """
    today = dt.datetime.today()
    if ChecklistSubmissionRecord.objects.filter(date_checked__gte=today).exists():
        daily_update_performed = True
    else:
        daily_update_performed = False
    return render(request, 'core/forkliftchecklist/checklistmgmt.html', {'daily_update_performed' : daily_update_performed})

def display_blend_statistics(request):
    """Display blend statistics and production data.
    
    Renders a template showing weekly blend totals by year, upcoming blend demand,
    and daily production quantities for current and previous weeks.
        
    Returns:
        Rendered template with blend statistics context data
        
    """

    create_weekly_blend_totals_table()
    context = create_weekly_blend_totals_table_context()

    return render(request, 'core/reports/blendstatistics.html', context)

def display_maximum_producible_quantity(request):
    """Display the maximum producible quantity page.
    
    Renders the template for viewing maximum producible quantities of blends
    based on component availability.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template for max producible quantity page
        
    Template:
        core/reports/maxproduciblequantity.html
    """
    return render(request, 'core/reports/maxproduciblequantity.html', {})

def display_truck_rail_material_schedule(request):
    """Display truck and rail material schedule page.

    Shows upcoming truck and rail material deliveries, including:
    - Required delivery dates
    - Tank assignments and capacity warnings
    - Vendor information

    Filters for orders within the last 3 days and only shows undelivered quantities.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with truck/rail schedule context

    Template:
        core/reports/truckrailmaterialschedule.html
    """
    three_days_ago = dt.datetime.today() - dt.timedelta(days = 3)
    truck_rail_item_codes = list(
        StorageTank.objects
        .filter(item_description__istartswith='CHEM')
        .values_list('item_code', flat=True)
        .distinct()
    )
    truck_and_rail_orders = PoPurchaseOrderDetail.objects.filter(itemcode__in=truck_rail_item_codes) \
        .filter(requireddate__gte=three_days_ago) \
        .filter(quantityreceived=0) \
        .order_by('requireddate')

    tank_levels = TankLevel.objects.all()
    for tank in tank_levels:
        tank_label_kinpak = f'TANK {tank.tank_name}'
        tank.item_code = StorageTank.objects.filter(tank_label_kpk__iexact=tank_label_kinpak).first().item_code
        tank.max_gallons = StorageTank.objects.filter(tank_label_kpk__iexact=tank_label_kinpak).first().max_gallons

    for item in truck_and_rail_orders:
        po_in_question = PoPurchaseOrderHeader.objects.get(purchaseorderno=item.purchaseorderno)
        item.confirmto = po_in_question.confirmto
        item.vendorno = po_in_question.vendorno
        item.tank = "Confirm with Ginny"
        if item.commenttext and " time" in item.commenttext:
            item.commenttext = item.commenttext.replace(" time", "")

    return render(request, 'core/reports/truckrailmaterialschedule.html', {'truck_and_rail_orders' : truck_and_rail_orders}) 


@login_required
@ensure_csrf_cookie
def display_component_stock_after_orders(request):
    """Render the coverage page answering the 100433 / 100507TANKO stock question."""
    payload = build_component_stock_coverage_payload()
    context = {
        'coverage_json': json.dumps(payload, cls=DjangoJSONEncoder),
    }
    return render(request, 'core/reports/component_stock_after_orders.html', context)


@login_required
def get_component_stock_after_orders_data(request):
    """Return a fresh snapshot of component coverage data as JSON."""
    payload = build_component_stock_coverage_payload()
    return JsonResponse(payload, safe=False, json_dumps_params={'cls': DjangoJSONEncoder})

def display_component_shortages(request):
    """Display component shortages and procurement needs.
    
    Shows a list of component shortages filtered by procurement type 'B' (buy),
    ordered by start time and filtered to show only single instances. Optionally
    filters by PO number if provided in request.
    
    Args:
        request: HTTP request object containing:
            po-filter (str, optional): PO number to filter results by
            
    Returns:
        Rendered template with component shortages context
        
    Template:
        core/componentshortages.html
    """
    component_shortages = ComponentShortage.objects \
        .filter(procurement_type__iexact='B') \
        .order_by('start_time').filter(component_instance_count=1)
    if not request.GET.get('po-filter') == None:
        component_shortages = component_shortages.filter(po_number__iexact=request.GET.get('po-filter'))

    return render(request, 'core/reports/componentshortages.html', {'component_shortages' : component_shortages})

def display_subcomponent_shortages(request):
    """Display subcomponent shortages and procurement needs.
    
    Shows a list of subcomponent shortages ordered by start time and filtered to show
    only single instances. Optionally filters by PO number if provided in request.
    
    Args:
        request: HTTP request object containing:
            po-filter (str, optional): PO number to filter results by
            
    Returns:
        Rendered template with subcomponent shortages context
        
    Template:
        core/productionplanning/subcomponentshortages.html
    """
    subcomponent_shortages = SubComponentShortage.objects.all().order_by('start_time').filter(subcomponent_instance_count=1)
    if not request.GET.get('po-filter') == None:
        subcomponent_shortages = subcomponent_shortages.filter(po_number__iexact=request.GET.get('po-filter'))

    return render(request, 'core/productionplanning/subcomponentshortages.html', {'subcomponent_shortages' : subcomponent_shortages})

def display_forklift_issues(request):
    """Display forklift inspection issues from the past 2 days.
    
    Retrieves forklift inspection checklist records where items were marked as 'Bad'
    within the past 48 hours. Compiles a list of issues including the forklift ID,
    operator name, problem area, and comments.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with forklift issues context data
        
    Template:
        core/forkliftchecklist/forkliftissues.html
    """
    two_days_ago = dt.datetime.today() - dt.timedelta(days = 2)
    bad_conditions = Q()
    for field in ChecklistLog._meta.get_fields():
        # only include fields which are of type CharField
        if isinstance(field, models.CharField):
            kwargs = {f'{field.name}__iexact': 'Bad'}
            bad_conditions |= Q(**kwargs)
    issues_queryset = ChecklistLog.objects.filter(bad_conditions).filter(submitted_date__gte=two_days_ago)

    forklift_issues = []
    model_fields = ChecklistLog._meta.get_fields()
    # Filter out only TextField instances and ignore the first TextField
    char_fields = [field for field in model_fields if isinstance(field, CharField)][1:]

    for issue in issues_queryset:
        for field in char_fields:
            field_name = field.name
            comment_field_name = field_name + "_comments"
            if getattr(issue, field_name) == 'Bad':
                forklift_issues.append([
                    issue.forklift,
                    issue.operator_name,
                    field.verbose_name,  # Assuming the verbose_name is set to the descriptive name
                    getattr(issue, comment_field_name)
                ])

    return render(request, 'core/forkliftchecklist/forkliftissues.html', { 'forklift_issues' : forklift_issues })

def display_loop_status(request):
    """Display loop status information for the data loop on the server.
    
    Retrieves all loop status records and renders them in a template.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with loop status context data
        
    Template:
        core/loopstatus/loopstatus.html
    """
    loop_statuses = LoopStatus.objects.all()

    return render(request, 'core/loopstatus/loopstatus.html', {'loop_statuses' : loop_statuses})


@login_required
def display_function_toggles(request):
    """Display management page for data looper function toggles."""
    toggles = get_all_function_toggles()
    context = {'toggles': toggles}
    return render(request, 'core/loopstatus/function_toggles.html', context)

def feedback(request):
    """Handle user feedback submission.

    Displays feedback form and processes submissions. Sends feedback emails to 
    configured recipients when valid feedback is submitted.
    
    Args:
        request: HTTP request object containing:
            POST data with feedback_type and message if submitted
            
    Returns:
        GET: Rendered feedback form template
        POST: Redirect to feedback page on success
        
    Template:
        core/feedback/feedback.html
    """
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback_type = form.cleaned_data['feedback_type']
            message = form.cleaned_data['message']

            # Get the username of the logged in user, or 'anon' if no user is logged in
            username = request.user.username if request.user.is_authenticated else 'anon'

            # Include the username in the email subject
            email_subject = f'Feedback: {feedback_type} from {username}'

            sender_address = os.getenv('NOTIF_EMAIL_ADDRESS')
            sender_pass =  os.getenv('NOTIF_PW')
            recipient_addresses = 'pmedlin@kinpakinc.com,jdavis@kinpakinc.com'
            recipient_list = recipient_addresses.split(',')

            for recipient in recipient_list:
                email_message = MIMEMultipart('alternative')
                email_message['From'] = sender_address
                email_message['To'] = recipient
                email_message['Subject'] = email_subject
                email_message.attach(MIMEText(message, 'plain'))

                session = smtplib.SMTP('smtp.gmail.com', 587)
                session.starttls()
                session.login(sender_address, sender_pass)
                session.sendmail(sender_address, recipient, email_message.as_string())
                session.quit()

            messages.success(request, 'Thank you for your feedback!')
            return redirect('feedback')
    else:
        form = FeedbackForm()
    return render(request, 'core/feedback/feedback.html', {'form': form})

def display_ghs_label_search(request):
    """Display GHS label search and upload page.
    
    Shows form for searching existing GHS pictograms and uploading new ones.
    The form allows uploading new pictogram images and associating them with 
    item codes.
    
    Args:
        request: HTTP request object
        
    Returns:
        GET: Rendered template with empty form
        POST: Redirect to search page after successful upload
        
    Template:
        core/GHSlabelGen/labels/ghslookuppage.html
    """
    if request.method == 'POST':
        form = GHSPictogramForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('display-ghs-label-search')
    else:
        form = GHSPictogramForm()

    return render(request, 'core/GHSlabelGen/labels/ghslookuppage.html', {'form': form})

def display_ghs_label(request, encoded_item_code):
    """Display GHS label for an item.
    
    Renders a template showing the GHS pictogram and label information for a given item code.
    Decodes the base64 encoded item code and retrieves the associated GHS pictogram record.
    If no pictogram exists, creates a basic item info dict.
    
    Args:
        request: HTTP request object
        encoded_item_code (str): Base64 encoded item code to look up
        
    Returns:
        Rendered template with GHS label context including:
            this_ghs_pictogram: GHS pictogram record or basic item info dict
            image_url: Full URL to pictogram image
            
    Template:
        core/GHSlabelGen/labels/ghsprinttemplate.html
    """
    item_code_bytestr = base64.b64decode(encoded_item_code)
    item_code = item_code_bytestr.decode()
    if GHSPictogram.objects.filter(item_code=item_code).exists():
        this_ghs_pictogram = GHSPictogram.objects.filter(item_code=item_code).first()
        image_reference_url = this_ghs_pictogram.image_reference.url
    else:
        this_ghs_pictogram = {
            "item_code":item_code,
            "item_description":CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
        }
        image_reference_url = ""
    
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    
    if '1337' not in image_reference_url and '1337' not in base_url:
        image_reference_url = ':1337' + image_reference_url
    image_url = f'{base_url}{image_reference_url}'

    return render(request, 'core/GHSlabelGen/labels/ghsprinttemplate.html', {'this_ghs_pictogram': this_ghs_pictogram, 'image_url' : image_url}) 

def display_all_ghs_pictograms(request):
    """Display all GHS pictograms.
    
    Shows a list of all GHS pictogram records in the system, including:
    - Item codes
    - Item descriptions 
    - Associated pictogram images
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with all GHS pictogram records
        
    Template:
        core/labels/GHSlabelGen/allghslabels.html
    """
    all_ghs_pictograms = GHSPictogram.objects.all()

    return render(request, 'core/GHSlabelGen/labels/allghslabels.html', {'all_ghs_pictograms' : all_ghs_pictograms}) 

def display_partial_container_label(request):
    """Display partial container label page.
    
    Shows a label template for partial containers, including:
    - Current date/time
    - Item code
    - Item description
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code
            
    Returns:
        Rendered template with label content context
        
    Template:
        core/inventorycounts/partialcontainerlabel.html
    """
    today_now = dt.datetime.now()
    encoded_item_code = request.GET.get("encodedItemCode", "")
    item_code = get_unencoded_item_code(encoded_item_code, "itemCode")
    if CiItem.objects.filter(itemcode__iexact=item_code).exists():
        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
    else:
        item_code = "<Enter ItemCode>"
        item_description = "<Enter Description>"
    label_contents = {
        'date' : today_now,
        'item_code' : item_code,
        'item_description' : item_description
    }

    return render(request, 'core/inventorycounts/partialcontainerlabel.html', {"label_contents" : label_contents})

def display_blend_tote_label(request):
    """Display blend ID label for a lot number.
    
    Renders a template for a blend tote label
            
    Returns:
        Rendered template. All important stuff is done on the page using js
        
    Template:
        core/labels/blendlabeltemplate.html
    """
    
    return render(request, 'core/labels/blendtotelabel.html', {})

def display_blend_tank_restrictions(request):
    """Display blend tank restrictions page.
    
    Shows current blend tank restrictions and allows adding/editing restrictions.
    Restrictions specify which tanks certain blends can be made in.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with context containing:
            blend_tank_restrictions: QuerySet of BlendTankRestriction objects
            new_restriction_form: Form for adding new restrictions
            
    Template:
        core/blendtankrestrictions.htm
    """
    blend_tank_restrictions = BlendTankRestriction.objects.all()
    new_restriction_form = BlendTankRestrictionForm()
    item_codes = blend_tank_restrictions.values_list('item_code', flat=True)
    item_descriptions = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__in=item_codes)}
    for restriction in blend_tank_restrictions:
        restriction.item_description = item_descriptions.get(restriction.item_code, "")

    context = { 'blend_tank_restrictions' : blend_tank_restrictions, 'new_restriction_form' : new_restriction_form }
    
    return render(request, 'core/productionplanning/blendtankrestrictions.html', context)

def display_test_page(request):
    """Display test page for blend component usage analysis.
    
    Renders a test page showing blend component usage data for a hardcoded item.
    Used for testing and debugging the get_relevant_blend_runs function.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template with blend usage test data
        
    Template:
        core/testpage.html
    """
    item_code = '602001'
    item_quantity = 1500
    start_time = 0.0
    blend_subcomponent_usage = get_relevant_blend_runs(item_code, item_quantity, start_time)
    item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc

    return render(request, 'core/testpage.html', {'blend_subcomponent_usage' : blend_subcomponent_usage,
                                                  'item_code' : item_code,
                                                  'item_description' : item_description})

def display_blend_ingredient_quantity_checker(request):
    """Display page for checking blend ingredient quantities.
    
    Shows a table of blend ingredient transactions that have quantities outside 
    expected ranges based on bill of materials. Helps identify potential issues
    with blend ingredient usage.

    Args:
        request: HTTP request object

    Returns:
        Rendered template with matching transactions data
        
    Template:
        core/blendingredientquantitychecker.html
    """
    matching_transactions = get_transactions_for_bom_check()
    return render(request, 'core/blendingredientquantitychecker.html', {'matching_transactions' : matching_transactions})

def display_missing_audit_groups(request):
    """Display a form for adding missing audit groups.

    Retrieves items that don't have audit groups assigned and displays them in a
    formset for bulk creation. Filters can be applied via the 'filterString' GET parameter.

    Args:
        request: The HTTP request object

    Returns:
        Rendered template with formset for creating audit groups
    """
    filter_string = request.GET.get('filterString', 'all')
    # Fetch item codes that are not in AuditGroup
    missing_items = get_relevant_ci_item_itemcodes(filter_string)
    AuditGroupFormSet = modelformset_factory(AuditGroup, form=AuditGroupForm, extra=len(missing_items))
    
    if request.method == 'POST':
        formset = AuditGroupFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            # Redirect or indicate success as needed
            return render(request, 'core/inventorycounts/auditgroupsuccess.html')
    else:
        # Prepopulate the formset with missing items
        formset_initial_data = [{'item_code': item[0], 'item_description' : item[1], 'counting_unit' : item[2]} for item in missing_items]
        audit_group_formset = AuditGroupFormSet(queryset=AuditGroup.objects.none(), initial=formset_initial_data)
    
    return render(request, 'core/missingauditgroups.html', {'audit_group_formset': audit_group_formset, 'missing_items' : missing_items})

def display_raw_material_label(request):
    """
    Renders a template for printing raw material labels with today's date.
    Used for labeling incoming raw materials with receipt date.

    """
    today_date = dt.datetime.now()

    return render(request, 'core/labels/rawmateriallabel.html', {'today_date' : today_date})

def display_flush_tote_label(request):
    """
    Renders the flush tote label template for printing labels.
    """
    return render(request, 'core/labels/flushtotelabel.html')

def display_tank_level_change_report(request):
    selected_tank = request.GET.get('tank')

    sql_query = """
        WITH previous_levels AS (
            SELECT 
                id,
                tank_name,
                timestamp,
                filled_gallons,
                LAG(filled_gallons) OVER (
                    PARTITION BY tank_name 
                    ORDER BY timestamp
                ) as previous_volume
            FROM core_tanklevellog
            where tank_name = %s
        ) SELECT 
            tank_name,
            timestamp,
            filled_gallons,
            previous_volume,
            (filled_gallons - previous_volume) as volume_change
        FROM previous_levels
        WHERE 
            ABS(filled_gallons - previous_volume) > 10
            AND previous_volume IS NOT NULL
            ORDER BY timestamp DESC;
    """
    records = []
    with connection.cursor() as cursor:
        cursor.execute(sql_query, [selected_tank])
        if selected_tank:
            for row in cursor.fetchall():
                records.append({
                    'tank_name': row[0],
                    'timestamp': row[1],
                    'current_volume': row[2],
                    'prev_reading': row[3],
                    'volume_change': row[4]
                })

    # Convert query results to list of dictionaries for template
    
    # Get unique dates from records
    dates = []
    for record in records:
        record_date = record['timestamp'].date()
        if record_date not in dates:
            dates.append(record_date)
    dates.sort(reverse=True)

    # Calculate daily volume change totals
    daily_totals = []
    for date in dates:
        daily_total = 0
        for record in records:
            if record['timestamp'].date() == date:
                daily_total += record['volume_change']
        daily_totals.append({
            'date': date,
            'total_change': daily_total
        })
    
    # Get item code from StorageTank for selected tank
    tank_item_code = None
    if selected_tank:
        try:
            tank = StorageTank.objects.filter(tank_label_kpk=f"TANK {selected_tank}").first()
            tank_item_code = tank.item_code
        except StorageTank.DoesNotExist:
            pass
    
    # Get BI transactions for each date
    daily_bi_transactions = []
    if tank_item_code:
        for date in dates:
            sql = """
                SELECT COALESCE(SUM(transactionqty), 0) 
                FROM im_itemtransactionhistory 
                WHERE itemcode = %s
                AND transactioncode = 'BI'
                AND CAST(transactiondate AS DATE) = %s
            """
            with connection.cursor() as cursor:
                cursor.execute(sql, [tank_item_code, date])
                bi_total = cursor.fetchone()[0]
                daily_bi_transactions.append({
                    'date': date,
                    'bi_total': bi_total
                })

    # Combine daily totals and BI transactions into single list
    combined_daily_data = []
    for total, bi in zip(daily_totals, daily_bi_transactions):
        combined_daily_data.append({
            'date': total['date'],
            'total_change': total['total_change'],
            'bi_total': bi['bi_total']
    })

    # Add daily totals and BI transactions to each record
    for record in records:
        record_date = record['timestamp'].date()
        # Find matching daily total and BI data
        for daily_data in combined_daily_data:
            if daily_data['date'] == record_date:
                record['daily_total'] = daily_data['total_change']
                record['daily_bi'] = daily_data['bi_total']
                break

    # Get unique tank list for dropdown
    tanks = TankLevelLog.objects.values_list('tank_name', flat=True).distinct().order_by('tank_name')
    
    context = {
        'tanks': tanks,
        'selected_tank': selected_tank,
        'records': records,
    }
    
    return render(request, 'core/reports/tanklevelchangereport.html', context)

def display_all_purchasing_aliases(request):
    supply_type = normalize_supply_type(
        request.GET.get('supply_type'),
        default=PurchasingAlias.SUPPLY_TYPE_OPERATING,
    )
    aliases = (
        PurchasingAlias.objects
        .filter(supply_type=supply_type)
        .order_by('vendor', 'id')
    )
    # The form can be used for a creation form on the same page
    form = PurchasingAliasForm(initial={'supply_type': supply_type})
    context = {
        'purchasing_aliases': aliases,
        'form': form,
        'current_supply_type': supply_type,
        'current_supply_type_label': _SUPPLY_TYPE_LOOKUP[supply_type],
        'supply_type_choices': PurchasingAlias.SUPPLY_TYPE_CHOICES,
    }
    # You'll need to create this template: 'core/purchasing_aliases/display_all_purchasing_aliases.html'
    return render(request, 'core/operatingsupplies/purchasingaliasrecords.html', context)


@login_required
@ensure_csrf_cookie
def display_container_classifications(request):
    classifications = BlendContainerClassification.objects.order_by('item_code', 'id')
    for item in classifications:
        print(item.item_code)
        print(item.flush_tote)
    form = BlendContainerClassificationForm()

    context = {
        'classifications': classifications,
        'form': form,
    }

    return render(request, 'core/lotnumbers/containerclassificationrecords.html', context)


@login_required
@ensure_csrf_cookie
def discharge_testing_entry_view(request):
    """Render the discharge testing entry form for lab technicians."""
    if not is_lab_user(request.user):
        return HttpResponseForbidden('Lab technician access required.')

    context = {
        'production_line_choices': DischargeTestingRecord.DISCHARGE_SOURCE_CHOICES,
        'discharge_type_options': DischargeTestingRecord.DISCHARGE_TYPE_CHOICES,
        'sampling_personnel_options': get_sampling_personnel_options(),
    }
    return render(request, 'core/discharge_testing_entry.html', context)


@login_required
@ensure_csrf_cookie
def discharge_testing_records_view(request):
    """Render the discharge testing records page with initial options and data."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden('Staff access required.')

    context = {
        'production_line_choices': DischargeTestingRecord.DISCHARGE_SOURCE_CHOICES,
        'discharge_type_options': DischargeTestingRecord.DISCHARGE_TYPE_CHOICES,
        'sampling_personnel_options': get_sampling_personnel_options(),
        'flush_totes': list_discharge_tests(),
    }
    return render(request, 'core/discharge_testing_records.html', context)


@login_required
@ensure_csrf_cookie
def display_purchasing_alias_audit(request):
    """Render the monthly purchasing alias audit checklist."""

    supply_type = normalize_supply_type(
        request.GET.get('supply_type'),
        default=PurchasingAlias.SUPPLY_TYPE_OPERATING,
    )

    aliases = (
        PurchasingAlias.objects
        .filter(supply_type=supply_type)
        .filter(monthly_audit_needed=True)
        .order_by('vendor', 'vendor_part_number')
    )
    current_month_start = timezone.localdate().replace(day=1)

    alias_rows = []
    for alias in aliases:
        last_audit = alias.last_audit_date
        counted_this_month = bool(last_audit and last_audit >= current_month_start)
        alias_rows.append({
            'alias': alias,
            'counted_this_month': counted_this_month,
        })

    context = {
        'alias_rows': alias_rows,
        'current_month_start': current_month_start,
        'current_supply_type': supply_type,
        'current_supply_type_label': _SUPPLY_TYPE_LOOKUP[supply_type],
        'supply_type_choices': PurchasingAlias.SUPPLY_TYPE_CHOICES,
    }

    return render(request, 'core/operatingsupplies/purchasingalias_audit.html', context)


@login_required
@ensure_csrf_cookie
def display_production_holidays(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden('You do not have access to manage production holidays.')

    holidays = ProductionHoliday.objects.order_by('date')
    context = {
        'holidays': holidays,
    }

    return render(request, 'core/production_holidays.html', context)


@login_required
@ensure_csrf_cookie
def display_desk_labor_rates(request):
    """Admin-only page to view and edit hourly labor rates by desk."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden('Admin access required.')

    rates = DeskLaborRate.objects.order_by('desk_name')
    return render(request, 'core/desk_labor_rates.html', {'rates': rates})
