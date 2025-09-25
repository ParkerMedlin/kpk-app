from core.models import FoamFactor
from core.forms import FoamFactorForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render

def update_foam_factor(request, foam_factor_id):
    """
    Updates an existing foam factor record with new data from POST request.
    
    Args:
        request: HTTP request object containing form data
        foam_factor_id: ID of the foam factor record to update
        
    Returns:
        HttpResponseRedirect to foam factors page after update
        
    Raises:
        Http404: If foam factor record with given ID does not exist
    """
    if request.method == "POST":
        print(foam_factor_id)
        request.GET.get('edit-yes-no', 0)
        foam_factor = get_object_or_404(FoamFactor, id = foam_factor_id)
        edit_foam_factor = FoamFactorForm(request.POST or None, instance=foam_factor, prefix='editFoamFactorModal')

        if edit_foam_factor.is_valid():
            edit_foam_factor.save()

        return HttpResponseRedirect('/core/foam-factors')

def delete_foam_factor(request, foam_factor_id):
    """
    Deletes a foam factor record with the specified ID.
    
    Args:
        request: HTTP request object
        foam_factor_id: ID of the foam factor record to delete
        
    Returns:
        Redirect to foam factors display page after deletion
        
    Raises:
        FoamFactor.DoesNotExist: If foam factor with given ID does not exist
    """
    try:
        foam_factor_to_delete = FoamFactor.objects.get(pk=foam_factor_id)
        foam_factor_to_delete.delete()
    except Exception as e:
        print(str(e))

    return redirect('display-foam-factors')

def add_foam_factor(request):
    """
    Handles adding new foam factor records.
    
    Validates and saves new foam factor submissions, checking for duplicates.
    If duplicate item code found, returns error form for editing existing record.
    
    Args:
        request: HTTP request object containing form data
        
    Returns:
        Redirect to foam factors list on success, or error form on validation failure
        
    Template:
        core/foamfactorerrorform.html (on error)
    """

    if 'addNewFoamFactor' in request.POST:
        add_foam_factor_form = FoamFactorForm(request.POST, prefix='addFoamFactorModal')
        distinct_item_codes = FoamFactor.objects.values_list('item_code', flat=True).distinct()
        if add_foam_factor_form.is_valid() and add_foam_factor_form.cleaned_data['item_code'] not in distinct_item_codes:
            new_foam_factor = FoamFactor()
            new_foam_factor = add_foam_factor_form.save()
            return redirect('display-foam-factors')
        else:
            if add_foam_factor_form.cleaned_data['item_code'] in distinct_item_codes:
                specific_error_designation = "The item below already had a foam factor. If you'd like to edit it, you may do so below."
                foam_factor_id = FoamFactor.objects.filter(item_code__iexact=add_foam_factor_form.cleaned_data['item_code']).first().id
                foam_factor = FoamFactor.objects.get(pk=foam_factor_id)
                foam_factor_form = FoamFactorForm(instance=foam_factor, prefix='editFoamFactorModal')
                edit_or_add = 'edit'
            else:
                specific_error_designation = None
                edit_or_add = 'add'
            return render(request, 'core/foamfactorerrorform.html', {'foam_factor_form' : foam_factor_form, 
                                                                     'specific_error' : specific_error_designation,
                                                                     'foam_factor_id' : foam_factor_id,
                                                                     'edit_or_add' : edit_or_add})