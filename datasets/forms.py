from django import forms
from . import services


def build_column_mapping_form(csv_columns, guessed_mapping):
    """
    Dynamically builds the step-2 form ('Map CSV fields with DB fields'):
    one <select> per DB field, with the uploaded file's columns as options
    and the default guessed by services.guess_mapping.
    """
    choices = [("", "-- not mapped --")] + [(col, col) for col in csv_columns]

    fields = {}
    for key, label, required in services.FIELD_DEFINITIONS:
        fields[f"map__{key}"] = forms.ChoiceField(
            choices=choices,
            required=required,
            label=label,
            initial=guessed_mapping.get(key) or "",
            widget=forms.Select(attrs={"class": "form-select"}),
        )

    return type("ColumnMappingForm", (forms.Form,), fields)
