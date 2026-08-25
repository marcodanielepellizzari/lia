"""
HTML pages for uploading and managing artifact reference data: the
user's own Pb isotope measurements on archaeological/artifact samples,
used as an overlay data source on the analysis charts (see the
`analysis` app).
"""
import os
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView

from accounts.mixins import RegisteredRequiredMixin
from catalog.models import Country
from .forms import ArtifactSetForm, ArtifactForm, ArtifactCSVUploadForm
from .models import ArtifactSet, Artifact
from . import services


class ArtifactSetListView(RegisteredRequiredMixin, ListView):
    model = ArtifactSet
    template_name = "artifacts/artifactset_list.html"
    context_object_name = "artifact_sets"

    def get_queryset(self):
        return ArtifactSet.objects.filter(owner=self.request.user)


class ArtifactSetCreateView(RegisteredRequiredMixin, CreateView):
    model = ArtifactSet
    form_class = ArtifactSetForm
    template_name = "artifacts/artifactset_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Set di artefatti creato. Ora aggiungi i dati.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("artifactset-detail", args=[self.object.pk])


class ArtifactSetDetailView(RegisteredRequiredMixin, DetailView):
    model = ArtifactSet
    template_name = "artifacts/artifactset_detail.html"
    context_object_name = "artifact_set"

    def get_queryset(self):
        # each user only manages their own artifact sets
        return ArtifactSet.objects.filter(owner=self.request.user)


@login_required
def artifact_add_manual(request, pk):
    """One-artifact-at-a-time manual entry: re-renders the same page with
    the list of artifacts already added, so the user can keep adding
    without navigating away."""
    artifact_set = get_object_or_404(ArtifactSet, pk=pk, owner=request.user)

    if request.method == "POST":
        form = ArtifactForm(request.POST)
        if form.is_valid():
            artifact = form.save(commit=False)
            artifact.artifact_set = artifact_set
            artifact.save()
            messages.success(request, f"Artefatto '{artifact.label}' aggiunto.")
            return redirect("artifact-add-manual", pk=pk)
    else:
        form = ArtifactForm()

    return render(request, "artifacts/artifact_add_manual.html", {
        "artifact_set": artifact_set, "form": form,
        "artifacts": artifact_set.artifacts.all(),
    })


@login_required
def artifact_upload_csv(request, pk):
    """Bulk alternative to manual entry, for larger artifact batches."""
    artifact_set = get_object_or_404(ArtifactSet, pk=pk, owner=request.user)

    if request.method == "POST":
        form = ArtifactCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            uploaded = request.FILES["file"]
            full_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{uploaded.name}")
            with open(full_path, "wb") as fh:
                for chunk in uploaded.chunks():
                    fh.write(chunk)

            rows = services.parse_artifact_csv(full_path)
            created = 0
            for row in rows:
                country = None
                if row["country_name"]:
                    country, _ = Country.objects.get_or_create(name=row["country_name"])
                Artifact.objects.create(
                    artifact_set=artifact_set,
                    label=row["label"], description=row["description"],
                    country=country, location_detail=row["location_detail"],
                    pb208_206=row["pb208_206"], pb207_206=row["pb207_206"],
                    pb206_204=row["pb206_204"], pb207_204=row["pb207_204"], pb208_204=row["pb208_204"],
                )
                created += 1
            messages.success(request, f"Importati {created} artefatti.")
            return redirect("artifactset-detail", pk=pk)
    else:
        form = ArtifactCSVUploadForm()

    return render(request, "artifacts/artifact_upload_csv.html", {"artifact_set": artifact_set, "form": form})


@login_required
def artifact_delete(request, pk, artifact_pk):
    artifact_set = get_object_or_404(ArtifactSet, pk=pk, owner=request.user)
    if request.method == "POST":
        artifact_set.artifacts.filter(pk=artifact_pk).delete()
        messages.success(request, "Artefatto rimosso.")
    return redirect("artifactset-detail", pk=pk)
