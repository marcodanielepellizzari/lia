from django.contrib import admin
from django.utils import timezone
from django.contrib import messages

from .models import Dataset, DatasetShare, MergeRequest, SavedFilter, DataUsageLog
from .models import DatasetStatus, DatasetVisibility


class DatasetShareInline(admin.TabularInline):
    model = DatasetShare
    extra = 1


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "visibility", "status", "default_symbol", "default_color", "created_at")
    list_filter = ("visibility", "status")
    search_fields = ("name", "owner__username")
    inlines = [DatasetShareInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_admin_role or user.is_reviewer:
            return qs
        return qs.filter(owner=user) | qs.filter(visibility=DatasetVisibility.PUBLIC) | qs.filter(shares__shared_with=user)


@admin.register(MergeRequest)
class MergeRequestAdmin(admin.ModelAdmin):
    """
    The review panel from slide 7: "Receive merge request -> Verify
    new anagraphical fields -> Verify redundant/inconsistent data ->
    Add notes -> Approve Merge -> Set data permissions".
    """
    list_display = ("id", "dataset", "submitted_by", "status", "reviewer", "created_at")
    list_filter = ("status",)
    readonly_fields = ("dataset", "submitted_by", "new_anagraphical_values", "potential_duplicates", "created_at")
    actions = ["approve_merge", "reject_merge"]

    def has_module_permission(self, request):
        # Only Reviewer and Admin see the review queue (slide 10)
        return request.user.is_authenticated and request.user.is_reviewer

    has_view_permission = has_change_permission = has_module_permission

    @admin.action(description="Approve merge: publish the dataset into main")
    def approve_merge(self, request, queryset):
        updated = 0
        for merge_request in queryset.filter(status="open"):
            dataset = merge_request.dataset
            dataset.status = DatasetStatus.MERGED
            dataset.visibility = DatasetVisibility.PUBLIC
            dataset.save(update_fields=["status", "visibility"])

            merge_request.status = MergeRequest.Status.APPROVED
            merge_request.reviewer = request.user
            merge_request.reviewed_at = timezone.now()
            merge_request.save(update_fields=["status", "reviewer", "reviewed_at"])
            updated += 1
        self.message_user(request, f"{updated} merge requests approved.", level=messages.SUCCESS)

    @admin.action(description="Reject merge")
    def reject_merge(self, request, queryset):
        updated = queryset.filter(status="open").update(
            status=MergeRequest.Status.REJECTED, reviewer=request.user, reviewed_at=timezone.now()
        )
        for merge_request in queryset:
            merge_request.dataset.status = DatasetStatus.REJECTED
            merge_request.dataset.save(update_fields=["status"])
        self.message_user(request, f"{updated} merge requests rejected.", level=messages.WARNING)


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_shared_with_team", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_admin_role:
            return qs
        return qs.filter(owner=request.user)


@admin.register(DataUsageLog)
class DataUsageLogAdmin(admin.ModelAdmin):
    list_display = ("dataset", "user", "action", "timestamp")
    list_filter = ("action",)
    readonly_fields = [f.name for f in DataUsageLog._meta.fields]

    def has_add_permission(self, request):
        return False  # logs are only created via application code, never by hand
