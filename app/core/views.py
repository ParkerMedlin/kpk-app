from django.shortcuts import render
from .models import lotnumexcel, safetyChecklistForm, lotnumrecord, lotnumrecordForm
from .models import blendthese
from django.http import HttpResponseRedirect
from datetime import datetime

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
    get_blends = blendthese.objects.all()
    return render(request, 'core/blendthese.html', {'blendlist': get_blends,})


def lotnumsfromexcel(request):
    get_excellotnums = lotnumexcel.objects.order_by('-date')
    return render(request, 'core/lotnumsfromexcel.html', {'lotnumlist': get_excellotnums,})


def lotnumrecords(request):
    get_lotnums = lotnumrecord.objects.all()
    return render(request, 'core/lotnumrecords.html', {'lotnumlist': get_lotnums})


def lotnumform(request):
    submitted = False
    if request.method == "POST":
        form = lotnumrecordForm(request.POST)
        if form.is_valid():
            newLotNumSubmission = form.save(commit=False)
            today = datetime.today()
            newLotNumSubmission.date = today
            newLotNumSubmission.save()
            return HttpResponseRedirect('/core/lotnumrecords')
    else:
        form = lotnumrecordForm
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/lotnumform.html', {'form':form, 'submitted':submitted})

#def blendsheet(request):
#    procQ = procedurelist.objects.all()
#    ingQ = bm_billdetail.objects.all()
#    
#    return render(request, 'core/blendthese.html', {'procedurelist': get_blends,})


# -------------- EXCEL-BASED TABLE UPDATERS -------------- #

# -------------- SAGE-BASED TABLE UPDATERS -------------- #