from django import forms
from .models import Dataset, DatasetShare, MergeRequest


class DatasetForm(forms.ModelForm):
    """Loading step 1 (slide 6): name, visibility, and -- per explicit
    request -- default symbol/color to use in future charts."""

    class Meta:
        model = Dataset
        fields = ["name", "visibility", "default_symbol", "default_color"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "E.g. Liguria - December 2023"}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
            "default_symbol": forms.Select(attrs={"class": "form-select"}),
            "default_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
        }
        labels = {
            "name": "Dataset name",
            "visibility": "Visibility",
            "default_symbol": "Default chart symbol",
            "default_color": "Default chart color",
        }


class DatasetShareForm(forms.ModelForm):
    class Meta:
        model = DatasetShare
        fields = ["shared_with", "can_edit"]
        widgets = {
            "shared_with": forms.Select(attrs={"class": "form-select"}),
            "can_edit": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {"shared_with": "Share with", "can_edit": "Can edit"}


class UploadFileForm(forms.Form):
    file = forms.FileField(
        label="CSV or Excel file",
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv,.xls,.xlsx"}),
    )


class MergeRequestReviewForm(forms.ModelForm):
    class Meta:
        model = MergeRequest
        fields = ["review_notes"]
        widgets = {
            "review_notes": forms.Textarea(attrs={"class": "form-control", "rows": 4,
                                                    "placeholder": "Notes for the dataset owner..."}),
        }
        labels = {"review_notes": "Review notes"}
