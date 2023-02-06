from django.urls import path, include
from core.views import display_batch_issue_table
from prodverse.views import *

urlpatterns = [
    path('batchIssueTable/<line>', display_batch_issue_table, name='batchIssueTable'),
    path('getciItemFields/', get_json_ciItem_fields, name='get-item-info'),
    path('productionschedule/', display_production_schedule, name='excel_inline'),
    path('lookupitem/', display_lookup_item, name='lookup_item'),
    path('getBOMfields/', get_json_prodBOM_fields, name='get-json-prodBOM-fields'),
    path('item_info_request/', get_json_item_info, name='get-item-info-prodverse'),
]