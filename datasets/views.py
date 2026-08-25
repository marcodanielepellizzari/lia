from django.db.models import Q
from rest_framework import viewsets, permissions

from .models import Sample
from .serializers import SampleSerializer
from .filters import SampleFilter
from workflow.models import DatasetVisibility


class SampleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Main endpoint for the analysis page.

    Visibility rules (slide 8/10):
    - Unregistered (anonymous user): only samples from the public dataset.
    - Registered: public + own private datasets + datasets shared with them.
    - Reviewer/Admin: everything.
    """
    serializer_class = SampleSerializer
    filterset_class = SampleFilter
    permission_classes = [permissions.AllowAny]  # the query is restricted in get_queryset

    def get_queryset(self):
        qs = Sample.objects.select_related(
            "locality", "locality__country", "deposit_type", "lead_isotopes", "dataset"
        )

        user = self.request.user
        if not user.is_authenticated:
            return qs.filter(dataset__visibility=DatasetVisibility.PUBLIC)
        if user.is_admin_role or user.is_reviewer:
            return qs
        return qs.filter(
            Q(dataset__visibility=DatasetVisibility.PUBLIC)
            | Q(dataset__owner=user)
            | Q(dataset__shares__shared_with=user)
        ).distinct()
