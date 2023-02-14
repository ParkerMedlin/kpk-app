from django.urls import path
from prodverse import views as prodverse_views
from core import views as core_views

urlpatterns = [
    path('pickticket/<str:item_code>/', prodverse_views.display_pickticket_detail, name='specsheet_detail'),
    path('productionschedule/', prodverse_views.display_production_schedule, name='production_schedule'),
    path('specsheet/<str:item_code>/', prodverse_views.display_specsheet_detail, name='specsheet_detail'),
    path('specsheet-lookup/', prodverse_views.display_specsheet_lookup_page, name='specsheet_error_page'),
    path('lookupitemquantity/', core_views.display_lookup_item_quantity, name='core_lookup_item'),
]