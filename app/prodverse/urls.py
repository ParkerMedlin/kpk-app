from django.urls import path
from prodverse import views

urlpatterns = [
    path('productionschedule/', views.display_production_schedule, name='excel_inline'),
    path('specsheet/<str:item_code>/', views.display_specsheet_detail, name='specsheet_detail'),
    path('specsheet/specsheet-error', views.display_specsheet_error_page, name='specsheet_error_page'),
    path('productionschedule/', views.display_production_schedule, name='excel_inline')
]