from core.models import DeskOneSchedule, DeskTwoSchedule, BillOfMaterials
from django.db.models import Q
from django.http import JsonResponse

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