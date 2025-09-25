from core.models import GHSPictogram
from django.shortcuts import redirect

def delete_ghs_pictogram(request):
    """Delete a GHS pictogram record.
    
    Deletes the GHS pictogram record with the specified ID and redirects to the provided page.
    
    Args:
        request: HTTP request containing:
            redirect-page (str): Page to redirect to after deletion
            id (int): ID of GHS pictogram record to delete
            
    Returns:
        Redirect to specified page after deleting record
    """
    redirect_page = request.GET.get("redirect-page", 0)
    id_item_to_delete = request.GET.get("id", 0)
    GHSPictogram.objects.get(pk=id_item_to_delete).delete()

    return redirect(redirect_page)

def update_ghs_pictogram(request):
    """Update a GHS pictogram record.
    
    Updates the GHS pictogram record with the specified ID using form data.
    Handles file upload for new pictogram images.
    
    Args:
        request: HTTP POST request containing:
            id (int): ID of GHS pictogram to update
            item_code (str): Item code
            item_description (str): Item description
            image_reference (File): New pictogram image file
            
    Returns:
        Redirect to GHS label search page after update
    """
    if request.method == "POST":
        id_to_update = request.POST.get("id", 0)
        this_ghs_pictogram = GHSPictogram.objects.get(pk=id_to_update)
        this_ghs_pictogram.item_code = request.POST.get("item_code", "")
        this_ghs_pictogram.item_description = request.POST.get("item_description", "")
        if request.FILES.get("image_reference", False):
            this_ghs_pictogram.image_reference = request.FILES["image_reference"]
        this_ghs_pictogram.save()
    return redirect('display-ghs-label-search')