from django.contrib import admin
from django.db.models import Q

from .models import Sample, LeadIsotopeMeasurement, CopperIsotopeMeasurement


class LeadIsotopeInline(admin.StackedInline):
    model = LeadIsotopeMeasurement
    extra = 0


class CopperIsotopeInline(admin.StackedInline):
    model = CopperIsotopeMeasurement
    extra = 0


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ("label", "locality", "dataset", "access_level", "created_by", "created_at")
    list_filter = ("access_level", "dataset__visibility", "locality__country")
    search_fields = ("label", "locality__locality_mine")
    inlines = [LeadIsotopeInline, CopperIsotopeInline]
    readonly_fields = ("trace_elements",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_admin_role or user.is_reviewer:
            return qs
        return qs.filter(_visible_dataset_filter(user))

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if obj is None:
            return True
        if request.user.is_reviewer:
            return True
        return obj.dataset.owner_id == request.user.id and obj.dataset.status == "draft"


def _visible_dataset_filter(user):
    return (
        Q(dataset__owner=user)
        | Q(dataset__visibility="public")
        | Q(dataset__shares__shared_with=user)
    )
