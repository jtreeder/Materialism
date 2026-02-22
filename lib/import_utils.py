"""Dataset import utilities — file parsing, analysis, and normalization.

Supports CSV, Excel (.xlsx), JSON, and PDF (via pdftotext) file types.
Used by both the CLI import tool and the /api/datasets/* API endpoints.
"""

import csv
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone

from lib.normalize import normalize_name, normalize_cas, parse_float
from lib.classify import classify_chemical, classify_polymer
from lib.confidence import compute_confidence
from lib.schema import (
    CHEMICAL_FIELDS, POLYMER_FIELDS,
    NAME_COLS, CAS_COLS, DD_COLS, DP_COLS, DH_COLS,
    MW_COLS, BP_COLS, DENSITY_COLS, MV_COLS, CATEGORY_COLS,
    SMILES_COLS, FORMULA_COLS, GHS_COLS, RADIUS_COLS,
    find_column,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, "data", "datasets")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "manifest.json")


# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------

def detect_file_type(filepath):
    """Detect file type from extension and content.

    Returns one of: 'csv', 'excel', 'json', 'pdf', or None.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".csv", ".tsv"):
        return "csv"
    if ext in (".xlsx", ".xls"):
        return "excel"
    if ext == ".json":
        return "json"
    if ext == ".pdf":
        return "pdf"
    # Try to sniff content
    try:
        with open(filepath, "rb") as f:
            head = f.read(16)
        if head.startswith(b"%PDF"):
            return "pdf"
        if head[:4] == b"PK\x03\x04":
            return "excel"
        # Try as text
        with open(filepath, "r", encoding="utf-8-sig") as f:
            first = f.read(512)
        if first.strip().startswith(("{", "[")):
            return "json"
        if "," in first or "\t" in first:
            return "csv"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# File readers — return (headers, rows) where rows are list of dicts
# ---------------------------------------------------------------------------

def _read_csv(filepath):
    """Read CSV/TSV file. Returns (headers, rows)."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        # Detect delimiter
        sample = f.read(4096)
        f.seek(0)
        if "\t" in sample and sample.count("\t") > sample.count(","):
            delimiter = "\t"
        else:
            delimiter = ","
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames or []
        for row in reader:
            rows.append(dict(row))
    return headers, rows


def _read_excel(filepath):
    """Read Excel file. Returns (headers, rows)."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl is required to read Excel files: pip install openpyxl")

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not all_rows:
        return [], []

    # First row as headers
    raw_headers = all_rows[0]
    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(raw_headers)]
    rows = []
    import datetime as _dt
    for row_vals in all_rows[1:]:
        if not row_vals or all(v is None for v in row_vals):
            continue
        row = {}
        for i, val in enumerate(row_vals):
            if i < len(headers):
                # Fix Excel date-mangled values
                if isinstance(val, _dt.datetime):
                    val = ""
                row[headers[i]] = val
        rows.append(row)
    return headers, rows


def _read_json(filepath):
    """Read JSON file. Returns (headers, rows).

    Handles both array-of-objects and {"data": [...]} formats.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        # Look for a list-valued key
        for key in ("data", "chemicals", "solvents", "compounds", "results", "entries"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # Use first list value found
            for v in data.values():
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    data = v
                    break

    if not isinstance(data, list) or not data:
        return [], []

    # Flatten to list of dicts
    rows = []
    all_keys = set()
    for item in data:
        if isinstance(item, dict):
            all_keys.update(item.keys())
            rows.append({k: v for k, v in item.items()})
    headers = sorted(all_keys)
    return headers, rows


def read_source(filepath, file_type=None):
    """Read any supported source file.

    Returns: (headers: list[str], rows: list[dict])
    """
    if file_type is None:
        file_type = detect_file_type(filepath)

    if file_type == "csv":
        return _read_csv(filepath)
    elif file_type == "excel":
        return _read_excel(filepath)
    elif file_type == "json":
        return _read_json(filepath)
    elif file_type == "pdf":
        raise NotImplementedError(
            "PDF parsing requires custom handling. Use scripts/clean_hsp.py for OCR PDFs, "
            "or convert the PDF to CSV first."
        )
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# ---------------------------------------------------------------------------
# Column auto-mapping
# ---------------------------------------------------------------------------

_CANONICAL_ALIAS_MAP = {
    "name": NAME_COLS,
    "cas_number": CAS_COLS,
    "delta_d": DD_COLS,
    "delta_p": DP_COLS,
    "delta_h": DH_COLS,
    "molecular_weight": MW_COLS,
    "boiling_point": BP_COLS,
    "density": DENSITY_COLS,
    "molar_volume": MV_COLS,
    "category": CATEGORY_COLS,
    "smiles": SMILES_COLS,
    "molecular_formula": FORMULA_COLS,
    "ghs_hazard": GHS_COLS,
    "radius": RADIUS_COLS,
}


def auto_map_columns(headers):
    """Auto-detect column mapping from source headers to canonical schema.

    Returns:
        mapping: {original_col_name: canonical_field_name}
        unmapped: list of original columns that couldn't be mapped
    """
    mapping = {}
    used_canonical = set()
    unmapped = []

    lower_to_orig = {h.lower().strip(): h for h in headers}

    for canonical, aliases in _CANONICAL_ALIAS_MAP.items():
        for alias in aliases:
            if alias in lower_to_orig and canonical not in used_canonical:
                orig = lower_to_orig[alias]
                if orig not in mapping:
                    mapping[orig] = canonical
                    used_canonical.add(canonical)
                    break

    for h in headers:
        if h not in mapping:
            unmapped.append(h)

    return mapping, unmapped


# ---------------------------------------------------------------------------
# Dataset analysis
# ---------------------------------------------------------------------------

def analyze_dataset(filepath, file_type=None):
    """Produce a full analysis report for a data source file.

    Returns a dict with:
        analysis_id, file_type, filepath, row_count, columns_found,
        column_mapping, unmapped_columns, hsp_coverage, cas_coverage,
        smiles_coverage, quality_issues, sample_rows, detected_type
    """
    if file_type is None:
        file_type = detect_file_type(filepath)

    headers, rows = read_source(filepath, file_type)
    mapping, unmapped = auto_map_columns(headers)

    # Reverse mapping for quick lookup
    rev = {v: k for k, v in mapping.items()}

    # Count coverage
    total = len(rows)
    if total == 0:
        return {
            "analysis_id": str(uuid.uuid4())[:8],
            "file_type": file_type,
            "filepath": filepath,
            "row_count": 0,
            "columns_found": headers,
            "column_mapping": mapping,
            "unmapped_columns": unmapped,
            "hsp_coverage": 0,
            "cas_coverage": 0,
            "smiles_coverage": 0,
            "quality_issues": [{"severity": "error", "message": "No data rows found"}],
            "sample_rows": [],
            "detected_type": "unknown",
        }

    hsp_count = 0
    cas_count = 0
    smiles_count = 0
    has_radius = False
    quality_issues = []
    outlier_count = 0

    dd_col = rev.get("delta_d")
    dp_col = rev.get("delta_p")
    dh_col = rev.get("delta_h")
    name_col = rev.get("name")
    cas_col = rev.get("cas_number")
    smiles_col = rev.get("smiles")
    radius_col = rev.get("radius")

    if not name_col:
        quality_issues.append({"severity": "error", "message": "No name column detected"})
    if not dd_col or not dp_col or not dh_col:
        quality_issues.append({"severity": "error",
                               "message": "Missing HSP columns (need delta_d, delta_p, delta_h)"})

    names_seen = set()
    duplicate_names = 0

    for row in rows:
        # HSP coverage
        dd = parse_float(row.get(dd_col)) if dd_col else None
        dp = parse_float(row.get(dp_col)) if dp_col else None
        dh = parse_float(row.get(dh_col)) if dh_col else None
        if dd is not None and dp is not None and dh is not None:
            hsp_count += 1
            # Outlier check
            if dd < 10 or dd > 25 or dp < 0 or dp > 25 or dh < 0 or dh > 30:
                outlier_count += 1

        # CAS coverage
        cas_val = str(row.get(cas_col, "")).strip() if cas_col else ""
        if cas_val and normalize_cas(cas_val):
            cas_count += 1
        elif cas_val and cas_val not in ("", "None", "nan"):
            # Malformed CAS
            pass

        # SMILES coverage
        smiles_val = str(row.get(smiles_col, "")).strip() if smiles_col else ""
        if smiles_val and smiles_val not in ("", "None", "nan"):
            smiles_count += 1

        # Radius detection
        if radius_col and parse_float(row.get(radius_col)) is not None:
            has_radius = True

        # Duplicate names
        name_val = str(row.get(name_col, "")).strip().lower() if name_col else ""
        if name_val:
            if name_val in names_seen:
                duplicate_names += 1
            names_seen.add(name_val)

    # Quality issues
    if outlier_count > 0:
        quality_issues.append({
            "severity": "warning",
            "message": f"{outlier_count} rows have HSP values outside typical ranges "
                       f"(dD: 10-25, dP: 0-25, dH: 0-30 MPa^0.5)"
        })

    if duplicate_names > 0:
        quality_issues.append({
            "severity": "warning",
            "message": f"{duplicate_names} duplicate names within this dataset"
        })

    if cas_col:
        malformed_cas = 0
        for row in rows:
            cas_val = str(row.get(cas_col, "")).strip()
            if cas_val and cas_val not in ("", "None", "nan") and not normalize_cas(cas_val):
                malformed_cas += 1
        if malformed_cas > 0:
            quality_issues.append({
                "severity": "warning",
                "message": f"{malformed_cas} malformed CAS numbers"
            })

    # Detect chemicals vs polymers
    detected_type = "chemicals"
    if has_radius:
        detected_type = "polymers" if not dd_col else "both"

    # Sample rows (first 5)
    sample_rows = []
    for row in rows[:5]:
        sample = {}
        for orig_col, canon in mapping.items():
            sample[canon] = str(row.get(orig_col, ""))[:80]
        sample_rows.append(sample)

    return {
        "analysis_id": str(uuid.uuid4())[:8],
        "file_type": file_type,
        "filepath": filepath,
        "row_count": total,
        "columns_found": headers,
        "column_mapping": mapping,
        "unmapped_columns": unmapped,
        "hsp_coverage": round(100 * hsp_count / total, 1) if total else 0,
        "cas_coverage": round(100 * cas_count / total, 1) if total else 0,
        "smiles_coverage": round(100 * smiles_count / total, 1) if total else 0,
        "quality_issues": quality_issues,
        "sample_rows": sample_rows,
        "detected_type": detected_type,
    }


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def load_manifest():
    """Load the dataset manifest. Returns dict."""
    if not os.path.exists(MANIFEST_PATH):
        return {"version": 1, "datasets": {}}
    with open(MANIFEST_PATH, "r") as f:
        return json.load(f)


def save_manifest(manifest):
    """Save the dataset manifest to disk."""
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


# ---------------------------------------------------------------------------
# Normalize and write dataset
# ---------------------------------------------------------------------------

def normalize_and_write(filepath, dataset_id, column_mapping=None, metadata=None,
                        file_type=None, confidence_tier=0.30):
    """Parse, normalize, and write a dataset to data/datasets/<id>/.

    Args:
        filepath: path to the source file
        dataset_id: unique slug for this dataset
        column_mapping: {orig_col: canonical_field} (auto-detected if None)
        metadata: dict with optional fields: name, source_url, description
        file_type: override file type detection
        confidence_tier: base confidence score for this dataset

    Returns:
        manifest_entry: dict suitable for insertion into manifest.json
    """
    if metadata is None:
        metadata = {}

    headers, rows = read_source(filepath, file_type)

    if column_mapping is None:
        column_mapping, _ = auto_map_columns(headers)

    # Reverse mapping: canonical -> original column name
    rev = {v: k for k, v in column_mapping.items()}

    # Normalize rows into canonical schema
    chemicals = []
    polymers = []

    for row in rows:
        name_col = rev.get("name")
        name = str(row.get(name_col, "")).strip() if name_col else ""
        if not name:
            continue

        dd = parse_float(row.get(rev.get("delta_d"))) if rev.get("delta_d") else None
        dp = parse_float(row.get(rev.get("delta_p"))) if rev.get("delta_p") else None
        dh = parse_float(row.get(rev.get("delta_h"))) if rev.get("delta_h") else None
        if dd is None or dp is None or dh is None:
            continue

        cas_raw = str(row.get(rev.get("cas_number"), "")).strip() if rev.get("cas_number") else ""
        cas = normalize_cas(cas_raw)

        smiles = str(row.get(rev.get("smiles"), "")).strip() if rev.get("smiles") else ""
        if smiles in ("None", "nan"):
            smiles = ""

        formula = str(row.get(rev.get("molecular_formula"), "")).strip() if rev.get("molecular_formula") else ""
        mw = parse_float(row.get(rev.get("molecular_weight"))) if rev.get("molecular_weight") else None
        bp = parse_float(row.get(rev.get("boiling_point"))) if rev.get("boiling_point") else None
        density = parse_float(row.get(rev.get("density"))) if rev.get("density") else None
        mv = parse_float(row.get(rev.get("molar_volume"))) if rev.get("molar_volume") else None
        ghs = str(row.get(rev.get("ghs_hazard"), "")).strip() if rev.get("ghs_hazard") else ""
        radius = parse_float(row.get(rev.get("radius"))) if rev.get("radius") else None

        category_raw = str(row.get(rev.get("category"), "")).strip() if rev.get("category") else ""

        entry = {
            "name": name,
            "cas_number": cas,
            "delta_d": dd,
            "delta_p": dp,
            "delta_h": dh,
            "source": dataset_id,
            "source_url": metadata.get("source_url", ""),
            "source_count": 1,
        }

        if radius is not None:
            # Polymer entry
            entry["radius"] = radius
            entry["type"] = category_raw or classify_polymer(name)
            entry["confidence"] = compute_confidence(entry, is_polymer=True,
                                                     confidence_tier=confidence_tier)
            polymers.append(entry)
        else:
            # Chemical entry
            entry["smiles"] = smiles
            entry["molecular_formula"] = formula
            entry["molecular_weight"] = mw
            entry["boiling_point"] = bp
            entry["density"] = density
            entry["molar_volume"] = mv
            entry["ghs_hazard"] = ghs
            entry["category"] = category_raw or classify_chemical(name, smiles)
            entry["hidden"] = ""
            entry["confidence"] = compute_confidence(entry, is_polymer=False,
                                                     confidence_tier=confidence_tier)
            chemicals.append(entry)

    # Write to dataset directory
    ds_dir = os.path.join(DATASETS_DIR, dataset_id)
    os.makedirs(os.path.join(ds_dir, "raw"), exist_ok=True)

    # Copy raw source file
    raw_dest = os.path.join(ds_dir, "raw", os.path.basename(filepath))
    if os.path.abspath(filepath) != os.path.abspath(raw_dest):
        shutil.copy2(filepath, raw_dest)

    # Write chemicals CSV
    if chemicals:
        chem_path = os.path.join(ds_dir, "chemicals.csv")
        with open(chem_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CHEMICAL_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for chem in sorted(chemicals, key=lambda x: x["name"].lower()):
                row_out = {}
                for field in CHEMICAL_FIELDS:
                    val = chem.get(field)
                    row_out[field] = val if val is not None else ""
                writer.writerow(row_out)

    # Write polymers CSV
    if polymers:
        poly_path = os.path.join(ds_dir, "polymers.csv")
        with open(poly_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=POLYMER_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for poly in sorted(polymers, key=lambda x: x["name"].lower()):
                row_out = {}
                for field in POLYMER_FIELDS:
                    val = poly.get(field)
                    row_out[field] = val if val is not None else ""
                writer.writerow(row_out)

    # Determine which fields have data
    fields_available = []
    if chemicals:
        for f_name in CHEMICAL_FIELDS:
            if any(c.get(f_name) for c in chemicals):
                fields_available.append(f_name)
    if polymers:
        for f_name in POLYMER_FIELDS:
            if f_name not in fields_available and any(p.get(f_name) for p in polymers):
                fields_available.append(f_name)

    # Build manifest entry
    manifest_entry = {
        "id": dataset_id,
        "name": metadata.get("name", dataset_id),
        "source_url": metadata.get("source_url", ""),
        "description": metadata.get("description", ""),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "chemical_count": len(chemicals),
        "polymer_count": len(polymers),
        "fields_available": fields_available,
        "quality_notes": metadata.get("quality_notes", ""),
        "active": True,
        "confidence_tier": confidence_tier,
    }

    # Write per-dataset metadata
    ds_metadata = {
        **manifest_entry,
        "column_mapping": column_mapping,
        "original_file": os.path.basename(filepath),
    }
    with open(os.path.join(ds_dir, "metadata.json"), "w") as f:
        json.dump(ds_metadata, f, indent=2)

    # Update manifest
    manifest = load_manifest()
    manifest["datasets"][dataset_id] = manifest_entry
    save_manifest(manifest)

    return manifest_entry


def remove_dataset(dataset_id):
    """Remove a dataset from the manifest and optionally delete its directory.

    Returns True if removed, False if not found.
    """
    manifest = load_manifest()
    if dataset_id not in manifest["datasets"]:
        return False

    del manifest["datasets"][dataset_id]
    save_manifest(manifest)

    ds_dir = os.path.join(DATASETS_DIR, dataset_id)
    if os.path.isdir(ds_dir):
        shutil.rmtree(ds_dir)

    return True
