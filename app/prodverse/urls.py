from django.urls import path, include
from core.views import display_batch_issue_table
from prodverse.views import display_lookup_item, display_excel_inline, get_json_item_info, get_json_item_from_desc, get_json_ciItem_fields

urlpatterns = [
    path('batchIssueTable/<line>', display_batch_issue_table, name='batchIssueTable'),
    path('getciItemFields/', get_json_ciItem_fields, name='get-item-info'),
    path('excelinline/', display_excel_inline, name='excel_inline'),
    path('lookupitem/', display_lookup_item, name='lookup_item'),
    path('lookupitem/iteminfo_request/', get_json_item_info, name='get-item-info'),
    path('lookupitem/iteminfo_fromdesc_request/', get_json_item_from_desc, name='get-info-from-desc')
]