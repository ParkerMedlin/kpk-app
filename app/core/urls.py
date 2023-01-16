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
    path('blendshortages/', views.display_blend_these, name='blend-shortages'),
    path('lotnumrecords/', views.display_lot_num_records, name='display-lot-num-records'),
    path('addlotnumrecord/', views.add_lot_num_record, name='add-lot-num-record'),
    path('updatelotnumrecord/<lot_num_id>', views.update_lot_num_record, name='update-lot-num-record'),
    path('deletelotnumrecords/<records_to_delete>', views.delete_lot_num_records, name='delete-lot-num-records'),
    path('lotnumform/', views.display_new_lot_form, name='new-lot-num-form'),
    path('blendsheet/<lot>/', views.display_blend_sheet, name='blendsheet'),
    path('blendsheetcomplete/', views.display_conf_blend_sheet_complete, name='blend-sheet-complete'),
    path('blendsheet/', views.display_blend_sheet, name='blendsheet'),
    path('infofromitemdesc_request/', views.get_json_from_item_desc, name='get-json-from-item-desc'),
    path('infofromitemcode_request/', views.get_json_from_item_code, name='get-json-from-item-code'),
    path('reports/', views.display_report_center, name='report-center'),
    path('reports/<which_report>/<part_number>', views.display_report, name='report'),
    path('adddeskonescheduleitem/', views.add_deskone_schedule_item, name='add-lot-to-deskone-schedule'),
    path('adddesktwoscheduleitem/', views.add_desktwo_schedule_item, name='add-lot-to-desktwo-schedule'),
    path('blendschedule/<blendarea>', views.display_blend_schedule, name='blend-schedule'),
    path('mngReq/<request_type>/<blend_area>/<blend_id>/<blend_list_position>', views.manage_blend_schedule, name='schedule-manager'),
    path('batchIssueTable/<line>', views.display_batch_issue_table, name='batch-issue-table'),
    path('issuesheets/<prod_line>/<issue_date>', views.display_issue_sheets, name='issue-sheets'),
    path('blendcountsheets/', views.display_upcoming_counts, name='upcoming-counts'),
    path('countlist/add/<encoded_partnumber_list>/<encoded_pk_list>', views.add_count_list, name='add-count-list'),
    path('countlist/display/<encoded_pk_list>', views.display_count_list, name='display-count-list'),
    path('displayfinishedcounts/<encoded_pk_list>', views.display_count_report, name='display-finished-counts'),
    path('delete_countrecord/<redirect_page>/<items_to_delete>/<all_items>', views.delete_count_record, name='delete-count-record'),
    path('countrecords/', views.display_count_records, name='display-count-records'),
    path('productionblendruns/', views.display_all_upcoming_production, name='production-blend-runs'),
    path('chemshortages/', views.display_chem_shortages, name='all-chem-shortages'),
    path('chemloc_request_itemcode/', views.get_json_chemloc_from_itemcode, name='get-chem-location-from-itemcode'),
    path('chemloc_request_itemdesc/', views.get_json_chemloc_from_itemdesc, name='get-chem-location-from-itemdesc'),
    path('lookuplocation/', views.display_lookup_location, name='lookup-location'),
    path('lookuplotnum/', views.display_lookup_lotnums, name='lookup_lotnums'),
    path('tanklevels/', views.display_tank_levels, name='tank-levels'),
    path('gettankspecs/', views.get_json_tank_specs, name='get-tank-specs'),
    path('gettanklevels/', views.get_tank_levels_html, name='get-tanks-html'),
    path('getblendBOMfields/', views.get_json_blendBOM_fields, name='get-json-blend-bom-fields'),
    path('checklistmgmt/', views.display_checklist_mgmt_page, name='display-checklist-mgmt-page'),
    path('updateforkliftsubtracker/', views.update_submission_tracker, name='update-submission-tracker'),
    path('emailsubmissionreport/<recipient_address>', views.email_submission_report, name='email-submission-report'),
    path('emailissuereport/<recipient_address>', views.email_issue_report, name='email-issue-report'),
    path('testpage/', views.display_test_page, name='test-page'),
]