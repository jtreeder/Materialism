#!/usr/bin/env python3
"""Dataset import tool for Materialism HSP database.

Imports data from CSV, Excel, JSON, or PDF sources into the per-dataset
directory structure under data/datasets/<id>/.

Usage:
    python import_dataset.py --file path/to/data.csv --id my_dataset
    python import_dataset.py --file path/to/data.xlsx --id my_dataset --name "My Dataset"
    python import_dataset.py --file data.csv --analyze-only
    python import_dataset.py --id my_dataset --remove
    python import_dataset.py --id my_dataset --set-confidence 0.45
    python import_dataset.py --id my_dataset --toggle          # toggle active/inactive
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "data", "datasets")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "manifest.json")

sys.path.insert(0, BASE_DIR)
from lib.normalize import normalize_name, normalize_cas, parse_float
from lib.classify import classify_chemical, classify_polymer
from lib.confidence import compute_confidence
from lib.schema import (
    CHEMICAL_FIELDS, POLYMER_FIELDS, HSP_RANGES,
    empty_chemical, empty_polymer, validate_row,
)


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest():
    """Load the manifest file, creating it if it doesn't exist."""
    if not os.path.exists(MANIFEST_PATH):
        return {"version": 1, "datasets": {}}
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def save_manifest(manifest):
    """Write manifest to disk."""
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Updated: {MANIFEST_PATH}")


# ---------------------------------------------------------------------------
# File detection & reading
# ---------------------------------------------------------------------------

def detect_file_type(filepath):
    """Detect the type of a data file."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".csv", ".tsv"):
        return "csv"
    elif ext in (".xlsx", ".xls"):
        return "excel"
    elif ext == ".json":
        return "json"
    elif ext == ".pdf":
        return "pdf"
    else:
        # Try to detect CSV by reading first line
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                first_line = f.readline()
            if "," in first_line or "\t" in first_line:
                return "csv"
        except (UnicodeDecodeError, IOError):
            pass
        return "unknown"


def read_csv_data(filepath):
    """Read a CSV/TSV file and return (headers, rows)."""
    # Detect delimiter
    with open(filepath, "r", encoding="utf-8-sig") as f:
        sample = f.read(4096)
    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")

    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, dialect=dialect)
        headers = reader.fieldnames or []
        for row in reader:
            rows.append(row)
    return headers, rows


def read_excel_data(filepath):
    """Read an Excel file and return (headers, rows)."""
    try:
        import openpyxl
    except ImportError:
        print("ERROR: openpyxl not installed. Install with: pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not all_rows:
        return [], []

    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(all_rows[0])]
    rows = []
    for raw_row in all_rows[1:]:
        row = {}
        for i, val in enumerate(raw_row):
            if i < len(headers):
                row[headers[i]] = val
        rows.append(row)
    return headers, rows


def read_json_data(filepath):
    """Read a JSON file and return (headers, rows).

    Supports both array-of-objects and dict-with-array formats.
    """
    with open(filepath) as f:
        data = json.load(f)

    # If it's a list of dicts, use directly
    if isinstance(data, list):
        items = data
    # If it's a dict, look for the largest list value
    elif isinstance(data, dict):
        lists = [(k, v) for k, v in data.items() if isinstance(v, list)]
        if lists:
            # Pick the largest list
            items = max(lists, key=lambda x: len(x[1]))[1]
        else:
            print("ERROR: JSON file does not contain a list of records.")
            sys.exit(1)
    else:
        print("ERROR: Unsupported JSON structure.")
        sys.exit(1)

    if not items or not isinstance(items[0], dict):
        return [], []

    headers = list(items[0].keys())
    rows = items
    return headers, rows


def read_file(filepath):
    """Read a data file and return (headers, rows, file_type)."""
    ftype = detect_file_type(filepath)
    if ftype == "csv":
        h, r = read_csv_data(filepath)
    elif ftype == "excel":
        h, r = read_excel_data(filepath)
    elif ftype == "json":
        h, r = read_json_data(filepath)
    elif ftype == "pdf":
        print("PDF import requires OCR processing.")
        print("Use scripts/clean_hsp.py for Hansen PDF tables, or convert to CSV first.")
        sys.exit(1)
    else:
        print(f"ERROR: Cannot detect file type for {filepath}")
        sys.exit(1)
    return h, r, ftype


# ---------------------------------------------------------------------------
# Column auto-mapping
# ---------------------------------------------------------------------------

# Patterns to recognize common column names
COLUMN_PATTERNS = {
    "name": [
        r"^(chemical\s*)?name$", r"^solvent$", r"^compound$", r"^molecule$",
        r"^material$", r"^polymer[_ ]?name$", r"^solvent[_ ]?name$",
    ],
    "cas_number": [
        r"^cas", r"^cas[_ ]?(number|#|no\.?)$", r"^cas[_ ]?rn$",
    ],
    "smiles": [
        r"^smiles$", r"^canonical[_ ]?smiles$",
    ],
    "molecular_formula": [
        r"^(molecular[_ ]?)?formula$",
    ],
    "delta_d": [
        r"^(delta[_ ]?)?d$", r"^dd$", r"^dispersion$", r"^hansen[_ ]?d$",
        r"^[δd][dD]", r"^dD", r"^delta[_ ]?d",
    ],
    "delta_p": [
        r"^(delta[_ ]?)?p$", r"^dp$", r"^polar(ity)?$", r"^hansen[_ ]?p$",
        r"^[δd][pP]", r"^dP", r"^delta[_ ]?p",
    ],
    "delta_h": [
        r"^(delta[_ ]?)?h$", r"^dh$", r"^h[- ]?bond", r"^hydrogen",
        r"^hansen[_ ]?h$", r"^[δd][hH]", r"^dH", r"^delta[_ ]?h",
    ],
    "molecular_weight": [
        r"^(molecular[_ ]?)?weight$", r"^mw", r"^mol[_ ]?wt",
        r"^MWt", r"^molar[_ ]?mass$",
    ],
    "boiling_point": [
        r"^(boiling[_ ]?)?point$", r"^bp$", r"^Tb", r"^b\.?p\.?$",
    ],
    "density": [
        r"^density", r"^rho$", r"^ρ$",
    ],
    "molar_volume": [
        r"^(molar[_ ]?)?volume$", r"^[vV][_ ]?m", r"^MVol",
        r"^mol[_ ]?vol",
    ],
    "ghs_hazard": [
        r"^ghs", r"^hazard", r"^H_Statement",
    ],
    "radius": [
        r"^(interaction[_ ]?)?radius$", r"^R0$", r"^r0$",
        r"^R₀$", r"^solubility[_ ]?radius$",
    ],
    "type": [
        r"^(polymer[_ ]?)?type$", r"^category$", r"^class$",
    ],
}


def auto_map_columns(headers):
    """Auto-detect column mapping from source headers to canonical fields.

    Returns a dict: {source_col: canonical_field}
    """
    mapping = {}
    used_fields = set()

    for header in headers:
        h_clean = header.strip()
        h_lower = h_clean.lower().replace("(", "").replace(")", "").strip()

        for field, patterns in COLUMN_PATTERNS.items():
            if field in used_fields:
                continue
            for pattern in patterns:
                if re.search(pattern, h_lower, re.I):
                    mapping[h_clean] = field
                    used_fields.add(field)
                    break
            if h_clean in mapping:
                break

    return mapping


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_data(headers, rows, column_mapping=None):
    """Analyze a dataset and return a report dict."""
    if column_mapping is None:
        column_mapping = auto_map_columns(headers)

    total = len(rows)
    report = {
        "total_rows": total,
        "headers": headers,
        "column_mapping": column_mapping,
        "unmapped_columns": [h for h in headers if h not in column_mapping],
        "mapped_fields": list(column_mapping.values()),
    }

    # Check field coverage
    has_name = 0
    has_hsp = 0
    has_cas = 0
    has_smiles = 0
    has_mw = 0
    has_bp = 0
    has_radius = 0
    outliers = []

    name_col = None
    for src, dst in column_mapping.items():
        if dst == "name":
            name_col = src

    for i, row in enumerate(rows):
        # Check name
        name_val = None
        for src, dst in column_mapping.items():
            if dst == "name":
                name_val = row.get(src)
                break
        if name_val and str(name_val).strip():
            has_name += 1

        # Check HSP
        dd = dp = dh = None
        for src, dst in column_mapping.items():
            val = row.get(src)
            if dst == "delta_d":
                dd = parse_float(val)
            elif dst == "delta_p":
                dp = parse_float(val)
            elif dst == "delta_h":
                dh = parse_float(val)
        if dd is not None and dp is not None and dh is not None:
            has_hsp += 1
            # Range check
            for param, val in [("delta_d", dd), ("delta_p", dp), ("delta_h", dh)]:
                lo, hi = HSP_RANGES[param]
                if val < lo or val > hi:
                    outliers.append((i, param, val))

        # Check CAS
        for src, dst in column_mapping.items():
            if dst == "cas_number":
                cas_val = str(row.get(src, "")).strip()
                if cas_val and normalize_cas(cas_val):
                    has_cas += 1
                break

        # Check SMILES
        for src, dst in column_mapping.items():
            if dst == "smiles":
                s = str(row.get(src, "")).strip()
                if s:
                    has_smiles += 1
                break

        # Check MW
        for src, dst in column_mapping.items():
            if dst == "molecular_weight":
                if parse_float(row.get(src)) is not None:
                    has_mw += 1
                break

        # Check BP
        for src, dst in column_mapping.items():
            if dst == "boiling_point":
                if parse_float(row.get(src)) is not None:
                    has_bp += 1
                break

        # Check radius (polymer indicator)
        for src, dst in column_mapping.items():
            if dst == "radius":
                if parse_float(row.get(src)) is not None:
                    has_radius += 1
                break

    report["has_name"] = has_name
    report["has_hsp"] = has_hsp
    report["has_cas"] = has_cas
    report["has_smiles"] = has_smiles
    report["has_mw"] = has_mw
    report["has_bp"] = has_bp
    report["has_radius"] = has_radius
    report["outliers"] = outliers[:20]  # cap at 20 examples
    report["is_polymer_data"] = has_radius > total * 0.3

    # Quality issues
    issues = []
    if has_name < total * 0.9:
        issues.append(f"{total - has_name} rows missing chemical name")
    if has_hsp < total * 0.5:
        issues.append(f"Only {has_hsp}/{total} rows have complete HSP triplets")
    if "delta_d" not in report["mapped_fields"]:
        issues.append("No delta_d column detected")
    if "delta_p" not in report["mapped_fields"]:
        issues.append("No delta_p column detected")
    if "delta_h" not in report["mapped_fields"]:
        issues.append("No delta_h column detected")
    if "name" not in report["mapped_fields"]:
        issues.append("No name column detected")
    if len(outliers) > 0:
        issues.append(f"{len(outliers)} values outside typical HSP ranges")
    report["issues"] = issues

    return report


def print_report(report, filepath=None):
    """Print a human-readable analysis report."""
    total = report["total_rows"]
    print()
    print("=" * 60)
    print("DATASET ANALYSIS REPORT")
    print("=" * 60)
    if filepath:
        print(f"  File: {filepath}")
    print(f"  Total rows: {total}")
    print()

    # Column mapping
    print("Column mapping (auto-detected):")
    for src, dst in report["column_mapping"].items():
        print(f"  {src:30s} → {dst}")
    if report["unmapped_columns"]:
        print(f"\n  Unmapped columns: {', '.join(report['unmapped_columns'])}")

    # Coverage
    print(f"\nField coverage:")
    print(f"  Name:             {report['has_name']:>5}/{total} ({pct(report['has_name'], total)})")
    print(f"  HSP triplet:      {report['has_hsp']:>5}/{total} ({pct(report['has_hsp'], total)})")
    print(f"  CAS number:       {report['has_cas']:>5}/{total} ({pct(report['has_cas'], total)})")
    print(f"  SMILES:           {report['has_smiles']:>5}/{total} ({pct(report['has_smiles'], total)})")
    print(f"  Molecular weight: {report['has_mw']:>5}/{total} ({pct(report['has_mw'], total)})")
    print(f"  Boiling point:    {report['has_bp']:>5}/{total} ({pct(report['has_bp'], total)})")
    if report["has_radius"]:
        print(f"  Radius (R₀):      {report['has_radius']:>5}/{total} ({pct(report['has_radius'], total)})")

    # Data type
    if report["is_polymer_data"]:
        print(f"\n  Detected as: POLYMER data (has radius/R₀ values)")
    else:
        print(f"\n  Detected as: CHEMICAL/SOLVENT data")

    # Quality issues
    if report["issues"]:
        print(f"\nQuality issues:")
        for issue in report["issues"]:
            print(f"  ⚠ {issue}")

    # Outlier examples
    if report["outliers"]:
        print(f"\nHSP outlier examples (first {len(report['outliers'])}):")
        for row_idx, param, val in report["outliers"][:5]:
            lo, hi = HSP_RANGES[param]
            print(f"  Row {row_idx}: {param} = {val} (typical: {lo}-{hi})")

    # Sample rows
    print(f"\nSample data (first 3 rows):")
    mapping = report["column_mapping"]
    for src, dst in list(mapping.items())[:8]:
        print(f"  {dst:20s}", end="")
    print()
    print(f"  {'─' * 20}" * min(8, len(mapping)))

    print("=" * 60)


def pct(n, total):
    """Format as percentage string."""
    if total == 0:
        return "0%"
    return f"{100 * n / total:.0f}%"


# ---------------------------------------------------------------------------
# Import / normalize
# ---------------------------------------------------------------------------

def normalize_and_write(dataset_id, name, source_url, headers, rows,
                        column_mapping, confidence_tier, filepath):
    """Normalize data and write to the dataset directory."""
    ds_dir = os.path.join(DATASETS_DIR, dataset_id)
    os.makedirs(os.path.join(ds_dir, "raw"), exist_ok=True)

    # Copy raw file
    if filepath and os.path.exists(filepath):
        raw_dest = os.path.join(ds_dir, "raw", os.path.basename(filepath))
        if not os.path.exists(raw_dest):
            shutil.copy2(filepath, raw_dest)
            print(f"  Copied raw file to: {raw_dest}")

    # Determine if this is polymer or chemical data
    has_radius_col = "radius" in column_mapping.values()
    report = analyze_data(headers, rows, column_mapping)
    is_polymer = report["is_polymer_data"]

    chemicals = []
    polymers = []
    skipped = 0
    skip_reasons = []

    for row in rows:
        # Map source columns to canonical fields
        mapped = {}
        for src_col, dst_field in column_mapping.items():
            mapped[dst_field] = row.get(src_col)

        # Get name
        raw_name = str(mapped.get("name", "")).strip() if mapped.get("name") else ""
        if not raw_name:
            skipped += 1
            continue

        # Parse HSP values
        dd = parse_float(mapped.get("delta_d"))
        dp = parse_float(mapped.get("delta_p"))
        dh = parse_float(mapped.get("delta_h"))
        if dd is None or dp is None or dh is None:
            skipped += 1
            skip_reasons.append("missing HSP")
            continue

        # Normalize CAS
        cas = normalize_cas(str(mapped.get("cas_number", "")).strip()
                           if mapped.get("cas_number") else "")

        if is_polymer or (has_radius_col and parse_float(mapped.get("radius")) is not None):
            entry = empty_polymer()
            entry["name"] = raw_name
            entry["cas_number"] = cas
            entry["delta_d"] = dd
            entry["delta_p"] = dp
            entry["delta_h"] = dh
            entry["radius"] = parse_float(mapped.get("radius"))
            entry["type"] = str(mapped.get("type", "")).strip() if mapped.get("type") else ""
            if not entry["type"]:
                entry["type"] = classify_polymer(raw_name)
            entry["source"] = dataset_id
            entry["source_url"] = source_url
            entry["dataset_id"] = dataset_id
            entry["confidence"] = compute_confidence(entry, is_polymer=True,
                                                     confidence_tier=confidence_tier)
            polymers.append(entry)
        else:
            entry = empty_chemical()
            entry["name"] = raw_name
            entry["cas_number"] = cas
            entry["smiles"] = str(mapped.get("smiles", "")).strip() if mapped.get("smiles") else ""
            entry["molecular_formula"] = (str(mapped.get("molecular_formula", "")).strip()
                                          if mapped.get("molecular_formula") else "")
            entry["delta_d"] = dd
            entry["delta_p"] = dp
            entry["delta_h"] = dh
            entry["molecular_weight"] = parse_float(mapped.get("molecular_weight"))
            entry["boiling_point"] = parse_float(mapped.get("boiling_point"))
            entry["density"] = parse_float(mapped.get("density"))
            entry["molar_volume"] = parse_float(mapped.get("molar_volume"))
            entry["ghs_hazard"] = (str(mapped.get("ghs_hazard", "")).strip()
                                   if mapped.get("ghs_hazard") else "")
            entry["category"] = classify_chemical(raw_name, entry["smiles"])
            entry["source"] = dataset_id
            entry["source_url"] = source_url
            entry["dataset_id"] = dataset_id
            entry["confidence"] = compute_confidence(entry, is_polymer=False,
                                                     confidence_tier=confidence_tier)
            chemicals.append(entry)

    # Write chemicals CSV
    chem_path = os.path.join(ds_dir, "chemicals.csv")
    with open(chem_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CHEMICAL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for chem in chemicals:
            row_out = {}
            for field in CHEMICAL_FIELDS:
                val = chem.get(field)
                row_out[field] = val if val is not None else ""
            writer.writerow(row_out)
    print(f"  Written: {chem_path} ({len(chemicals)} chemicals)")

    # Write polymers CSV
    poly_path = os.path.join(ds_dir, "polymers.csv")
    with open(poly_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=POLYMER_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for poly in polymers:
            row_out = {}
            for field in POLYMER_FIELDS:
                val = poly.get(field)
                row_out[field] = val if val is not None else ""
            writer.writerow(row_out)
    print(f"  Written: {poly_path} ({len(polymers)} polymers)")

    # Write metadata
    fields_available = []
    if chemicals:
        for f in CHEMICAL_FIELDS:
            if any(c.get(f) for c in chemicals):
                fields_available.append(f)
    if polymers:
        for f in POLYMER_FIELDS:
            if any(p.get(f) for p in polymers):
                fields_available.append(f)
    fields_available = sorted(set(fields_available))

    reason_counts = {}
    for r in skip_reasons:
        reason_counts[r] = reason_counts.get(r, 0) + 1

    metadata = {
        "id": dataset_id,
        "name": name,
        "source_url": source_url,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "original_files": [os.path.basename(filepath)] if filepath else [],
        "column_mapping": {k: v for k, v in column_mapping.items()},
        "import_report": {
            "total_rows_in_source": len(rows),
            "chemicals_imported": len(chemicals),
            "polymers_imported": len(polymers),
            "rows_skipped": skipped,
            "skip_reasons": [f"{v} rows: {k}" for k, v in reason_counts.items()],
        },
        "chemical_count": len(chemicals),
        "polymer_count": len(polymers),
        "fields_available": fields_available,
        "quality_notes": "",
        "active": True,
        "confidence_tier": confidence_tier,
    }

    meta_path = os.path.join(ds_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Written: {meta_path}")

    # Update manifest
    manifest = load_manifest()
    manifest["datasets"][dataset_id] = {
        "id": dataset_id,
        "name": name,
        "source_url": source_url,
        "imported_at": metadata["imported_at"],
        "chemical_count": len(chemicals),
        "polymer_count": len(polymers),
        "fields_available": fields_available,
        "quality_notes": "",
        "active": True,
        "confidence_tier": confidence_tier,
    }
    save_manifest(manifest)

    print(f"\nImport complete: {len(chemicals)} chemicals, {len(polymers)} polymers")
    if skipped:
        print(f"  ({skipped} rows skipped)")


# ---------------------------------------------------------------------------
# Remove dataset
# ---------------------------------------------------------------------------

def remove_dataset(dataset_id):
    """Remove a dataset from the manifest and optionally its directory."""
    manifest = load_manifest()
    if dataset_id not in manifest["datasets"]:
        print(f"Dataset '{dataset_id}' not found in manifest.")
        return

    del manifest["datasets"][dataset_id]
    save_manifest(manifest)

    ds_dir = os.path.join(DATASETS_DIR, dataset_id)
    if os.path.exists(ds_dir):
        shutil.rmtree(ds_dir)
        print(f"  Removed directory: {ds_dir}")

    print(f"Dataset '{dataset_id}' removed.")


# ---------------------------------------------------------------------------
# Toggle active/inactive
# ---------------------------------------------------------------------------

def toggle_dataset(dataset_id):
    """Toggle a dataset's active status."""
    manifest = load_manifest()
    if dataset_id not in manifest["datasets"]:
        print(f"Dataset '{dataset_id}' not found in manifest.")
        return

    current = manifest["datasets"][dataset_id].get("active", True)
    manifest["datasets"][dataset_id]["active"] = not current
    save_manifest(manifest)
    status = "active" if not current else "inactive"
    print(f"Dataset '{dataset_id}' is now {status}.")


# ---------------------------------------------------------------------------
# Set confidence tier
# ---------------------------------------------------------------------------

def set_confidence(dataset_id, tier):
    """Set a dataset's confidence tier."""
    manifest = load_manifest()
    if dataset_id not in manifest["datasets"]:
        print(f"Dataset '{dataset_id}' not found in manifest.")
        return

    manifest["datasets"][dataset_id]["confidence_tier"] = tier
    save_manifest(manifest)
    print(f"Dataset '{dataset_id}' confidence tier set to {tier}.")


# ---------------------------------------------------------------------------
# List datasets
# ---------------------------------------------------------------------------

def list_datasets():
    """Print a summary of all datasets."""
    manifest = load_manifest()
    datasets = manifest.get("datasets", {})

    if not datasets:
        print("No datasets imported yet.")
        return

    print(f"\n{'ID':<25s} {'Name':<35s} {'Chems':>6s} {'Polys':>6s} {'Active':>7s} {'Conf':>5s}")
    print("─" * 90)
    for ds_id, ds in sorted(datasets.items()):
        status = "  ✓" if ds.get("active", True) else "  ✗"
        conf = f"{ds.get('confidence_tier', 0.25):.2f}"
        print(f"{ds_id:<25s} {ds.get('name', '')[:35]:<35s} "
              f"{ds.get('chemical_count', 0):>6d} {ds.get('polymer_count', 0):>6d} "
              f"{status:>7s} {conf:>5s}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Import datasets into Materialism HSP database"
    )
    parser.add_argument("--file", "-f", help="Path to source data file")
    parser.add_argument("--id", "-i", dest="dataset_id", help="Dataset ID (slug)")
    parser.add_argument("--name", "-n", help="Human-readable dataset name")
    parser.add_argument("--url", "-u", help="Source URL for attribution")
    parser.add_argument("--confidence", "-c", type=float, default=0.35,
                        help="Base confidence tier (0.0-1.0, default: 0.35)")
    parser.add_argument("--analyze-only", "-a", action="store_true",
                        help="Analyze file without importing")
    parser.add_argument("--remove", action="store_true",
                        help="Remove a dataset by ID")
    parser.add_argument("--toggle", action="store_true",
                        help="Toggle dataset active/inactive")
    parser.add_argument("--set-confidence", type=float, metavar="TIER",
                        help="Set confidence tier for a dataset")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List all datasets")
    parser.add_argument("--mapping", "-m", action="append", metavar="SRC=DST",
                        help="Manual column mapping (e.g. 'Solvent=name')")

    args = parser.parse_args()

    # List mode
    if args.list:
        list_datasets()
        return

    # Remove mode
    if args.remove:
        if not args.dataset_id:
            print("ERROR: --id required for --remove")
            sys.exit(1)
        remove_dataset(args.dataset_id)
        return

    # Toggle mode
    if args.toggle:
        if not args.dataset_id:
            print("ERROR: --id required for --toggle")
            sys.exit(1)
        toggle_dataset(args.dataset_id)
        return

    # Set confidence
    if args.set_confidence is not None:
        if not args.dataset_id:
            print("ERROR: --id required for --set-confidence")
            sys.exit(1)
        set_confidence(args.dataset_id, args.set_confidence)
        return

    # Import mode — need a file
    if not args.file:
        parser.print_help()
        return

    filepath = os.path.abspath(args.file)
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    print(f"Reading: {filepath}")
    headers, rows, ftype = read_file(filepath)
    print(f"  File type: {ftype}")
    print(f"  Rows: {len(rows)}")
    print(f"  Columns: {len(headers)}")

    # Auto-map columns
    column_mapping = auto_map_columns(headers)

    # Apply manual overrides
    if args.mapping:
        for m in args.mapping:
            if "=" not in m:
                print(f"WARNING: Invalid mapping format '{m}', expected 'SRC=DST'")
                continue
            src, dst = m.split("=", 1)
            column_mapping[src.strip()] = dst.strip()

    # Analyze
    report = analyze_data(headers, rows, column_mapping)
    print_report(report, filepath)

    if args.analyze_only:
        print("\n(Analyze-only mode — no data written)")
        return

    # Import
    dataset_id = args.dataset_id
    if not dataset_id:
        # Generate ID from filename
        dataset_id = re.sub(r"[^a-z0-9]+", "_",
                            os.path.splitext(os.path.basename(filepath))[0].lower())
        dataset_id = dataset_id.strip("_")

    name = args.name or dataset_id.replace("_", " ").title()
    source_url = args.url or ""

    # Check if dataset already exists
    manifest = load_manifest()
    if dataset_id in manifest["datasets"]:
        print(f"\nWARNING: Dataset '{dataset_id}' already exists.")
        print("  Use --remove first, or choose a different --id.")
        sys.exit(1)

    print(f"\nImporting as '{dataset_id}'...")
    normalize_and_write(dataset_id, name, source_url, headers, rows,
                        column_mapping, args.confidence, filepath)


if __name__ == "__main__":
    main()
