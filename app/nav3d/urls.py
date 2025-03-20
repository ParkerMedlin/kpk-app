from django.urls import path
from . import views

app_name = 'nav3d'

urlpatterns = [
    path('', views.nav3d_interface, name='interface'),
] 