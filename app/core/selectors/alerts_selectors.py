from core.models import FormulaChangeAlert
from django.http import JsonResponse

async def get_active_formula_change_alerts(request):
    """
    Asynchronously retrieves active formula change alerts.
    Returns a JSON list of objects, each containing:
    - ingredient_item_code
    - notification_trigger_quantity
    - parent_item_codes (the list of parent items this alert applies to)
    """
    try:
        
        alerts_data = []
        # Since is_active was removed, we fetch all.
        # If is_active is ever re-introduced, filter here: FormulaChangeAlert.objects.filter(is_active=True)
        for alert in FormulaChangeAlert.objects.all():
            alerts_data.append({
                'ingredient_item_code': alert.ingredient_item_code,
                'notification_trigger_quantity': alert.notification_trigger_quantity,
                'parent_item_codes': alert.parent_item_codes 
            })

        
        return JsonResponse({'alerts_data': alerts_data})
    except Exception as e:
        # Log the exception e
        return JsonResponse({'error': str(e)}, status=500)