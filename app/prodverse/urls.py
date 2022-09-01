from django.urls import path, include
from core import views

urlpatterns = [
    path('batchIssueTable/<line>', views.display_batch_issue_table, name='batchIssueTable'),
]