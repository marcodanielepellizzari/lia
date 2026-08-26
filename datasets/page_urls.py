from django.urls import path
from . import page_views

urlpatterns = [
    path("", page_views.DatasetListView.as_view(), name="dataset-list"),
    path("new/", page_views.DatasetCreateView.as_view(), name="dataset-create"),
    path("<int:pk>/", page_views.DatasetDetailView.as_view(), name="dataset-detail"),
    path("<int:pk>/upload/", page_views.upload_file, name="dataset-upload"),
    path("<int:pk>/upload/map/", page_views.upload_map_columns, name="dataset-upload-map"),
    path("<int:pk>/upload/preview/", page_views.upload_preview, name="dataset-upload-preview"),
    path("<int:pk>/upload/rejected-rows/", page_views.download_rejected_rows, name="dataset-rejected-rows"),
    path("<int:pk>/share/", page_views.dataset_share_manage, name="dataset-share"),
    path("<int:pk>/submit-review/", page_views.dataset_submit_for_review, name="dataset-submit-review"),
]
