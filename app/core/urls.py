from django.urls import path
from core import views

urlpatterns = [
    path('safetychecklist/', views.safetychecklist, name='safety-checklist'),
]