from django.urls import path
from prodverse.views import *

urlpatterns = [
    path('productionschedule/', display_production_schedule, name='excel_inline'),
    path('specsheet/<str:item_code>/', display_specsheet_detail, name='specsheet_detail'),
    path('specsheet/specsheet-error', display_specsheet_error_page, name='specsheet_error_page'),
    path('productionschedule/', display_production_schedule, name='excel_inline'),