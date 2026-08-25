"""
Pb isotope provenance analysis page.

Lets the user pick which data sources to plot (any Dataset they can see
under the usual visibility rules, plus their own ArtifactSets), apply
location / deposit-type / access-level filters, and renders:

  - three standard binary Pb-Pb diagrams used in provenance studies:
        1. 206Pb/204Pb vs 207Pb/204Pb
        2. 206Pb/204Pb vs 208Pb/204Pb
        3. 207Pb/206Pb vs 208Pb/206Pb
    each either as raw points or, for deposit datasets, as a kernel
    density estimate (KDE) contour -- the classic way to show a "field"
    of ore-deposit signatures behind a handful of artifact points.
  - one interactive 3D scatter plot with the three 204Pb-normalized
    ratios (206/204, 207/204, 208/204) on the x/y/z axes: the only
    combination of the five ratios that gives a genuinely 3D isotopic
    space (the other two ratios, 207/206 and 208/206, are themselves
    derived from the 204-normalized ones).

The server builds the JSON data payload (including, for density mode,
the KDE grids); the actual plotting happens client-side with Plotly.js
(see the frontend stack decision in the project README) -- no build
step, everything lives in one template.
"""
import json
from decimal import Decimal

import numpy as np
from scipy.stats import gaussian_kde

from django.db.models import Q
from django.shortcuts import render

from catalog.models import Country
from workflow.models import Dataset, DatasetVisibility
from artifacts.models import ArtifactSet

# (diagram_key, x_field, y_field) for the three binary Pb-Pb diagrams.
DIAGRAMS = [
    ("diagram1", "pb206_204", "pb207_204"),
    ("diagram2", "pb206_204", "pb208_204"),
    ("diagram3", "pb207_206", "pb208_206"),
]

MIN_POINTS_FOR_KDE = 5  # below this, a density surface is not meaningful -> fall back to points


def _to_float(value):
    """Decimal is not JSON-serializable; None must stay None (missing
    measurement), not become 0."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _visible_datasets(user):
    """Same visibility rule used across the app: Unregistered sees only
    the public dataset, Registered also sees their own + shared ones,
    Reviewer/Admin see everything."""
    qs = Dataset.objects.select_related("owner")
    if not user.is_authenticated:
        return qs.filter(visibility=DatasetVisibility.PUBLIC)
    if user.is_admin_role or user.is_reviewer:
        return qs
    return qs.filter(
        Q(owner=user) | Q(visibility=DatasetVisibility.PUBLIC) | Q(shares__shared_with=user)
    ).distinct()


def _compute_kde_grid(xs, ys, grid_size=60, padding_ratio=0.15):
    """Evaluates a Gaussian KDE of (xs, ys) on a regular grid. Returns
    {"x": [...], "y": [...], "z": [[...]]} ready for a Plotly contour
    trace, or None if there aren't enough points for a meaningful estimate."""
    if len(xs) < MIN_POINTS_FOR_KDE:
        return None
    xs_arr = np.array(xs, dtype=float)
    ys_arr = np.array(ys, dtype=float)
    try:
        kde = gaussian_kde(np.vstack([xs_arr, ys_arr]))
    except (np.linalg.LinAlgError, ValueError):
        # e.g. all points identical -> singular covariance matrix
        return None

    x_pad = (xs_arr.max() - xs_arr.min()) * padding_ratio or abs(xs_arr.mean()) * 0.1 or 1.0
    y_pad = (ys_arr.max() - ys_arr.min()) * padding_ratio or abs(ys_arr.mean()) * 0.1 or 1.0
    x_grid = np.linspace(xs_arr.min() - x_pad, xs_arr.max() + x_pad, grid_size)
    y_grid = np.linspace(ys_arr.min() - y_pad, ys_arr.max() + y_pad, grid_size)
    xx, yy = np.meshgrid(x_grid, y_grid)
    zz = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)

    return {"x": x_grid.tolist(), "y": y_grid.tolist(), "z": zz.tolist()}


def _build_density_payload(groups):
    """For each of the 3 diagrams, computes a KDE grid per DATASET group
    (not artifact sets: those stay as discrete points to compare against
    the density field, which is the whole point of a provenance study)."""
    density_by_diagram = {}
    for diagram_key, x_field, y_field in DIAGRAMS:
        entries = []
        for group in groups:
            if group["kind"] != "dataset":
                continue
            xs, ys = [], []
            for point in group["points"]:
                if point[x_field] is not None and point[y_field] is not None:
                    xs.append(point[x_field])
                    ys.append(point[y_field])
            grid = _compute_kde_grid(xs, ys)
            if grid:
                entries.append({"name": group["name"], "color": group["color"], "grid": grid})
        density_by_diagram[diagram_key] = entries
    return density_by_diagram


def pb_diagrams(request):
    visible_datasets = _visible_datasets(request.user)
    own_artifact_sets = (
        ArtifactSet.objects.filter(owner=request.user) if request.user.is_authenticated
        else ArtifactSet.objects.none()
    )

    # No selection yet (first visit) -> default to every visible dataset,
    # so the page isn't empty on first load.
    selected_dataset_ids = request.GET.getlist("datasets") or [str(d.pk) for d in visible_datasets]
    selected_artifact_set_ids = request.GET.getlist("artifact_sets")
    selected_country_ids = request.GET.getlist("countries")
    deposit_type_contains = request.GET.get("deposit_type", "").strip()
    access_level = request.GET.get("access_level", "").strip()
    display_mode = request.GET.get("display_mode", "points")
    if display_mode not in ("points", "density"):
        display_mode = "points"

    groups = []

    # --- deposit samples: one chart group per selected Dataset ---
    datasets_qs = visible_datasets.filter(pk__in=selected_dataset_ids)
    for dataset in datasets_qs:
        samples = dataset.samples.select_related(
            "locality__country", "deposit_type", "lead_isotopes"
        ).filter(lead_isotopes__isnull=False)

        if selected_country_ids:
            samples = samples.filter(locality__country_id__in=selected_country_ids)
        if deposit_type_contains:
            samples = samples.filter(deposit_type__name__icontains=deposit_type_contains)
        if access_level:
            samples = samples.filter(access_level=access_level)

        points = []
        for sample in samples:
            iso = sample.lead_isotopes
            points.append({
                "label": sample.label,
                "location": str(sample.locality),
                "pb206_204": _to_float(iso.pb206_204),
                "pb207_204": _to_float(iso.pb207_204),
                "pb208_204": _to_float(iso.pb208_204),
                "pb207_206": _to_float(iso.pb207_206),
                "pb208_206": _to_float(iso.pb208_206),
            })
        if points:
            groups.append({
                "name": dataset.name, "kind": "dataset",
                "color": dataset.default_color, "symbol": dataset.default_symbol,
                "points": points,
            })

    # --- artifacts: one chart group per selected ArtifactSet ---
    artifact_sets_qs = (
        own_artifact_sets.filter(pk__in=selected_artifact_set_ids)
        if selected_artifact_set_ids else ArtifactSet.objects.none()
    )
    for artifact_set in artifact_sets_qs:
        artifacts = artifact_set.artifacts.all()
        if selected_country_ids:
            artifacts = artifacts.filter(country_id__in=selected_country_ids)

        points = []
        for artifact in artifacts:
            points.append({
                "label": artifact.label,
                "location": artifact.location_detail or (str(artifact.country) if artifact.country else ""),
                "pb206_204": _to_float(artifact.pb206_204),
                "pb207_204": _to_float(artifact.pb207_204),
                "pb208_204": _to_float(artifact.pb208_204),
                "pb207_206": _to_float(artifact.pb207_206),
                "pb208_206": _to_float(artifact.pb208_206),
            })
        if points:
            groups.append({
                "name": artifact_set.name, "kind": "artifact_set",
                "color": artifact_set.default_color, "symbol": artifact_set.default_symbol,
                "points": points,
            })

    density_by_diagram = _build_density_payload(groups) if display_mode == "density" else {}

    context = {
        "visible_datasets": visible_datasets,
        "own_artifact_sets": own_artifact_sets,
        "countries": Country.objects.all().order_by("name"),
        "selected_dataset_ids": [str(x) for x in selected_dataset_ids],
        "selected_artifact_set_ids": selected_artifact_set_ids,
        "selected_country_ids": selected_country_ids,
        "deposit_type_contains": deposit_type_contains,
        "access_level": access_level,
        "display_mode": display_mode,
        "groups_json": json.dumps(groups),
        "density_json": json.dumps(density_by_diagram),
        "total_points": sum(len(g["points"]) for g in groups),
    }
    return render(request, "analysis/pb_diagrams.html", context)
