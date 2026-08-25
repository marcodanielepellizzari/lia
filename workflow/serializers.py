from rest_framework import serializers
from .models import SavedFilter, MergeRequest, Dataset


class SavedFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedFilter
        fields = ["id", "name", "filter_config", "is_shared_with_team", "created_at"]
        read_only_fields = ["id", "created_at"]


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            "id", "name", "owner", "visibility", "status", "source_file_name",
            "default_symbol", "default_color", "created_at",
        ]
        read_only_fields = ["id", "owner", "status", "created_at"]


class MergeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MergeRequest
        fields = [
            "id", "dataset", "submitted_by", "status",
            "new_anagraphical_values", "potential_duplicates",
            "reviewer", "review_notes", "created_at", "reviewed_at",
        ]
        read_only_fields = ["id", "submitted_by", "status", "reviewer", "created_at", "reviewed_at"]
