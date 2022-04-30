from django.urls import path
from core import views

urlpatterns = [
    path('safetychecklist/', views.safetychecklist, name='safety-checklist'),
    path('blendthese/', views.blendsforthese, name='blend-these'),
    path('lotnumbersfromexcel/', views.lotnumsfromexcel, name='lot-numbers-excel'),
    path('lotnumrecords/', views.lotnumrecords, name='lot-num-records'),
    path('lotnumform/', views.lotnumform, name='lot-number-form'),
    #path('blendsheet/', name='blend-sheet'),
]