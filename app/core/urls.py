from django.urls import path
from core import views

urlpatterns = [
    path('safetychecklist/', views.safetychecklist, name='safety-checklist'),
    path('blendthese/', views.blendsforthese, name='blend-these'),
    path('lotnumbers/', views.lotnums, name='lot-numbers'),
]