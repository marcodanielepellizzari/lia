from django.urls import path
from . import page_views

urlpatterns = [
    path("", page_views.MergeRequestListView.as_view(), name="merge-request-list"),
    path("<int:pk>/", page_views.merge_request_detail, name="merge-request-detail"),
]
