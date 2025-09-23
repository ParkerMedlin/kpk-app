import logging
import base64
from django.shortcuts import render
from django.core.paginator import Paginator
from core.models import LotNumRecord, BillOfMaterials, ComponentUsage, ComponentShortage, SubComponentUsage, TimetableRunData, ImItemTransactionHistory, CiItem, BlendCountRecord, BlendComponentCountRecord, ImItemWarehouse, PoPurchaseOrderDetail, DeskOneSchedule, DeskTwoSchedule
from prodverse.models import WarehouseCountRecord
import datetime as dt
from core.services.production_planning_services import get_relevant_blend_runs, get_relevant_item_runs
from core.kpkapp_utils.dates import count_weekend_days, calculate_production_hours
from core.selectors.inventory_and_transactions_selectors import get_lot_number_quantities

logger = logging.getLogger(__name__)

def create_report(request, which_report):
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
        
    Templates:
        core/reports/lotnumsreport.html
        core/reports/upcomingrunreport.html
    """

    encoded_item_code = request.GET.get('itemCode')
    item_code_bytestr = base64.b64decode(encoded_item_code)
    item_code = item_code_bytestr.decode()
    if which_report=="Lot-Numbers":
        no_lots_found = False
        lot_num_queryset = LotNumRecord.objects.filter(item_code__iexact=item_code).order_by('-date_created', '-lot_number')
        if lot_num_queryset.exists():
            item_description = lot_num_queryset.first().item_description
        lot_num_paginator = Paginator(lot_num_queryset, 25)
        page_num = request.GET.get('page')
        current_page = lot_num_paginator.get_page(page_num)
        # lot_number_quantities = { lot.receiptno : (lot.quantityonhand, lot.transactiondate) for lot in ImItemCost.objects.filter(itemcode__iexact=item_code)}
        lot_number_quantities = get_lot_number_quantities(item_code)
        for lot in current_page:
            this_lot_number = lot_number_quantities.get(lot.lot_number,('',''))
            lot.qty_on_hand = this_lot_number[0]
            lot.date_entered = this_lot_number[1]

        blend_info = {'item_code' : item_code, 'item_description' : item_description}

        return render(request, 'core/reports/lotnumsreport.html', {'no_lots_found' : no_lots_found, 'current_page' : current_page, 'blend_info': blend_info})

    elif which_report=="All-Upcoming-Runs":
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
        # upcoming_runs = TimetableRunData.objects.filter(component_item_code__iexact=item_code).order_by('starttime')
        if upcoming_runs.exists():
            item_description = upcoming_runs.first().component_item_description
        else:
            no_runs_found = True
            item_description = ''
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
        return render(request, 'core/reports/upcomingrunsreport/upcomingrunsreport.html', context)

    elif which_report=="Startron-Runs":
        startron_item_codes = ['14000.B', '14308.B', '14308AMBER.B', '93100DSL.B', '93100GAS.B', '93100XBEE.B', '93100TANK.B', '93100GASBLUE.B', '93100GASAMBER.B']
        startron_runs = TimetableRunData.objects.filter(component_item_code__in=startron_item_codes)
        return render(request, 'core/reports/startronreport.html', {'startron_runs' : startron_runs})

    elif which_report=="Transaction-History":
        no_transactions_found = False
        if ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).exists():
            transactions_list = ImItemTransactionHistory.objects.filter(itemcode__iexact=item_code).order_by('-transactiondate')
            item_description = CiItem.objects.filter(itemcode=item_code).first().itemcodedesc
        else:
            no_transactions_found = True
            transactions_list = {}
            item_description = ''
        for item in transactions_list:
            item.item_description = item_description
        item_info = {'item_code' : item_code, 'item_description' : item_description}
        return render(request, 'core/reports/transactionsreport.html', {'no_transactions_found' : no_transactions_found, 'transactions_list' : transactions_list, 'item_info': item_info})
        
    elif which_report=="Count-History":
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
        return render(request, 'core/reports/inventorycountsreport.html', context)

    elif which_report=="Counts-And-Transactions":
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
        return render(request, 'core/reports/countsandtransactionsreport.html', context)
    
    elif which_report=="Where-Used":
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        all_bills_where_used = BillOfMaterials.objects.filter(component_item_code__iexact=item_code)
        item_info = {'item_code' : item_code,
                    'item_description' : item_description
                    }
        context = {'all_bills_where_used' : all_bills_where_used,
            'item_info' : item_info
            }
        # may want to do pagination if this gets ugly
        return render(request, 'core/reports/whereusedreport.html', context)

    elif which_report=="Purchase-Orders":
        item_description = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().component_item_description
        standard_uom = BillOfMaterials.objects.filter(component_item_code__iexact=item_code).first().standard_uom
        two_days_ago = dt.datetime.today() - dt.timedelta(days = 2)
        orders_not_found = False
        procurementtype = BillOfMaterials.objects \
            .filter(component_item_code__iexact=item_code) \
            .first().procurementtype
        if not procurementtype == 'M':
            all_purchase_orders = PoPurchaseOrderDetail.objects \
                    .filter(itemcode=item_code) \
                    .filter(requireddate__gte=two_days_ago) \
                    .order_by('requireddate')
        else:
            orders_not_found = True
            all_purchase_orders = None
        item_info = {
                    'item_code' : item_code,
                    'item_description' : item_description,
                    'standard_uom' : standard_uom
                    }
        context = {
            'orders_not_found' : orders_not_found,
            'all_purchase_orders' : all_purchase_orders, 
            'item_info' : item_info
        }
        return render(request, 'core/reports/purchaseordersreport.html', context)

    elif which_report=="Bill-Of-Materials":
        these_bills = BillOfMaterials.objects.filter(item_code__iexact=item_code)
        for bill in these_bills:
            if bill.qtyonhand and bill.qtyperbill:
                bill.max_blend =  bill.qtyonhand / bill.qtyperbill
        item_info = {'item_code' : item_code,
                    'item_description' : these_bills.first().item_description
                    }

        return render(request, 'core/reports/billofmaterialsreport.html', {'these_bills' : these_bills, 'item_info' : item_info})

    elif which_report=="Max-Producible-Quantity":
        return render(request, 'core/reports/maxproduciblequantity.html')

    elif which_report=="Blend-What-If":
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

        return render(request, 'core/reports/whatifblend.html', {
                                    'blend_subcomponent_usage' : blend_subcomponent_usage,
                                    'item_code' : item_code,
                                    'item_description' : item_description,
                                    'blend_quantity' : blend_quantity,
                                    'start_time' : start_time,
                                    'new_blend_run_components' : new_blend_run_components})
    
    elif which_report=="Item-Component-What-If":
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

        return render(request, 'core/reports/whatifproductionitem.html', {
                                    'item_component_usage' : item_component_usage,
                                    'item_code' : item_code,
                                    'item_description' : item_description,
                                    'item_quantity' : item_quantity,
                                    'start_time' : start_time,
                                    'new_item_run_components' : new_item_run_components})
    
    elif which_report=="Component-Usage-For-Scheduled-Blends":
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

        return render(request, 'core/reports/blendcomponentconsumption.html', {
                                    'blend_component_changes' : blend_component_changes,
                                    'component_onhandquantity' : component_onhandquantity,
                                    'item_code' : item_code})
    
    elif which_report=="Transaction-Mismatches":
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

        return render(request, 'core/reports/transactionmismatches.html', {
                                    # 'transaction_mismatches' : result,
                                    'parent_item_transactions' : parent_item_transactions,
                                    'item_code' : item_code})

    else:
        return render(request, '')