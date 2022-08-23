from django.urls import path, include
from core import views

urlpatterns = [
    path('batchIssueTable/<line>', views.batchIssueTable, name='batchIssueTable'),
]