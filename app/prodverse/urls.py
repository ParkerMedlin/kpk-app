from django.urls import path
from prodverse import views as prodverse_views
from core import views as core_views

urlpatterns = [
    path("get_last_modified/<str:file_name>/", prodverse_views.get_last_modified, name="get_last_modified"),
    path('item-qc/', prodverse_views.display_item_qc, name='itemqc'),
    path('pick-ticket/<str:item_code>/', prodverse_views.display_pickticket_detail, name='spec-sheet-detail'),
    path('production-schedule/', prodverse_views.display_production_schedule, name='production-schedule'),
    path('spec-sheet/<str:item_code>/<str:po_number>/<str:juliandate>/', prodverse_views.display_specsheet_detail, name='spec-sheet-detail'),
    path('spec-sheet-lookup/', prodverse_views.display_specsheet_lookup_page, name='spec-sheet-error-page'),
    path('lookup-item-quantity/', core_views.display_lookup_item_quantity, name='core-lookup-item'),
    path('update-checkbox-state/<int:row_id>', views.update_checkbox_state, name='update_checkbox_state'),
    path('update-dropdown-state/<int:row_id>', views.update_dropdown_state, name='update_dropdown_state'),
    path('get-row-state/<int:row_id>', views.get_row_state, name='get_row_state'),
]