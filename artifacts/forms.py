from django import forms
from .models import ArtifactSet, Artifact


class ArtifactSetForm(forms.ModelForm):
    class Meta:
        model = ArtifactSet
        fields = ["name", "default_symbol", "default_color"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Es. Bronzo Ligure - scavo 2024"}),
            "default_symbol": forms.Select(attrs={"class": "form-select"}),
            "default_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
        }
        labels = {
            "name": "Nome del set di artefatti",
            "default_symbol": "Simbolo nei grafici",
            "default_color": "Colore nei grafici",
        }


class ArtifactForm(forms.ModelForm):
    class Meta:
        model = Artifact
        fields = ["label", "description", "country", "location_detail",
                  "pb208_206", "pb207_206", "pb206_204", "pb207_204", "pb208_204"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.Select(attrs={"class": "form-select"}),
            "location_detail": forms.TextInput(attrs={"class": "form-control"}),
            "pb208_206": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "pb207_206": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "pb206_204": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "pb207_204": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "pb208_204": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
        }
        labels = {
            "label": "Label / ID reperto",
            "description": "Descrizione",
            "country": "Paese di ritrovamento",
            "location_detail": "Sito / località di ritrovamento",
        }


class ArtifactCSVUploadForm(forms.Form):
    file = forms.FileField(
        label="File CSV",
        help_text=("Colonne attese: Label, Country, Location, Description, "
                    "208Pb/206Pb, 207Pb/206Pb, 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb"),
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )
