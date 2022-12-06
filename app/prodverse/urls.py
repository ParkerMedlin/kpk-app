from django.urls import path, include
from core.views import display_batch_issue_table
from prodverse.views import display_lookup_item, display_excel_inline, get_json_from_item_code, get_json_from_item_desc, get_json_ciItem_fields, get_json_prodBOM_fields

urlpatterns = [
    path('batchIssueTable/<line>', display_batch_issue_table, name='batchIssueTable'),
    path('getciItemFields/', get_json_ciItem_fields, name='get-item-info'),
    path('excelinline/', display_excel_inline, name='excel_inline'),
    path('lookupitem/', display_lookup_item, name='lookup_item'),
    path('getprodBOMfields/', get_json_prodBOM_fields, name='get-json-prodBOM-fields'),
    path('infofromitemcode_request/', get_json_from_item_code, name='get-item-info'),
    path('infofromitemdesc_request/', get_json_from_item_desc, name='get-info-from-desc')
]