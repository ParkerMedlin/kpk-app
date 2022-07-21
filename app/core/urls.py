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
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('blendsheet/<lot>/', views.blendsheet, name='blendsheet'),
    path('blendthese/', views.blendsforthese, name='blend-these'),
    path('lotnumform/', views.lotnumform, name='lot-number-form'),
    path('lotnumrecords/', views.lotnumrecords, name='lot-num-records'),
    path('forkliftchecklist/', views.forkliftchecklist, name='forklift-checklist'),
    path('forkliftchecklist/forkliftserial_request/', views.forkliftserial_request, name='forkliftid_request'),
    path('lotnumform/itemcodedesc_request/', views.itemcodedesc_request, name='itemcodedesc_request1'),
    path('reports/itemcodedesc_request/', views.itemcodedesc_request, name='itemcodedesc_request2'),
    path('reports/', views.reportcenter, name='reporthomebase'),
    path('reports/<which_report>/<part_number>', views.reportmaker, name='report'),
    path('upcomingcounts/', views.upcomingblendcounts, name='upcomingcounts'),
    path('testpage/', views.testPageFunction, name='testpage'),
]