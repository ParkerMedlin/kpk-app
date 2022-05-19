from django.urls import path, include
from core import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'BlendInstructions', views.BlendInstructionViewSet)
router.register(r'BlendThese', views.BlendTheseViewSet)
router.register(r'BmBillDetail', views.BmBillDetailViewSet)
router.register(r'BmBillHeader', views.BmBillHeaderViewSet)
router.register(r'ChecklistLogs', views.ChecklistLogViewSet)
router.register(r'CiItem', views.CiItemViewSet)
router.register(r'ImItemCost', views.ImItemCostViewSet)
router.register(r'ImItemtransactionHistory', views.ImItemTransactionHistoryViewSet)
router.register(r'ImItemWarehouse', views.ImItemWarehouseViewSet)
router.register(r'LotNumRecords', views.LotNumRecordViewSet)
router.register(r'PoPurchaseOrderDetails', views.PoPurchaseOrderDetailViewSet)







urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('blendsheet/', views.blendsheet, name='blendsheet'),
    path('blendthese/', views.blendsforthese, name='blend-these'),
    path('lotnumform/', views.lotnumform, name='lot-number-form'),
    path('blendsheet/<part_number>/<lot_number>/<quantity>/', views.blendsheet, name='blendsheet'),
    path('lotnumrecords/', views.lotnumrecords, name='lot-num-records'),
    path('safetychecklist/', views.safetychecklist, name='safety-checklist'),
    path('lotnumform/itemcodedesc_request/', views.itemcodedesc_request, name='itemcodedesc_request')
]