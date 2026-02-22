"""Canonical field definitions for Materialism HSP database."""

CHEMICAL_FIELDS = [
    "name", "cas_number", "smiles", "molecular_formula",
    "delta_d", "delta_p", "delta_h",
    "molecular_weight", "boiling_point", "density", "molar_volume",
    "category", "ghs_hazard",
    "confidence", "source_count", "source", "source_url",
    "dataset_id", "hidden",
]

POLYMER_FIELDS = [
    "name", "cas_number",
    "delta_d", "delta_p", "delta_h",
    "radius", "type",
    "confidence", "source_count", "source", "source_url",
    "dataset_id", "hidden",
]

# Required HSP triplet fields
HSP_FIELDS = ["delta_d", "delta_p", "delta_h"]

# Typical HSP value ranges for quality checks (MPa^0.5)
HSP_RANGES = {
    "delta_d": (10.0, 26.0),
    "delta_p": (0.0, 30.0),
    "delta_h": (0.0, 50.0),
}


def empty_chemical():
    """Return a chemical dict with all canonical fields set to defaults."""
    return {
        "name": "", "cas_number": "", "smiles": "", "molecular_formula": "",
        "delta_d": None, "delta_p": None, "delta_h": None,
        "molecular_weight": None, "boiling_point": None, "density": None,
        "molar_volume": None, "category": "", "ghs_hazard": "",
        "confidence": 0, "source_count": 1, "source": "", "source_url": "",
        "dataset_id": "", "hidden": "",
    }


def empty_polymer():
    """Return a polymer dict with all canonical fields set to defaults."""
    return {
        "name": "", "cas_number": "",
        "delta_d": None, "delta_p": None, "delta_h": None,
        "radius": None, "type": "",
        "confidence": 0, "source_count": 1, "source": "", "source_url": "",
        "dataset_id": "", "hidden": "",
    }


def validate_row(row, is_polymer=False):
    """Validate a row has the required HSP triplet. Returns (ok, issues)."""
    issues = []
    for f in HSP_FIELDS:
        val = row.get(f)
        if val is None:
            issues.append(f"missing {f}")
    if not row.get("name"):
        issues.append("missing name")
    # Range checks
    for f in HSP_FIELDS:
        val = row.get(f)
        if val is not None:
            lo, hi = HSP_RANGES[f]
            if val < lo or val > hi:
                issues.append(f"{f}={val} outside typical range [{lo}, {hi}]")
    return len(issues) == 0, issues
