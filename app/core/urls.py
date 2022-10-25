from django.urls import path, include
from core import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'BlendBillOfMaterials', views.BlendBillOfMaterialsViewSet)
router.register(r'CountRecord', views.CountRecordViewSet)
router.register(r'BlendInstruction', views.BlendInstructionViewSet)
router.register(r'BlendThese', views.BlendTheseViewSet)
router.register(r'BmBillDetail', views.BmBillDetailViewSet)
router.register(r'BmBillHeader', views.BmBillHeaderViewSet)
router.register(r'ChecklistLog', views.ChecklistLogViewSet)
router.register(r'CiItem', views.CiItemViewSet)
router.register(r'ImItemCost', views.ImItemCostViewSet)
router.register(r'ImItemtransactionHistory', views.ImItemTransactionHistoryViewSet)
router.register(r'ImItemWarehouse', views.ImItemWarehouseViewSet)
router.register(r'LotNumRecords', views.LotNumRecordViewSet)
router.register(r'PoPurchaseOrderDetail', views.PoPurchaseOrderDetailViewSet)
router.register(r'ProdBillOfMaterials', views.ProdBillOfMaterialsViewSet)
router.register(r'TimetableRunData', views.TimetableRunDataViewSet)
router.register(r'UpcomingBlendCount', views.UpcomingBlendCountViewSet)


urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest-framework')),
    path('forkliftchecklist/', views.display_forklift_checklist, name='forklift-checklist'),
    path('forkliftchecklist/forklift_serial_request/', views.get_json_forklift_serial, name='get-forklift-serial'),
    path('blendthese/', views.display_blend_these, name='blend-these'),
    path('lotnumrecords/', views.display_lot_num_records, name='lot-num-records'),
    path('lotnumform/', views.display_new_lot_form, name='new-lot-num-form'),
    path('blendsheet/<lot>/', views.display_blend_sheet, name='blendsheet'),
    path('blendsheetcomplete/', views.display_conf_blend_sheet_complete, name='blend-sheet-complete'),
    path('blendsheet/', views.display_blend_sheet, name='blendsheet'),
    path('lotnumform/itemcodedesc_request/', views.get_json_item_description, name='get-item-desc-lotnumform'),
    path('reports/itemcodedesc_request/', views.get_json_item_description, name='get-item-desc-reportcenter'),
    path('reports/', views.display_report_center, name='report-center'),
    path('reports/<which_report>/<part_number>', views.display_report, name='report'),
    path('upcomingcounts/', views.display_upcoming_counts, name='upcoming-counts'),
    path('addlot/<lotnum>/<partnum>/<blendarea>', views.add_lot_to_schedule, name='add-lot-to-schedule'),
    path('blendschedule/<blendarea>', views.display_blend_schedule, name='blend-schedule'),
    path('mngReq/<request_type>/<blend_area>/<blend_id>/<blend_list_position>', views.manage_blend_schedule, name='schedule-manager'),
    path('batchIssueTable/<line>', views.display_batch_issue_table, name='batch-issue-table'),
    path('issuesheets/<prod_line>/<issue_date>', views.display_issue_sheets, name='issue-sheets'),
    path('countlist/add/<encoded_list>', views.add_count_list, name='add-count-list'),
    path('countlist/display/<primary_key_str>', views.display_count_list, name='display-count-list'),
    path('countrecords/', views.display_count_records, name='display-count-records'),
    path('allupcomingproduction/', views.display_all_upcoming_production, name='all-upcoming-production'),
    path('chemshortages/', views.display_chem_shortages, name='all-chem-shortages'),
    path('lookuplocation/itemcodedesc_request_itemcode/', views.get_json_chemloc_from_itemcode, name='get-chem-location-from-itemcode'),
    path('lookuplocation/itemcodedesc_request_desc/', views.get_json_chemloc_from_itemdesc, name='get-chem-location-from-desc'),
    path('lookuplocation/', views.display_lookup_location, name='lookup-location'),
    path('tankleveldisplay/', views.display_tank_levels, name='tank-levels'),
    path('testpage/', views.display_test_page, name='test-page'),
]