"""
Artifacts uploaded by the user to compare their Pb isotope ratios against
the ore deposit database (typical archaeometric provenance workflow).

Kept as a separate, lightweight model from datasets.Sample: an artifact
is not part of the deposit database, has no locality/dataset review
workflow, and exists purely as an overlay data source on the analysis
charts (see the `analysis` app).
"""
from django.db import models
from django.conf import settings

from catalog.models import Country
from workflow.models import PlotSymbol


class ArtifactSet(models.Model):
    """
    A batch of artifacts uploaded together, treated as one selectable
    data source on the analysis page -- the same idea as workflow.Dataset,
    but without the private/shared/review workflow: it's the user's own
    reference data, not something that gets merged into a shared database.
    """
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artifact_sets")

    default_symbol = models.CharField(max_length=20, choices=PlotSymbol.choices, default=PlotSymbol.STAR)
    default_color = models.CharField(max_length=7, default="#d62728", help_text="Hex color code, e.g. #d62728")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Artifact(models.Model):
    """One artifact with its own Pb isotope measurement, belonging to an ArtifactSet."""
    artifact_set = models.ForeignKey(ArtifactSet, on_delete=models.CASCADE, related_name="artifacts")

    label = models.CharField(max_length=200)
    description = models.CharField(max_length=300, blank=True)

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name="artifacts")
    location_detail = models.CharField(max_length=200, blank=True, help_text="Find spot / site name")

    pb208_206 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb207_206 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb206_204 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb207_204 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb208_204 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return f"{self.label} ({self.artifact_set.name})"
