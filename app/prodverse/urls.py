from django.urls import path
from prodverse import views
from core import views

urlpatterns = [
    path('pickticket/<str:item_code>/', views.display_pickticket_detail, name='specsheet_detail'),
    path('productionschedule/', views.display_production_schedule, name='production_schedule'),
    path('specsheet/<str:item_code>/', views.display_specsheet_detail, name='specsheet_detail'),
    path('specsheet/specsheet-lookup', views.display_specsheet_lookup_page, name='specsheet_error_page'),
    path('lookupitemquantity/', core.views.display_lookup_item_quantity, name='core_lookup_item'),
]