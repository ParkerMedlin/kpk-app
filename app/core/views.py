from django.shortcuts import render
from .models import lotnumexcel, safetyChecklistForm
from .models import Blendthese
from django.http import HttpResponseRedirect
from datetime import datetime
#import pandas as pd # dataframes
import os # for obtaining user path
import psycopg2 # connect w postgres db
import pyexcel as pe # grab the sheet
#import pyodbc # connect w Sage db
import time

def safetychecklist(request):
    submitted = False
    if request.method == "POST":
        form = safetyChecklistForm(request.POST)
        if form.is_valid():
            checklistSubmission = form.save(commit=False)
            now = datetime.now()
            checklistSubmission.date = now
            current_user = request.user
            checklistSubmission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklistSubmission.save()
            return HttpResponseRedirect('/core/safetychecklist?submitted=True')
    else:
        form = safetyChecklistForm
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/forkliftsafetylist.html', {'form':form, 'submitted':submitted})

def blendsforthese(request):
    get_blends = Blendthese.objects.all()
    return render(request, 'core/blendthese.html', {'data': get_blends,})

def lotnums(request):
    get_lotnums = lotnumexcel.objects.all()
    return render(request, 'core/lotnumbers.html', {'data': get_lotnums,})


# -------------- EXCEL-BASED TABLE UPDATERS -------------- #

# -------------- SAGE-BASED TABLE UPDATERS -------------- #