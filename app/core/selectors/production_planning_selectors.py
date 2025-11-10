import logging

from core.models import CiItem, ComponentShortage, DeskOneSchedule, DeskTwoSchedule, BillOfMaterials
from django.db.models import Q
from django.http import JsonResponse

logger = logging.getLogger(__name__)

MARINE_LINE_PGAF = [
    '052004N', '052006', '052070', '32500.B', '32700.B', '32800.B',
    '33200CONC.B', '33200DIL.B', '33200DILRED.B', '33300.B', '33400.B',
    '33700.B', '33900.B', '619529-BLUE.B', 'AF600.B', 'ANT1G.B',
    'ANT1G5050.B', 'ANT27BLUE.B'
]


def get_excluded_blend_item_codes():
    """Return blend item codes that should always be excluded from shortages."""
    excluded_qs = (
        CiItem.objects
        .filter(productline__in=['W/W', 'PGAF'])
        .filter(itemcodedesc__startswith='BLEND')
        .exclude(itemcode__in=MARINE_LINE_PGAF)
        .values_list('itemcode', flat=True)
    )
    excluded_codes = list(excluded_qs)
    logger.debug('Excluded %s blend item codes from shortages view.', len(excluded_codes))
    return excluded_codes


def get_schedulable_blend_shortages():
    """Return the base queryset used by the blend shortages dashboard."""
    excluded_item_codes = get_excluded_blend_item_codes()
    return (
        ComponentShortage.objects
        .filter(component_item_description__startswith='BLEND')
        .filter(procurement_type__iexact='M')
        .filter(component_instance_count=1)
        .exclude(prod_line__iexact='Hx')
        .exclude(component_item_code__in=excluded_item_codes)
        .order_by('start_time')
    )

def get_components_in_use_soon(request):
    """Get list of components that will be used soon in scheduled blends.
    
    Queries the blend schedules (Desk 1 and Desk 2) to find upcoming blends,
    then looks up their bill of materials to identify chemical, dye and fragrance
    components that will be needed.

    Args:
        request: HTTP request object
        
    Returns:
        JsonResponse containing list of component item codes that will be used soon
        in scheduled blends
    """
    blends_in_demand = [item.item_code for item in DeskOneSchedule.objects.all()]
    blends_in_demand.append(item.item_code for item in DeskTwoSchedule.objects.all())
    boms_in_use_soon = BillOfMaterials.objects \
                                .filter(item_code__in=blends_in_demand) \
                                .filter((Q(component_item_description__startswith="CHEM") | Q(component_item_description__startswith="DYE") | Q(component_item_description__startswith="FRAGRANCE")))
    components_in_use_soon = { 'componentList' : [item.component_item_code for item in boms_in_use_soon]}

    return JsonResponse(components_in_use_soon, safe=False)
