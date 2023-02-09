from django.urls import path
from prodverse.views import *

urlpatterns = [
    path('productionschedule/', display_production_schedule, name='excel_inline'),
]