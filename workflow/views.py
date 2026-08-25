from rest_framework import viewsets, permissions

from .models import SavedFilter, Dataset, DatasetVisibility
from .serializers import SavedFilterSerializer, DatasetSerializer


class IsRegisteredOrReadOnly(permissions.BasePermission):
    """Only authenticated users (Registered+) can create datasets or saved
    filters (slide 10: 'Unregistered' -> 'Query public data' only)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class SavedFilterViewSet(viewsets.ModelViewSet):
    serializer_class = SavedFilterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedFilter.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DatasetViewSet(viewsets.ModelViewSet):
    """
    Creating a dataset = step 5 of slide 6 ("Save private dataset" ->
    assign a name, sharing option, then merge request).
    """
    serializer_class = DatasetSerializer
    permission_classes = [IsRegisteredOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Dataset.objects.all()
        if not user.is_authenticated:
            return qs.filter(visibility=DatasetVisibility.PUBLIC)
        if user.is_admin_role or user.is_reviewer:
            return qs
        return qs.filter(owner=user) | qs.filter(visibility=DatasetVisibility.PUBLIC) | qs.filter(shares__shared_with=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
