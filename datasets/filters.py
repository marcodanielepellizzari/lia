import django_filters as df
from .models import Sample


class SampleFilter(df.FilterSet):
    """Base filter for the API; future Pb analysis pages will build more
    targeted queries directly on top of LeadIsotopeMeasurement."""
    country = df.CharFilter(field_name="locality__country__name", lookup_expr="iexact")
    deposit_type = df.CharFilter(field_name="deposit_type__name", lookup_expr="icontains")
    pb206_204_min = df.NumberFilter(field_name="lead_isotopes__pb206_204", lookup_expr="gte")
    pb206_204_max = df.NumberFilter(field_name="lead_isotopes__pb206_204", lookup_expr="lte")
    pb207_204_min = df.NumberFilter(field_name="lead_isotopes__pb207_204", lookup_expr="gte")
    pb207_204_max = df.NumberFilter(field_name="lead_isotopes__pb207_204", lookup_expr="lte")

    class Meta:
        model = Sample
        fields = ["country", "deposit_type", "access_level"]
