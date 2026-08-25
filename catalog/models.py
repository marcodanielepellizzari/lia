"""
ANAGRAPHICAL tables (dimension tables).

Mapped 1:1 onto the recurring fields in the "Database ores" file (columns
Country, Region, Area/Deposit, Locality/Mine, Geologic unit/Formation,
Deposit type, Pb analysis Instrument, References, ...) which in the
Excel file are repeated as free text on every row of every country
sheet: here they become normalized, reusable, deduplicated references --
this is the "Deposit table to be used as single source of truth"
requested in slide 3.
"""
from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. "Italy", "Morocco"

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlottingRegion(models.Model):
    """E.g. 'Liguria-Appennino', 'Iberia N: Pirineos' -- used for marker styling in analysis."""
    name = models.CharField(max_length=200, unique=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="plotting_regions")
    suggested_symbol = models.CharField(max_length=100, blank=True)  # "Bright green circles" etc.

    def __str__(self):
        return self.name


class GeologicUnit(models.Model):
    name = models.CharField(max_length=300, unique=True)

    def __str__(self):
        return self.name


class DepositType(models.Model):
    name = models.CharField(max_length=300, unique=True)

    def __str__(self):
        return self.name


class Laboratory(models.Model):
    """E.g. 'Institut fur Geologie-Bern', 'Isotrace Laboratory, Oxford'."""
    name = models.CharField(max_length=300, unique=True)

    def __str__(self):
        return self.name


class AnalyticalMethod(models.Model):
    """E.g. MC-ICP-MS, TIMS, ICP-QMS, ICP-MS -- reused for Pb, Cu, and chemical analyses."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Reference(models.Model):
    """Bibliographic citation: also corresponds to the 'BIBL' sheet of the file."""
    citation = models.CharField(max_length=500, unique=True)  # e.g. "Cattin et al. (2011)"
    doi_or_url = models.URLField(blank=True)

    def __str__(self):
        return self.citation


class ChemicalElement(models.Model):
    """
    The ~70 element columns (Li, Be, B, Na, ... U) of the file become rows
    here instead of 70 fixed columns -- the core of the fact/anag split:
    adding a new element does not require a database migration.
    """
    symbol = models.CharField(max_length=4, unique=True)     # "Pb", "Cu", "Yb"
    name = models.CharField(max_length=50, blank=True)       # "Lead", "Copper"
    mass_number = models.PositiveIntegerField(null=True, blank=True)  # 208, 63, 172...

    class Meta:
        ordering = ["mass_number"]

    def __str__(self):
        return self.symbol


class Locality(models.Model):
    """
    The "Deposit table" single source of truth mentioned in slide 3.
    A Sample (fact) always points to an existing Locality: no more
    deposit coordinates/names retyped and potentially inconsistent on
    every row, as currently happens in the Excel sheet.
    """
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="localities")
    plotting_region = models.ForeignKey(
        PlottingRegion, on_delete=models.SET_NULL, null=True, blank=True, related_name="localities"
    )
    region = models.CharField(max_length=200, blank=True)          # e.g. "LIGURIA"
    area_deposit = models.CharField(max_length=200, blank=True)    # e.g. "Appennino Ligure"
    locality_mine = models.CharField(max_length=200, blank=True)   # e.g. "Libiola"
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_latitude_approx = models.BooleanField(default=False)
    is_longitude_approx = models.BooleanField(default=False)
    geologic_unit = models.ForeignKey(
        GeologicUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name="localities"
    )
    used_in_the_past = models.CharField(max_length=200, blank=True)  # e.g. "3rd millennium BC"
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "localities"
        unique_together = ("country", "area_deposit", "locality_mine")

    def __str__(self):
        return f"{self.locality_mine or self.area_deposit} ({self.country})"
