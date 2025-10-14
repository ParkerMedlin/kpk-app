import logging
from core.models import BillOfMaterials, SubComponentUsage, CiItem, ComponentUsage, ComponentShortage
from django.http import JsonResponse

logger = logging.getLogger(__name__)

def get_relevant_blend_runs(item_code, item_quantity, start_time):
    """Get relevant blend runs and their component usage for a given item.
    
    Retrieves and processes blend run data for a specified item, calculating component
    usage quantities and tracking inventory levels. Identifies potential shortages
    based on projected usage.

    Args:
        item_code (str): Code identifying the blend item
        item_quantity (float): Quantity of blend item needed
        start_time (float): Starting time reference point for usage calculations
        
    Returns:
        list: Blend run details including:
            - Component and subcomponent item codes and descriptions
            - Start times and production lines
            - Projected inventory levels after runs
            - Shortage flags for components below 0 quantity
    """
    blend_subcomponent_queryset = BillOfMaterials.objects \
        .filter(item_code__iexact=item_code) \
        .exclude(component_item_code__iexact='030143') \
        .exclude(component_item_code__startswith='/') \
        .distinct('component_item_code')
    this_blend_subcomponent_item_codes = [item.component_item_code for item in blend_subcomponent_queryset]

    this_blend_component_usages = {} # this will store the quantity used for each component
    for subcomponent_item_code in this_blend_subcomponent_item_codes:
        try:
            this_blend_component_usages[subcomponent_item_code] = float(BillOfMaterials.objects \
                                                                    .filter(item_code__iexact=item_code) \
                                                                    .filter(component_item_code__iexact=subcomponent_item_code) \
                                                                    .first().qtyperbill) * float(item_quantity)
        except TypeError as e:
            print(str(e))
            continue
    
    blend_subcomponent_usage_queryset = SubComponentUsage.objects \
        .filter(subcomponent_item_code__in=this_blend_subcomponent_item_codes) \
        .exclude(subcomponent_item_code__startswith='/') \
        .order_by('start_time')
    
    blend_subcomponent_usage_list = [
            {
                'component_item_code' : usage.component_item_code,
                'component_item_description' : usage.component_item_description,
                'subcomponent_item_code' : usage.subcomponent_item_code,
                'subcomponent_item_description' : usage.subcomponent_item_description,
                'start_time' : float(usage.start_time),
                'prod_line' : usage.prod_line,
                'subcomponent_onhand_after_run' : usage.subcomponent_onhand_after_run,
                'subcomponent_run_qty' : usage.subcomponent_run_qty,
                'run_source' : 'original'
            }
            for usage in blend_subcomponent_usage_queryset
        ]

    for key, value in this_blend_component_usages.items():
        for item in blend_subcomponent_usage_list:
            if item['subcomponent_item_code'] == key:
                if float(item['start_time']) > float(start_time):
                    item['subcomponent_onhand_after_run'] = float(item['subcomponent_onhand_after_run']) - float(value)
                item['subcomponent_item_description'] = CiItem.objects.filter(itemcode__iexact=item['subcomponent_item_code']).first().itemcodedesc

    for item in blend_subcomponent_usage_list:
        if item['subcomponent_onhand_after_run'] < 0:
            item['subcomponent_shortage'] = True
        else:
            item['subcomponent_shortage'] = False
        if "SCHEDULED: " in item['prod_line']:
            item['prod_line'] = item['prod_line'].replace("SCHEDULED: ", "")

    return blend_subcomponent_usage_list

def get_relevant_item_runs(item_code, item_quantity, start_time):
    """
    Retrieves and processes component usage data for a specific item.

    Args:
        item_code (str): The code identifying the item
        item_quantity (float): Quantity of the item being produced
        start_time (float): Unix timestamp marking start of production

    Returns:
        list: List of dicts containing component usage data, with fields:
            - item_code: Code of the finished item
            - item_description: Description of the finished item  
            - component_item_code: Code of the component
            - component_item_description: Description of the component
            - start_time: Production start time
            - prod_line: Production line
            - component_onhand_after_run: Component quantity remaining after run
            - component_run_qty: Component quantity used in run
            - run_source: Source of the run data
            - component_shortage: Boolean indicating if component will be short
    """
    item_component_queryset = BillOfMaterials.objects \
        .filter(item_code__iexact=item_code) \
        .exclude(component_item_code__startswith='/') \
        .distinct('component_item_code')
    this_item_component_item_codes = [item.component_item_code for item in item_component_queryset]

    this_item_component_usages = {} # this will store the quantity used for each component
    for component_item_code in this_item_component_item_codes:
        try:
            this_item_component_usages[component_item_code] = float(BillOfMaterials.objects \
                                                                    .filter(item_code__iexact=item_code) \
                                                                    .filter(component_item_code__iexact=component_item_code) \
                                                                    .first().qtyperbill) * float(item_quantity)
        except TypeError as e:
            print(str(e))
            continue
    
    item_component_usage_queryset = ComponentUsage.objects \
        .filter(component_item_code__in=this_item_component_item_codes) \
        .exclude(component_item_code__startswith='/') \
        .order_by('start_time')
    item_codes = list(item_component_usage_queryset.values_list('item_code', flat=True))
    item_descriptions = {item.itemcode : item.itemcodedesc for item in CiItem.objects.filter(itemcode__in=item_codes)}
    item_component_usage_list = [
            {
                'item_code' : usage.item_code,
                'item_description' : item_descriptions[usage.item_code],
                'component_item_code' : usage.component_item_code,
                'component_item_description' : usage.component_item_description,
                'start_time' : float(usage.start_time),
                'prod_line' : usage.prod_line,
                'component_onhand_after_run' : usage.component_onhand_after_run,
                'component_run_qty' : usage.run_component_qty,
                'run_source' : 'original'
            }
            for usage in item_component_usage_queryset
        ]

    for key, value in this_item_component_usages.items():
        for item in item_component_usage_list:
            if item['component_item_code'] == key:
                if float(item['start_time']) > float(start_time):
                    item['component_onhand_after_run'] = float(item['component_onhand_after_run']) - float(value)
                item['component_item_description'] = CiItem.objects.filter(itemcode__iexact=item['component_item_code']).first().itemcodedesc

    for item in item_component_usage_list:
        if item['component_onhand_after_run'] < 0:
            item['component_shortage'] = True
        else:
            item['component_shortage'] = False
        if "SCHEDULED: " in item['prod_line']:
            item['prod_line'] = item['prod_line'].replace("SCHEDULED: ", "")

    return item_component_usage_list

def calculate_new_shortage(item_code, additional_qty):
    """
    Calculates the new first shortage time for an item based on a new on-hand quantity.
    
    Args:
        item_code (str): The item code to check
        new_onhand_qty (float): The new on-hand quantity to use in calculations
        
    Returns:
        float: The new shortage time in hours, or None if no shortage found
    """
    # Get all component usage records for this item where quantity goes negative
    usage_records = ComponentUsage.objects.filter(
        component_item_code__iexact=item_code,
        component_onhand_after_run__lt=0
    ).order_by('start_time')
    
    if not usage_records.exists():
        return None
    if item_code=='TOTE-USED/NEW':
        return None
    
    # Add additional quantity to each record's component_onhand_after_run
    for record in usage_records:
        # print(f'{record.component_item_code}, start_time = {record.start_time}, oh after = {record.component_onhand_after_run}')
        adjusted_onhand = record.component_onhand_after_run + additional_qty
        # print(f'adjusted_onhand = {adjusted_onhand}')

        # If adjusted quantity is still negative, this is where shortage occurs
        if adjusted_onhand < 0:
            return {'start_time' : record.start_time, 'component_onhand_after_run' : record.component_onhand_after_run}

    # No shortage found
    return None

def get_component_consumption(component_item_code, blend_item_code_to_exclude):
    """Get component consumption details for a given component item code.

    Calculates how much of a component is needed by different blends, excluding a specified
    blend item code. Looks at component shortages and bill of materials to determine:
    - Which blends use this component
    - How much of the component each blend needs
    - Total component usage across all blends
    
    Args:
        component_item_code (str): Item code of the component to analyze
        blend_item_code_to_exclude (str): Item code of blend to exclude from analysis
        
    Returns:
        dict: Component consumption details including:
            - Per blend: item code, description, qty needed, first shortage date, component usage
            - Total component usage across all blends
    """
    item_codes_using_this_component = []
    for bill in BillOfMaterials.objects.filter(component_item_code__iexact=component_item_code).exclude(item_code__iexact=blend_item_code_to_exclude).exclude(item_code__startswith="/"):
        item_codes_using_this_component.append(bill.item_code)
    shortages_using_this_component = ComponentShortage.objects.filter(component_item_code__in=item_codes_using_this_component).exclude(component_item_code__iexact=blend_item_code_to_exclude)
    total_component_usage = 0
    component_consumption = {}
    for shortage in shortages_using_this_component:
        this_bill = BillOfMaterials.objects.filter(item_code__iexact=shortage.component_item_code) \
            .filter(component_item_code__iexact=component_item_code) \
            .exclude(item_code__startswith="/") \
            .first()
        # shortage.component_usage = shortage.adjustedrunqty * this_bill.qtyperbill
        total_component_usage += float(shortage.run_component_qty)
        component_consumption[shortage.component_item_code] = {
            'blend_item_code' : shortage.component_item_code,
            'blend_item_description' : shortage.component_item_description,
            'blend_total_qty_needed' : shortage.three_wk_short,
            'blend_first_shortage' : shortage.start_time,
            'component_usage' : shortage.run_component_qty
            }
    component_consumption['total_component_usage'] = float(total_component_usage)
    return component_consumption
