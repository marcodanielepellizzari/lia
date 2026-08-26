"""
HTML pages (Django templates) for data loading and dataset management.
The DRF APIs in datasets/views.py remain available for future use
(external clients, analysis pages) but are not the main path here: the
server renders HTML directly, no frontend build step.
"""
import csv
import os
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView

from accounts.mixins import RegisteredRequiredMixin
from workflow.models import Dataset, DatasetVisibility, DatasetStatus, MergeRequest, DatasetShare
from workflow.forms import DatasetForm, DatasetShareForm
from . import services
from .forms import build_column_mapping_form


# ---------------------------------------------------------------------
# Dataset list and detail
# ---------------------------------------------------------------------

class DatasetListView(ListView):
    """
    Also visible to 'Unregistered' users: shows only the public dataset.
    Registered users additionally see their own private datasets and
    those shared with them. Reviewer/Admin see everything.
    """
    model = Dataset
    template_name = "datasets/dataset_list.html"
    context_object_name = "datasets"

    def get_queryset(self):
        user = self.request.user
        qs = Dataset.objects.select_related("owner").order_by("-created_at")
        if not user.is_authenticated:
            return qs.filter(visibility=DatasetVisibility.PUBLIC)
        if user.is_admin_role or user.is_reviewer:
            return qs
        return qs.filter(
            Q(owner=user) | Q(visibility=DatasetVisibility.PUBLIC) | Q(shares__shared_with=user)
        ).distinct()


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = "datasets/dataset_detail.html"
    context_object_name = "dataset"

    def get_queryset(self):
        # same visibility rule as the list view, so private datasets can't
        # be reached by guessing a direct URL
        user = self.request.user
        qs = Dataset.objects.all()
        if not user.is_authenticated:
            return qs.filter(visibility=DatasetVisibility.PUBLIC)
        if user.is_admin_role or user.is_reviewer:
            return qs
        return qs.filter(
            Q(owner=user) | Q(visibility=DatasetVisibility.PUBLIC) | Q(shares__shared_with=user)
        ).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dataset = self.object
        user = self.request.user
        ctx["is_owner"] = user.is_authenticated and dataset.owner_id == user.id
        ctx["can_edit"] = ctx["is_owner"] or (user.is_authenticated and user.is_reviewer)
        ctx["sample_count"] = dataset.samples.count()
        ctx["shares"] = dataset.shares.select_related("shared_with")
        ctx["open_merge_request"] = dataset.merge_requests.filter(status=MergeRequest.Status.OPEN).first()
        rejected = self.request.session.get(_rejected_rows_session_key(dataset.pk))
        ctx["rejected_rows_count"] = len(rejected["rows"]) if rejected else 0
        return ctx


class DatasetCreateView(RegisteredRequiredMixin, CreateView):
    """Loading step 1 (slide 6): creates the 'container' dataset with
    name, visibility, and default symbol/color; then moves on to upload."""
    model = Dataset
    form_class = DatasetForm
    template_name = "datasets/dataset_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.status = DatasetStatus.DRAFT
        response = super().form_valid(form)
        messages.success(self.request, "Dataset created. Now upload the file with the samples.")
        return response

    def get_success_url(self):
        return reverse("dataset-upload", args=[self.object.pk])


@login_required
def dataset_share_manage(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk)
    if dataset.owner_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("Only the dataset owner can manage its sharing.")

    if request.method == "POST":
        if "remove_share_id" in request.POST:
            DatasetShare.objects.filter(id=request.POST["remove_share_id"], dataset=dataset).delete()
            messages.success(request, "Sharing removed.")
            return redirect("dataset-share", pk=dataset.pk)

        form = DatasetShareForm(request.POST)
        if form.is_valid():
            share = form.save(commit=False)
            share.dataset = dataset
            share.save()
            if dataset.visibility == DatasetVisibility.PRIVATE:
                dataset.visibility = DatasetVisibility.SHARED
                dataset.save(update_fields=["visibility"])
            messages.success(request, f"Dataset shared with {share.shared_with}.")
            return redirect("dataset-share", pk=dataset.pk)
    else:
        form = DatasetShareForm()

    return render(request, "datasets/share_manage.html", {
        "dataset": dataset, "form": form, "shares": dataset.shares.select_related("shared_with"),
    })


@login_required
def dataset_submit_for_review(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)
    if request.method != "POST":
        return redirect("dataset-detail", pk=pk)
    if dataset.samples.count() == 0:
        messages.error(request, "You can't submit a dataset with no samples for review.")
        return redirect("dataset-detail", pk=pk)
    if dataset.status != DatasetStatus.DRAFT:
        messages.error(request, "This dataset is already in review or has already been processed.")
        return redirect("dataset-detail", pk=pk)

    MergeRequest.objects.create(dataset=dataset, submitted_by=request.user)
    dataset.status = DatasetStatus.PENDING_REVIEW
    dataset.save(update_fields=["status"])
    messages.success(request, "Merge request sent to the Reviewer.")
    return redirect("dataset-detail", pk=pk)


# ---------------------------------------------------------------------
# CSV upload wizard: upload -> map columns -> preview -> confirm
# (slide 6, steps 1-5). State between steps lives in the session, except
# for the uploaded file itself, which is written to disk (MEDIA_ROOT/uploads).
# ---------------------------------------------------------------------

def _session_key(dataset_pk):
    return f"upload_wizard_{dataset_pk}"


def _rejected_rows_session_key(dataset_pk):
    return f"upload_wizard_rejected_rows_{dataset_pk}"


def _get_owned_draft_dataset(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk)
    if dataset.owner_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("Only the owner can upload data into this dataset.")
    if dataset.status != DatasetStatus.DRAFT:
        messages.error(request, "This dataset is no longer a draft: you can't upload more data.")
    return dataset


@login_required
def upload_file(request, pk):
    """Step 1: file upload."""
    dataset = _get_owned_draft_dataset(request, pk)

    if request.method == "POST":
        form = _upload_form(request)
        if form.is_valid():
            uploaded = request.FILES["file"]
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"{uuid.uuid4().hex}_{uploaded.name}"
            full_path = os.path.join(upload_dir, filename)
            with open(full_path, "wb") as fh:
                for chunk in uploaded.chunks():
                    fh.write(chunk)

            request.session[_session_key(pk)] = {"file_path": full_path, "original_name": uploaded.name}
            dataset.source_file_name = uploaded.name
            dataset.save(update_fields=["source_file_name"])
            return redirect("dataset-upload-map", pk=pk)
    else:
        form = _upload_form(request)

    return render(request, "datasets/upload_file.html", {"dataset": dataset, "form": form})


def _upload_form(request):
    from workflow.forms import UploadFileForm
    return UploadFileForm(request.POST or None, request.FILES or None)


@login_required
def upload_map_columns(request, pk):
    """Step 2: mapping CSV columns -> DB fields, with a guessed default."""
    dataset = _get_owned_draft_dataset(request, pk)
    state = request.session.get(_session_key(pk))
    if not state:
        messages.error(request, "Upload a file first.")
        return redirect("dataset-upload", pk=pk)

    df = services.load_dataframe(state["file_path"])
    guessed = services.guess_mapping(df.columns)
    FormClass = build_column_mapping_form(df.columns, guessed)

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            mapping = {key.replace("map__", ""): value for key, value in form.cleaned_data.items() if value}
            state["column_mapping"] = mapping
            request.session[_session_key(pk)] = state
            request.session.modified = True
            return redirect("dataset-upload-preview", pk=pk)
    else:
        form = FormClass()

    return render(request, "datasets/map_columns.html", {
        "dataset": dataset, "form": form, "detected_columns": list(df.columns),
    })


@login_required
def upload_preview(request, pk):
    """Step 3: preview + validation, with confirmation for step 4 (the actual import)."""
    dataset = _get_owned_draft_dataset(request, pk)
    state = request.session.get(_session_key(pk))
    if not state or "column_mapping" not in state:
        messages.error(request, "Complete the column mapping first.")
        return redirect("dataset-upload-map", pk=pk)

    df = services.load_dataframe(state["file_path"])
    element_columns = services.detect_trace_element_columns(df.columns)
    preview = services.preview_rows(df, state["column_mapping"], element_columns)

    if request.method == "POST":
        created_count, new_anag, rejected_rows = services.import_rows(
            df, dataset, request.user, state["column_mapping"], element_columns
        )
        del request.session[_session_key(pk)]
        if rejected_rows:
            request.session[_rejected_rows_session_key(pk)] = {
                "columns": list(df.columns), "rows": rejected_rows,
            }
        request.session.modified = True
        messages.success(request, f"Imported {created_count} samples into dataset '{dataset.name}'.")
        for kind, values in new_anag.items():
            unique_values = sorted(set(values))
            if unique_values:
                messages.info(request, f"New anagraphical values ({kind}): {', '.join(unique_values)}")
        if rejected_rows:
            messages.warning(
                request,
                f"{len(rejected_rows)} row(s) were not imported: at least one Pb ratio was present but "
                "not all 5 could be completed. Download the raw data for those rows from this page.",
            )
        return redirect("dataset-detail", pk=pk)

    return render(request, "datasets/preview_import.html", {
        "dataset": dataset, "preview": preview, "field_definitions": services.FIELD_DEFINITIONS,
    })


@login_required
def download_rejected_rows(request, pk):
    """
    Raw data (as read from the uploaded file, before any mapping) for the
    rows the last import discarded because their Pb ratios couldn't be
    completed to all 5 -- so the owner can fix and re-upload them.
    """
    dataset = get_object_or_404(Dataset, pk=pk)
    if dataset.owner_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("Only the owner can download this dataset's rejected rows.")

    data = request.session.pop(_rejected_rows_session_key(pk), None)
    request.session.modified = True
    if not data:
        messages.error(request, "No rejected-rows file available (maybe already downloaded, or no rows were rejected).")
        return redirect("dataset-detail", pk=pk)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="dataset_{pk}_righe_scartate.csv"'
    writer = csv.DictWriter(response, fieldnames=data["columns"])
    writer.writeheader()
    writer.writerows(data["rows"])
    return response
