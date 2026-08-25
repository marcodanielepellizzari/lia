"""
CSV import for artifact sets. Deliberately simpler than the deposit
sample import in datasets.services: artifact files are small and have a
fixed, known column set, so no interactive column-mapping wizard is
needed here -- just a direct header lookup with a couple of accepted
aliases per column.
"""
from datasets.services import clean_text, clean_decimal
import pandas as pd

EXPECTED_COLUMNS = {
    "label": ["Label", "label", "ID"],
    "country": ["Country", "country"],
    "location_detail": ["Location", "Site", "location"],
    "description": ["Description", "description"],
    "pb208_206": ["208Pb/206Pb"],
    "pb207_206": ["207Pb/206Pb"],
    "pb206_204": ["206Pb/204Pb"],
    "pb207_204": ["207Pb/204Pb"],
    "pb208_204": ["208Pb/204Pb"],
}


def _find_column(df_columns, candidates):
    for candidate in candidates:
        if candidate in df_columns:
            return candidate
    return None


def parse_artifact_csv(file_path):
    """Returns a list of plain dicts, one per artifact row, with the
    country still as a raw name (resolved to a Country FK by the caller,
    which has DB access) and Pb ratios already cleaned to Decimal/None."""
    df = pd.read_csv(file_path)
    resolved = {key: _find_column(df.columns, candidates) for key, candidates in EXPECTED_COLUMNS.items()}

    rows = []
    for _, row in df.iterrows():
        label = clean_text(row.get(resolved["label"])) if resolved["label"] else ""
        if not label:
            continue
        data = {
            "label": label,
            "description": clean_text(row.get(resolved["description"])) if resolved["description"] else "",
            "country_name": clean_text(row.get(resolved["country"])) if resolved["country"] else "",
            "location_detail": clean_text(row.get(resolved["location_detail"])) if resolved["location_detail"] else "",
        }
        for key in ["pb208_206", "pb207_206", "pb206_204", "pb207_204", "pb208_204"]:
            value, _ = clean_decimal(row.get(resolved[key])) if resolved[key] else (None, False)
            data[key] = value
        rows.append(data)
    return rows
