from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, Team


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Only Admin can create new users/teams and manage permissions
    # (slide 10: "Create new users and teams" / "Manage permissions" -> Admin only)
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Application role", {"fields": ("role",)}),
    )

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_admin_role

    has_add_permission = has_change_permission = has_delete_permission = has_module_permission


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    filter_horizontal = ("members",)

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_admin_role
