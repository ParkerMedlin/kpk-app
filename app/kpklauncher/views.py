from django.shortcuts import render
    
def launcher(request):
    return render(request, 'kpklauncher/launcher.html')

