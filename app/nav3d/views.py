from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def nav3d_interface(request):
    """
    Renders the 3D navigation interface for the navbar
    """
    return render(request, 'nav3d/interface.html') 