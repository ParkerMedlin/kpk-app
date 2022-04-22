from django.shortcuts import render
from .models import safetyChecklistForm
from django.http import HttpResponseRedirect
from datetime import datetime

def safetychecklist(request):
    submitted = False
    if request.method == "POST":
        form = safetyChecklistForm(request.POST)
        if form.is_valid():
            checklistSubmission = form.save(commit=False)
            now = datetime.now()
            checklistSubmission.date = datetime.now()
            current_user = request.user
            checklistSubmission.operator_name = (current_user.first_name + " " + current_user.last_name)
            checklistSubmission.save()
            return HttpResponseRedirect('/core/safetychecklist?submitted=True')
    else:
        form = safetyChecklistForm
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'core/forkliftsafetylist.html', {'form':form, 'submitted':submitted})