from django.urls import path, include
from core.views import display_batch_issue_table
from prodverse.views import *

urlpatterns = [
    path('batchIssueTable/<line>', display_batch_issue_table, name='batchIssueTable'),
    path('getBOMfields/', get_json_prodBOM_fields, name='get-json-prodBOM-fields'),
    path('getciItemFields/', get_json_ciItem_fields, name='get-item-info'),
    path('item_info_request/', get_json_item_info, name='get-item-info'),
    path('lookupitem/', display_lookup_item, name='lookup_item'),
    path('productionschedule/', display_production_schedule, name='excel_inline'),
    path('specsheet/<str:item_code>/', display_specsheet_detail, name='specsheet_detail'),
    path('specsheet/specsheet-error', display_specsheet_error_page, name='specsheet_error_page'),
]