from rest_framework import serializers
from .models import Sample, LeadIsotopeMeasurement


class LeadIsotopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadIsotopeMeasurement
        fields = ["pb208_206", "pb207_206", "pb206_204", "pb207_204", "pb208_204", "quality_assessment"]


class SampleSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source="locality.country.name", read_only=True)
    locality_name = serializers.CharField(source="locality.locality_mine", read_only=True)
    latitude = serializers.DecimalField(source="locality.latitude", max_digits=9, decimal_places=6, read_only=True)
    longitude = serializers.DecimalField(source="locality.longitude", max_digits=9, decimal_places=6, read_only=True)
    lead_isotopes = LeadIsotopeSerializer(read_only=True)
    dataset_symbol = serializers.CharField(source="dataset.default_symbol", read_only=True)
    dataset_color = serializers.CharField(source="dataset.default_color", read_only=True)

    class Meta:
        model = Sample
        fields = [
            "id", "label", "access_level", "country", "locality_name",
            "latitude", "longitude", "deposit_type", "age",
            "lead_isotopes", "trace_elements", "dataset_symbol", "dataset_color",
        ]
