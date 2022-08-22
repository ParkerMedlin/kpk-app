from django.urls import path, include
from core import views

urlpatterns = [
    path('issuesheet/<line>', views.issueSheets, name='issuesheet'),
]