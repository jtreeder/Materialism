"""Import chemical HSP data from CSV files.

Expected CSV columns (flexible matching):
- name / chemical / compound
- cas / cas_number / cas_no
- delta_d / dD / dispersion
- delta_p / dP / polar
- delta_h / dH / hydrogen
- molecular_weight / mw (optional)
- boiling_point / bp (optional)
- density (optional)
- molar_volume / mv (optional)
- category / type (optional)
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from backend.app.models.database import Chemical, get_engine, get_session, init_db

# Column name aliases
NAME_COLS = {"name", "chemical", "compound", "solvent", "material"}
CAS_COLS = {"cas", "cas_number", "cas_no", "casrn", "cas number"}
DD_COLS = {"delta_d", "dd", "dispersion", "δd", "deltad", "d_d"}
DP_COLS = {"delta_p", "dp", "polar", "δp", "deltap", "d_p"}
DH_COLS = {"delta_h", "dh", "hydrogen", "δh", "deltah", "d_h", "h_bonding"}
MW_COLS = {"molecular_weight", "mw", "mol_weight", "molar_mass"}
BP_COLS = {"boiling_point", "bp", "boiling", "b.p."}
DENSITY_COLS = {"density", "rho", "ρ"}
MV_COLS = {"molar_volume", "mv", "mol_volume", "vm"}
CATEGORY_COLS = {"category", "type", "class", "group"}
SMILES_COLS = {"smiles", "smi"}


def _find_col(headers, aliases):
    """Find the matching column name from a set of aliases."""
    lower_headers = {h.lower().strip(): h for h in headers}
    for alias in aliases:
        if alias in lower_headers:
            return lower_headers[alias]
    return None


def _parse_float(val):
    if val is None or val.strip() == "":
        return None
    try:
        return float(val.replace(",", ""))
    except ValueError:
        return None


def import_csv(filepath, session=None, data_source=None):
    """Import chemicals from a CSV file into the database.

    Returns:
        tuple of (imported_count, skipped_count, errors)
    """
    if session is None:
        engine = init_db()
        session = get_session(engine)

    if data_source is None:
        data_source = os.path.basename(filepath)

    imported = 0
    skipped = 0
    errors = []

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        # Map columns
        name_col = _find_col(headers, NAME_COLS)
        cas_col = _find_col(headers, CAS_COLS)
        dd_col = _find_col(headers, DD_COLS)
        dp_col = _find_col(headers, DP_COLS)
        dh_col = _find_col(headers, DH_COLS)
        mw_col = _find_col(headers, MW_COLS)
        bp_col = _find_col(headers, BP_COLS)
        density_col = _find_col(headers, DENSITY_COLS)
        mv_col = _find_col(headers, MV_COLS)
        category_col = _find_col(headers, CATEGORY_COLS)
        smiles_col = _find_col(headers, SMILES_COLS)

        if not name_col:
            return 0, 0, ["No name column found. Expected one of: " + str(NAME_COLS)]
        if not dd_col or not dp_col or not dh_col:
            return 0, 0, ["Missing HSP columns. Need δD, δP, δH."]

        for i, row in enumerate(reader):
            try:
                name = row.get(name_col, "").strip()
                if not name:
                    skipped += 1
                    continue

                dd = _parse_float(row.get(dd_col))
                dp = _parse_float(row.get(dp_col))
                dh = _parse_float(row.get(dh_col))

                if dd is None or dp is None or dh is None:
                    skipped += 1
                    continue

                # Check for duplicates by CAS or name
                cas = row.get(cas_col, "").strip() if cas_col else ""
                existing = None
                if cas:
                    existing = session.query(Chemical).filter_by(cas_number=cas).first()
                if not existing:
                    existing = session.query(Chemical).filter_by(name=name).first()

                if existing:
                    skipped += 1
                    continue

                chem = Chemical(
                    name=name,
                    cas_number=cas if cas else None,
                    smiles=row.get(smiles_col, "").strip() if smiles_col else None,
                    delta_d=dd,
                    delta_p=dp,
                    delta_h=dh,
                    molecular_weight=_parse_float(row.get(mw_col)) if mw_col else None,
                    boiling_point=_parse_float(row.get(bp_col)) if bp_col else None,
                    density=_parse_float(row.get(density_col)) if density_col else None,
                    molar_volume=_parse_float(row.get(mv_col)) if mv_col else None,
                    category=row.get(category_col, "").strip() if category_col else None,
                    data_source=data_source,
                )
                session.add(chem)
                imported += 1

            except Exception as e:
                errors.append(f"Row {i+2}: {e}")

        session.commit()

    return imported, skipped, errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_csv.py <csvfile> [data_source]")
        sys.exit(1)

    filepath = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else None

    imported, skipped, errors = import_csv(filepath, data_source=source)
    print(f"Imported: {imported}, Skipped: {skipped}, Errors: {len(errors)}")
    for err in errors[:10]:
        print(f"  {err}")
