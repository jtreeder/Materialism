"""
integrate_enriched.py — Map solvents_enriched.csv into the app's dataset structure.

Reads:  data/processed/solvents_enriched.csv
Writes:
  - data/datasets/hspip_solvents/chemicals.csv  (updated with enriched data)
  - data/classyfire_cache.json                  (updated with ClassyFire results)
  - data/manifest.json                          (updated fields_available)

Then runs build_unified.py and generate_html.py.
"""

import csv
import json
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
ENRICHED_CSV = DATA_DIR / "processed" / "solvents_enriched.csv"
DATASET_CSV = DATA_DIR / "datasets" / "hspip_solvents" / "chemicals.csv"
CF_CACHE = DATA_DIR / "classyfire_cache.json"
MANIFEST = DATA_DIR / "manifest.json"

# ─── Category map from ClassyFire cf_class → app category ────────────────────
CF_CLASS_TO_CATEGORY = {
    "Organooxygen compounds": "ether",          # broad — refined below by subclass
    "Organochlorides": "halogenated",
    "Organobromides": "halogenated",
    "Organoiodides": "halogenated",
    "Organofluorides": "fluorinated",
    "Organofluorides and their derivatives": "fluorinated",
    "Organonitrogen compounds": "amine",
    "Organohalogen compounds": "halogenated",
    "Organonitrogen compounds": "amine",
    "Hydrocarbons": "hydrocarbon",
    "Benzenoids": "aromatic",
    "Benzene and substituted derivatives": "aromatic",
    "Naphthalenes": "aromatic",
    "Organosulfur compounds": "sulfur compound",
    "Organophosphorus compounds": "inorganic",
    "Organosilicon compounds": "inorganic",
    "Inorganic compounds": "inorganic",
    "Vinyl halides": "halogenated",
    "Alkyl halides": "halogenated",
    "Allyl-type 1,3-dipolar organic compounds": "hydrocarbon",
    "Organonitrogen compounds": "amine",
    "Benzotriazoles and derivatives": "heterocyclic",
    "Azoles": "heterocyclic",
    "Triazoles and derivatives": "heterocyclic",
    "Benzazoles": "heterocyclic",
    "Pyridines and derivatives": "amine",
    "Pyrimidines and pyrimidine derivatives": "heterocyclic",
    "Diazines": "heterocyclic",
    "Quinolines and derivatives": "heterocyclic",
    "Isoquinolines and derivatives": "heterocyclic",
    "Organic 1,3-dipolar compounds": "hydrocarbon",
    "Vinyl compounds": "hydrocarbon",
    "Oligopeptides": "other",
    "Keto acids and derivatives": "acid",
    "Amino acids and derivatives": "amine",
    "Fatty acyls": "ester",
    "Glycerophospholipids": "inorganic",
    "Wax esters": "ester",
    "Phenols": "alcohol",
    "Enols": "alcohol",
    "Alcohols and polyols": "alcohol",
    "Methyl esters": "ester",
    "Carboxylic acids and derivatives": "acid",
    "Nitrogen compounds": "amine",
}

CF_SUBCLASS_TO_CATEGORY = {
    "Esters": "ester",
    "Lactones": "ester",
    "Carboxylic acid esters": "ester",
    "Carbonates": "ester",
    "Ketones": "ketone",
    "Cyclic ketones": "ketone",
    "Diketones": "ketone",
    "Aldehydes": "aldehyde",
    "Alcohols": "alcohol",
    "Diols": "alcohol",
    "Triols": "alcohol",
    "Phenols": "alcohol",
    "Carboxylic acids": "acid",
    "Dicarboxylic acids and derivatives": "acid",
    "Ethers": "ether",
    "Aliphatic ethers": "ether",
    "Aromatic ethers": "ether",
    "Epoxides": "ether",
    "Nitriles": "nitrile",
    "Aliphatic nitriles": "nitrile",
    "Aromatic nitriles": "nitrile",
    "Amines": "amine",
    "Primary amines": "amine",
    "Secondary amines": "amine",
    "Tertiary amines": "amine",
    "Aromatic amines": "amine",
    "Amides": "amide",
    "Lactams": "amide",
    "Imides": "amide",
    "Sulfoxides": "sulfoxide",
    "Sulfones": "sulfoxide",
    "Thiols": "sulfur compound",
    "Thioethers": "sulfur compound",
    "Disulfides": "sulfur compound",
    "Sulfur heterocycles": "heterocyclic",
    "Halogenated hydrocarbons": "halogenated",
    "Nitro compounds": "nitro",
    "Nitroso compounds": "nitro",
    "Terpenoids": "terpene",
    "Monoterpenoids": "terpene",
    "Sesquiterpenoids": "terpene",
    "Alkyl halides": "halogenated",
    "Dihalogenated hydrocarbons": "halogenated",
    "Organofluorides": "fluorinated",
    "Fluorinated hydrocarbons": "fluorinated",
    "Benzene and substituted derivatives": "aromatic",
    "Naphthalenes": "aromatic",
    "Acyclic hydrocarbons": "hydrocarbon",
    "Alkenes": "hydrocarbon",
    "Alkynes": "hydrocarbon",
    "Alkanes": "hydrocarbon",
    "Cyclic hydrocarbons": "hydrocarbon",
    "Glycol ethers": "glycol ether",
    "Imidazoles": "heterocyclic",
    "Pyridines": "amine",
    "Morpholines": "amine",
    "Piperidines": "amine",
    "Piperazines": "amine",
    "Organosilicon compounds": "inorganic",
}


def cf_to_category(cf_class, cf_subclass, name_clean, smiles):
    """Map ClassyFire class/subclass to app category, fallback to classify_chemical."""
    # Try subclass first (more specific)
    if cf_subclass and cf_subclass in CF_SUBCLASS_TO_CATEGORY:
        return CF_SUBCLASS_TO_CATEGORY[cf_subclass]
    # Then class
    if cf_class and cf_class in CF_CLASS_TO_CATEGORY:
        return CF_CLASS_TO_CATEGORY[cf_class]
    # Fallback to rule-based
    sys.path.insert(0, str(BASE_DIR))
    from lib.classify import classify_chemical
    return classify_chemical(name_clean or "", smiles or "")


def load_enriched():
    rows = []
    with open(ENRICHED_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"Loaded {len(rows)} rows from solvents_enriched.csv")
    return rows


def build_chemicals_csv(rows):
    """Map enriched columns to chemicals.csv schema and write."""
    out_rows = []
    classyfire_updates = {}

    for row in rows:
        name = row.get("name_clean") or row.get("Name") or ""
        cas = row.get("cas_final") or row.get("CAS") or ""
        smiles = row.get("smiles_canonical") or ""
        mol_formula = row.get("mol_formula") or ""
        dd = row.get("dD") or ""
        dp = row.get("dP") or ""
        dh = row.get("dH") or ""
        mw = row.get("mw") or ""
        bp = row.get("bp_c") or ""
        density = row.get("density_g_ml") or ""
        molar_vol = ""  # not in our output
        ghs = row.get("ghs_hazard_statements") or ""
        conf_score = row.get("confidence_score") or "0.85"
        source_url = row.get("url_primary") or ""
        cf_class = row.get("cf_class") or ""
        cf_subclass = row.get("cf_subclass") or ""

        # Map to category
        category = cf_to_category(cf_class or None, cf_subclass or None, name, smiles)

        # Use confidence_score from pipeline if available, else default
        try:
            conf = float(conf_score) if conf_score else 0.85
        except ValueError:
            conf = 0.85

        out_row = {
            "name": name,
            "cas_number": cas,
            "smiles": smiles,
            "molecular_formula": mol_formula,
            "delta_d": dd,
            "delta_p": dp,
            "delta_h": dh,
            "molecular_weight": mw,
            "boiling_point": bp,
            "density": density,
            "molar_volume": molar_vol,
            "category": category,
            "ghs_hazard": ghs,
            "confidence": f"{conf:.3f}",
            "source_count": "1",
            "source": "hspip_solvents",
            "source_url": source_url,
            "hidden": "",
        }
        out_rows.append(out_row)

        # Build ClassyFire cache entry keyed by CAS
        if cas and (cf_class or cf_subclass):
            classyfire_updates[cas] = {
                "class": cf_class,
                "subclass": cf_subclass,
                "kingdom": row.get("cf_kingdom") or "",
                "superclass": row.get("cf_superclass") or "",
                "direct_parent": row.get("cf_direct_parent") or "",
            }

    print(f"Built {len(out_rows)} rows for chemicals.csv")
    print(f"ClassyFire cache updates: {len(classyfire_updates)} entries")
    return out_rows, classyfire_updates


def write_chemicals_csv(rows):
    fields = ["name", "cas_number", "smiles", "molecular_formula",
              "delta_d", "delta_p", "delta_h", "molecular_weight",
              "boiling_point", "density", "molar_volume", "category",
              "ghs_hazard", "confidence", "source_count", "source",
              "source_url", "hidden"]
    with open(DATASET_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Written: {DATASET_CSV}")


def update_classyfire_cache(updates):
    existing = {}
    if CF_CACHE.exists():
        with open(CF_CACHE) as f:
            existing = json.load(f)
    before = len(existing)
    existing.update(updates)
    with open(CF_CACHE, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"ClassyFire cache: {before} → {len(existing)} entries ({len(updates)} added/updated)")


def update_manifest(n_chemicals):
    with open(MANIFEST) as f:
        manifest = json.load(f)

    ds = manifest["datasets"]["hspip_solvents"]
    ds["fields_available"] = [
        "name", "cas_number", "smiles", "molecular_formula",
        "delta_d", "delta_p", "delta_h", "molecular_weight",
        "boiling_point", "density", "category", "ghs_hazard",
        "confidence", "source_count", "source", "source_url",
    ]
    ds["chemical_count"] = n_chemicals
    ds["quality_notes"] = (
        "Enriched: CAS resolved, SMILES from PubChem, physical properties from NIST, "
        "GHS hazard statements from PubChem, ClassyFire classification."
    )
    ds["confidence_tier"] = 0.9

    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest updated: hspip_solvents now has {n_chemicals} chemicals, confidence_tier=0.9")


def run(cmd):
    print(f"\n$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=str(BASE_DIR))
    if result.returncode != 0:
        print(f"  WARNING: exit code {result.returncode}")
    return result.returncode


def main():
    if not ENRICHED_CSV.exists():
        print(f"ERROR: {ENRICHED_CSV} not found. Run solvent_pipeline.py first.")
        sys.exit(1)

    rows = load_enriched()
    chemicals, cf_updates = build_chemicals_csv(rows)

    # Coverage report
    n = len(chemicals)
    has_smiles = sum(1 for r in chemicals if r["smiles"])
    has_bp = sum(1 for r in chemicals if r["boiling_point"])
    has_ghs = sum(1 for r in chemicals if r["ghs_hazard"])
    has_cas = sum(1 for r in chemicals if r["cas_number"])
    has_cf = sum(1 for r in chemicals if r.get("category") not in ("other", ""))
    print(f"\nCoverage ({n} rows):")
    print(f"  CAS:    {has_cas}/{n} ({has_cas/n*100:.0f}%)")
    print(f"  SMILES: {has_smiles}/{n} ({has_smiles/n*100:.0f}%)")
    print(f"  bp_c:   {has_bp}/{n} ({has_bp/n*100:.0f}%)")
    print(f"  GHS:    {has_ghs}/{n} ({has_ghs/n*100:.0f}%)")
    print(f"  Category (non-other): {has_cf}/{n} ({has_cf/n*100:.0f}%)")

    write_chemicals_csv(chemicals)
    update_classyfire_cache(cf_updates)
    update_manifest(n)

    # Rebuild unified + regenerate HTML
    run("python3 build_unified.py")
    run("python3 generate_html.py")

    print("\nIntegration complete.")
    print("  → data/datasets/hspip_solvents/chemicals.csv updated")
    print("  → data/classyfire_cache.json updated")
    print("  → data/processed/unified_chemicals.csv rebuilt")
    print("  → materialism.html and database.html regenerated")


if __name__ == "__main__":
    main()
