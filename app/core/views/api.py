from core.models import (
    Forklift,
    LotNumRecord,
    FoamFactor,
    ItemLocation,
    AuditGroup,
    ImItemWarehouse,
    BlendProtection,
    GHSPictogram,
    CiItem,
    PurchasingAlias,
    StorageTank,
    PoPurchaseOrderDetail,
    BillOfMaterials,
    LoopStatus,
    BlendTankRestriction,
    BlendContainerClassification,
    SoSalesOrderDetail,
    ProductionHoliday,
    DeskLaborRate,
)
from prodverse.models import SpecSheetData
from django.http import JsonResponse, HttpRequest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.conf import settings
import json, math, logging, re
from decimal import Decimal, InvalidOperation
from django.db.models import Q, Max, F, DecimalField, ExpressionWrapper
from core.services.production_planning_services import (
    get_component_consumption,
    project_datetime_from_production_hours,
    list_production_holidays,
    create_production_holiday,
    update_production_holiday,
    delete_production_holiday,
)
from core.services.blend_scheduling_services import (
    calculate_shortage_times,
    get_blend_schedule_querysets,
)
import datetime as dt
from django.utils import timezone
from core.kpkapp_utils.string_utils import get_unencoded_item_code
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import connection
from core.selectors.inventory_selectors import get_count_record_model
from core.services.tank_levels_services import get_tank_levels_html, extract_all_tank_levels
from core.services import reports_services
from core.services import (
    create_discharge_test,
    record_discharge_action_and_final_ph,
    record_discharge_initial_ph,
)
from core.services.discharge_testing_services import GROUP_LAB_TECHNICIAN, GROUP_LINE_PERSONNEL
from core.services.bom_costing_service import (
    BomCostingService,
    CircularBomReferenceError,
    ItemNotFoundError,
)
from core.services.purchasing_cost_service import (
    PurchasingCostParseError,
    load_default_purchasing_costs,
    load_purchasing_costs_from_file,
    load_purchasing_costs_with_both_values,
)
from core.services.cost_impact_service import analyze_cost_impacts
import time
from django.utils.dateparse import parse_datetime
from typing import Dict
from core.selectors import get_discharge_test, list_discharge_tests

logger = logging.getLogger(__name__)

def _serialize_lot_record(lot_record):
    """Return a JSON-serializable dict representation of a LotNumRecord."""
    return {
        'id': lot_record.id,
        'lot_number': lot_record.lot_number,
        'item_code': lot_record.item_code,
        'item_description': lot_record.item_description,
        'lot_quantity': float(lot_record.lot_quantity) if lot_record.lot_quantity is not None else None,
        'date_created': lot_record.date_created.strftime('%Y-%m-%d') if lot_record.date_created else None,
        'line': lot_record.line,
        'desk': lot_record.desk,
        'start_time': lot_record.start_time.isoformat() if lot_record.start_time else None,
        'stop_time': lot_record.stop_time.isoformat() if lot_record.stop_time else None,
        'sage_entered_date': lot_record.sage_entered_date.strftime('%Y-%m-%d') if lot_record.sage_entered_date else None,
        'sage_qty_on_hand': float(lot_record.sage_qty_on_hand) if lot_record.sage_qty_on_hand is not None else None,
        'run_date': lot_record.run_date.strftime('%Y-%m-%d') if lot_record.run_date else None,
        'run_day': lot_record.run_day,
    }


def _safe_float(value):
    """Convert a value to float when possible, otherwise return None."""
    if value is None:
        return None

    if isinstance(value, (int, float, Decimal)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None

        normalized = cleaned.replace(',', '')
        try:
            return float(normalized)
        except ValueError:
            match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', normalized)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    return None

    return None

def _parse_timestudy_value(raw_value):
    """
    Convert a string datetime into a timezone-aware value using the project's timezone.

    Accepts ISO strings (with or without timezone). Returns None if the value is empty.
    Raises ValueError if parsing fails.
    """
    if not raw_value:
        return None

    parsed = parse_datetime(raw_value)
    if not parsed:
        # Attempt to parse basic datetime-local input (YYYY-MM-DDTHH:MM)
        try:
            parsed = dt.datetime.fromisoformat(raw_value)
        except ValueError as exc:
            raise ValueError(f"Invalid datetime value: {raw_value}") from exc

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed



@login_required
@require_GET
def get_json_misc_report_types(request):
    """Return the set of miscellaneous report definitions for use in the UI."""
    reports = reports_services.get_misc_report_definitions()
    return JsonResponse({'reports': reports})


@login_required
@require_http_methods(["GET", "POST"])
def get_json_bom_cost(request):
    """Return the FIFO cost breakdown for a requested item and quantity."""
    data_source = request.POST if request.method == 'POST' else request.GET
    item_code = (data_source.get('item_code') or '').strip()
    quantity_raw = (data_source.get('quantity') or '1').strip()
    warehouse = (data_source.get('warehouse') or 'ALL').strip() or 'ALL'

    # Precedent demand parameters
    sales_order_no = (data_source.get('sales_order_no') or '').strip()
    line_key = (data_source.get('line_key') or '').strip()
    promise_date_raw = (data_source.get('promise_date') or '').strip()
    include_precedent = (data_source.get('include_precedent') or '').lower() in ('1', 'true', 'yes')

    if not item_code:
        return JsonResponse({'error': 'item_code query parameter is required'}, status=400)

    try:
        requested_qty = Decimal(quantity_raw)
    except InvalidOperation:
        return JsonResponse({'error': 'quantity must be numeric'}, status=400)

    if requested_qty <= 0:
        return JsonResponse({'error': 'quantity must be greater than zero'}, status=400)

    # Parse promise date if provided
    promise_date = None
    if promise_date_raw:
        try:
            promise_date = dt.datetime.fromisoformat(promise_date_raw).date()
        except ValueError:
            pass  # Ignore invalid dates

    purchasing_costs = {}
    pricing_label = 'Standard costs only'

    if request.method == 'POST' and request.FILES.get('cost_override'):
        try:
            purchasing_costs, uploaded_name = load_purchasing_costs_from_file(
                request.FILES['cost_override']
            )
        except PurchasingCostParseError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        pricing_label = f"Uploaded workbook ({uploaded_name})" if uploaded_name else 'Uploaded workbook'
    else:
        default_costs, workbook_name = load_default_purchasing_costs()
        purchasing_costs = default_costs
        if purchasing_costs:
            if workbook_name:
                pricing_label = f"Server workbook ({workbook_name})"
            else:
                pricing_label = 'Server workbook'

    service = BomCostingService(warehouse_code=warehouse, purchasing_costs=purchasing_costs)
    started = time.perf_counter()

    # If precedent demand is requested, use queue-aware calculation
    # This simulates ALL prior orders to get accurate cost at queue position
    if include_precedent and sales_order_no and line_key:
        try:
            cost_result, precedent_result = service.calculate_precedent_demand(
                item_code=item_code,
                quantity=requested_qty,
                sales_order_no=sales_order_no,
                line_key=line_key,
                promise_date=promise_date,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

            payload = {
                'itemCode': cost_result.item_code,
                'itemDescription': cost_result.item_description,
                'requestedQuantity': float(cost_result.requested_quantity),
                'warehouse': cost_result.warehouse_code,
                'totalCost': float(cost_result.total_cost),
                'unitCost': float(cost_result.unit_cost),
                'elapsedMs': elapsed_ms,
                'rows': [row.to_dict() for row in cost_result.rows],
                'pricingSource': pricing_label,
                'precedentDemand': precedent_result.to_dict(),
                'queueAware': True,
            }
            return JsonResponse(payload)

        except ItemNotFoundError:
            return JsonResponse({'error': f'Item {item_code.upper()} was not found'}, status=404)
        except CircularBomReferenceError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except Exception as exc:
            # Fall back to fresh calculation if precedent fails
            logger.warning("Precedent demand calculation failed, falling back: %s", exc)

    # Standard fresh calculation (no queue awareness)
    try:
        result = service.calculate(item_code=item_code, quantity=requested_qty)
    except ItemNotFoundError:
        return JsonResponse({'error': f'Item {item_code.upper()} was not found'}, status=404)
    except CircularBomReferenceError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    payload = {
        'itemCode': result.item_code,
        'itemDescription': result.item_description,
        'requestedQuantity': float(result.requested_quantity),
        'warehouse': result.warehouse_code,
        'totalCost': float(result.total_cost),
        'unitCost': float(result.unit_cost),
        'elapsedMs': elapsed_ms,
        'rows': [row.to_dict() for row in result.rows],
        'pricingSource': pricing_label,
        'queueAware': False,
    }

    return JsonResponse(payload)


@login_required
@require_http_methods(["GET", "POST"])
def get_json_sales_order_vs_bom_cost(request):
    """Return FIFO costing insights for all open sales orders."""
    data_source = request.POST if request.method == "POST" else request.GET
    warehouse = (data_source.get("warehouse") or "MTG").strip().upper() or "MTG"
    limit_param = (data_source.get("limit") or "").strip()
    limit = None
    if limit_param:
        try:
            parsed_limit = int(limit_param)
            if parsed_limit > 0:
                limit = min(parsed_limit, 5000)
        except ValueError:
            return JsonResponse({"error": "limit must be an integer"}, status=400)

    purchasing_costs = {}
    pricing_label = "Standard costs only"

    if request.method == "POST" and request.FILES.get("cost_override"):
        try:
            purchasing_costs, uploaded_name = load_purchasing_costs_from_file(
                request.FILES["cost_override"]
            )
        except PurchasingCostParseError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        pricing_label = (
            f"Uploaded workbook ({uploaded_name})"
            if uploaded_name
            else "Uploaded workbook"
        )
    else:
        default_costs, workbook_name = load_default_purchasing_costs()
        purchasing_costs = default_costs
        if purchasing_costs:
            pricing_label = (
                f"Server workbook ({workbook_name})"
                if workbook_name
                else "Server workbook"
            )

    service = BomCostingService(
        warehouse_code=warehouse, purchasing_costs=purchasing_costs
    )
    started = time.perf_counter()
    timings: Dict[str, float] = {}

    open_qty_expr = ExpressionWrapper(
        F("quantityordered") - F("quantityshipped"),
        output_field=DecimalField(max_digits=20, decimal_places=6),
    )

    order_qs = (
        SoSalesOrderDetail.objects.filter(itemtype__iexact="1")
        .annotate(open_qty=open_qty_expr)
        .filter(open_qty__gt=Decimal("0"))
    )
    if warehouse != "ALL":
        order_qs = order_qs.filter(warehousecode__iexact=warehouse)

    order_qs = order_qs.order_by("promisedate", "salesorderno", "lineseqno")
    if limit is not None:
        order_qs = order_qs[:limit]

    order_values = order_qs.values(
        "salesorderno",
        "linekey",
        "lineseqno",
        "itemcode",
        "itemcodedesc",
        "warehousecode",
        "promisedate",
        "unitprice",
        "open_qty",
    )
    orders = list(order_values)
    timings["orderQueryMs"] = round((time.perf_counter() - started) * 1000, 2)

    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    analyzed_count = 0
    negative_count = 0

    unique_item_codes = {
        (entry.get("itemcode") or "").strip().upper()
        for entry in orders
        if entry.get("itemcode")
    }
    warm_start = time.perf_counter()
    service.warm_caches(unique_item_codes)
    timings["cacheWarmMs"] = round((time.perf_counter() - warm_start) * 1000, 2)

    def _to_decimal(value) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    def _to_float(value) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    rows = []
    costing_start = time.perf_counter()

    for entry in orders:
        item_code = (entry.get("itemcode") or "").strip()
        open_qty = _to_decimal(entry.get("open_qty"))
        if open_qty <= Decimal("0"):
            continue

        try:
            cost_result = service.calculate(
                item_code=item_code, quantity=open_qty, capture_rows=False
            )
        except ItemNotFoundError:
            rows.append(
                {
                    "salesOrderNo": entry.get("salesorderno") or "",
                    "lineKey": entry.get("linekey") or "",
                    "lineSeqNo": entry.get("lineseqno") or "",
                    "itemCode": item_code,
                    "description": entry.get("itemcodedesc") or "",
                    "promiseDate": (
                        entry.get("promisedate").isoformat()
                        if entry.get("promisedate")
                        else None
                    ),
                    "status": "error",
                    "statusNote": "Item not found in CI_Item",
                    "openQty": _to_float(open_qty),
                }
            )
            continue
        except CircularBomReferenceError as exc:
            rows.append(
                {
                    "salesOrderNo": entry.get("salesorderno") or "",
                    "lineKey": entry.get("linekey") or "",
                    "lineSeqNo": entry.get("lineseqno") or "",
                    "itemCode": item_code,
                    "description": entry.get("itemcodedesc") or "",
                    "promiseDate": (
                        entry.get("promisedate").isoformat()
                        if entry.get("promisedate")
                        else None
                    ),
                    "status": "error",
                    "statusNote": str(exc),
                    "openQty": _to_float(open_qty),
                }
            )
            continue
        except ValueError as exc:
            rows.append(
                {
                    "salesOrderNo": entry.get("salesorderno") or "",
                    "lineKey": entry.get("linekey") or "",
                    "lineSeqNo": entry.get("lineseqno") or "",
                    "itemCode": item_code,
                    "description": entry.get("itemcodedesc") or "",
                    "promiseDate": (
                        entry.get("promisedate").isoformat()
                        if entry.get("promisedate")
                        else None
                    ),
                    "status": "error",
                    "statusNote": str(exc),
                    "openQty": _to_float(open_qty),
                }
            )
            continue

        analyzed_count += 1
        line_total_cost = cost_result.total_cost
        unit_cost = (
            line_total_cost / open_qty if open_qty > Decimal("0") else Decimal("0")
        )
        unit_price = _to_decimal(entry.get("unitprice"))
        sales_amount = unit_price * open_qty
        margin = sales_amount - line_total_cost
        margin_pct = (
            (margin / sales_amount) * Decimal("100")
            if sales_amount > Decimal("0")
            else None
        )

        total_cost += line_total_cost
        total_revenue += sales_amount
        if margin < Decimal("0"):
            negative_count += 1

        rows.append(
            {
                "salesOrderNo": entry.get("salesorderno") or "",
                "lineKey": entry.get("linekey") or "",
                "lineSeqNo": entry.get("lineseqno") or "",
                "itemCode": item_code,
                "description": entry.get("itemcodedesc") or "",
                "promiseDate": (
                    entry.get("promisedate").isoformat()
                    if entry.get("promisedate")
                    else None
                ),
                "openQty": _to_float(open_qty),
                "unitPrice": _to_float(unit_price),
                "salesAmount": _to_float(sales_amount),
                "unitCost": _to_float(unit_cost),
                "totalCost": _to_float(line_total_cost),
                "margin": _to_float(margin),
                "marginPct": _to_float(margin_pct) if margin_pct is not None else None,
                "status": "ok",
                "statusNote": "",
            }
        )

    timings["costingMs"] = round((time.perf_counter() - costing_start) * 1000, 2)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    timings["totalMs"] = elapsed_ms
    summary_margin = total_revenue - total_cost

    payload = {
        "warehouse": warehouse,
        "pricingSource": pricing_label,
        "elapsedMs": elapsed_ms,
        "summary": {
            "rowsProcessed": len(rows),
            "ordersAnalyzed": analyzed_count,
            "negativeMarginCount": negative_count,
            "totalRevenue": _to_float(total_revenue),
            "totalCost": _to_float(total_cost),
            "totalMargin": _to_float(summary_margin),
        },
        "limitApplied": limit,
        "rows": rows,
        "timings": timings,
    }
    logger.info(
        "SalesOrderVsBomCost rows=%s analyzed=%s negatives=%s unique_items=%s timings=%s",
        len(rows),
        analyzed_count,
        negative_count,
        len(unique_item_codes),
        timings,
    )
    return JsonResponse(payload)


@login_required
@require_GET
def get_next_purchasing_alias_id(request):
    """Return the next available purchasing alias ID (max + 1)."""

    max_id = PurchasingAlias.objects.aggregate(max_id=Max('id')).get('max_id') or 0
    next_id = max_id + 1

    return JsonResponse({'status': 'success', 'next_id': next_id})


@login_required
@require_GET
def get_next_container_classification_id(request):
    """Return the next available container classification ID (max + 1)."""

    max_id = BlendContainerClassification.objects.aggregate(max_id=Max('id')).get('max_id') or 0
    next_id = max_id + 1

    return JsonResponse({'status': 'success', 'next_id': next_id})


def get_json_forklift_serial(request):
    """
    Retrieves and returns the serial number for a forklift as JSON response.
    
    Args:
        request: HTTP request object containing 'unit-number' GET parameter
        
    Returns:
        JsonResponse containing the forklift's serial number
        
    Raises:
        Forklift.DoesNotExist: If no forklift matches the given unit number
    """
    if request.method == "GET":
        forklift_unit_number = request.GET.get('unit-number', 0)
        forklift = Forklift.objects.get(unit_number=forklift_unit_number)
    return JsonResponse(forklift.serial_no, safe=False)

def get_json_lot_details(request, lot_id):
    """
    Retrieves all fields for a specific lot number by its ID and returns them as JSON.
    
    Args:
        request: The HTTP request object
        lot_id: The ID of the lot number record to retrieve
        
    Returns:
        JsonResponse containing all fields of the requested lot number
    """
    try:
        # Get the lot number record by ID
        lot_record = LotNumRecord.objects.get(id=lot_id)
        print(lot_record)

        return JsonResponse(_serialize_lot_record(lot_record))
    
    except LotNumRecord.DoesNotExist:
        return JsonResponse({'error': f'Lot record with ID {lot_id} not found'}, status=404)
    
    except Exception as e:
        return JsonResponse({'error': str(e)})


@require_GET
def get_json_lot_details_by_number(request):
    """
    Retrieve lot details by lot number (case-insensitive).
    """
    lot_number = request.GET.get('lot_number')
    if not lot_number:
        return JsonResponse({'error': 'lot_number query parameter is required'}, status=400)

    lot_record = LotNumRecord.objects.filter(lot_number__iexact=lot_number.strip()).first()
    if not lot_record:
        return JsonResponse({'error': f'Lot record with number {lot_number} not found'}, status=404)

    return JsonResponse(_serialize_lot_record(lot_record))

def get_json_latest_lot_num_record(request):
    """
    Retrieves the latest lot number record and returns it as JSON.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing the latest lot number record data
        
    Fields returned:
        id: Record ID
        lot_number: Lot number string
        item_code: Item code
        item_description: Item description
        date_created: Creation date
        desk: Desk assignment
        line: Production line
        lot_quantity: Quantity in lot
    """
    latest_lot_num_record = LotNumRecord.objects.latest('id')
    return JsonResponse(_serialize_lot_record(latest_lot_num_record))


@login_required
@require_POST
def update_lot_timestudy(request, lot_id):
    """
    Update timestudy fields (start_time/stop_time) for a lot.
    Expects JSON or form-encoded payload with optional start_time/stop_time values.
    """
    try:
        lot_record = LotNumRecord.objects.get(pk=lot_id)
    except LotNumRecord.DoesNotExist:
        return JsonResponse({'error': f'Lot record with ID {lot_id} not found'}, status=404)

    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    else:
        payload = request.POST.dict()

    errors = {}
    updated_fields = []

    current_start = lot_record.start_time
    current_stop = lot_record.stop_time

    if 'start_time' in payload:
        start_raw = payload.get('start_time')
        if isinstance(start_raw, str):
            start_raw = start_raw.strip()
        try:
            parsed_start = _parse_timestudy_value(start_raw)
            if parsed_start != current_start:
                lot_record.start_time = parsed_start
                updated_fields.append('start_time')
        except ValueError as exc:
            errors['start_time'] = str(exc)

    if 'stop_time' in payload:
        stop_raw = payload.get('stop_time')
        if isinstance(stop_raw, str):
            stop_raw = stop_raw.strip()
        try:
            parsed_stop = _parse_timestudy_value(stop_raw)
            if parsed_stop != current_stop:
                lot_record.stop_time = parsed_stop
                updated_fields.append('stop_time')
        except ValueError as exc:
            errors['stop_time'] = str(exc)

    if errors:
        return JsonResponse({'status': 'error', 'errors': errors}, status=400)

    if not updated_fields:
        return JsonResponse({'status': 'noop', 'message': 'No timestudy changes supplied.'})

    updated_fields = list(dict.fromkeys(updated_fields + ['last_modified']))

    lot_record.save(update_fields=updated_fields)
    lot_record.refresh_from_db(fields=['start_time', 'stop_time', 'last_modified'])

    return JsonResponse(
        {
            'status': 'success',
            'data': _serialize_lot_record(lot_record),
            'updated_fields': updated_fields,
        }
    )

def get_json_all_foam_factors(request):
    """
    Retrieves all FoamFactor objects and returns them as a JSON response.
    """
    try:
        foam_factors = FoamFactor.objects.all()
        # Serialize the queryset to a list of dictionaries
        # Ensuring that all relevant fields are included.
        
        simplified_data = [
            {
                'item_code': factor.item_code,
                'factor': factor.factor
            }
            for factor in foam_factors
        ]
            
        return JsonResponse({'foam_factors': simplified_data}, safe=False)
    except Exception as e:
        # Log the exception e
        return JsonResponse({'error': 'Failed to retrieve foam factors', 'details': str(e)}, status=500)

def get_json_containers_from_count(request):
    """Get container data from a count record in JSON format.
    
    Retrieves the containers field from a specified count record and returns it as JSON.
    Handles different record types through dynamic model selection.

    Args:
        request: HTTP request containing:
            countRecordId: ID of the count record to retrieve containers from
            recordType: Type of count record (e.g. 'blend', 'component')

    Returns:
        JsonResponse containing:
            - List of containers if found
            - Error message and status if record not found or other error occurs
    """
    count_record_id = request.GET.get('countRecordId')
    record_type = request.GET.get('recordType')

    model = get_count_record_model(record_type)

    try:
        count_record = model.objects.get(id=count_record_id)
        containers = count_record.containers or []
        return JsonResponse(containers, safe=False)
    except model.DoesNotExist:
        return JsonResponse({'error': 'Count record not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_json_matching_lot_numbers(request):
    """Get matching lot numbers for a production line, run date and item code.
    
    Queries the LotNumRecord model to find lot numbers matching the specified criteria.
    Returns lot numbers and their quantities on hand that match the production line,
    run date (if provided), and item code filters.

    Args:
        request: HTTP request containing:
            prodLine: Production line code
            runDate: Run date to filter by (0 indicates null run date)
            itemCode: Item code to match

    Returns:
        JsonResponse containing list of dictionaries with:
            - lot_number: The matching lot number
            - quantityOnHand: Current quantity on hand for that lot
    """
    prod_line = request.GET.get('prodLine')
    run_date = request.GET.get('runDate')
    item_code = get_unencoded_item_code(request.GET.get('itemCode'), 'itemCode')
    if run_date == 0 or run_date == '0':
        lot_numbers_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code) \
            .filter(run_date__isnull=True) \
            .filter(line__iexact=prod_line) \
            .filter(sage_qty_on_hand__gt=0) \
            .order_by('-date_created')
    else:
        lot_numbers_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).filter(run_date=run_date).filter(line__iexact=prod_line)
    result = [{'lot_number' : lot.lot_number, 'quantityOnHand' : lot.sage_qty_on_hand } for lot in lot_numbers_queryset]

    return JsonResponse(result, safe=False)

def get_json_counting_unit(request):
    """
    API endpoint to retrieve counting method information for a specific item code.
    
    Returns JSON with:
    - counting_unit: The counting method used for this item
    - standard_uom: The standard unit of measure for the item
    """
    item_code = request.GET.get('itemCode')

    print(item_code)
    
    if not item_code:
        return JsonResponse({'error': 'Item code is required'}, status=400)
    
    try:
        # Get the audit group for this item
        audit_group = AuditGroup.objects.filter(item_code__iexact=item_code).first()
        
        if not audit_group:
            return JsonResponse({'error': 'No audit group found for this item'}, status=404)
        
        # Get the CI item for standard UOM
        ci_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        
        if not ci_item:
            return JsonResponse({'error': 'Item not found in CI Items'}, status=404)
        
        # Return the counting method and standard UOM
        return JsonResponse({
            'counting_unit': audit_group.counting_unit,
            'standard_uom': ci_item.standardunitofmeasure,
            'ship_weight': ci_item.shipweight,
        })
        
    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)}, status=500)

def get_json_item_location(request):
    """Get item location information from database.
    
    Retrieves location, description, quantity and UOM information for an item based on
    the provided lookup parameters. Used by the location lookup page to display item details.

    Args:
        request: HTTP request containing:
            lookup-type (str): Type of lookup ('itemCode', etc)
            item (str): Encoded item code to look up
            restriction (str): Optional restriction on lookup

    Returns:
        JsonResponse containing:
            itemCode: Item code
            itemDescription: Item description 
            bin: Storage bin location
            zone: Storage zone
            qtyOnHand: Current quantity on hand
            standardUOM: Standard unit of measure
    """
    if request.method == "GET":
        lookup_type = request.GET.get('lookup-type', 0)
        lookup_value = request.GET.get('item', 0)
        item_code = get_unencoded_item_code(lookup_value, lookup_type)
        print(item_code)
        
        requested_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        qty_on_hand = round(ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(warehousecode__iexact='MTG').first().quantityonhand, 2)
        item_description = requested_item.itemcodedesc
        print(item_description)
        standard_uom = requested_item.standardunitofmeasure

        if ItemLocation.objects.filter(item_code__iexact=item_code).exists():
            requested_item = ItemLocation.objects.get(item_code=item_code)
            bin = requested_item.bin
            zone = requested_item.zone
        else:
            bin = "no location listed."
            zone = ""

        response_item = {
            "itemCode" : item_code,
            "itemDescription" : item_description,
            "bin" : bin,
            "zone" : zone,
            "qtyOnHand" : qty_on_hand,
            "standardUOM" : standard_uom
        }
    return JsonResponse(response_item, safe=False)

def get_json_item_info(request):
    """Get item information from database.

    Retrieves item details from CiItem and ImItemWarehouse tables based on provided lookup parameters.
    Returns UV/freeze protection info for blends and GHS pictogram info if requested.

    Args:
        request: HTTP GET request containing:
            lookup-type (str): Type of lookup ('itemCode', etc)
            item (str): Item code or other lookup value 
            restriction (str): Optional filter for GHS blends

    Returns:
        JsonResponse containing item details:
            item_code: Item code
            item_description: Item description 
            qtyOnHand: Current quantity on hand (non-GHS items)
            standardUOM: Standard unit of measure (non-GHS items)
            uv_protection: UV protection level for blends
            shipweight: Item shipping weight (non-GHS items)
            freeze_protection: Freeze protection level for blends
    """
    if request.method == "GET":
        lookup_type = request.GET.get('lookup-type', 0)
        lookup_value = request.GET.get('item', 0)
        print(lookup_value)
        lookup_restriction = request.GET.get('restriction', 0)

        item_code = get_unencoded_item_code(lookup_value, lookup_type)
        print(item_code)
        
        if BlendProtection.objects.filter(item_code__iexact=item_code).exists():
            item_protection = BlendProtection.objects.filter(item_code__iexact=item_code).first()
            uv_protection = item_protection.uv_protection
            freeze_protection = item_protection.freeze_protection

            # Get lot numbers with quantity on hand for this item code
            lot_numbers_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code) \
                                                    .filter(sage_qty_on_hand__gt=0) \
                                                    .order_by('-date_created')
            lot_numbers = [{'lot_number': lot.lot_number, 
                        'quantity': lot.sage_qty_on_hand} 
                        for lot in lot_numbers_queryset]
        else:
            uv_protection = "Not a blend."
            freeze_protection = "Not a blend."
            lot_numbers = "None."

        if lookup_restriction == 'ghs-blends':
            requested_item = GHSPictogram.objects.filter(item_code__iexact=item_code).first()
            response_item = {
                "item_code" : requested_item.item_code,
                "item_description" : requested_item.item_description,
            }
        else:
            requested_item = CiItem.objects.filter(itemcode__iexact=item_code).first()
            requested_im_warehouse_item = ImItemWarehouse.objects.filter(itemcode__iexact=item_code, warehousecode__exact='MTG').first()

            if requested_item is None or requested_im_warehouse_item is None:
                return JsonResponse(
                    {'status': 'error', 'message': f'Item data unavailable for {item_code}.'},
                    status=404
                )

            ship_weight = getattr(requested_item, 'shipweight', None)
            ship_weight_value = _safe_float(ship_weight)
            
            response_item = {
                "item_code" : requested_item.itemcode,
                "item_description" : requested_item.itemcodedesc,
                "qtyOnHand" : requested_im_warehouse_item.quantityonhand,
                "standardUOM" : requested_item.standardunitofmeasure,
                "uv_protection" : uv_protection,
                "shipweight" : ship_weight_value,
                "freeze_protection" : freeze_protection,
                "lot_numbers" : lot_numbers
            }

    return JsonResponse(response_item, safe=False)

def get_json_tank_specs(request):
    """Get storage tank specifications from database.
    
    Retrieves tank specifications including item codes, descriptions and capacities
    for all storage tanks in the system.

    Args:
        request: HTTP GET request

    Returns:
        JsonResponse containing tank data dictionary:
            tank_label_vega (str): Tank identifier as key
            item_code (str): Item code stored in tank
            item_description (str): Description of item in tank
            max_gallons (int): Maximum capacity in gallons
    """
    if request.method == "GET":
        tank_queryset = StorageTank.objects.all()
        tank_dict = {}
        for tank in tank_queryset:
            tank_dict[tank.tank_label_vega] = {
                'item_code' : tank.item_code,
                'item_description' : tank.item_description,
                'gallons_per_inch' : tank.gallons_per_inch,
                'max_gallons' : tank.max_gallons
            }

        data = tank_dict

    return JsonResponse(data, safe=False)

def _get_single_tank_level_dict(tank_identifier, request=None):
    """Return the JSON payload for a single tank level lookup.

    This mirrors the structure returned by the public view but stays reusable for
    internal callers (e.g., reporting services) by accepting an optional request.
    """

    if request is not None and request.method != "GET":
        logger.warning("[TankMonitor] Non-GET request: %s", request.method)
        return {"status": "error", "error_message": "Invalid request method"}

    cache_key = "TANK_MONITOR_LEVELS"

    def _normalize_tag_key(raw_key: str) -> str:
        cleaned = (raw_key or "").strip().upper()
        # Accept both "TANK B" and "B" by trimming a leading "TANK" token
        if cleaned.startswith("TANK"):
            cleaned = cleaned[4:].strip()
        return cleaned

    def _find_matching_key(levels: dict, lookup_key: str):
        def norm(val: str) -> str:
            return ''.join((val or '').split()).upper()

        lookup_norm = norm(lookup_key)

        # First try strict equality (raw and normalized)
        if lookup_key in levels:
            return lookup_key
        for key in levels.keys():
            if norm(key) == lookup_norm:
                return key

        # If caller passed only the letter (e.g., "B"), find a key whose
        # final alpha token matches, regardless of spacing ("10 B", "10B")
        if len(lookup_norm) == 1:  # single letter intent
            for key in levels.keys():
                key_norm = norm(key)
                if key_norm.endswith(lookup_norm):
                    return key
        return None

    tag_key = _normalize_tag_key(tank_identifier)

    levels_dict = cache.get(cache_key)

    def _fetch_levels():
        try:
            # Use provided request when available; otherwise synthesize a minimal GET
            fetch_request = request
            if fetch_request is None:
                fetch_request = HttpRequest()
                fetch_request.method = "GET"

            html_response = get_tank_levels_html(fetch_request)
            html_dict = json.loads(html_response.content.decode("utf-8"))
            html_string = html_dict.get("html_string", "")

            if not html_string:
                logger.error("[TankMonitor] Empty HTML string from get_tank_levels_html.")
                return None

            return extract_all_tank_levels(html_string)
        except Exception as exc:  # noqa: BLE001
            logger.error("[TankMonitor] Cache rebuild failed: %s", exc, exc_info=True)
            return None

    if levels_dict is None:
        levels_dict = _fetch_levels()
        if levels_dict is None:
            return {"status": "error", "error_message": "Backend error during refresh"}

        cache_timeout = getattr(settings, "TANK_LEVEL_CACHE_TIMEOUT", 0.9)
        cache.set(cache_key, levels_dict, cache_timeout)

    gallons_value = levels_dict.get(tag_key)

    if gallons_value is None:
        matched_key = _find_matching_key(levels_dict, tag_key)
        if matched_key:
            gallons_value = levels_dict.get(matched_key)
    if gallons_value is not None:
        return {"status": "ok", "gallons": gallons_value}

    logger.warning("[TankMonitor] Tag '%s' not found in cached levels.", tag_key)
    return {"status": "error", "error_message": "Gauge data not found in cache/HTML"}


def get_json_single_tank_level(request, tank_identifier):
    """
    Return JSON containing current gallons for a single tank.

    Optimisations:
      • Results for *all* tanks are cached for a short TTL (default 1 s) so that
        hundreds of client polls share a single expensive HTML scrape/parse.
      • Cache key: 'TANK_MONITOR_LEVELS'
    """

    payload = _get_single_tank_level_dict(tank_identifier, request=request)
    status_code = 405 if request.method != "GET" else 200
    return JsonResponse(payload, status=status_code)

def get_json_bill_of_materials_fields(request):
    """Get bill of materials fields based on restriction type.
    
    Retrieves item codes and descriptions from CI_Item table filtered by various
    restriction types. Used to populate dropdowns and lookups for bill of materials.

    Args:
        request: HTTP request object containing:
            restriction (str): Type of items to retrieve:
                'blend' - Only blend items
                'blendcomponent' - Only chemical/dye/fragrance components
                'blends-and-components' - Both blends and components
                'spec-sheet-items' - Items with spec sheets
                'ghs-blends' - Items with GHS pictograms
                'foam-factor-blends' - Blend items without foam factors
                None - All items except those starting with '/'

    Returns:
        JsonResponse containing:
            item_codes (list): List of matching item codes
            item_descriptions (list): List of matching item descriptions
    """
    if request.method == "GET":
        restriction = request.GET.get('restriction', 0)
        if restriction == 'blend':
            item_references = CiItem.objects.filter(itemcodedesc__startswith='BLEND').values_list('itemcode', 'itemcodedesc')

        elif restriction == 'blendcomponent':
            item_references = CiItem.objects.filter(Q(itemcodedesc__startswith="CHEM") | Q(itemcodedesc__startswith="DYE") | Q(itemcodedesc__startswith="FRAGRANCE")).values_list('itemcode', 'itemcodedesc')

        elif restriction == 'blends-and-components':
            item_references = CiItem.objects.filter(Q(itemcodedesc__startswith="CHEM") | Q(itemcodedesc__startswith="DYE") | Q(itemcodedesc__startswith="FRAGRANCE") | Q(itemcodedesc__startswith="BLEND")).values_list('itemcode', 'itemcodedesc')

        elif restriction == 'spec-sheet-items':
            distinct_item_codes = SpecSheetData.objects.values_list('item_code', flat=True).distinct()
            item_references = CiItem.objects.filter(itemcode__in=distinct_item_codes).values_list('itemcode', 'itemcodedesc')
        
        elif restriction == 'ghs-blends':
            item_references = GHSPictogram.objects.all().values_list('item_code', 'item_description')

        elif restriction == 'foam-factor-blends':
            distinct_item_codes = FoamFactor.objects.values_list('item_code', flat=True).distinct()
            print(distinct_item_codes)
            item_references = CiItem.objects.filter(itemcodedesc__startswith='BLEND').exclude(itemcode__in=distinct_item_codes).values_list('itemcode', 'itemcodedesc')

        else:
            item_references = CiItem.objects.exclude(itemcode__startswith='/').values_list('itemcode', 'itemcodedesc')
 
        itemcode_list = [item[0] for item in item_references]
        itemdesc_list = [item[1] for item in item_references]
        bom_json = {
            'item_codes' : itemcode_list,
            'item_descriptions' : itemdesc_list

        }

    return JsonResponse(bom_json, safe=False)

def get_json_get_max_producible_quantity(request, lookup_value):
    """Calculate maximum producible quantity for a blend based on component availability.
    
    Examines bill of materials and current inventory levels to determine the limiting 
    component that restricts production capacity. Considers:
    
    - Current on-hand quantities of all components
    - Quantities already allocated to other blend orders
    - Bill of materials ratios for each component
    
    Args:
        request (HttpRequest): Request object containing lookup parameters
        lookup_value (str): Base64 encoded item code or description to analyze
        
    Returns:
        JsonResponse: Contains:
            - Maximum producible quantity
            - Limiting factor details (component code, description, UOM)
            - Current inventory levels
            - Expected next shipment date
    """
    lookup_type = request.GET.get('lookup-type', 0)
    this_item_code = get_unencoded_item_code(lookup_value, lookup_type)
    all_bills_this_itemcode = BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD").filter(item_code__iexact=this_item_code)
    item_info = {bill.component_item_code: {'qtyonhand' : bill.qtyonhand, 'qtyperbill' : bill.qtyperbill} for bill in all_bills_this_itemcode}
    
    # create a list of all the component part numbers
    all_components_this_bill = list(BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD").filter(item_code__iexact=this_item_code).values_list('component_item_code'))
    for listposition, component in enumerate(all_components_this_bill):
        all_components_this_bill[listposition] = component[0]

    max_producible_quantities = {}
    consumption_detail = {}
    component_consumption_totals = {}
    for component in all_components_this_bill:
         # don't need to consider DI Water (030143). 
        if component != '030143':
            # get a dictionary with the consumption info. "this_item_code" is the blend itemcode.
            this_component_consumption = get_component_consumption(component, this_item_code)
            consumption_detail[component] = this_component_consumption
            # get the appropriate item_info dict, get the quantity, subtract the total usage
            this_item_info_dict = item_info.get(component, "dfadsfd")
            component_onhand_quantity = this_item_info_dict.get('qtyonhand', "")
            available_component_minus_orders = float(component_onhand_quantity or 0) - float(this_component_consumption['total_component_usage'] or 0)
            component_consumption_totals[component] = float(this_component_consumption['total_component_usage'] or 0)
            # reverse-engineer the maximum producible qty of the blend by dividing available component by qtyperbill 
            max_producible_quantities[component] = math.floor(float(available_component_minus_orders or 0) / float(this_item_info_dict.get('qtyperbill', "") or 1))
            if max_producible_quantities[component] < 0:
                max_producible_quantities[component] = 0

    # print(max_producible_quantities)
    limiting_factor_item_code = min(max_producible_quantities, key=max_producible_quantities.get)
    limiting_factor_component = BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD") \
        .filter(component_item_code__iexact=limiting_factor_item_code) \
        .filter(item_code__iexact=this_item_code).first()
    limiting_factor_item_description = limiting_factor_component.component_item_description
    limiting_factor_UOM = limiting_factor_component.standard_uom
    limiting_factor_quantity_onhand = limiting_factor_component.qtyonhand
    limiting_factor_OH_minus_other_orders = float(limiting_factor_quantity_onhand or 0) - float(component_consumption_totals[limiting_factor_item_code] or 0)
    yesterday_date = dt.datetime.now()-dt.timedelta(days=1)

    if (PoPurchaseOrderDetail.objects.filter(itemcode__iexact=limiting_factor_item_code, quantityreceived__exact=0, requireddate__gt=yesterday_date).exists()):
            next_shipment_date = PoPurchaseOrderDetail.objects.filter(
                itemcode__iexact = limiting_factor_item_code,
                quantityreceived__exact = 0,
                requireddate__gt=yesterday_date
                ).order_by('requireddate').first().requireddate
    else:
        next_shipment_date = "No PO's found."

    responseJSON = {
        'item_code' : this_item_code,
        'item_description' : all_bills_this_itemcode.first().item_description,
        'max_producible_quantities' : max_producible_quantities,
        'component_consumption_totals' : component_consumption_totals,
        'limiting_factor_item_code' : limiting_factor_item_code,
        'limiting_factor_item_description' : limiting_factor_item_description,
        'limiting_factor_UOM' : limiting_factor_UOM,
        'limiting_factor_quantity_onhand' : limiting_factor_quantity_onhand,
        'limiting_factor_OH_minus_other_orders' : limiting_factor_OH_minus_other_orders,
        'next_shipment_date' : next_shipment_date,
        'max_producible_quantity' : str(max_producible_quantities[limiting_factor_item_code]),
        'consumption_detail' : consumption_detail
        }
    return JsonResponse(responseJSON, safe = False)

def get_json_current_user_initials(request):
    """Get initials of the currently logged-in user.
    
    Retrieves the initials (first + last name) of the authenticated user.
    Used for container label printing to show who generated the label.
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing:
            initials (str): User's initials (e.g., "JD" for John Doe)
            username (str): User's username
            full_name (str): User's full name
            is_authenticated (bool): Whether user is authenticated
    """
    if request.user.is_authenticated:
        user = request.user
        # Generate initials from first and last name
        initials = ""
        if user.first_name and user.last_name:
            initials = user.first_name[0].upper() + user.last_name[0].upper()
        elif user.first_name:
            initials = user.first_name[0].upper()
        elif user.last_name:
            initials = user.last_name[0].upper()
        else:
            # Fallback to first two characters of username if no names available
            initials = user.username[:2].upper()
        
        response_json = {
            'initials': initials,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip(),
            'is_authenticated': True
        }
    else:
        response_json = {
            'initials': 'ANON',
            'username': 'anonymous',
            'full_name': 'Anonymous User',
            'is_authenticated': False
        }
    
    return JsonResponse(response_json, safe=False)

def get_json_refresh_status(request):
    """Get JSON response indicating if loop status needs refresh.

    Checks if any loop status records are older than 5 minutes and returns
    status indicating if system is up or down. Uses timezone offset to handle
    timestamp comparison issues.

    Args:
        request: HTTP GET request

    Returns:
        JsonResponse containing:
            status (str): 'up' if all records are current, 'down' if any are stale
    """
    # This ridiculous dt.timedelta subtraction is happening because adding a timezone to the five_minutes_ago
    # variable does not make the comparison work. The code will say that the five_minutes_ago variable is
    # 5 hours newer than the timestamps in the database if they are nominally the same time.
    if request.method == "GET":
        five_minutes_ago = timezone.now() - dt.timedelta(minutes=305)
        status_queryset = LoopStatus.objects.all().filter(time_stamp__lt=five_minutes_ago)
        if status_queryset.exists():
            response_data = {'status' : 'down'}
        else:
            response_data = {'status' : 'up'}
    return JsonResponse(response_data, safe=False)


@require_GET
def get_json_loop_status_detail(request):
    """Get detailed loop status for all functions.

    Returns all LoopStatus records with function names, results, and timestamps.
    Used by CLI tools to show detailed health of data sync functions.

    Args:
        request: HTTP GET request

    Returns:
        JsonResponse containing:
            status (str): 'up' if all functions healthy, 'degraded' if some failed, 'down' if stale
            functions (list): List of function status objects with:
                - function_name (str): Name of the function
                - function_result (str): Result/status of last execution
                - time_stamp (str): ISO timestamp of last execution
                - minutes_ago (int): Minutes since last execution
                - is_healthy (bool): Whether function is considered healthy
    """
    # Use naive datetime to match database timestamps (stored in local time)
    now_naive = dt.datetime.now()
    stale_threshold = now_naive - dt.timedelta(minutes=5)

    loop_statuses = LoopStatus.objects.all().order_by('function_name')

    functions = []
    has_failures = False
    has_stale = False

    for status in loop_statuses:
        # Calculate minutes ago using naive comparison
        if status.time_stamp:
            ts = status.time_stamp
            # Strip timezone info if present for consistent comparison
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            delta = now_naive - ts
            minutes_ago = int(delta.total_seconds() / 60)
        else:
            minutes_ago = -1
            ts = None

        # Determine if this function is healthy
        # Healthy = recent timestamp AND result doesn't indicate error
        result_lower = (status.function_result or '').lower()
        is_error = any(word in result_lower for word in ['error', 'failed', 'exception', 'timeout'])
        is_stale = ts and ts < stale_threshold
        is_healthy = not is_error and not is_stale and minutes_ago >= 0

        if is_error:
            has_failures = True
        if is_stale:
            has_stale = True

        functions.append({
            'function_name': status.function_name,
            'function_result': status.function_result,
            'time_stamp': status.time_stamp.isoformat() if status.time_stamp else None,
            'minutes_ago': minutes_ago,
            'is_healthy': is_healthy,
            'is_stale': is_stale,
            'is_error': is_error,
        })

    # Determine overall status
    if has_stale:
        overall_status = 'down'
    elif has_failures:
        overall_status = 'degraded'
    else:
        overall_status = 'up'

    response_data = {
        'status': overall_status,
        'checked_at': now_naive.isoformat(),
        'function_count': len(functions),
        'healthy_count': sum(1 for f in functions if f['is_healthy']),
        'functions': functions,
    }

    return JsonResponse(response_data)

def get_json_all_ghs_fields(request):
    """Get all GHS pictogram fields as JSON.
    
    Retrieves all GHS pictogram records and returns their item codes and descriptions
    as JSON data. Used to populate item selection dropdowns.
    
    Args:
        request: HTTP GET request
        
    Returns:
        JsonResponse containing:
            item_codes (list): List of item codes with GHS pictograms
            item_descriptions (list): List of item descriptions
    """
    if request.method == "GET":
        item_references = GHSPictogram.objects.all().values_list('item_code', 'item_description')
        itemcode_list = [item[0] for item in item_references]
        itemdesc_list = [item[1] for item in item_references]
        options_json = {
            'item_codes' : itemcode_list,
            'item_descriptions' : itemdesc_list
        }

    return JsonResponse()

def get_json_container_label_data(request):
    """Retrieve container data for label printing.
    
    Gets specific container data from a count record for generating partial container labels.
    Includes item information, container details, and calculated net weights.
    
    Args:
        request: HTTP GET request containing:
            countRecordId (str): ID of the count record
            containerId (str): ID of the specific container
            recordType (str): Type of count record
            
    Returns:
        JsonResponse containing:
            item_code (str): Item code for the label
            item_description (str): Item description
            container_quantity (float): Container quantity
            container_type (str): Type of container
            tare_weight (float): Container tare weight
            net_weight (float): Calculated net weight
            net_gallons (float): Calculated net gallons (if applicable)
            date (str): Current date for label
            shipweight (float): Item ship weight for calculations
    """
    count_record_id = request.GET.get('countRecordId')
    container_id = request.GET.get('containerId')
    record_type = request.GET.get('recordType')
    
    try:
        model = get_count_record_model(record_type)
        count_record = model.objects.get(id=count_record_id)
        
        # Find the specific container in the containers JSON field
        container_data = None
        if count_record.containers:
            for container in count_record.containers:
                if str(container.get('container_id')) == str(container_id):
                    container_data = container
                    break
        
        if not container_data:
            return JsonResponse({'error': 'Container not found'}, status=404)
        
        # Get item information for calculations
        item_info = {}
        if CiItem.objects.filter(itemcode__iexact=count_record.item_code).exists():
            ci_item = CiItem.objects.filter(itemcode__iexact=count_record.item_code).first()
            
            # Safely convert shipweight to float, handling non-numeric characters
            shipweight_value = None
            if ci_item.shipweight:
                try:
                    # Remove common non-numeric characters like '#' and convert to float
                    cleaned_shipweight = str(ci_item.shipweight).replace('#', '').replace('lbs', '').replace('lb', '').strip()
                    shipweight_value = float(cleaned_shipweight) if cleaned_shipweight else None
                except (ValueError, TypeError):
                    print(f"⚠️ WARNING - Invalid shipweight format for {count_record.item_code}: {ci_item.shipweight}")
                    shipweight_value = None
            
            item_info = {
                'shipweight': shipweight_value,
                'standardUOM': ci_item.standardunitofmeasure
            }
            # Debug logging for unit issues
            print(f"🔍 DEBUG SINGLE - Item: {count_record.item_code}, StandardUOM: {ci_item.standardunitofmeasure}, Shipweight: {ci_item.shipweight} -> {shipweight_value}")
        else:
            print(f"❌ DEBUG SINGLE - Item {count_record.item_code} not found in CiItem table!")
        
        # Calculate net weight and gallons with container-specific logic
        gross_weight = float(container_data.get('container_quantity', 0))
        tare_weight = float(container_data.get('tare_weight', 0))
        is_net_measurement = container_data.get('net_measurement', False)
        container_type = container_data.get('container_type', 'Unknown')
        
        # Calculate net weight based on measurement type
        if is_net_measurement:
            # For NET measurements, the container_quantity IS the net weight
            net_weight = gross_weight
        else:
            # For gross measurements, subtract tare weight
            net_weight = gross_weight - tare_weight
        
        # Calculate secondary unit conversion (only for pound items)
        net_gallons = None
        if item_info.get('shipweight') and net_weight > 0:
            # Only convert for pound items - gallon items don't need weight conversions
            if item_info.get('standardUOM') == 'LB':
                # For pound items, net_weight is in pounds, convert to gallons for volume display
                net_gallons = net_weight / item_info['shipweight']  # pounds / lbs/gal = gallons
            # For gallon items: no conversion needed, weight is irrelevant for volume measurements
        
        # Validate container type and tare weight consistency
        expected_tare_weights = {
            "275gal tote": 125, "poly drum": 22, "regular metal drum": 37,
            "300gal tote": 150, "small poly drum": 13, "enzyme metal drum": 50,
            "plastic pail": 3, "metal pail": 4, "cardboard box": 2,
            "gallon jug": 1, "large poly tote": 0, "stainless steel tote": 0,
            "storage tank": 0, "pallet": 45
        }
        expected_tare = expected_tare_weights.get(container_type, 0)
        
        response_data = {
            'item_code': count_record.item_code,
            'item_description': count_record.item_description,
            'container_id': container_data.get('container_id'),
            'container_quantity': container_data.get('container_quantity'),
            'container_type': container_type,
            'tare_weight': container_data.get('tare_weight'),
            'expected_tare_weight': expected_tare,
            'net_weight': net_weight,
            'net_gallons': net_gallons,
            'date': dt.datetime.now().strftime('%Y-%m-%d'),
            'shipweight': item_info.get('shipweight'),
            'standard_uom': item_info.get('standardUOM'),
            'net_measurement': is_net_measurement,
            'tare_weight_valid': abs(tare_weight - expected_tare) < 5 if not is_net_measurement else True
        }
        
        return JsonResponse(response_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_json_all_container_labels_data(request):
    """Retrieve all container data for batch label printing.
    
    Gets all container data from a count record for generating multiple partial container labels.
    
    Args:
        request: HTTP GET request containing:
            countRecordId (str): ID of the count record
            recordType (str): Type of count record
            
    Returns:
        JsonResponse containing array of container label data objects
    """
    count_record_id = request.GET.get('countRecordId')
    record_type = request.GET.get('recordType')
    
    try:
        model = get_count_record_model(record_type)
        count_record = model.objects.get(id=count_record_id)
        
        if not count_record.containers:
            return JsonResponse({'containers': []}, safe=False)
        
        # Get item information for calculations
        item_info = {}
        if CiItem.objects.filter(itemcode__iexact=count_record.item_code).exists():
            ci_item = CiItem.objects.filter(itemcode__iexact=count_record.item_code).first()
            
            # Safely convert shipweight to float, handling non-numeric characters
            shipweight_value = None
            if ci_item.shipweight:
                try:
                    # Remove common non-numeric characters like '#' and convert to float
                    cleaned_shipweight = str(ci_item.shipweight).replace('#', '').replace('lbs', '').replace('lb', '').strip()
                    shipweight_value = float(cleaned_shipweight) if cleaned_shipweight else None
                except (ValueError, TypeError):
                    print(f"⚠️ WARNING - Invalid shipweight format for {count_record.item_code}: {ci_item.shipweight}")
                    shipweight_value = None
            
            item_info = {
                'shipweight': shipweight_value,
                'standardUOM': ci_item.standardunitofmeasure
            }
            # Debug logging for unit issues
            print(f"🔍 DEBUG - Item: {count_record.item_code}, StandardUOM: {ci_item.standardunitofmeasure}, Shipweight: {ci_item.shipweight} -> {shipweight_value}")
        else:
            print(f"❌ DEBUG - Item {count_record.item_code} not found in CiItem table!")
        
        containers_data = []
        for container in count_record.containers:
            # Skip empty containers
            if not container.get('container_quantity'):
                continue
                
            # Calculate net weight and gallons with container-specific logic
            gross_weight = float(container.get('container_quantity', 0))
            tare_weight = float(container.get('tare_weight', 0))
            is_net_measurement = container.get('net_measurement', False)
            container_type = container.get('container_type', 'Unknown')
            
            # Calculate net weight based on measurement type
            if is_net_measurement:
                # For NET measurements, the container_quantity IS the net weight
                net_weight = gross_weight
            else:
                # For gross measurements, subtract tare weight
                net_weight = gross_weight - tare_weight
            
            # Calculate secondary unit conversion (only for pound items)
            net_gallons = None
            if item_info.get('shipweight') and net_weight > 0:
                # Only convert for pound items - gallon items don't need weight conversions
                if item_info.get('standardUOM') == 'LB':
                    # For pound items, net_weight is in pounds, convert to gallons for volume display
                    net_gallons = net_weight / item_info['shipweight']  # pounds / lbs/gal = gallons
                # For gallon items: no conversion needed, weight is irrelevant for volume measurements
            
            # Validate container type and tare weight consistency
            expected_tare_weights = {
                "275gal tote": 125, "poly drum": 22, "regular metal drum": 37,
                "300gal tote": 150, "small poly drum": 13, "enzyme metal drum": 50,
                "plastic pail": 3, "metal pail": 4, "cardboard box": 2,
                "gallon jug": 1, "large poly tote": 0, "stainless steel tote": 0,
                "storage tank": 0, "pallet": 45
            }
            expected_tare = expected_tare_weights.get(container_type, 0)
            
            container_label_data = {
                'container_id': container.get('container_id'),
                'item_code': count_record.item_code,
                'item_description': count_record.item_description,
                'container_quantity': container.get('container_quantity'),
                'container_type': container_type,
                'tare_weight': container.get('tare_weight'),
                'expected_tare_weight': expected_tare,
                'net_weight': net_weight,
                'net_gallons': net_gallons,
                'date': dt.datetime.now().strftime('%Y-%m-%d'),
                'shipweight': item_info.get('shipweight'),
                'standard_uom': item_info.get('standardUOM'),
                'net_measurement': is_net_measurement,
                'tare_weight_valid': abs(tare_weight - expected_tare) < 5 if not is_net_measurement else True
            }
            containers_data.append(container_label_data)
        
        return JsonResponse({'containers': containers_data}, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_json_lot_number(request):
    """Get lot number information from database.
    
    Retrieves lot number information for an item code from the LotNumRecord model.
    Used to populate lot number fields in forms and displays.
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code to look up
            
    Returns:
        JsonResponse containing either:
            lot_number (str): Lot number for item if found
            error (str): Error message if lookup fails
    """
    print(request.GET.get("encodedItemCode"))
    item_code = get_unencoded_item_code(request.GET.get("encodedItemCode"), 'itemCode')
    try:
        lot_record = LotNumRecord.objects.filter(item_code__iexact=item_code).filter(sage_qty_on_hand__gt=0, sage_qty_on_hand__isnull=False).filter().order_by('date_created').first()
        if lot_record:
            return JsonResponse({'lot_number': lot_record.lot_number})
        else:
            lot_record = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('date_created').first()
            return JsonResponse({'lot_number': lot_record.lot_number})
    except Exception as e:
        return JsonResponse({'error': str(e)})

def get_json_most_recent_lot_records(request):
    """Get most recent lot records for an item.
    
    Retrieves the 10 most recent lot number records for an item code from the LotNumRecord model,
    ordered by creation date descending. Returns the lot numbers and their current quantities
    on hand in Sage.
    
    Args:
        request: HTTP GET request containing:
            encodedItemCode (str): Base64 encoded item code to look up
            
    Returns:
        JsonResponse containing:
            Dict mapping lot numbers to their Sage quantities on hand for the 10 most recent lots
    """
    item_code = get_unencoded_item_code(request.GET.get("encodedItemCode"), 'itemCode')
    if LotNumRecord.objects.filter(item_code__iexact=item_code).exists():
        lot_records = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created')[:10]

    else:
        lot_records = {
            'item_code' : '',
            'item_description'  : '',
            'lot_number' : '',
            'lot_quantity' : '',
            'date_created' : '',
            'line' : '',
            'desk' : '',
            'sage_entered_date' : '',
            'sage_qty_on_hand'  : '',
            'run_date' : '',
            'run_day' : ''
        }
    for lot in lot_records:
        if lot.sage_entered_date == None:
            lot.sage_entered_date = 'Not Entered'
            lot.sage_qty_on_hand = '0'
        print(lot.lot_number + ": " + str(lot.date_created))

    return JsonResponse({lot_record.lot_number : lot_record.sage_qty_on_hand for lot_record in lot_records})

def get_json_blend_tank_restriction(request):
    """Get blend tank restriction data in JSON format.
    
    Retrieves blend tank restriction data for a specific item code and returns it
    as JSON. The item code can be looked up by either direct code or description.
    
    Args:
        request: HTTP GET request containing:
            lookup-type (str): Type of lookup ('item-code' or 'item-desc')
            item (str): Item code or description to look up

    Returns:
        JsonResponse containing:
            result (str): Error message if lookup failed
            blend_restriction (obj): BlendTankRestriction object if found
    """
    response = {}
    lookup_type = request.GET.get('lookup-type', 0)
    lookup_value = request.GET.get('item', 0)
    item_code = get_unencoded_item_code(lookup_value, lookup_type)
    try:
        blend_restriction = BlendTankRestriction.objects.get(item_code__iexact=item_code)
    except Exception as e:
        response = { 'result' : str(e) }
    
    if not response:
        response = { 'blend_restriction' : blend_restriction } 

    return JsonResponse(response, safe=False)

def get_json_all_blend_qtyperbill(request):
    """Get JSON response containing blend quantities per bill.
    
    Retrieves all blend bill of materials records and returns a JSON mapping of
    item codes to their adjusted quantities per bill (quantity * foam factor).
    
    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing:
            Dict mapping item codes to adjusted quantities per bill
    """
    blend_bills_of_materials = BillOfMaterials.objects \
        .filter(component_item_description__startswith='BLEND')

    response = { item.item_code : item.qtyperbill * item.foam_factor for item in blend_bills_of_materials }

    return JsonResponse(response, safe=False)

def get_tote_classification_data(request):
    """Return blend container classifications indexed by item code."""
    classifications = (
        BlendContainerClassification.objects
        .all()
        .values('item_code', 'tote_classification', 'hose_color', 'tank_classification')
    )

    response = {}
    for entry in classifications:
        item_code = (entry['item_code'] or '').strip()
        if not item_code:
            continue

        tote_classification = (entry['tote_classification'] or '').strip()
        hose_color = (entry['hose_color'] or '').strip()
        tank_classification = (entry['tank_classification'] or '').strip()

        payload = {
            'tote_classification': tote_classification,
            'hose_color': hose_color,
            'tank_classification': tank_classification,
        }

        response[item_code] = payload
        response.setdefault(item_code.upper(), payload)

    return JsonResponse(response)

def get_daily_tank_values(request):
    """Get the last tank level entry for each day over a specified period.
    
    Retrieves the most recent tank level reading for each day over the past N days
    for a specified tank. Orders results with most recent entries first.

    Args:
        request: HTTP request object
        tank_name (str): Tank identifier (default 'L')
        days (int): Number of days to look back (default 30)

    Returns:
        JsonResponse containing list of daily tank readings
    """

    sql = """
        WITH daily_last_entries AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY DATE(timestamp) ORDER BY timestamp DESC) as rn
            FROM core_tanklevellog ct 
            WHERE tank_name = %s
            AND timestamp >= CURRENT_DATE - INTERVAL '%s days'
        )
        SELECT * FROM daily_last_entries 
        WHERE rn = 1
        ORDER BY timestamp DESC;
    """

    # Get tank name and days parameters from request, with defaults
    tank_name = request.GET.get('tank_name')
    days = request.GET.get('days', 30)
    
    with connection.cursor() as cursor:
        cursor.execute(sql, [tank_name, days])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
        
    return JsonResponse({'tank_readings': results})


@login_required
@require_http_methods(["GET", "POST"])
def get_projected_production_datetime(request):
    """Return when a given number of production hours will land on the calendar.

    Query params / form fields:
        - production_hours (required): float number of production hours to project.
        - start_datetime (optional): ISO datetime string to use as the baseline. Defaults to now.
        - Holidays are loaded from ProductionHoliday table (active rows only).
    """

    data_source = request.POST if request.method == 'POST' else request.GET
    hours_raw = (data_source.get('production_hours') or data_source.get('hours') or '').strip()

    if not hours_raw:
        return JsonResponse({'error': 'production_hours is required'}, status=400)

    try:
        production_hours = float(hours_raw)
    except ValueError:
        return JsonResponse({'error': 'production_hours must be numeric'}, status=400)

    start_raw = (data_source.get('start_datetime') or '').strip()
    start_dt = None
    if start_raw:
        parsed_start = parse_datetime(start_raw)
        if not parsed_start:
            try:
                parsed_start = dt.datetime.fromisoformat(start_raw)
            except ValueError:
                return JsonResponse({'error': 'start_datetime must be ISO-8601 formatted'}, status=400)
        start_dt = parsed_start

    try:
        baseline = project_datetime_from_production_hours(0, start=start_dt)
        projected = project_datetime_from_production_hours(production_hours, start=start_dt)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    tz = timezone.get_current_timezone()
    holiday_dates = list(ProductionHoliday.objects.filter(active=True).values_list('date', flat=True))

    payload: Dict = {
        'production_hours_requested': production_hours,
        'baseline_start_datetime': baseline.isoformat(),
        'projected_datetime': projected.isoformat(),
        'projected_date': projected.date().isoformat(),
        'projected_time': projected.time().strftime('%H:%M'),
        'timezone': str(tz),
        'business_rules': {
            'production_window': {'start': '06:00', 'end': '15:00'},
            'daily_production_hours': 9,
            'excluded_weekdays': ['Friday', 'Saturday', 'Sunday'],
            'holidays_active': [d.isoformat() for d in holiday_dates],
        },
    }

    return JsonResponse(payload)


@login_required
@require_GET
def get_json_blend_shortage_times(request):
    """
    Return shortage timing data for the given blend area.

    Response shape:
        {
            "area": "<Desk_1|Desk_2|LET_Desk|Hx|Dm|Totes>",
            "shortages": [ {blend_id: (hourshort, cumulative_qty)}, ... ]
        }
    """
    area = request.GET.get('area')
    if not area:
        return JsonResponse({'error': 'area query parameter is required'}, status=400)

    querysets = get_blend_schedule_querysets()
    if area not in querysets:
        return JsonResponse(
            {'error': f'Unknown area \"{area}\"', 'valid_areas': list(querysets.keys())},
            status=400,
        )

    queryset = querysets[area]
    shortage_results = calculate_shortage_times(queryset, area)

    serialized = []
    for result in shortage_results:
        blend_id, (hourshort, cumulative_qty) = next(iter(result.items()))
        if hasattr(hourshort, 'isoformat'):
            hourshort = hourshort.isoformat()
        if isinstance(cumulative_qty, Decimal):
            cumulative_qty = float(cumulative_qty)
        serialized.append({blend_id: (hourshort, cumulative_qty)})

    return JsonResponse({'area': area, 'shortages': serialized})


def _require_staff(user):
    return user.is_staff or user.is_superuser


def _parse_json_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return None
    return None


def _parse_boolean(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    string_value = str(value).strip().lower()
    if string_value in {'1', 'true', 't', 'yes', 'y', 'on'}:
        return True
    if string_value in {'0', 'false', 'f', 'no', 'n', 'off'}:
        return False
    return None


@login_required
@require_GET
def get_json_production_holidays(request):
    if not _require_staff(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    include_inactive = str(request.GET.get('include_inactive', '')).lower() in {'1', 'true', 'yes'}
    holidays = list_production_holidays(include_inactive=include_inactive)
    return JsonResponse({'status': 'success', 'holidays': holidays})


@login_required
@require_POST
def create_json_production_holiday(request):
    if not _require_staff(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    payload = _parse_json_payload(request) or request.POST
    date_raw = (payload.get('date') or '').strip()
    description = (payload.get('description') or '').strip()
    active_val = payload.get('active', True)
    active = _parse_boolean(active_val)
    if active is None:
        active = True

    try:
        parsed_date = dt.date.fromisoformat(date_raw)
    except ValueError:
        return JsonResponse({'status': 'error', 'error': 'date must be YYYY-MM-DD'}, status=400)

    try:
        holiday_data = create_production_holiday(date=parsed_date, description=description, active=active)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    return JsonResponse({'status': 'success', 'holiday': holiday_data})


@login_required
@require_http_methods(["POST", "PUT"])
def update_json_production_holiday(request, holiday_id):
    if not _require_staff(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    payload = _parse_json_payload(request) or request.POST
    date_raw = payload.get('date')
    description = payload.get('description')
    active_val = payload.get('active')

    parsed_date = None
    if date_raw is not None:
        try:
            parsed_date = dt.date.fromisoformat(str(date_raw).strip())
        except ValueError:
            return JsonResponse({'status': 'error', 'error': 'date must be YYYY-MM-DD'}, status=400)

    active = _parse_boolean(active_val)

    try:
        holiday_data = update_production_holiday(
            holiday_id,
            date=parsed_date,
            description=description.strip() if isinstance(description, str) else description,
            active=active,
        )
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    return JsonResponse({'status': 'success', 'holiday': holiday_data, 'holiday_id': holiday_id})


@login_required
@require_http_methods(["POST", "DELETE"])
def delete_json_production_holiday(request, holiday_id):
    if not _require_staff(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        delete_production_holiday(holiday_id)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=404)

    return JsonResponse({'status': 'success', 'holiday_id': holiday_id})


@login_required
@require_GET
def get_json_desk_labor_rates(request):
    """List all desk labor rates (staff-only)."""
    if not _require_staff(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    rates = [
        {
            'id': rate.id,
            'desk_name': rate.desk_name,
            'hourly_rate': float(rate.hourly_rate),
            'updated_at': rate.updated_at.isoformat() if rate.updated_at else None,
            'updated_by': rate.updated_by.get_username() if rate.updated_by else None,
        }
        for rate in DeskLaborRate.objects.order_by('desk_name')
    ]

    return JsonResponse({'status': 'success', 'rates': rates})


@login_required
@require_POST
def update_json_desk_labor_rate(request):
    """Create or update a desk labor rate (staff-only)."""
    if not _require_staff(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    payload = _parse_json_payload(request) or request.POST
    desk_name = (payload.get('desk_name') or '').strip()
    hourly_rate_raw = (payload.get('hourly_rate') or '').strip()

    if not desk_name:
        return JsonResponse({'error': 'desk_name is required'}, status=400)

    try:
        hourly_rate = Decimal(hourly_rate_raw)
    except (InvalidOperation, ValueError):
        return JsonResponse({'error': 'hourly_rate must be numeric'}, status=400)

    if hourly_rate < 0:
        return JsonResponse({'error': 'hourly_rate must be non-negative'}, status=400)

    rate_obj, _created = DeskLaborRate.objects.get_or_create(desk_name=desk_name)
    rate_obj.hourly_rate = hourly_rate
    rate_obj.updated_by = request.user
    rate_obj.save(update_fields=['hourly_rate', 'updated_by', 'updated_at'])

    return JsonResponse({
        'status': 'success',
        'rate': {
            'id': rate_obj.id,
            'desk_name': rate_obj.desk_name,
            'hourly_rate': float(rate_obj.hourly_rate),
            'updated_at': rate_obj.updated_at.isoformat() if rate_obj.updated_at else None,
            'updated_by': rate_obj.updated_by.get_username() if rate_obj.updated_by else None,
        }
    })

@csrf_exempt
def validate_blend_item(request):
    """Validate a provided item code, ensuring it exists and starts with BLEND- or CHEM-."""
    if request.method == 'POST':
        item_code = request.POST.get('item_code', '').strip()
        if not item_code:
            return JsonResponse({'valid': False, 'error': 'No item code provided.'})

        item = CiItem.objects.filter(itemcode__iexact=item_code).first()
        if item and (item.itemcodedesc.upper().startswith('BLEND-') or
                    item.itemcodedesc.upper().startswith('CHEM')):
            return JsonResponse({'valid': True, 'item_description': item.itemcodedesc})
        else:
            return JsonResponse({'valid': False, 'error': 'Item not found or not a valid BLEND/CHEM code.'})

    return JsonResponse({'valid': False, 'error': 'Invalid request method.'})


@login_required
@require_http_methods(["GET", "POST"])
def get_json_cost_impact_analysis(request):
    """Analyze how raw material cost changes impact BLENDs and finished goods."""
    data_source = request.POST if request.method == "POST" else request.GET
    warehouse = (data_source.get("warehouse") or "MTG").strip().upper() or "MTG"
    limit_param = (data_source.get("limit") or "500").strip()

    try:
        limit = int(limit_param)
        limit = min(max(limit, 1), 1000)
    except ValueError:
        return JsonResponse({"error": "limit must be an integer"}, status=400)

    # Load purchasing costs with both est_landed and next_cost
    pricing_label = "Standard costs only"
    uploaded_file = None

    if request.method == "POST" and request.FILES.get("cost_override"):
        uploaded_file = request.FILES["cost_override"]

    try:
        purchasing_costs, workbook_name = load_purchasing_costs_with_both_values(uploaded_file)
    except PurchasingCostParseError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    if workbook_name:
        if uploaded_file:
            pricing_label = f"Uploaded workbook ({workbook_name})"
        else:
            pricing_label = f"Server workbook ({workbook_name})"

    if not purchasing_costs:
        return JsonResponse({
            "error": "No purchasing costs available. Please upload a workbook or configure server workbook path."
        }, status=400)

    started = time.perf_counter()

    # Perform cost impact analysis
    result = analyze_cost_impacts(
        purchasing_costs=purchasing_costs,
        warehouse=warehouse,
        limit=limit
    )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

    # Build response payload
    payload = {
        'warehouse': warehouse,
        'pricingSource': pricing_label,
        'elapsedMs': elapsed_ms,
        'summary': result.summary,
        'rawMaterialChanges': [
            {
                'itemCode': item['item_code'],
                'itemDescription': item['item_description'],
                'currentCost': float(item['current_cost']),
                'nextCost': float(item['next_cost']),
                'delta': float(item['delta']),
                'pctChange': float(item['pct_change']),
            }
            for item in result.raw_material_changes
        ],
        'affectedBlends': result.affected_blends,
        'affectedFinishedGoods': result.affected_finished_goods,
        'salesOrderImpacts': result.sales_order_impacts,
    }

    return JsonResponse(payload)


def _user_in_group(user, group_name):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return user.groups.filter(name__iexact=group_name).exists()


def _user_display(user):
    if not user:
        return None
    full_name = user.get_full_name()
    return full_name or user.get_username()


def _sampling_personnel_display(tote):
    sampling_name = getattr(tote, 'sampling_personnel_name', None)
    if sampling_name:
        return sampling_name
    return _user_display(tote.sampling_personnel)


def _serialize_flush_tote_reading(tote):
    return {
        'id': tote.id,
        'date': tote.date.isoformat() if tote.date else None,
        'discharge_source': tote.discharge_source,
        'production_line': tote.discharge_source,
        'flush_type': tote.flush_type,
        'initial_pH': _safe_float(tote.initial_pH),
        'action_required': tote.action_required or '',
        'final_pH': _safe_float(tote.final_pH),
        'final_disposition': tote.final_disposition,
        'lab_technician_id': tote.lab_technician_id,
        'lab_technician_name': _user_display(tote.lab_technician),
        'sampling_personnel_id': tote.sampling_personnel_id,
        'sampling_personnel_name': _sampling_personnel_display(tote),
    }


def _parse_flush_tote_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        payload = _parse_json_payload(request)
        if payload is None:
            raise ValueError('Invalid JSON payload.')
        return payload
    return request.POST.dict()


def _validation_error_payload(exc):
    if hasattr(exc, 'message_dict'):
        return exc.message_dict
    return {'error': exc.messages}


@login_required
@require_http_methods(["GET", "POST"])
def discharge_testing_list_api(request):
    if request.method == "GET":
        limit_param = (request.GET.get("limit") or "").strip()
        limit = None
        if limit_param:
            try:
                parsed = int(limit_param)
                if parsed < 1:
                    raise ValueError
                limit = min(parsed, 1000)
            except ValueError:
                return JsonResponse({"error": "limit must be a positive integer"}, status=400)

        totes = list_discharge_tests(limit=limit)
        return JsonResponse(
            {
                'status': 'success',
                'totes': [_serialize_flush_tote_reading(tote) for tote in totes],
            }
        )

    try:
        payload = _parse_flush_tote_payload(request)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    discharge_source = (payload.get('discharge_source') or payload.get('production_line') or '').strip()
    flush_type = (payload.get('flush_type') or '').strip()
    final_disposition = (payload.get('final_disposition') or '').strip()
    sampling_personnel_name = (payload.get('sampling_personnel_name') or '').strip()
    initial_ph = payload.get('initial_pH')
    action_required = payload.get('action_required')
    final_ph = payload.get('final_pH')

    try:
        tote = create_discharge_test(
            discharge_source=discharge_source,
            flush_type=flush_type,
            final_disposition=final_disposition,
            sampling_personnel_name=sampling_personnel_name,
            user=request.user,
            initial_pH=initial_ph,
            action_required=action_required,
            final_pH=final_ph,
        )
    except ValidationError as exc:
        return JsonResponse({'status': 'error', 'errors': _validation_error_payload(exc)}, status=400)

    return JsonResponse(
        {
            'status': 'success',
            'tote': _serialize_flush_tote_reading(tote),
        },
        status=201,
    )


@login_required
@require_http_methods(["PATCH", "PUT"])
def discharge_testing_detail_api(request, pk):
    try:
        payload = _parse_flush_tote_payload(request)
    except ValueError as exc:
        return JsonResponse({'status': 'error', 'error': str(exc)}, status=400)

    if not payload:
        return JsonResponse({'status': 'error', 'error': 'No update fields provided.'}, status=400)

    try:
        tote = get_discharge_test(pk)
    except Exception:
        return JsonResponse({'status': 'error', 'error': 'Flush tote not found.'}, status=404)

    is_admin = request.user.is_staff or request.user.is_superuser
    is_line = is_admin or _user_in_group(request.user, GROUP_LINE_PERSONNEL)
    is_lab = is_admin or _user_in_group(request.user, GROUP_LAB_TECHNICIAN)

    line_fields = {'discharge_source', 'production_line', 'flush_type'}
    lab_fields = {'initial_pH', 'final_pH', 'action_required'}

    requested_line_fields = line_fields.intersection(payload.keys())
    requested_lab_fields = lab_fields.intersection(payload.keys())

    if requested_line_fields and not is_line:
        return JsonResponse({'status': 'error', 'error': 'Forbidden'}, status=403)
    if requested_lab_fields and not is_lab:
        return JsonResponse({'status': 'error', 'error': 'Forbidden'}, status=403)
    if not requested_line_fields and not requested_lab_fields:
        return JsonResponse({'status': 'error', 'error': 'No valid fields supplied.'}, status=400)

    try:
        if requested_line_fields:
            updated_fields = []
            if 'discharge_source' in requested_line_fields or 'production_line' in requested_line_fields:
                tote.discharge_source = (
                    payload.get('discharge_source') or payload.get('production_line') or ''
                ).strip()
                updated_fields.append('discharge_source')
            if 'flush_type' in requested_line_fields:
                tote.flush_type = (payload.get('flush_type') or '').strip()
                updated_fields.append('flush_type')

            tote.full_clean()
            tote.save(update_fields=updated_fields)

        if 'initial_pH' in requested_lab_fields:
            tote = record_discharge_initial_ph(tote, ph_value=payload.get('initial_pH'), user=request.user)

        if 'final_pH' in requested_lab_fields:
            tote = record_discharge_action_and_final_ph(
                tote,
                action_text=payload.get('action_required'),
                final_ph=payload.get('final_pH'),
                user=request.user,
            )
        elif 'action_required' in requested_lab_fields:
            tote.action_required = (payload.get('action_required') or '').strip()
            tote.full_clean()
            tote.save(update_fields=['action_required'])

    except ValidationError as exc:
        return JsonResponse({'status': 'error', 'errors': _validation_error_payload(exc)}, status=400)

    return JsonResponse(
        {
            'status': 'success',
            'tote': _serialize_flush_tote_reading(tote),
        }
    )
