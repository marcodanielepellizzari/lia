"""
The "glue" between the functional slides and the data model:
- Dataset: container for an upload (slide 6 "Loading data - new
  private dataset"), with name, sharing option, status.
- DatasetShare: point-to-point sharing with other users/teams (slide 3).
- MergeRequest: the two-step review from slide 7
  ("Loading data - review steps").
- SavedFilter: saved, reusable filters/charts on the analysis page
  (slide 3, last bullet).
- DataUsageLog: data usage/citation tracking (slide 3, last bullet).
"""
from django.db import models
from django.conf import settings


class DatasetVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    SHARED = "shared", "Shared with specific users/teams"
    PUBLIC = "public", "Public (main dataset)"


class DatasetStatus(models.TextChoices):
    DRAFT = "draft", "Draft"                       # uploaded, being edited by the owner
    PENDING_REVIEW = "pending_review", "Pending review"  # merge request submitted
    MERGED = "merged", "Merged into main"           # approved: merged into the public dataset
    REJECTED = "rejected", "Rejected"


class PlotSymbol(models.TextChoices):
    """Fixed set of symbols usable in future charts (both matplotlib and
    Plotly support these same conceptual names)."""
    CIRCLE = "circle", "Circle"
    SQUARE = "square", "Square"
    TRIANGLE = "triangle-up", "Triangle"
    DIAMOND = "diamond", "Diamond"
    STAR = "star", "Star"
    CROSS = "cross", "Cross"
    INVERTED_TRIANGLE = "triangle-down", "Inverted triangle"


class Dataset(models.Model):
    """Corresponds to a 'private dataset' from slide 6, or to the public
    'main' dataset when visibility=public."""

    name = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="datasets")
    visibility = models.CharField(max_length=10, choices=DatasetVisibility.choices, default=DatasetVisibility.PRIVATE)
    status = models.CharField(max_length=20, choices=DatasetStatus.choices, default=DatasetStatus.DRAFT)

    source_file_name = models.CharField(max_length=300, blank=True)  # original uploaded CSV file name
    default_plotting_notes = models.TextField(blank=True)  # "set default plotting values" (slide 7)

    # Default symbol and color used for THIS dataset in future charts
    # (e.g. all samples from "Liguria Dec 2023" plotted as green circles,
    # unless explicitly overridden by the user during analysis).
    default_symbol = models.CharField(max_length=20, choices=PlotSymbol.choices, default=PlotSymbol.CIRCLE)
    default_color = models.CharField(
        max_length=7, default="#1f77b4",
        help_text="Hex color code, e.g. #1f77b4",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class DatasetShare(models.Model):
    """Point-to-point sharing of a private dataset with another user
    (slide 3: 'ability to share with other users')."""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="shares")
    shared_with = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="datasets_shared_with_me")
    can_edit = models.BooleanField(default=False)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("dataset", "shared_with")


class MergeRequest(models.Model):
    """
    The "review steps" from slide 7:
    - the Registered user submits the merge request at the end of the upload (slide 6.5.3)
    - the Reviewer checks new anagraphical values and possible duplicates
    - the Reviewer approves/rejects and sets data permissions
    """

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="merge_requests")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="merge_requests_submitted"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    # "Verify new anagraphical fields" / "Verify possible redundant/inconsistent data"
    new_anagraphical_values = models.JSONField(
        default=dict, blank=True,
        help_text="New anagraphical values detected during the upload (e.g. new Locality, new GeologicUnit).",
    )
    potential_duplicates = models.JSONField(default=list, blank=True)

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="merge_requests_reviewed",
    )
    review_notes = models.TextField(blank=True)  # "Add notes" (slide 7)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"MergeRequest #{self.pk} - {self.dataset.name} ({self.status})"


class SavedFilter(models.Model):
    """Filter/chart configurations saved on the analysis page
    (slide 3: 'Name and save filter configurations')."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_filters")
    name = models.CharField(max_length=150)
    filter_config = models.JSONField(
        help_text="E.g. {'countries': ['Italy'], 'elements': ['Pb','Cu'], 'plot': 'pb_isotope_diagram'}"
    )
    is_shared_with_team = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner", "name")

    def __str__(self):
        return f"{self.name} ({self.owner})"


class DataUsageLog(models.Model):
    """Tracks who used/exported which samples, for the 'Track data usage
    and references' requirement in slide 3."""

    class Action(models.TextChoices):
        VIEW = "view", "View"
        EXPORT = "export", "Export"
        CITE = "cite", "Cite in analysis"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="usage_logs")
    action = models.CharField(max_length=10, choices=Action.choices)
    sample_ids = models.JSONField(default=list, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
