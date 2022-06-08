from django.urls import path, include
from kpklauncher import views

urlpatterns = [
    path("launcher/", views.launcher, name="launcher")   
]