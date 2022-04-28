from django.urls import path
from core import views

urlpatterns = [
    path('safetychecklist/', views.safetychecklist, name='safety-checklist'),
    path('blendthese/', views.blendsforthese, name='blend-these'),
    path('lotnumbersfromexcel/', views.lotnumsfromexcel, name='lot-numbers'),
    #path('lotnumform', views.lotnumform, name='lot-number-form')
    #path('blendsheet/', name='blend-sheet'),
]