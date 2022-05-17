from django.urls import path, include
from core import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'checklistlogs', views.checklistlogViewSet)
router.register(r'blendtheseblends', views.blendtheseViewSet)
router.register(r'lotnumrecords', views.lotnumrecordViewSet)
router.register(r'blendInstructions', views.blendInstructionViewSet)
router.register(r'PoPurchaseorderdetails', views.PoPurchaseorderdetailViewSet)
router.register(r'ImItemwarehouse', views.ImItemwarehouseViewSet)
router.register(r'ImItemtransactionhistory', views.ImItemtransactionhistoryViewSet)
router.register(r'ImItemcost', views.ImItemcostViewSet)
router.register(r'CiItem', views.CiItemViewSet)
router.register(r'BmBillheader', views.BmBillheaderViewSet)
router.register(r'BmBilldetail', views.BmBilldetailViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('blendsheet/', views.blendsheet, name='blendsheet'),
    path('blendthese/', views.blendsforthese, name='blend-these'),
    path('lotnumform/', views.lotnumform, name='lot-number-form'),
    path('blendsheet/<part_number>/<lot_number>/<quantity>/', views.blendsheet, name='blendsheet'),
    path('lotnumrecords/', views.lotnumrecords, name='lot-num-records'),
    path('safetychecklist/', views.safetychecklist, name='safety-checklist'),
]