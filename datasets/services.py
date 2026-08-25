"""
Data-loading logic shared between the management command (import_samples)
and the web wizard (datasets/page_views.py), so the two entry points don't
drift apart over time.

Implements steps 2-4 of the "Loading data" slide:
    2. Map CSV fields with DB fields   -> guess_mapping() + FIELD_DEFINITIONS
    3. Control data types/missing vals -> clean_text / clean_decimal
    4. Consistency check anagraphical  -> import_rows() tracks new values
"""
import re
import decimal

import pandas as pd

# (field_key, UI label, required)
FIELD_DEFINITIONS = [
    ("label", "Sample / Label", True),
    ("country", "Country", True),
    ("region", "Region", False),
    ("area_deposit", "Area / Deposit", False),
    ("locality_mine", "Locality / Mine", False),
    ("geologic_unit", "Geologic unit / Formation", False),
    ("deposit_type", "Deposit type", False),
    ("age", "Age", False),
    ("mineral_assemblage", "Mineral assemblage / Constituents", False),
    ("primary_secondary", "Primary / Secondary", False),
    ("analysed_mineral_description", "Analysed mineral / Description", False),
    ("notes_evidences_references", "Notes / Evidences / References", False),
    ("literature_data", "Literature data", False),
    ("pb208_206", "208Pb/206Pb", False),
    ("pb207_206", "207Pb/206Pb", False),
    ("pb206_204", "206Pb/204Pb", False),
    ("pb207_204", "207Pb/204Pb", False),
    ("pb208_204", "208Pb/204Pb", False),
    ("pb_quality_assessment", "Pb quality assessment", False),
    ("pb_instrument", "Pb analysis instrument", False),
    ("pb_reference", "Pb reference", False),
]

# Heuristic used to propose a default in the mapping UI, based on the real
# headers of the sample file ("Database ores dicembre 2023.xls").
HEURISTIC_HEADERS = {
    "label": ["sample/label"],
    "country": ["country"],
    "region": ["region"],
    "area_deposit": ["area/", "deposit"],
    "locality_mine": ["locality/", "mine"],
    "geologic_unit": ["geologic unit", "formation"],
    "deposit_type": ["deposit type"],
    "age": ["age"],
    "mineral_assemblage": ["mineral assemblage"],
    "primary_secondary": ["primary/"],
    "analysed_mineral_description": ["analised mineral"],
    "notes_evidences_references": ["notes/evidences"],
    "literature_data": ["literature data"],
    "pb208_206": ["208pb/206pb"],
    "pb207_206": ["207pb/206pb"],
    "pb206_204": ["206pb/204pb"],
    "pb207_204": ["207pb/204pb"],
    "pb208_204": ["208pb/204pb"],
    "pb_quality_assessment": ["quality"],
    "pb_instrument": ["pb analysis"],
    "pb_reference": ["reference"],
}

ELEMENT_COL_RE = re.compile(r"^(mg/Kg|Wt%)\s*\n?\s*(\d+)\s*([A-Za-z]{1,3})", re.IGNORECASE)


def load_dataframe(file_path):
    path = str(file_path).lower()
    if path.endswith(".csv"):
        return pd.read_csv(file_path)
    return pd.read_excel(file_path)


def guess_mapping(columns):
    """Returns {field_key: guessed_column_name_or_None}."""
    normalized = {str(c): re.sub(r"\s+", " ", str(c)).strip().lower() for c in columns}
    guesses = {}
    for key, needles in HEURISTIC_HEADERS.items():
        found = None
        for col, norm in normalized.items():
            if all(needle in norm for needle in needles):
                found = col
                break
        guesses[key] = found
    return guesses


def detect_trace_element_columns(columns):
    """Columns not explicitly mapped that follow the 'mg/Kg <mass> <symbol>'
    or 'Wt% <mass> <symbol>' pattern -> element metadata."""
    mapping = {}
    for col in columns:
        m = ELEMENT_COL_RE.match(str(col))
        if m:
            unit_raw, mass, symbol = m.groups()
            mapping[col] = {"symbol": symbol.strip(), "unit": "mg/kg" if unit_raw.lower().startswith("mg") else "wt%"}
    return mapping


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def clean_decimal(value):
    """Returns (decimal_value_or_None, is_below_detection_limit)."""
    text = clean_text(value)
    if not text or text.upper() in {"NAN", "ND", "N/A"}:
        return None, False
    if text.upper().startswith("<"):
        return None, True
    try:
        return decimal.Decimal(text.replace(",", ".")), False
    except (decimal.InvalidOperation, ValueError):
        return None, False


def preview_rows(df, column_mapping, element_columns, max_rows=10):
    """Preview for wizard step 3: total rows, rows without a label
    (discarded), detected element columns, first N mapped rows."""
    label_col = column_mapping.get("label")
    total = len(df)
    valid_labels = df[label_col].apply(clean_text).ne("") if label_col else pd.Series([False] * total)
    sample_rows = []
    for _, row in df.head(max_rows).iterrows():
        sample_rows.append({key: clean_text(row.get(column_mapping.get(key), "")) for key, _, _ in FIELD_DEFINITIONS})
    return {
        "total_rows": total,
        "rows_with_label": int(valid_labels.sum()),
        "rows_skipped": int(total - valid_labels.sum()),
        "element_columns_detected": len(element_columns),
        "sample_rows": sample_rows,
    }


def import_rows(df, dataset, owner, column_mapping, element_columns):
    """
    Performs the actual import (step 5 of the loading-data slide). Returns
    (samples_created_count, new_anagraphical_values_dict).
    """
    from catalog.models import Country, GeologicUnit, DepositType, Locality, AnalyticalMethod, Reference
    from .models import Sample, LeadIsotopeMeasurement

    new_anag = {"localities": [], "geologic_units": [], "deposit_types": []}
    created_count = 0

    def get(row, key):
        col = column_mapping.get(key)
        if not col or col not in row.index:
            return ""
        return row[col]

    for _, row in df.iterrows():
        label = clean_text(get(row, "label"))
        if not label:
            continue

        country_name = clean_text(get(row, "country")) or "Unknown"
        country, _ = Country.objects.get_or_create(name=country_name)

        gu_name = clean_text(get(row, "geologic_unit"))
        geologic_unit = None
        if gu_name:
            geologic_unit, created = GeologicUnit.objects.get_or_create(name=gu_name)
            if created:
                new_anag["geologic_units"].append(gu_name)

        dt_name = clean_text(get(row, "deposit_type"))
        deposit_type = None
        if dt_name:
            deposit_type, created = DepositType.objects.get_or_create(name=dt_name)
            if created:
                new_anag["deposit_types"].append(dt_name)

        locality, created = Locality.objects.get_or_create(
            country=country,
            area_deposit=clean_text(get(row, "area_deposit")),
            locality_mine=clean_text(get(row, "locality_mine")),
            defaults={
                "region": clean_text(get(row, "region")),
                "geologic_unit": geologic_unit,
            },
        )
        if created:
            new_anag["localities"].append(str(locality))

        sample = Sample.objects.create(
            dataset=dataset,
            label=label,
            locality=locality,
            geologic_unit=geologic_unit,
            deposit_type=deposit_type,
            age=clean_text(get(row, "age")),
            mineral_assemblage=clean_text(get(row, "mineral_assemblage")),
            primary_secondary=clean_text(get(row, "primary_secondary")),
            analysed_mineral_description=clean_text(get(row, "analysed_mineral_description")),
            notes_evidences_references=clean_text(get(row, "notes_evidences_references")),
            literature_data=clean_text(get(row, "literature_data")),
            created_by=owner,
        )

        pb_values = {}
        for key in ["pb208_206", "pb207_206", "pb206_204", "pb207_204", "pb208_204"]:
            value, _ = clean_decimal(get(row, key))
            pb_values[key] = value
        if any(v is not None for v in pb_values.values()):
            instrument = None
            instr_name = clean_text(get(row, "pb_instrument"))
            if instr_name:
                instrument, _ = AnalyticalMethod.objects.get_or_create(name=instr_name)
            reference = None
            ref_name = clean_text(get(row, "pb_reference"))
            if ref_name:
                reference, _ = Reference.objects.get_or_create(citation=ref_name)
            LeadIsotopeMeasurement.objects.create(
                sample=sample, instrument=instrument, reference=reference,
                quality_assessment=clean_text(get(row, "pb_quality_assessment")),
                **pb_values,
            )

        trace_elements = {}
        for col, meta in element_columns.items():
            value, is_bdl = clean_decimal(row.get(col))
            if value is None and not is_bdl:
                continue
            trace_elements[meta["symbol"]] = {
                "value": float(value) if value is not None else None,
                "unit": meta["unit"],
                "bdl": is_bdl,
            }
        if trace_elements:
            sample.trace_elements = trace_elements
            sample.save(update_fields=["trace_elements"])

        created_count += 1

    return created_count, new_anag
