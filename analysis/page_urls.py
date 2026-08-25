from django.urls import path
from . import page_views

urlpatterns = [
    path("", page_views.pb_diagrams, name="pb-diagrams"),
]
