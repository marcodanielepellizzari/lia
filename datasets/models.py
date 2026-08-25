"""
FACT tables.

Design note (after discussion with the user): Pb isotope ratios are the
core of the application -- the future analysis/visualization pages will
be built on top of them. Trace elements (~70 in the original file) are
instead supporting metadata: no need for a separate relational table per
row/element, a JSONField on Sample is simpler to maintain and still
enough for looking them up or exporting them.
"""
from django.db import models

from catalog.models import Locality, GeologicUnit, DepositType, Laboratory, AnalyticalMethod, Reference


class AccessLevel(models.TextChoices):
    FREE = "free", "Free"
    LIMITED = "limited", "Limited"


class Sample(models.Model):
    """One 'Sample/Label' row from the original file."""

    dataset = models.ForeignKey(
        "workflow.Dataset", on_delete=models.CASCADE, related_name="samples",
        help_text="Source private dataset, or the public 'main' dataset after merging.",
    )

    label = models.CharField(max_length=200)
    access_level = models.CharField(max_length=10, choices=AccessLevel.choices, default=AccessLevel.FREE)

    in_cu_database = models.BooleanField(default=False)
    in_pbag_database = models.BooleanField(default=False)
    in_sn_database = models.BooleanField(default=False)

    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="samples")
    geologic_unit = models.ForeignKey(
        GeologicUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="samples"
    )
    deposit_type = models.ForeignKey(
        DepositType, on_delete=models.SET_NULL, null=True, blank=True, related_name="samples"
    )
    age = models.CharField(max_length=200, blank=True)

    mineral_assemblage = models.TextField(blank=True)
    primary_secondary = models.CharField(max_length=10, blank=True)
    analysed_mineral_description = models.CharField(max_length=300, blank=True)

    notes_evidences_references = models.TextField(blank=True)
    literature_data = models.CharField(max_length=300, blank=True)

    # Metadata: trace elements, not normalized.
    # E.g. {"Cu": {"value": 1442.3, "unit": "mg/kg", "bdl": false}, "Zn": {...}}
    trace_elements = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="samples_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["label"])]

    def __str__(self):
        return self.label


class LeadIsotopeMeasurement(models.Model):
    """
    The heart of the application: Pb isotope ratios. Indexed on the three
    standard denominators used in Pb-Pb provenance diagrams, which will
    be the axes of the future visualization pages.
    """
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name="lead_isotopes")

    pb208_206 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb207_206 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb206_204 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb207_204 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    pb208_204 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    instrument = models.ForeignKey(AnalyticalMethod, on_delete=models.SET_NULL, null=True, blank=True)
    laboratory = models.ForeignKey(Laboratory, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.ForeignKey(Reference, on_delete=models.SET_NULL, null=True, blank=True)
    lab_details = models.CharField(max_length=300, blank=True)

    quality_assessment = models.CharField(max_length=50, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["pb206_204"]),
            models.Index(fields=["pb207_204"]),
            models.Index(fields=["pb208_204"]),
        ]

    def __str__(self):
        return f"Pb isotopes - {self.sample.label}"


class CopperIsotopeMeasurement(models.Model):
    """63Cu/65Cu, d63 columns -- secondary compared to Pb, but already present in the original file."""
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name="copper_isotopes")

    cu63_65 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    d63 = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    instrument = models.ForeignKey(AnalyticalMethod, on_delete=models.SET_NULL, null=True, blank=True)
    laboratory = models.ForeignKey(Laboratory, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.ForeignKey(Reference, on_delete=models.SET_NULL, null=True, blank=True)
    lab_details = models.CharField(max_length=300, blank=True)
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"Cu isotopes - {self.sample.label}"
