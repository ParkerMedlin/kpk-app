from django.urls import path, include
from core import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'BlendBillOfMaterials', views.BlendBillOfMaterialsViewSet)
router.register(r'BlendInvLog', views.BlendInvLogViewSet)
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
    path('blendsheet/<lot>/', views.blendsheet, name='blendsheet'),
    path('blendsheetcomplete/', views.blendsheetcomplete, name='blendsheetcomplete'),
    path('blendsheet/', views.blendsheet, name='blendsheet'),
    path('lotnumform/itemcodedesc_request/', views.get_json_item_description, name='get-item-desc-lotnumform'),
    path('reports/itemcodedesc_request/', views.get_json_item_description, name='get-item-desc-reportcenter'),
    path('reports/', views.reportcenter, name='reporthomebase'),
    path('reports/<which_report>/<part_number>', views.reportmaker, name='report'),
    path('upcomingcounts/', views.upcomingblendcounts, name='upcomingcounts'),
    path('addlot/<lotnum>/<partnum>/<blendarea>', views.thisLotToSchedule, name='addLotPage'),
    path('blendschedule/<blendarea>', views.blendSchedule, name='blendSchedule'),
    path('mngReq/<reqType>/<blend_area>/<blend_id>/<blend_listposition>', views.blndSchedMgmt, name='schedMngr'), 
    path('batchIssueTable/<line>', views.batchIssueTable, name='batchIssueTable'),
    path('issuesheets/<prodLine>/<issueDate>', views.issueSheets, name='issueSheets'),
    path('testpage/<prodLine>/<issueDate>', views.testPageFunction, name='testpage'),
]