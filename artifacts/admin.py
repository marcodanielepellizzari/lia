from django.contrib import admin
from .models import ArtifactSet, Artifact


class ArtifactInline(admin.TabularInline):
    model = Artifact
    extra = 0


@admin.register(ArtifactSet)
class ArtifactSetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "default_symbol", "default_color", "created_at")
    inlines = [ArtifactInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_admin_role:
            return qs
        return qs.filter(owner=request.user)
