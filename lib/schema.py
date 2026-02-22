"""Canonical field definitions for the Materialism HSP database."""

CHEMICAL_FIELDS = [
    "name", "cas_number", "smiles", "molecular_formula",
    "delta_d", "delta_p", "delta_h",
    "molecular_weight", "boiling_point", "density", "molar_volume",
    "category", "ghs_hazard",
    "confidence", "source_count", "source", "source_url", "hidden",
]

POLYMER_FIELDS = [
    "name", "cas_number",
    "delta_d", "delta_p", "delta_h",
    "radius", "type",
    "confidence", "source_count", "source", "source_url",
]

# Column name aliases for auto-mapping during import
NAME_COLS = {"name", "chemical", "compound", "solvent", "material", "molecule"}
CAS_COLS = {"cas", "cas_number", "cas_no", "casrn", "cas number", "cas #"}
DD_COLS = {"delta_d", "dd", "dispersion", "\u03b4d", "deltad", "d_d", "hansen_d",
           "dd_mpa05", "dd_mpa0.5", "\u03b4d (mpa^0.5)"}
DP_COLS = {"delta_p", "dp", "polar", "polarity", "\u03b4p", "deltap", "d_p", "hansen_p",
           "dp_mpa05", "dp_mpa0.5", "\u03b4p (mpa^0.5)"}
DH_COLS = {"delta_h", "dh", "hydrogen", "h-h bonding", "h_bonding", "\u03b4h", "deltah",
           "d_h", "hansen_h", "dh_mpa05", "dh_mpa0.5", "\u03b4h (mpa^0.5)",
           "hydrogen_bonding"}
MW_COLS = {"molecular_weight", "mw", "mol_weight", "molar_mass", "mwt_g_mol"}
BP_COLS = {"boiling_point", "bp", "boiling", "b.p.", "tb_c"}
DENSITY_COLS = {"density", "rho", "\u03c1", "density_g_cm3"}
MV_COLS = {"molar_volume", "mv", "mol_volume", "vm", "mvol_cm3_mol",
           "volume_cm3_per_mol"}
CATEGORY_COLS = {"category", "type", "class", "group"}
SMILES_COLS = {"smiles", "smi"}
FORMULA_COLS = {"molecular_formula", "formula", "molecular formula"}
GHS_COLS = {"ghs_hazard", "ghs", "h_statements", "hazard"}
RADIUS_COLS = {"radius", "r0", "r_0", "interaction_radius"}
POLYMER_TYPE_COLS = {"type", "polymer_type", "category"}


def find_column(headers, aliases):
    """Find the matching column name from a set of aliases.

    Returns the original column name (preserving case) or None.
    """
    lower_headers = {h.lower().strip(): h for h in headers}
    for alias in aliases:
        if alias in lower_headers:
            return lower_headers[alias]
    return None


def validate_row(row, fields):
    """Validate that a row dict has the required HSP fields.

    Returns True if name and all three delta values are present.
    """
    if not row.get("name"):
        return False
    if row.get("delta_d") is None or row.get("delta_p") is None or row.get("delta_h") is None:
        return False
    return True
