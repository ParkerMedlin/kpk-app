from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from datetime import date
from .models import OperatingSupply

@login_required
def display_operating_supplies_checklist(request):
    supplies = OperatingSupply.objects.filter(is_active=True).order_by('name')
    return render(request, 'core/operating_supplies/checklist.html', {'supplies': supplies})

@login_required
@require_POST
def add_operating_supply(request):
    name = request.POST.get('name')
    notes = request.POST.get('notes')
    if name:
        OperatingSupply.objects.create(name=name, notes=notes)
    return redirect('operating_supplies_checklist')

@login_required
@require_POST
def update_operating_supply(request, supply_id):
    supply = get_object_or_404(OperatingSupply, id=supply_id)
    supply.name = request.POST.get('name', supply.name)
    supply.notes = request.POST.get('notes', supply.notes)
    supply.save()
    return redirect('operating_supplies_checklist')

@login_required
@require_POST
def delete_operating_supply(request, supply_id):
    try:
        supply = get_object_or_404(OperatingSupply, id=supply_id)
        supply.is_active = False
        supply.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def check_operating_supply(request, supply_id):
    try:
        supply = get_object_or_404(OperatingSupply, id=supply_id)
        supply.last_checked_by = request.user
        supply.last_checked_date = date.today()
        supply.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}) 