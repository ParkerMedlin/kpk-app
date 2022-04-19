from django.shortcuts import render

def safetychecklist(request):
    submitted = False
    if request.method == "POST":
        form = safetyChecklistForm(request.POST)
        if form.is_valid():
            #now = datetime.now()
            #time = now.strftime('%m/%d/%Y, %I:%M:%S %p')
            #checklistlog.operator_name = 
            checklistSubmission = form.save(commit=False)
            checklistSubmission.operator_name = request.POST.get("username").lower()
            return HttpResponseRedirect('/safetychecklist?submitted=True')
    else:
        form = safetyChecklistForm
        if 'submitted' in request.GET:
            submitted=True

    return render(request, 'blendIO/forkliftsafetylist.html', {'form':form, 'submitted':submitted})