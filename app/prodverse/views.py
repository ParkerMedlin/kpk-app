from django.shortcuts import render
from .models import *

def display_production_schedule(request):
    return render(request, 'prodverse/productionschedule.html')