import base64
import logging
import math
import datetime as dt
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from bs4 import BeautifulSoup
from urllib.parse import quote
import socket
import urllib.error
import urllib.parse
import urllib.request

from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Sum, Max, OuterRef, Subquery, Exists, F
from django.db.models.functions import Upper

from core.kpkapp_utils.dates import count_weekend_days, calculate_production_hours
from core.models import (
    BillOfMaterials,
    BlendProtection,
    BlendComponentCountRecord,
    BlendCountRecord,
    CiItem,
    ComponentShortage,
    ComponentUsage,
    DeskOneSchedule,
    DeskTwoSchedule,
    ImItemTransactionHistory,
    ImItemWarehouse,
    LotNumRecord,
    PoPurchaseOrderDetail,
    TankLevel,
    SubComponentShortage,
    SubComponentUsage,
    TankLevelLog,
    StorageTank,
    TimetableRunData,
    WeeklyBlendTotals,
)
from core.selectors.lot_numbers_selectors import get_lot_number_quantities
from core.services.production_planning_services import (
    get_component_consumption,
    get_relevant_blend_runs,
    get_relevant_item_runs,
    calculate_new_shortage,
)
from core.services.blend_scheduling_services import advance_blends
from core.services.tank_levels_services import extract_all_tank_levels
from prodverse.models import WarehouseCountRecord
import pytz

logger = logging.getLogger(__name__)

_MISC_REPORT_DEFINITIONS = [
    {
        'slug': 'Transaction-History',
        'label': 'Transaction History',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Lot-Numbers',
        'label': 'Lot Numbers',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'All-Upcoming-Runs',
        'label': 'All Upcoming Runs',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Startron-Runs',
        'label': 'Startron Runs',
        'requires_item': False,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Count-History',
        'label': 'Count History',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Counts-And-Transactions',
        'label': 'Counts And Transactions',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Where-Used',
        'label': 'Where Used',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Max-Producible-Quantity',
        'label': 'Max Producible Quantity',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Purchase-Orders',
        'label': 'Purchase Orders',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Bill-Of-Materials',
        'label': 'Bill Of Materials',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Blend-What-If',
        'label': 'Blend What-If',
        'requires_item': True,
        'requires_quantity': True,
        'requires_start_time': True,
    },
    {
        'slug': 'Item-Component-What-If',
        'label': 'Item Component What-If',
        'requires_item': True,
        'requires_quantity': True,
        'requires_start_time': True,
    },
    {
        'slug': 'Component-Usage-For-Scheduled-Blends',
        'label': 'Component Usage For Scheduled Blends',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'Startron-Component-Coverage',
        'label': 'Startron Component Coverage (100433/100507TANKO)',
        'requires_item': False,
        'requires_quantity': False,
        'requires_start_time': False,
        'direct_url': '/core/component-stock-coverage/',
    },
    {
        'slug': 'Transaction-Mismatches',
        'label': 'Transaction Mismatches',
        'requires_item': True,
        'requires_quantity': False,
        'requires_start_time': False,
    },
    {
        'slug': 'BOM-Cost-Tool',
        'label': 'BOM Cost Estimator',
        'requires_item': False,
        'requires_quantity': False,
        'requires_start_time': False,
        'direct_url': '/core/bom-cost-tool/',
    },
    {
        'slug': 'Sales-Order-BOM-Cost',
        'label': 'Sales Order vs BOM Cost',
        'requires_item': False,
        'requires_quantity': False,
        'requires_start_time': False,
        'direct_url': '/core/sales-order-vs-bom-cost/',
    },
    {
        'slug': 'Blend-Protection-Audit',
        'label': 'Blend Protection Audit',
        'requires_item': False,
        'requires_quantity': False,
        'requires_start_time': False,
        'direct_url': '/core/blend-protection-audit/',
    },
    {
        'slug': 'Blend-Timestudy-Report',
        'label': 'Blend Timestudy Report',
        'requires_item': False,
        'requires_quantity': False,
        'requires_start_time': False,
        'direct_url': '/core/timestudies/report/',
    },
]

def get_active_blends_missing_blend_protection():
    """
    Return blends that have transaction history but no entry in blend_protection.
    A blend is identified by a bill_of_materials description starting with 'BLEND'.
    """
    try:
        active_items = list(ImItemTransactionHistory.objects.all().values_list('itemcode', flat=True))
        ci_blends = list(CiItem.objects.filter(itemcodedesc__istartswith='BLEND').values_list('itemcode', flat=True))
        active_blends = list(set(active_items) & set(ci_blends))
        blend_items = list(BlendProtection.objects.all().values_list('item_code', flat=True))
        missing_blends = list(set(active_blends) - set(blend_items))
        
        # Get CI_Item descriptions for missing blends
        missing_blends_with_desc = []
        if missing_blends:
            ci_items = CiItem.objects.filter(itemcode__in=missing_blends).values('itemcode', 'itemcodedesc')
            ci_items_dict = {item['itemcode']: item['itemcodedesc'] for item in ci_items}
            
            for item_code in missing_blends:
                missing_blends_with_desc.append({
                    'item_code': item_code,
                    'item_description': ci_items_dict.get(item_code, '')
                })
        
        missing_blends = missing_blends_with_desc

        # Remove specific item codes from the missing blends list
        items_to_ignore = {'26214.B', '26000.BCITGO', 'PK303000.B', '26000.B', '303000.B', '301000.B', '302000.B'}
        missing_blends = [
            blend for blend in missing_blends 
            if blend['item_code'] not in items_to_ignore
        ]

        return missing_blends

    except Exception as exc:
        logger.error("Failed to fetch blends missing blend_protection: %s", exc)
        return []


def get_uv_freeze_sheet_unmatched():
    """
    Return entries from specsheet_uv_freeze_missing if the table exists.
    """
    query = """
        SELECT
            item_code,
            description,
            uv_protection,
            freeze_protection,
            sheet_refreshed_at
        FROM specsheet_uv_freeze_missing
        ORDER BY item_code;
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.warning("specsheet_uv_freeze_missing not available: %s", exc)
        return []


def get_misc_report_definitions():
    """Return metadata describing the available miscellaneous reports."""
    return [definition.copy() for definition in _MISC_REPORT_DEFINITIONS]

def generate_lot_numbers_report(request, item_code):
    try:
        no_lots_found = False
        lot_num_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created', '-lot_number')
        if lot_num_queryset.exists():
            item_description = lot_num_queryset.first().item_description
        lot_num_paginator = Paginator(lot_num_queryset, 150)
        page_num = request.GET.get('page')
        current_page = lot_num_paginator.get_page(page_num)
        lot_number_quantities = get_lot_number_quantities(item_code)
        for lot in current_page:
            this_lot_number = lot_number_quantities.get(lot.lot_number,('',''))
            lot.qty_on_hand = this_lot_number[0]
            lot.date_entered = this_lot_number[1]

        blend_info = {'item_code' : item_code, 'item_description' : item_description}

        render_payload = {
            'template_string' : 'core/reports/lotnumsreport.html',
            'context' : {'no_lots_found' : no_lots_found, 'current_page' : current_page, 'blend_info': blend_info}
        }

        return render_payload

    except Exception as e:
        logger.error(f"Unexpected error generating lot numbers report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_all_upcoming_runs_report(item_code):
    try:
        no_runs_found = False
        report_type = ''
        this_bill = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first()
        component_prefixes = ['BLEND','BLISTER','ADAPTER','APPLICATOR','BAG','BAIL','BASE','BILGE PAD','BOTTLE',
            'CABLE TIE','CAN','CAP','CARD','CARTON','CLAM','CLIP','COLORANT',
            'CUP','DISPLAY','DIVIDER','DRUM','ENVELOPE','FILLED BOTTLE','FILLER',
            'FLAG','FUNNEL','GREASE','HANGER','HEADER','HOLDER','HOSE','INSERT',
            'JAR','LABEL','LID','PAD','PAIL','PLUG','POUCH','PUTTY STICK','RESIN',
            'SCOOT','SEAL DISC','SLEEVE','SPONGE','STRIP','SUPPORT','TOILET PAPER',
            'TOOL','TOTE','TRAY','TUB','TUBE','WINT KIT','WRENCH','REBATE',
            'RUBBERBAND']
        subcomponent_prefixes = ['CHEM','DYE','FRAGRANCE']
        starbrite_item_codes = ['080100UN','080116UN','081318UN','081816PUN','082314UN',
            '082708PUN','083416UN','083821UN','083823UN','085700UN','085716PUN','085732UN',
            '087208UN','087308UN','087516UN','089600UN','089616PUN','089632PUN']
        if any(this_bill.component_item_description.startswith(prefix) for prefix in component_prefixes) or item_code in starbrite_item_codes:
            upcoming_runs = ComponentUsage.objects.filter(component_item_code__iexact=item_code).order_by('start_time')
            report_type = 'Component'
        else:
            upcoming_runs = SubComponentUsage.objects.filter(subcomponent_item_code__iexact=item_code).order_by('start_time')
            report_type = 'SubComponent'
        if upcoming_runs.exists():
            item_description = upcoming_runs.first().component_item_description
        else:
            no_runs_found = True
        item_info = {
                'item_code' : item_code, 
                'item_description' : this_bill.component_item_description, 
                'standard_uom' : this_bill.standard_uom
                }
        context = {
            'report_type' : report_type,
            'no_runs_found' : no_runs_found,
            'upcoming_runs' : upcoming_runs,
            'item_info' : item_info
        }
        render_payload = {
            'template_string' : 'core/reports/upcomingrunsreport/upcomingrunsreport.html',
            'context' : context
        }

    except Exception as e:
        logger.error(f"Unexpected error generating all upcoming runs report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }

    return render_payload

def generate_startron_runs_report():
    try:
        startron_item_codes = ['14000.B', '14308.B', '14308AMBER.B', '93100DSL.B', '93100GAS.B', '93100XBEE.B', '93100TANK.B', '93100GASBLUE.B', '93100GASAMBER.B']
        startron_runs = TimetableRunData.objects.filter(component_item_code__in=startron_item_codes)
        render_payload = {
            'template_string' : 'core/reports/startronreport.html',
            'context' : {'startron_runs' : startron_runs}
        }
        return render_payload
    except Exception as e:
        logger.error(f"Unexpected error generating startron runs report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_transaction_history_report(request, item_code):
    try:
        transaction_codes_param = request.GET.get('transactionCodes') if request else None
        entry_no_param = request.GET.get('entryNo') if request else None
        transaction_code_filters = []
        if transaction_codes_param:
            transaction_code_filters = [
                code.strip().upper()
                for code in transaction_codes_param.split(',')
                if code.strip()
            ]

        ci_item = CiItem.objects.filter(itemcode=item_code).first()
        item_description = ci_item.itemcodedesc if ci_item else ''

        no_transactions_found = False
        transactions_qs = ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code)

        if transaction_code_filters:
            transactions_qs = transactions_qs.filter(transactioncode__in=transaction_code_filters)

        if entry_no_param:
            transactions_qs = transactions_qs.filter(entryno=entry_no_param.strip())

        if transactions_qs.exists():
            transactions_list = transactions_qs.order_by('-transactiondate')
        else:
            no_transactions_found = True
            transactions_list = []

        if transaction_code_filters and not transactions_list:
            no_transactions_found = True

        for item in transactions_list:
            item.item_description = item_description
        item_info = {'item_code' : item_code, 'item_description' : item_description}
        render_payload = {
            'template_string' : 'core/reports/transactionsreport.html',
            'context' : {
                'no_transactions_found' : no_transactions_found,
                'transactions_list' : transactions_list,
                'item_info': item_info,
                'applied_transaction_codes': transaction_code_filters,
            }
        }
        return render_payload
        
    except Exception as e:
        logger.error(f"Unexpected error generating transaction history report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_count_history_report(item_code):
    try:
        counts_not_found = False
        if BlendCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendCountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
        elif BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
        else:
            counts_not_found = True
            count_records = {}
        
        item_info = {'item_code' : item_code,
                    'item_description' : BillOfMaterials.objects \
                        .filter(component_item_code__iexact=item_code) \
                        .first().component_item_description
                    }
        context = {'counts_not_found' : counts_not_found,
            'blend_count_records' : count_records,
            'item_info' : item_info
            }
        render_payload = {
            'template_string' : 'core/reports/inventorycountsreport.html',
            'context' : context
        }
        return render_payload
    
    except Exception as e:
        logger.error(f"Unexpected error generating count history report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_counts_and_transactions_report(item_code):
    try:
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        current_onhand_quantity = ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(warehousecode__iexact='MTG').first().quantityonhand
        
        if BlendCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendCountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(count_records):
                count.count_order = str(order) + "counts"
        elif BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = BlendComponentCountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(count_records):
                count.count_order = str(order) + "counts"
        elif WarehouseCountRecord.objects.filter(item_code__iexact=item_code).exists():
            count_records = WarehouseCountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
            standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
            for order, count in enumerate(count_records):
                count.count_order = str(order) + "counts"
        else:
            counts_not_found = True
            count_records = {}
        if ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).exists():
            transactions_list = ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).order_by('-transactiondate')
            for order, count in enumerate(transactions_list):
                count.transaction_order = str(order) + "txns"
        else:
            no_transactions_found = True
            transactions_list = {}
        counts_and_transactions = {}
        for iteration, item in enumerate(count_records):
            item.iteration = iteration
            item.ordering_date = str(item.counted_date) + 'b' + str(item.iteration)
            counts_and_transactions[item.ordering_date] = item
            item.transactioncode = 'Count'
            print(count for count in counts_and_transactions)
        for iteration, item in enumerate(transactions_list):
            item.iteration = iteration
            item.ordering_date = str(item.transactiondate) + 'a' + str(item.iteration)
            counts_and_transactions[item.ordering_date] = item
        count_and_txn_keys = list(counts_and_transactions.keys())
        count_and_txn_keys.sort()
        count_and_txn_keys.reverse()
        counts_and_transactions_list = []
        for item in count_and_txn_keys:
            counts_and_transactions_list.append(counts_and_transactions[item])

        item_info = {'item_code' : item_code,
                    'item_description' : item_description
                    }
        context = {'counts_and_transactions_list' : counts_and_transactions_list,
            'item_info' : item_info,
            'current_onhand_quantity' : current_onhand_quantity
        }
        render_payload = {
            'template_string' : 'core/reports/countsandtransactionsreport.html',
            'context' : context
        }
        return render_payload
    except Exception as e:
        logger.error(f"Unexpected error generating counts and transactions report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload
    
def generate_where_used_report(item_code):
    try:
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        all_bills_where_used = BillOfMaterials.objects.filter(component_item_code__iexact=item_code)
        item_info = {'item_code' : item_code,
                    'item_description' : item_description
                    }
        context = {'all_bills_where_used' : all_bills_where_used,
            'item_info' : item_info
            }
        render_payload = {
            'template_string' : 'core/reports/whereusedreport.html',
            'context' : context
        }
        return render_payload

    except Exception as e:
        logger.error(f"Unexpected error generating where used report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_purchase_orders_report(item_code):
    try:
        bill_record = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first()

        item_description = bill_record.component_item_description if bill_record else ''
        standard_uom = bill_record.standard_uom if bill_record else ''

        two_days_ago = dt.date.today() - dt.timedelta(days=2)
        orders_not_found = False
        procurementtype = bill_record.procurementtype if bill_record else None

        if procurementtype != 'M':
            all_purchase_orders_qs = PoPurchaseOrderDetail.objects \
                .filter(itemcode__iexact=item_code) \
                .filter(requireddate__gte=two_days_ago) \
                .order_by('requireddate', 'purchaseorderno')
        else:
            orders_not_found = True
            all_purchase_orders_qs = PoPurchaseOrderDetail.objects.none()

        purchase_orders = list(all_purchase_orders_qs)

        if not purchase_orders:
            orders_not_found = True

        encoded_item_code = ''
        if item_code:
            encoded_item_code = quote(base64.b64encode(str(item_code).encode()).decode())

        def _normalize(value):
            return (value or '').strip().upper()

        receipt_lookup = defaultdict(list)

        if purchase_orders:
            po_numbers_raw = {po.purchaseorderno for po in purchase_orders if po.purchaseorderno}
            if po_numbers_raw:
                receipt_transactions = ImItemTransactionHistory.objects.filter(
                    itemcode__iexact=item_code,
                    transactioncode__in=['PO'],
                    transactionqty__gt=0,
                    receipthistorypurchaseorderno__in=po_numbers_raw
                ).order_by('transactiondate', 'entryno')

                for receipt in receipt_transactions:
                    key = (
                        _normalize(receipt.receipthistorypurchaseorderno),
                        _normalize(receipt.itemcode)
                    )
                    receipt_lookup[key].append(receipt)

        for detail in purchase_orders:
            po_key = (_normalize(detail.purchaseorderno), _normalize(detail.itemcode))
            matching_receipts = receipt_lookup.get(po_key, [])
            sorted_receipts = sorted(
                matching_receipts,
                key=lambda r: (
                    r.transactiondate or dt.date.max,
                    r.entryno or ''
                )
            )

            receipt_info = []
            receipt_dates = []
            total_receipt_qty = Decimal('0')

            for receipt in sorted_receipts:
                entry_number = (receipt.entryno or '').strip()
                transaction_date = receipt.transactiondate
                if transaction_date:
                    receipt_dates.append(transaction_date)
                receipt_quantity = Decimal(receipt.transactionqty or 0)
                total_receipt_qty += receipt_quantity

                transaction_url = ''
                if encoded_item_code and entry_number:
                    transaction_url = (
                        f"/core/create-report/Transaction-History?"
                        f"itemCode={encoded_item_code}&transactionCodes=PO&entryNo={quote(entry_number)}"
                    )

                receipt_info.append({
                    'entryno': entry_number,
                    'transactiondate': transaction_date,
                    'transactionqty': receipt_quantity,
                    'warehousecode': receipt.warehousecode,
                    'transaction_url': transaction_url,
                })

            earliest_receipt = min(receipt_dates) if receipt_dates else None
            latest_receipt = max(receipt_dates) if receipt_dates else None

            received_before_required = any(
                transaction_date and detail.requireddate and transaction_date < detail.requireddate
                for transaction_date in receipt_dates
            )

            ordered_qty = detail.quantityordered if detail.quantityordered is not None else Decimal('0')
            received_qty = detail.quantityreceived if detail.quantityreceived is not None else Decimal('0')

            receipt_status = 'Open'
            if receipt_info:
                tolerance = Decimal('0.0001')
                if ordered_qty > 0 and received_qty + tolerance >= ordered_qty:
                    receipt_status = 'Complete'
                elif ordered_qty == 0 and total_receipt_qty > 0:
                    receipt_status = 'Received'
                else:
                    receipt_status = 'Partial'

            detail.receipt_transactions = receipt_info
            detail.earliest_receipt_date = earliest_receipt
            detail.latest_receipt_date = latest_receipt
            detail.received_before_required = received_before_required
            detail.receipt_status = receipt_status
            detail.total_receipt_qty = total_receipt_qty

        item_info = {
                    'item_code' : item_code,
                    'item_description' : item_description,
                    'standard_uom' : standard_uom
                    }
        context = {
            'orders_not_found' : orders_not_found,
            'all_purchase_orders' : purchase_orders,
            'item_info' : item_info
        }
        render_payload = {
            'template_string' : 'core/reports/purchaseordersreport.html',
            'context' : context
        }
        return render_payload
        
    except Exception as e:
        logger.error(f"Unexpected error generating purchase orders report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_bill_of_materials_report(item_code):
    try:
        these_bills = BillOfMaterials.objects.filter(item_code__iexact=item_code)
        for bill in these_bills:
            if bill.qtyonhand and bill.qtyperbill:
                bill.max_blend =  bill.qtyonhand / bill.qtyperbill
        item_info = {'item_code' : item_code,
                    'item_description' : these_bills.first().item_description
                    }
        context = {'these_bills' : these_bills, 'item_info' : item_info}

        render_payload = {
            'template_string' : 'core/reports/billofmaterialsreport.html',
            'context' : context
        }
        return render_payload

    except Exception as e:
        logger.error(f"Unexpected error generating bill of materials report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_max_producible_quantity_report(item_code):
    try:
        bom_queryset = BillOfMaterials.objects.exclude(component_item_code__startswith="/BLD").filter(item_code__iexact=item_code)

        if not bom_queryset.exists():
            item_instance = CiItem.objects.filter(itemcode__iexact=item_code).first()
            context = {
                'item_code': item_code,
                'item_description': item_instance.itemcodedesc if item_instance else '',
                'components': [],
                'has_components': False,
                'max_producible_quantity': 0,
                'limiting_factor': None,
                'limiting_factor_consumption': [],
                'next_shipment_date': None,
            }
            return {
                'template_string': 'core/reports/maxproduciblequantityreport.html',
                'context': context,
            }

        component_summaries = []
        max_producible_quantities = {}

        for bill in bom_queryset:
            component_code = bill.component_item_code
            if component_code == '030143':
                # Skip DI Water - treated as unlimited for max quantity calculations
                continue

            consumption_detail = get_component_consumption(component_code, item_code) or {}
            total_component_usage = float(consumption_detail.get('total_component_usage') or 0)
            qty_on_hand = float(bill.qtyonhand or 0)
            qty_per_bill = float(bill.qtyperbill or 0)

            available_after_orders = qty_on_hand - total_component_usage

            if qty_per_bill > 0:
                max_possible = math.floor(available_after_orders / qty_per_bill)
            else:
                max_possible = 0

            if max_possible < 0:
                max_possible = 0

            max_producible_quantities[component_code] = max_possible

            consumption_entries = []
            for blend_code, detail in consumption_detail.items():
                if blend_code == 'total_component_usage':
                    continue
                consumption_entries.append({
                    'blend_item_code': blend_code,
                    'blend_item_description': detail.get('blend_item_description'),
                    'blend_total_qty_needed': detail.get('blend_total_qty_needed'),
                    'blend_first_shortage': detail.get('blend_first_shortage'),
                    'component_usage': detail.get('component_usage'),
                })

            consumption_entries.sort(
                key=lambda entry: entry.get('blend_first_shortage') if entry.get('blend_first_shortage') is not None else float('inf')
            )

            component_summaries.append({
                'component_item_code': component_code,
                'component_item_description': bill.component_item_description,
                'qty_per_bill': bill.qtyperbill,
                'qty_on_hand': bill.qtyonhand,
                'standard_uom': bill.standard_uom,
                'available_after_orders': available_after_orders,
                'max_possible_blend_qty': max_possible,
                'total_component_usage': total_component_usage,
                'consumption_detail': consumption_entries,
            })

        component_summaries.sort(key=lambda component: component['max_possible_blend_qty'])

        limiting_factor = None
        next_shipment_date = None
        limiting_consumption_detail = []
        max_producible_quantity = 0

        if max_producible_quantities:
            limiting_code = min(max_producible_quantities, key=max_producible_quantities.get)
            limiting_summary = next((component for component in component_summaries if component['component_item_code'] == limiting_code), None)

            if limiting_summary:
                limiting_factor = {
                    'component_item_code': limiting_summary['component_item_code'],
                    'component_item_description': limiting_summary['component_item_description'],
                    'standard_uom': limiting_summary['standard_uom'],
                    'qty_on_hand': limiting_summary['qty_on_hand'],
                    'available_after_orders': limiting_summary['available_after_orders'],
                    'total_component_usage': limiting_summary['total_component_usage'],
                }
                limiting_consumption_detail = limiting_summary['consumption_detail']
                max_producible_quantity = limiting_summary['max_possible_blend_qty']

                yesterday = dt.datetime.now() - dt.timedelta(days=1)
                next_shipment = PoPurchaseOrderDetail.objects.filter(
                    itemcode__iexact=limiting_code,
                    quantityreceived__exact=0,
                    requireddate__gt=yesterday
                ).order_by('requireddate').first()

                if next_shipment:
                    next_shipment_date = next_shipment.requireddate

        context = {
            'item_code': item_code,
            'item_description': bom_queryset.first().item_description,
            'components': component_summaries,
            'has_components': bool(component_summaries),
            'max_producible_quantity': max_producible_quantity,
            'limiting_factor': limiting_factor,
            'limiting_factor_consumption': limiting_consumption_detail,
            'next_shipment_date': next_shipment_date,
        }

        return {
            'template_string': 'core/reports/maxproduciblequantityreport.html',
            'context': context,
        }
    except Exception as e:
        logger.error(f"Unexpected error generating max producible quantity report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_blend_what_if_report(request, item_code):
    try:
        blend_quantity = request.GET.get('itemQuantity')
        start_time = request.GET.get('startTime')
        blend_subcomponent_usage = get_relevant_blend_runs(item_code, blend_quantity, start_time)

        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
        subcomponent_item_codes_queryset = BillOfMaterials.objects \
                                        .filter(item_code__iexact=item_code) \
                                        .exclude(component_item_code__iexact='030143') \
                                        .exclude(component_item_code__startswith='/')

        # calculate the usage for each component and then 
        new_blend_run_components = []
        for bill in subcomponent_item_codes_queryset:
            subcomponent_item_code = bill.component_item_code
            subcomponent_item_description = subcomponent_item_codes_queryset.filter(component_item_code__iexact=subcomponent_item_code).first().component_item_description
            subcomponent_usage = float(subcomponent_item_codes_queryset.filter(component_item_code__iexact=subcomponent_item_code).first().qtyperbill) * float(blend_quantity)
            new_blend_run = {
                'component_item_code' : item_code,
                'component_item_description' : item_description,
                'subcomponent_item_code' : subcomponent_item_code,
                'subcomponent_item_description' : subcomponent_item_description,
                'start_time' : float(start_time),
                'prod_line' : 'N/A',
                'subcomponent_run_qty' : subcomponent_usage,
                'subcomponent_onhand_after_run' : 'N/A',
                'run_source' : 'new_blend_run'
            }
            new_blend_run_components.append(new_blend_run)

        # Combine, then sort the merged list by start_time
        blend_subcomponent_usage = blend_subcomponent_usage + new_blend_run_components
        blend_subcomponent_usage = sorted(blend_subcomponent_usage, key=lambda x: x['start_time'])
        render_payload = {
            'template_string' : 'core/reports/whatifblend.html',
            'context' : {'blend_subcomponent_usage' : blend_subcomponent_usage,
                         'item_code' : item_code,
                         'item_description' : item_description,
                         'blend_quantity' : blend_quantity,
                         'start_time' : start_time, 'new_blend_run_components' : new_blend_run_components}
        }
        return render_payload

    except Exception as e:
        logger.error(f"Unexpected error generating blend what-if report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_item_component_what_if_report(request, item_code):
    try:
        item_quantity = request.GET.get('itemQuantity')
        start_time = request.GET.get('startTime')
        item_component_usage = get_relevant_item_runs(item_code, item_quantity, start_time)

        item_description = CiItem.objects.filter(itemcode__iexact=item_code).first().itemcodedesc
        component_item_codes_queryset = BillOfMaterials.objects \
                                        .filter(item_code__iexact=item_code) \
                                        .exclude(component_item_code__startswith='/')

        # calculate the usage for each component and then 
        new_item_run_components = []
        for bill in component_item_codes_queryset:
            component_item_code = bill.component_item_code
            component_item_description = component_item_codes_queryset.filter(component_item_code__iexact=component_item_code).first().component_item_description
            component_usage = float(component_item_codes_queryset.filter(component_item_code__iexact=component_item_code).first().qtyperbill) * float(item_quantity)
            new_item_run = {
                'item_code' : item_code,
                'item_description' : item_description,
                'component_item_code' : component_item_code,
                'component_item_description' : component_item_description,
                'start_time' : float(start_time),
                'prod_line' : 'N/A',
                'run_component_qty' : component_usage,
                'component_onhand_after_run' : 'N/A',
                'run_source' : 'new_item_run'
            }
            new_item_run_components.append(new_item_run)

        # Combine, then sort the merged list by start_time
        item_component_usage = item_component_usage + new_item_run_components
        item_component_usage = sorted(item_component_usage, key=lambda x: x['start_time'])
        render_payload = {
            'template_string' : 'core/reports/whatifproductionitem.html',
            'context' : {'item_component_usage' : item_component_usage,
                         'item_code' : item_code,
                         'item_description' : item_description,
                         'item_quantity' : item_quantity,
                         'start_time' : start_time, 'new_item_run_components' : new_item_run_components}
        }
        return render_payload

    except Exception as e:
        logger.error(f"Unexpected error generating item component what-if report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def generate_component_usage_for_scheduled_blends_report(item_code):
    try:
        relevant_blend_item_codes = [item.item_code for item in BillOfMaterials.objects.filter(component_item_code__iexact=item_code).exclude(component_item_code__startswith='/')]
        component_onhandquantity = ImItemWarehouse.objects.filter(itemcode__iexact=item_code).filter(warehousecode__iexact='MTG').first().quantityonhand
        desk_one_results = DeskOneSchedule.objects.filter(item_code__in=relevant_blend_item_codes)
        desk_two_results = DeskTwoSchedule.objects.filter(item_code__in=relevant_blend_item_codes)
        purchase_orders = PoPurchaseOrderDetail.objects.filter(quantityreceived=0, itemcode__iexact=item_code)

        combined_results = list(desk_one_results) + list(desk_two_results)
        blend_component_changes = []
        for result in combined_results:
            lot_quantity = LotNumRecord.objects.get(lot_number__iexact=result.lot).lot_quantity
            qty_per_bill = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).filter(item_code__iexact=result.item_code).first().qtyperbill
            if ComponentShortage.objects.filter(component_item_code__iexact=result.item_code).exists():
                when_short = ComponentShortage.objects.filter(component_item_code__iexact=result.item_code).order_by('start_time').first().start_time
            else:
                when_short = ''
            blend_component_changes.append({
                'type' : 'Blend',
                'blend_item_code': result.item_code,
                'blend_item_description': result.item_description,
                'blend_quantity': lot_quantity,
                'ingredient' : item_code,
                'ingredient_change_quantity': (-1) * lot_quantity * qty_per_bill,
                'when' : when_short
            })

        for purchase_order in purchase_orders:
            weekend_days_til_then = count_weekend_days(dt.date.today(), purchase_order.requireddate)
            blend_component_changes.append({
                'type' : 'Purchase Order',
                'ingredient' : item_code,
                'ingredient_change_quantity': purchase_order.quantityordered,
                'when' : calculate_production_hours(purchase_order.requireddate),
                'weekend_days_til_then' : weekend_days_til_then
            })
        
        blend_component_changes = sorted(blend_component_changes, key=lambda x: x['when'])

        cumulative_quantity = component_onhandquantity
        for change in blend_component_changes:
            cumulative_quantity += change['ingredient_change_quantity']
            change['onhand_after_change'] = cumulative_quantity
        
        render_payload = {
            'template_string' : 'core/reports/blendcomponentconsumption.html',
            'context' : {'blend_component_changes' : blend_component_changes,
                         'component_onhandquantity' : component_onhandquantity,
                         'item_code' : item_code}
        }
        return render_payload

    except Exception as e:
        logger.error(f"Unexpected error generating component usage for scheduled blends report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload


# ---------------------------------------------------------------------------
# Component coverage snapshot (100433 & 100507TANKO)
# ---------------------------------------------------------------------------


def _decimal_to_float(value):
    """Safely convert Decimals/None to float for JSON serialization."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError, InvalidOperation):
        return None


def _get_item_description(item_code: str) -> str:
    item = CiItem.objects.filter(itemcode__iexact=item_code).first()
    return item.itemcodedesc if item else ''


def _get_onhand_quantity(item_code: str, warehouse: str = 'MTG') -> float:
    record = ImItemWarehouse.objects.filter(
        itemcode__iexact=item_code,
        warehousecode__iexact=warehouse,
    ).first()
    if record and record.quantityonhand is not None:
        return float(record.quantityonhand)
    return 0.0


def _get_blends_for_component(component_item_code: str):
    """Return dict keyed by blend item_code for BOM rows using the component."""
    relationships = {}
    bills = (
        BillOfMaterials.objects
        .filter(component_item_code__iexact=component_item_code)
        .exclude(component_item_code__startswith='/')
    )
    for bill in bills:
        if bill.item_code in relationships:
            continue
        relationships[bill.item_code] = {
            'blend_item_code': bill.item_code,
            'blend_item_description': bill.item_description,
            'component_qty_per_blend': _decimal_to_float(bill.qtyperbill),
        }
    return relationships


def _get_shortage_runs_for_blends(blend_item_codes, subcomponent_item_code):
    if not blend_item_codes:
        return []

    usages = (
        SubComponentUsage.objects
        .filter(subcomponent_item_code__iexact=subcomponent_item_code)
        .filter(component_item_code__in=blend_item_codes)
        .order_by('start_time')
    )

    shortage_rows = []
    for usage in usages:
        shortage_rows.append({
            'blend_item_code': usage.component_item_code,
            'blend_item_description': usage.component_item_description,
            'start_time': _decimal_to_float(usage.start_time),
            'prod_line': usage.prod_line,
            'item_run_qty': _decimal_to_float(usage.subcomponent_run_qty),
            'component_onhand_after_run': _decimal_to_float(usage.subcomponent_onhand_after_run),
            'total_shortage': None,
            'one_wk_short': None,
            'two_wk_short': None,
            'three_wk_short': None,
            'next_order_due': None,
            'po_number': usage.po_number,
        })
    return shortage_rows


def _get_open_purchase_orders(component_item_code: str):
    """Return open PO lines for a component and aggregate incoming quantity."""
    if not component_item_code:
        return [], 0.0, None

    today = dt.date.today()

    open_po_lines = (
        PoPurchaseOrderDetail.objects
        .filter(itemcode__iexact=component_item_code)
        .filter(requireddate__isnull=False)
        .filter(requireddate__gte=today - dt.timedelta(days=1))
        .order_by('requireddate', 'purchaseorderno', 'lineseqno')
    )

    purchase_orders = []
    total_open_qty = Decimal('0')
    next_required_date = None

    for po in open_po_lines:
        ordered_qty = Decimal(po.quantityordered or 0)
        received_qty = Decimal(po.quantityreceived or 0)
        open_qty = ordered_qty - received_qty
        if open_qty <= 0:
            continue

        requireddate = po.requireddate
        if next_required_date is None or (requireddate and requireddate < next_required_date):
            next_required_date = requireddate

        total_open_qty += open_qty

        purchase_orders.append({
            'purchaseorderno': po.purchaseorderno,
            'requireddate': requireddate,
            'ordered_qty': _decimal_to_float(po.quantityordered),
            'received_qty': _decimal_to_float(po.quantityreceived),
            'open_qty': _decimal_to_float(open_qty),
            'commenttext': po.commenttext,
            'warehousecode': po.warehousecode,
        })

    return purchase_orders, _decimal_to_float(total_open_qty), next_required_date


def _project_after_usage(scheduled_rows, starting_on_hand, incoming_qty=0.0):
    """Simulate consumption across scheduled rows and return projection/first shortage."""
    if starting_on_hand is None:
        return None, None

    running = float(starting_on_hand) + float(incoming_qty or 0)
    first_shortage = None

    for row in scheduled_rows:
        usage = row.get('component_usage')
        if usage is None:
            continue
        running -= float(usage)
        if running < 0 and first_shortage is None:
            first_shortage = {
                'trigger_onhand': _decimal_to_float(running),
                'trigger_blend_item_code': row.get('blend_item_code'),
                'trigger_lot': row.get('lot_number'),
                'trigger_desk': row.get('desk'),
                'shortage_point': row.get('shortage_point'),
            }

    return _decimal_to_float(running), first_shortage


def _compute_desk_shortage_point(blend_item_code: str, area: str, cumulative_qty: float):
    """Mirror desk schedule shortage timing for a scheduled blend row.

    Args:
        blend_item_code: Parent blend item on the desk schedule.
        area: Desk area string (e.g., 'Desk_1', 'Desk_2', 'LET_Desk').
        cumulative_qty: Sum of prior lot quantities for the same blend on that desk.

    Returns:
        float|None: Hour-short value as displayed on desk schedules.
    """
    earliest_shortage = (
        ComponentShortage.objects
        .filter(component_item_code__iexact=blend_item_code)
        .order_by('start_time')
        .first()
    )

    if not earliest_shortage:
        return None

    hourshort = earliest_shortage.start_time

    if cumulative_qty and float(cumulative_qty) > 0:
        new_shortage = calculate_new_shortage(blend_item_code, cumulative_qty)
        if new_shortage:
            hourshort = new_shortage.get('start_time', hourshort)

    if 'LET' not in (area or ''):
        if blend_item_code in advance_blends:
            hourshort = max((hourshort - 30), 5)
        else:
            hourshort = max((hourshort - 5), 1)

    return hourshort


def _get_scheduled_usage_for_component(component_item_code: str, blend_lookup: dict):
    if not blend_lookup:
        return [], 0.0

    scheduled_rows = []
    total_usage = 0.0

    schedules = [
        (DeskOneSchedule.objects.filter(item_code__in=blend_lookup.keys()).order_by('order'), 'Desk 1', 'Desk_1'),
        (DeskTwoSchedule.objects.filter(item_code__in=blend_lookup.keys()).order_by('order'), 'Desk 2', 'Desk_2'),
    ]

    for queryset, desk_label, desk_area in schedules:
        cumulative_qty_by_item = defaultdict(float)
        for run in queryset:
            lot_quantity = None
            lot_record = LotNumRecord.objects.filter(lot_number__iexact=run.lot).first()
            if lot_record and lot_record.lot_quantity is not None:
                lot_quantity = _decimal_to_float(lot_record.lot_quantity)

            qty_per_bill = blend_lookup[run.item_code].get('component_qty_per_blend')
            component_usage = None
            if lot_quantity is not None and qty_per_bill is not None:
                component_usage = lot_quantity * qty_per_bill
                total_usage += component_usage

            shortage_point = _compute_desk_shortage_point(
                blend_item_code=run.item_code,
                area=desk_area,
                cumulative_qty=cumulative_qty_by_item[run.item_code],
            )

            # Update cumulative quantity after computing shortage so this run isn't double-counted
            if lot_quantity is not None:
                cumulative_qty_by_item[run.item_code] += lot_quantity

            scheduled_rows.append({
                'desk': desk_label,
                'blend_item_code': run.item_code,
                'blend_item_description': run.item_description,
                'lot_number': run.lot,
                'blend_area': run.blend_area,
                'tank': run.tank,
                'lot_quantity': lot_quantity,
                'component_qty_per_blend': qty_per_bill,
                'component_usage': component_usage,
                'shortage_point': _decimal_to_float(shortage_point) if shortage_point is not None else None,
            })

    return scheduled_rows, total_usage


def _find_tipping_shortage(rows, starting_on_hand, threshold=8000.0):
    """Return the first scheduled row that drops on-hand below a threshold.

    Args:
        rows (list[dict]): Scheduled usage rows (ordered).
        starting_on_hand (float): Starting on-hand quantity (Tank O gallons).
        threshold (float): Threshold gallons to test against.

    Returns:
        dict|None: Row info plus remaining_on_hand at tipping, else None.
    """
    if starting_on_hand is None:
        return None

    running = float(starting_on_hand)
    for row in rows:
        usage = row.get('component_usage')
        if usage is None:
            continue
        running -= float(usage)
        if running < threshold:
            return {
                'trigger_onhand': _decimal_to_float(running),
                'trigger_blend_item_code': row.get('blend_item_code'),
                'trigger_lot': row.get('lot_number'),
                'trigger_desk': row.get('desk'),
                'shortage_point': row.get('shortage_point'),
            }
    return None


def _fetch_live_tank_levels():
    """Fetch the live tank levels page and parse gallons."""
    try:
        req = urllib.request.Request('http://192.168.178.210/fieldDeviceData.htm')
        with urllib.request.urlopen(req, timeout=3.0) as fp:
            html_str = fp.read().decode('utf-8')
        html_str = urllib.parse.unquote(html_str)
        return extract_all_tank_levels(html_str)
    except (urllib.error.URLError, socket.timeout, socket.error) as exc:
        logger.warning("Unable to fetch live tank levels: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching live tank levels: %s", exc)
    return {}


def _normalize_tank_key(value: str) -> str:
    return (value or '').replace(' ', '').upper()


def _get_specific_tank_levels(tank_names):
    """Resolve tank gallons via the shared helper, with DB fallbacks."""
    # Imported lazily to avoid circular imports during Django startup
    from core.views import api as api_views

    tank_payload = {}

    def _match_key(levels: dict, lookup_key: str):
        def norm(val: str) -> str:
            return ''.join((val or '').split()).upper()

        # Align with tank monitor page: strip leading "TANK" and whitespace
        cleaned_lookup = (lookup_key or '')
        cleaned_lookup_upper = cleaned_lookup.upper()
        if cleaned_lookup_upper.startswith('TANK'):
            cleaned_lookup = cleaned_lookup[4:]
        lookup_norm = norm(cleaned_lookup)

        if lookup_key in levels:
            return lookup_key
        for key in levels.keys():
            if norm(key) == lookup_norm:
                return key
        if len(lookup_norm) == 1:  # single-letter tank like "O"
            for key in levels.keys():
                if norm(key).endswith(lookup_norm):
                    return key
        return None

    # Fetch live inches once so the report matches the tank levels page
    live_inches_by_tag = {}
    try:
        req = urllib.request.Request('http://192.168.178.210/fieldDeviceData.htm')
        with urllib.request.urlopen(req, timeout=3.0) as fp:
            html_str = fp.read().decode('utf-8')
        html_str = urllib.parse.unquote(html_str)
        soup = BeautifulSoup(html_str, "html.parser")
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            tag_cell = next((c for c in cells if "Tag:" in c.get_text()), None)
            inches_cell = next((c for c in cells if "IN " in c.get_text()), None)
            if not (tag_cell and inches_cell):
                continue

            raw_text = tag_cell.get_text().upper()
            if "TAG:" in raw_text:
                raw_text = raw_text.split("TAG:")[-1]
            normalized_text = ' '.join(raw_text.split())
            if not normalized_text:
                continue
            try:
                key_part = normalized_text.split("CMD3")[-1].strip()
            except Exception:  # noqa: BLE001
                key_part = normalized_text
            if key_part.startswith("TAG:"):
                key_part = key_part[4:].strip()
            elif key_part.startswith("TAG "):
                key_part = key_part[4:].strip()
            tag_text = key_part

            try:
                inches_str = inches_cell.get_text().split("IN")[0].strip()
                inches_val = float(inches_str)
                live_inches_by_tag[tag_text] = inches_val
            except (ValueError, IndexError):
                continue
    except (urllib.error.URLError, socket.timeout, socket.error) as exc:
        logger.warning("Unable to fetch live tank inches: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching live tank inches: %s", exc)

    for name in tank_names:
        gallons_value = None
        inches_value = None
        max_gallons_value = None
        gallons_per_inch_value = None

        # Primary: shared helper used by the API view
        try:
            helper_payload = api_views._get_single_tank_level_dict(name)
            if helper_payload.get('status') == 'ok':
                gallons_value = helper_payload.get('gallons')
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tank helper lookup failed for %s: %s", name, exc)

        # If live inches were found, prefer them over DB fallbacks for alignment with tank page
        match_key = _match_key(live_inches_by_tag, name)
        if match_key:
            inches_value = live_inches_by_tag.get(match_key)

        # Fallback: latest TankLevelLog (also use to capture inches when available)
        fallback_log = (
            TankLevelLog.objects
            .filter(tank_name__icontains=name)
            .order_by('-timestamp')
            .first()
        )
        if fallback_log:
            if gallons_value is None:
                gallons_value = fallback_log.filled_gallons
            if inches_value is None:
                inches_value = fallback_log.fill_height_inches

        # Fallback: TankLevel snapshot table
        fallback_level = (
            TankLevel.objects
            .filter(tank_name__icontains=name)
            .first()
        )
        if fallback_level:
            if gallons_value is None:
                gallons_value = fallback_level.filled_gallons
            if inches_value is None:
                inches_value = fallback_level.fill_height_inches

        # Capacity lookups
        # First try matching on the Vega label (e.g., "10 B"), then KPK label (e.g., "TANK B")
        letter_only = ''.join(ch for ch in name if ch.isalpha())
        max_gallons_qs = [
            StorageTank.objects.filter(tank_label_vega__iexact=name).first(),
            StorageTank.objects.filter(tank_label_kpk__iexact=name).first(),
            StorageTank.objects.filter(tank_label_kpk__iexact=f"TANK {letter_only}").first() if letter_only else None,
        ]
        for candidate in max_gallons_qs:
            if candidate and candidate.max_gallons is not None:
                max_gallons_value = candidate.max_gallons
                gallons_per_inch_value = candidate.gallons_per_inch
                break

        gallons_float = None
        if inches_value is not None and gallons_per_inch_value is not None:
            try:
                gallons_float = _decimal_to_float(Decimal(inches_value) * Decimal(gallons_per_inch_value))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Tank inches->gallons calc failed for %s: %s", name, exc)
        if gallons_float is None and gallons_value is not None:
            gallons_float = _decimal_to_float(gallons_value)
        max_gallons_float = _decimal_to_float(max_gallons_value)
        available_capacity = None
        if gallons_float is not None and max_gallons_float is not None:
            # "Available" defined by request as filled - max
            available_capacity = max_gallons_float - gallons_float

        tank_payload[name] = {
            'gallons': gallons_float,
            'max_gallons': max_gallons_float,
            'available_capacity': _decimal_to_float(available_capacity),
        }
    
    return tank_payload


def build_component_stock_coverage_payload():
    """Aggregate the data needed to answer the 100433 / 100507TANKO stock question."""
    tank_levels_raw = _get_specific_tank_levels(['TANK O'])
    # Normalize tank keys: remove numbers and whitespace, leaving only letters
    normalized_tank_levels = {}
    for key, value in tank_levels_raw.items():
        normalized_key = ''.join(char for char in key if char.isalpha())
        if normalized_key.upper().startswith('TANK'):
            normalized_key = normalized_key[4:]
        current_gallons = value.get('gallons') if isinstance(value, dict) else value
        max_gallons = value.get('max_gallons') if isinstance(value, dict) else None
        available_capacity = value.get('available_capacity') if isinstance(value, dict) else None

        # Compute available capacity if not already present and we have both values
        if available_capacity is None and current_gallons is not None and max_gallons is not None:
            available_capacity = _decimal_to_float(current_gallons - max_gallons)

        normalized_tank_levels[normalized_key] = {
            'gallons': _decimal_to_float(current_gallons),
            'max_gallons': _decimal_to_float(max_gallons),
            'available_capacity': _decimal_to_float(available_capacity),
        }

    component_configs = [
        {'item_code': '100433', 'paired_item_code': 'PP100433'},
        {'item_code': '100507TANKO', 'paired_item_code': None},
    ]

    components_payload = []
    for config in component_configs:
        item_code = config['item_code']
        paired_item_code = config.get('paired_item_code')

        blend_lookup = _get_blends_for_component(item_code)
        blend_codes = list(blend_lookup.keys())

        shortage_rows = _get_shortage_runs_for_blends(blend_codes, item_code)
        scheduled_rows, total_usage = _get_scheduled_usage_for_component(item_code, blend_lookup)

        on_hand_qty = _get_onhand_quantity(item_code)
        if item_code == '100507TANKO':
            tank_o = normalized_tank_levels.get('O') or {}
            if tank_o.get('gallons') is not None:
                on_hand_qty = tank_o.get('gallons')

        purchase_orders, incoming_po_qty, next_po_date = _get_open_purchase_orders(item_code)

        projected_after_schedule_raw = _decimal_to_float(
            on_hand_qty - total_usage if on_hand_qty is not None else None
        )
        projected_after_schedule_with_pos, first_shortage_with_pos = _project_after_usage(
            scheduled_rows,
            on_hand_qty,
            incoming_qty=incoming_po_qty,
        )
        projected_after_schedule_without_pos, first_shortage_without_pos = _project_after_usage(
            scheduled_rows,
            on_hand_qty,
            incoming_qty=0.0,
        )

        if item_code == '100507TANKO':
            tipping_shortage = _find_tipping_shortage(scheduled_rows, on_hand_qty, threshold=8000.0)
            tipping_shortage_with_pos = _find_tipping_shortage(
                scheduled_rows,
                (on_hand_qty + incoming_po_qty) if on_hand_qty is not None else None,
                threshold=8000.0,
            )
        else:
            tipping_shortage = None
            tipping_shortage_with_pos = None
        paired_on_hand = _get_onhand_quantity(paired_item_code) if paired_item_code else None

        components_payload.append({
            'item_code': item_code,
            'item_description': _get_item_description(item_code),
            'on_hand_qty': on_hand_qty,
            'incoming_po_qty': incoming_po_qty,
            'next_po_date': next_po_date,
            'purchase_orders': purchase_orders,
            'paired_item_code': paired_item_code,
            'paired_on_hand_qty': paired_on_hand,
            'blends': list(blend_lookup.values()),
            'shortage_runs': shortage_rows,
            'scheduled_usage': {
                'rows': scheduled_rows,
                'total_component_usage': _decimal_to_float(total_usage),
                'projected_on_hand_after_schedule': projected_after_schedule_raw,
                'projected_on_hand_after_schedule_incl_pos': projected_after_schedule_with_pos,
                'projected_on_hand_after_schedule_no_pos': projected_after_schedule_without_pos,
            },
            'shortage_projection': {
                'first_shortage_without_pos': first_shortage_without_pos,
                'first_shortage_with_pos': first_shortage_with_pos,
            },
            'tipping_shortage': tipping_shortage,
            'tipping_shortage_with_pos': tipping_shortage_with_pos,
        })

    tank_levels = normalized_tank_levels
    print("tank levels : ", tank_levels)
    return {
        'generated_at': dt.datetime.now(tz=pytz.UTC),
        'components': components_payload,
        'tanks': tank_levels,
    }

def generate_transaction_mismatches_report(item_code):
    try:
        parent_items = BillOfMaterials.objects.filter(component_item_code__iexact=item_code)
        parent_item_qtyperbills = { item.item_code : item.qtyperbill for item in parent_items }
        parent_item_codes = parent_items.values_list('item_code', flat=True)
        component_item_transaction_quantities = { transaction.entryno : transaction.transactionqty for transaction in ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).filter(transactioncode='BI') }
        print(component_item_transaction_quantities)
        parent_item_transactions = ImItemTransactionHistory.objects.filter(itemcode__in=parent_item_codes).filter(transactioncode='BR').order_by('-transactiondate')

        for transaction in parent_item_transactions:
            transaction.qtyperbill = parent_item_qtyperbills[transaction.itemcode]
            transaction.theory_component_transaction_qty = transaction.qtyperbill * transaction.transactionqty
            transaction.actual_component_transaction_qty = component_item_transaction_quantities.get(transaction.entryno,'Not Found')
            if transaction.actual_component_transaction_qty != 'Not Found':
                transaction.actual_component_transaction_qty = abs(transaction.actual_component_transaction_qty)
                transaction.discrepancy = float(transaction.actual_component_transaction_qty) - float(transaction.theory_component_transaction_qty)
                transaction.percentage = transaction.discrepancy / float(transaction.actual_component_transaction_qty) * 100
                if transaction.percentage > 5:
                    transaction.sus = True
                else:
                    transaction.sus = False

        # transaction_mismatches_query = f"""WITH ConsumedQuantity AS (
        #                 SELECT 
        #                     ith.entryno,
        #                     ith.itemcode, 
        #                     ith.transactiondate,
        #                     ith.timeupdated,
        #                     bom.qtyperbill,
        #                     ith.transactionqty,
        #                     ABS(ith.transactionqty) * (bom.qtyperbill / 0.975) AS calculated_consumed_qty
        #                 FROM 
        #                     im_itemtransactionhistory ith
        #                 JOIN 
        #                     bill_of_materials bom ON ith.itemcode = bom.item_code
        #                 WHERE 
        #                     ith.transactioncode IN ('BI', 'BR')
        #                     AND bom.component_item_code = '{str(item_code)}'
        #             ),
        #             ActualQuantity AS (
        #                 SELECT 
        #                     entryno,
        #                     itemcode, 
        #                     transactiondate,
        #                     timeupdated,
        #                     ABS(transactionqty) AS actual_transaction_qty
        #                 FROM 
        #                     im_itemtransactionhistory
        #                 WHERE 
        #                     itemcode = '{str(item_code)}'
        #                     AND transactioncode IN ('BI', 'BR')
        #             )
        #             SELECT 
        #                 cq.entryno,
        #                 cq.itemcode AS component_itemcode,
        #                 cq.transactiondate,
        #                 cq.timeupdated,
        #                 TO_CHAR(cq.qtyperbill, 'FM999999999.0000') AS qtyperbill,
        #                 TO_CHAR(cq.transactionqty, 'FM999999999.0000') AS transactionqty,
        #                 TO_CHAR(cq.calculated_consumed_qty, 'FM999999999.0000') AS calculated_consumed_qty,
        #                 TO_CHAR(aq.actual_transaction_qty, 'FM999999999.0000') AS actual_transaction_qty,
        #                 TO_CHAR((cq.calculated_consumed_qty - aq.actual_transaction_qty), 'FM999999999.0000') AS discrepancy
        #             FROM 
        #                 ConsumedQuantity cq
        #             JOIN 
        #                 ActualQuantity aq ON cq.entryno = aq.entryno
        #                 AND cq.transactiondate = aq.transactiondate
        #                 AND cq.timeupdated = aq.timeupdated
        #             WHERE 
        #                 ABS((cq.calculated_consumed_qty - aq.actual_transaction_qty) / cq.calculated_consumed_qty) > 0.05
        #             ORDER BY 
        #                 cq.transactiondate DESC, cq.timeupdated DESC;"""

        # with connection.cursor() as cursor:
        #     cursor.execute(transaction_mismatches_query)
        #     result = cursor.fetchall()

        render_payload = {
            'template_string' : 'core/reports/transactionmismatches.html',
            'context' : {'parent_item_transactions' : parent_item_transactions,
                         'item_code' : item_code}
        }
        return render_payload
        
    except Exception as e:
        logger.error(f"Unexpected error generating transaction mismatches report: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def create_report(request, which_report, item_code):

    """
    Creates a report based on the specified report type and item code.
    
    Decodes base64-encoded item code from request and generates either:
    - Lot number report showing lot numbers and quantities for an item
    - Upcoming runs report showing scheduled production runs using an item
    
    Args:
        request: HTTP request object containing encoded item code
        which_report (str): Type of report to generate ('Lot-Numbers' or 'All-Upcoming-Runs')
        
    Returns:
        Rendered template for requested report type
    """

    if which_report=="Lot-Numbers":
        render_payload = generate_lot_numbers_report(request, item_code)

    elif which_report=="All-Upcoming-Runs":
        render_payload = generate_all_upcoming_runs_report(item_code)

    elif which_report=="Startron-Runs":
        render_payload = generate_startron_runs_report()

    elif which_report=="Transaction-History":
        render_payload = generate_transaction_history_report(request, item_code)
        
    elif which_report=="Count-History":
        render_payload = generate_count_history_report(item_code)

    elif which_report=="Counts-And-Transactions":
        render_payload = generate_counts_and_transactions_report(item_code)
    
    elif which_report=="Where-Used":
        render_payload = generate_where_used_report(item_code)

    elif which_report=="Purchase-Orders":
        render_payload = generate_purchase_orders_report(item_code)

    elif which_report=="Bill-Of-Materials":
        render_payload = generate_bill_of_materials_report(item_code)

    elif which_report=="Max-Producible-Quantity":
        render_payload = generate_max_producible_quantity_report(item_code)
        
    elif which_report=="Blend-What-If":
        render_payload = generate_blend_what_if_report(request, item_code)
    
    elif which_report=="Item-Component-What-If":
        render_payload = generate_item_component_what_if_report(request, item_code)
    
    elif which_report=="Component-Usage-For-Scheduled-Blends":
        render_payload = generate_component_usage_for_scheduled_blends_report(item_code)
    
    elif which_report=="Transaction-Mismatches":
        render_payload = generate_transaction_mismatches_report(item_code)

    return render_payload

def create_weekly_blend_totals_table():
    try:
        with connection.cursor() as cursor:
            cursor.execute('''create table weekly_blend_totals_TEMP as
                    select date_trunc('week', core_lotnumrecord.sage_entered_date) as week_starting,
                    sum(core_lotnumrecord.lot_quantity) as blend_quantity
                    FROM core_lotnumrecord WHERE core_lotnumrecord.line like 'Prod'
                    GROUP BY week_starting ORDER BY week_starting;
                alter table weekly_blend_totals_TEMP add column id serial primary key;
                drop table if exists weekly_blend_totals;
                alter table weekly_blend_totals_TEMP rename to weekly_blend_totals;
                ''')
        logger.info("Weekly blend totals table created successfully")
        return True
    except Exception as e:
        logger.error(f"Unexpected error creating weekly blend totals table: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload

def create_weekly_blend_totals_table_context():
    try:
        weekly_blend_totals = WeeklyBlendTotals.objects.all()
        # blend_totals_2021 = weekly_blend_totals.filter(week_starting__year=2021)
        # for number, week in enumerate(blend_totals_2021):
        #     week.week_number = 'Week_' + str(number+1)
        # blend_totals_2022 = weekly_blend_totals.filter(week_starting__year=2022)
        # for number, week in enumerate(blend_totals_2022):
        #     week.week_number = 'Week_' + str(number+1)
        # blend_totals_2023 = weekly_blend_totals.filter(week_starting__year=2023)
        # for number, week in enumerate(blend_totals_2023):
        #     week.week_number = 'Week_' + str(number+1)
        # blend_totals_2024 = weekly_blend_totals.filter(week_starting__year=2024)
        # for number, week in enumerate(blend_totals_2024):
        #     week.week_number = 'Week_' + str(number+1)
        
        one_week_blend_demand = ComponentShortage.objects.filter(procurement_type__iexact='M').filter(component_item_code__startswith='BLEND').aggregate(total=Sum('one_wk_short'))
        two_week_blend_demand = ComponentShortage.objects.filter(procurement_type__iexact='M').filter(component_item_code__startswith='BLEND').aggregate(total=Sum('two_wk_short'))
        all_scheduled_blend_demand = ComponentShortage.objects.filter(procurement_type__iexact='M').filter(component_item_code__startswith='BLEND').aggregate(total=Sum('three_wk_short'))
        
        timezone = pytz.timezone("America/Chicago")
        now = dt.datetime.today()
        weekday = now.weekday()
        if weekday == 4:
            days_to_subtract = 5
        else:
            days_to_subtract = 7
        cutoff_date = now - dt.timedelta(days=days_to_subtract)
        days_from_monday = weekday +1
        this_monday_date = now - dt.timedelta(days=days_from_monday)
        this_tuesday_date = this_monday_date + dt.timedelta(days=1)
        this_wednesday_date = this_monday_date + dt.timedelta(days=2)
        this_thursday_date = this_monday_date + dt.timedelta(days=3)
        this_friday_date = this_monday_date + dt.timedelta(days = 4)
        lot_quantities_this_week = {
            'monday' : LotNumRecord.objects.filter(sage_entered_date__date=this_monday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'tuesday' : LotNumRecord.objects.filter(sage_entered_date__date=this_tuesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'wednesday' : LotNumRecord.objects.filter(sage_entered_date__date=this_wednesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'thursday' : LotNumRecord.objects.filter(sage_entered_date__date=this_thursday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'friday' : LotNumRecord.objects.filter(sage_entered_date__date=this_friday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total']
        }
        for key in lot_quantities_this_week:
            if lot_quantities_this_week[key] is None:
                lot_quantities_this_week[key] = 0
        lot_quantities_this_week['total'] = lot_quantities_this_week['monday'] + lot_quantities_this_week['tuesday'] + lot_quantities_this_week['wednesday'] + lot_quantities_this_week['thursday'] + lot_quantities_this_week['friday']

        last_monday_date = now - dt.timedelta(days=days_from_monday + 7)
        last_tuesday_date = last_monday_date + dt.timedelta(days = 1)
        last_wednesday_date = last_monday_date + dt.timedelta(days = 2)
        last_thursday_date = last_monday_date + dt.timedelta(days = 3)
        last_friday_date = last_monday_date + dt.timedelta(days = 4)
        lot_quantities_last_week = {
            'monday' : LotNumRecord.objects.filter(sage_entered_date__date=last_monday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'tuesday' : LotNumRecord.objects.filter(sage_entered_date__date=last_tuesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'wednesday' : LotNumRecord.objects.filter(sage_entered_date__date=last_wednesday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'thursday' : LotNumRecord.objects.filter(sage_entered_date__date=last_thursday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total'],
            'friday' : LotNumRecord.objects.filter(sage_entered_date__date=last_friday_date).filter(line__iexact='Prod').aggregate(total=Sum('lot_quantity'))['total']
        }
        for key in lot_quantities_last_week:
            if lot_quantities_last_week[key] is None:
                lot_quantities_last_week[key]=0
        lot_quantities_last_week['total'] = lot_quantities_last_week['monday'] + lot_quantities_last_week['tuesday'] + lot_quantities_last_week['wednesday'] + lot_quantities_last_week['thursday'] + lot_quantities_last_week['friday']

        this_monday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_monday_date).filter(line__iexact='Prod')
        this_tuesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_tuesday_date).filter(line__iexact='Prod')
        this_wednesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_wednesday_date).filter(line__iexact='Prod')
        this_thursday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_thursday_date).filter(line__iexact='Prod')
        this_friday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=this_friday_date).filter(line__iexact='Prod')
        last_monday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_monday_date).filter(line__iexact='Prod')
        last_tuesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_tuesday_date).filter(line__iexact='Prod')
        last_wednesday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_wednesday_date).filter(line__iexact='Prod')
        last_thursday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_thursday_date).filter(line__iexact='Prod')
        last_friday_lot_numbers = LotNumRecord.objects.filter(sage_entered_date__date=last_friday_date).filter(line__iexact='Prod')

        last_week_blends_produced = {'total' : weekly_blend_totals.order_by('-id')[1].blend_quantity}

        context = {
            'weekly_blend_totals' : weekly_blend_totals,
            # 'blend_totals_2021' : blend_totals_2021,
            # 'blend_totals_2022' : blend_totals_2022,
            # 'blend_totals_2023' : blend_totals_2023,
            'one_week_blend_demand' : one_week_blend_demand,
            'two_week_blend_demand' : two_week_blend_demand,
            'all_scheduled_blend_demand' : all_scheduled_blend_demand,
            'last_week_blends_produced' : last_week_blends_produced,
            'cutoff_date' : cutoff_date,
            'lot_quantities_this_week' : lot_quantities_this_week,
            'this_monday_lot_numbers' : this_monday_lot_numbers,
            'this_tuesday_lot_numbers' : this_tuesday_lot_numbers,
            'this_wednesday_lot_numbers' : this_wednesday_lot_numbers,
            'this_thursday_lot_numbers' : this_thursday_lot_numbers,
            'this_friday_lot_numbers' : this_friday_lot_numbers,
            'last_monday_lot_numbers' : last_monday_lot_numbers,
            'last_tuesday_lot_numbers' : last_tuesday_lot_numbers,
            'last_wednesday_lot_numbers' : last_wednesday_lot_numbers,
            'last_thursday_lot_numbers' : last_thursday_lot_numbers,
            'last_friday_lot_numbers' : last_friday_lot_numbers,
            'lot_quantities_last_week' : lot_quantities_last_week
            }

        return context
    except Exception as e:
        logger.error(f"Unexpected error creating weekly blend totals table: {e}")
        render_payload = {
            'template_string' : 'core/reports/reporterrorpage.html',
            'context' : {}
        }
        return render_payload
