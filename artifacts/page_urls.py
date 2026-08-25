from django.urls import path
from . import page_views

urlpatterns = [
    path("", page_views.ArtifactSetListView.as_view(), name="artifactset-list"),
    path("new/", page_views.ArtifactSetCreateView.as_view(), name="artifactset-create"),
    path("<int:pk>/", page_views.ArtifactSetDetailView.as_view(), name="artifactset-detail"),
    path("<int:pk>/add/", page_views.artifact_add_manual, name="artifact-add-manual"),
    path("<int:pk>/upload-csv/", page_views.artifact_upload_csv, name="artifact-upload-csv"),
    path("<int:pk>/artifacts/<int:artifact_pk>/delete/", page_views.artifact_delete, name="artifact-delete"),
]
