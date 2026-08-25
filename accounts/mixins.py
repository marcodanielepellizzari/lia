"""
Permission mixins reused by all web pages (not just the admin).
They map to the 4 roles from the "Security management" slide:
- Unregistered: no mixin (AllowAny) -> sees only public data/datasets
- Registered:   RegisteredRequiredMixin (== simple login)
- Reviewer:     ReviewerRequiredMixin
- Admin:        AdminRequiredMixin
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class RegisteredRequiredMixin(LoginRequiredMixin):
    """Any authenticated user is at least a 'Registered' user."""
    pass


class ReviewerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_reviewer

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("Only Reviewer and Admin can access this page.")


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin_role

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("Only Admin can access this page.")
