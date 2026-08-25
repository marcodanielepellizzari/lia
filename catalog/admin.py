from django.contrib import admin
from .models import (
    Country, PlottingRegion, GeologicUnit, DepositType,
    Laboratory, AnalyticalMethod, Reference, ChemicalElement, Locality,
)


class ReviewerEditableAdmin(admin.ModelAdmin):
    """
    Anagraphical tables can only be edited by Reviewer/Admin
    (slide 10: "Review and merge private data with main dataset" -> Admin
    and Reviewer only). Registered users can only view them read-only.
    """
    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_reviewer

    has_add_permission = has_delete_permission = has_change_permission


@admin.register(Country)
class CountryAdmin(ReviewerEditableAdmin):
    search_fields = ("name",)


@admin.register(PlottingRegion)
class PlottingRegionAdmin(ReviewerEditableAdmin):
    list_display = ("name", "country", "suggested_symbol")
    list_filter = ("country",)
    search_fields = ("name",)


@admin.register(GeologicUnit)
class GeologicUnitAdmin(ReviewerEditableAdmin):
    search_fields = ("name",)


@admin.register(DepositType)
class DepositTypeAdmin(ReviewerEditableAdmin):
    search_fields = ("name",)


@admin.register(Laboratory)
class LaboratoryAdmin(ReviewerEditableAdmin):
    search_fields = ("name",)


@admin.register(AnalyticalMethod)
class AnalyticalMethodAdmin(ReviewerEditableAdmin):
    search_fields = ("name",)


@admin.register(Reference)
class ReferenceAdmin(ReviewerEditableAdmin):
    search_fields = ("citation",)


@admin.register(ChemicalElement)
class ChemicalElementAdmin(ReviewerEditableAdmin):
    list_display = ("symbol", "name", "mass_number")
    ordering = ("mass_number",)


@admin.register(Locality)
class LocalityAdmin(ReviewerEditableAdmin):
    list_display = ("locality_mine", "area_deposit", "region", "country", "latitude", "longitude")
    list_filter = ("country",)
    search_fields = ("locality_mine", "area_deposit", "region")
