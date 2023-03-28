from django.urls import path
from prodverse import views as prodverse_views
from core import views as core_views

urlpatterns = [
    path('pick-ticket/<str:item_code>/', prodverse_views.display_pickticket_detail, name='spec-sheet-detail'),
    path('production-schedule/', prodverse_views.display_production_schedule, name='production-schedule'),
    path('spec-sheet/<str:item_code>/<str:po_number>/<str:juliandate>/', prodverse_views.display_specsheet_detail, name='spec-sheet-detail'),
    path('spec-sheet-lookup/', prodverse_views.display_specsheet_lookup_page, name='spec-sheet-error-page'),
    path('lookup-item-quantity/', core_views.display_lookup_item_quantity, name='core-lookup-item'),
]