from django.urls import path, include
from core.views import display_batch_issue_table
from prodverse.views import display_lookup_item, get_json_item_info, get_json_item_from_desc

urlpatterns = [
    path('batchIssueTable/<line>', display_batch_issue_table, name='batchIssueTable'),
    path('lookupitem/', display_lookup_item, name='lookup_item'),
    path('lookupitem/iteminfo_request/', get_json_item_info, name='get-item-info'),
    path('lookupitem/iteminfo_fromdesc_request/', get_json_item_from_desc, name='get-info-from-desc')
]