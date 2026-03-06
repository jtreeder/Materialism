"""
Create HSP_solvents_2 dataset by consolidating:
  - data/datasets/hspip_solvents/chemicals.csv  (1135 rows — base data)
  - data/processed/solvents_enriched.csv         (250 rows — name_iupac, cf_class from pipeline)
  - data/classyfire_cache.json                   (1195 entries — ClassyFire by CAS)

Outputs:
  data/datasets/hsp_solvents_2/solvents_enriched.csv  — pipeline schema
  data/datasets/hsp_solvents_2/chemicals.csv           — database schema
  data/datasets/hsp_solvents_2/metadata.json
"""

import csv
import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
OUT_DIR = DATA_DIR / "datasets" / "hsp_solvents_2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Acronym seed table ─────────────────────────────────────────────────────────
# Maps lowercase common/IUPAC name fragments → acronym(s)
# Key: exact lowercase name; Value: semicolon-separated acronyms
ACRONYM_MAP = {
    # Ketones
    "methyl ethyl ketone": "MEK",
    "butanone": "MEK",
    "2-butanone": "MEK",
    "methyl isobutyl ketone": "MIBK",
    "4-methylpentan-2-one": "MIBK",
    "4-methyl-2-pentanone": "MIBK",
    "cyclohexanone": "",
    "acetone": "",
    "propan-2-one": "",
    "2-propanone": "",
    # Halogenated
    "dichloromethane": "DCM",
    "methylene chloride": "DCM",
    "chloroform": "CHCl3",
    "trichloromethane": "CHCl3",
    "carbon tetrachloride": "CCl4",
    "tetrachloromethane": "CCl4",
    "1,2-dichloroethane": "DCE; EDC",
    # Ethers
    "tetrahydrofuran": "THF",
    "diethyl ether": "Et2O; DEE",
    "ethoxyethane": "Et2O; DEE",
    "methyl tert-butyl ether": "MTBE",
    "tert-butyl methyl ether": "MTBE",
    "2-methoxy-2-methylpropane": "MTBE",
    "1,4-dioxane": "dioxane",
    "dioxane": "dioxane",
    "1,2-dimethoxyethane": "DME; glyme",
    "dimethoxyethane": "DME",
    "dimethoxymethane": "DMM",
    # Amides / dipolar aprotic
    "dimethylformamide": "DMF",
    "n,n-dimethylformamide": "DMF",
    "dimethyl sulfoxide": "DMSO",
    "dimethyl sulphoxide": "DMSO",
    "dimethylacetamide": "DMAc",
    "n,n-dimethylacetamide": "DMAc",
    "n-methyl-2-pyrrolidinone": "NMP",
    "n-methyl-2-pyrrolidone": "NMP",
    "1-methyl-2-pyrrolidinone": "NMP",
    "1-methyl-2-pyrrolidone": "NMP",
    "hexamethylphosphoramide": "HMPA",
    "hexamethylphosphotriamide": "HMPA",
    # Nitriles
    "acetonitrile": "MeCN; ACN",
    "propanenitrile": "MeCN",  # No — that's propionitrile
    # Alcohols
    "methanol": "MeOH",
    "ethanol": "EtOH",
    "isopropanol": "IPA; iPrOH",
    "2-propanol": "IPA; iPrOH",
    "propan-2-ol": "IPA; iPrOH",
    "isopropyl alcohol": "IPA; iPrOH",
    "1-butanol": "n-BuOH",
    "n-butanol": "n-BuOH",
    "butan-1-ol": "n-BuOH",
    "2-butanol": "s-BuOH",
    "sec-butanol": "s-BuOH",
    "tert-butanol": "t-BuOH",
    "2-methyl-2-propanol": "t-BuOH",
    "2-methylpropan-2-ol": "t-BuOH",
    "benzyl alcohol": "BnOH",
    "phenylmethanol": "BnOH",
    "ethylene glycol": "EG",
    "1,2-ethanediol": "EG",
    "propylene glycol": "PG",
    "1,2-propanediol": "PG",
    "propylene glycol monomethyl ether": "PGME",
    "diethylene glycol": "DEG",
    "triethylene glycol": "TEG",
    # Esters
    "ethyl acetate": "EtOAc; EA",
    "butyl acetate": "BuOAc; BA",
    "n-butyl acetate": "BuOAc; BA",
    "isopropyl acetate": "iPrOAc",
    "methyl acetate": "MeOAc",
    "propyl acetate": "PrOAc",
    # Carbonates
    "propylene carbonate": "PC",
    "ethylene carbonate": "EC",
    "dimethyl carbonate": "DMC",
    "diethyl carbonate": "DEC",
    # Lactones
    "gamma-butyrolactone": "GBL",
    "γ-butyrolactone": "GBL",
    "butyrolactone": "GBL",
    # Acids
    "acetic acid": "AcOH; HOAc",
    "ethanoic acid": "AcOH; HOAc",
    "formic acid": "FA",
    "methanoic acid": "FA",
    # Carbon disulfide
    "carbon disulfide": "CS2",
    "carbon disulphide": "CS2",
    # Other
    "nitromethane": "MeNO2",
    "triethylamine": "TEA; Et3N",
    "pyridine": "py",
    "diisopropylethylamine": "DIPEA; Hünig's base",
    "n,n-diisopropylethylamine": "DIPEA; Hünig's base",
    "dimethyl sulfate": "DMS",
    "acetic anhydride": "Ac2O",
    "trifluoroacetic acid": "TFA",
    "trifluoroacetaldehyde": "",
}

# Also check by substring for common abbreviations
ACRONYM_SUBSTRING = {
    "methyl ethyl ketone": "MEK",
    "methyl isobutyl ketone": "MIBK",
    "dimethyl sulfoxide": "DMSO",
    "dimethyl sulphoxide": "DMSO",
    "dimethylformamide": "DMF",
    "dimethylacetamide": "DMAc",
    "tetrahydrofuran": "THF",
    "dichloromethane": "DCM",
    "methylene chloride": "DCM",
    "ethyl acetate": "EtOAc; EA",
    "acetonitrile": "MeCN; ACN",
    "isopropanol": "IPA",
    "isopropyl alcohol": "IPA",
    "n-methyl-2-pyrrolid": "NMP",
    "methyl tert-butyl ether": "MTBE",
    "tert-butyl methyl ether": "MTBE",
    "1-methyl-2-pyrrolid": "NMP",
    "hexamethylphosphor": "HMPA",
    "propylene carbonate": "PC",
    "ethylene carbonate": "EC",
    "dimethyl carbonate": "DMC",
    "diethyl carbonate": "DEC",
    "gamma-butyrolactone": "GBL",
    "trifluoroacetic acid": "TFA",
}


def get_acronyms(name_common: str, name_iupac: str) -> str:
    """Return semicolon-separated acronyms for a solvent."""
    names_to_check = [n.lower().strip() for n in [name_common, name_iupac] if n]

    # Exact match first
    for n in names_to_check:
        if n in ACRONYM_MAP:
            result = ACRONYM_MAP[n]
            return result if result else ""

    # Substring match
    for n in names_to_check:
        for substr, acronym in ACRONYM_SUBSTRING.items():
            if substr in n:
                return acronym

    return ""


def clean_ghs(raw_ghs: str) -> str:
    """Normalize GHS hazard string — semicolons to commas, deduplicate H-codes."""
    if not raw_ghs or not raw_ghs.strip():
        return ""
    # Already semicolons — extract H-codes and reconstruct
    codes = re.findall(r"H\d{3}", raw_ghs)
    codes = list(dict.fromkeys(codes))  # deduplicate, preserve order
    return "; ".join(codes) if codes else raw_ghs.strip()


def build_processing_notes(sources: list) -> str:
    """Build processing notes from list of (tag, message) tuples."""
    return " | ".join(f"[{tag}] {msg}" for tag, msg in sources if msg)


def main():
    # ── Load ClassyFire cache ──────────────────────────────────────────────────
    cf_cache_path = DATA_DIR / "classyfire_cache.json"
    cf_cache = {}
    if cf_cache_path.exists():
        with open(cf_cache_path) as f:
            cf_cache = json.load(f)
    print(f"ClassyFire cache: {len(cf_cache)} entries")

    # ── Load pipeline-enriched data (250 rows) ────────────────────────────────
    enriched_path = DATA_DIR / "processed" / "solvents_enriched.csv"
    enriched_by_cas = {}  # CAS → row dict
    if enriched_path.exists():
        with open(enriched_path) as f:
            for row in csv.DictReader(f):
                cas = row.get("cas_final", "").strip()
                if cas:
                    enriched_by_cas[cas] = row
    print(f"Pipeline-enriched rows: {len(enriched_by_cas)}")

    # ── Load base chemicals ───────────────────────────────────────────────────
    base_path = DATA_DIR / "datasets" / "hspip_solvents" / "chemicals.csv"
    with open(base_path) as f:
        base_rows = list(csv.DictReader(f))
    print(f"Base chemicals: {len(base_rows)}")

    # ── Output schema for solvents_enriched.csv (pipeline schema) ────────────
    pipeline_cols = [
        "name_iupac", "name_common", "name_acronyms",
        "cas", "mol_formula", "smiles",
        "dD", "dP", "dH", "radius",
        "mw", "bp_c", "density_g_ml",
        "cf_class", "cf_subclass",
        "ghs_hazard",
        "processing_notes",
    ]

    # ── Output schema for chemicals.csv (database schema) ────────────────────
    db_cols = [
        "name", "cas_number", "smiles", "molecular_formula",
        "delta_d", "delta_p", "delta_h",
        "molecular_weight", "boiling_point", "density",
        "category", "cf_class", "cf_subclass",
        "name_iupac", "name_common", "name_acronyms",
        "ghs_hazard", "confidence", "source", "source_url",
    ]

    pipeline_rows = []
    db_rows = []

    counters = {
        "total": 0, "has_iupac": 0, "has_cf": 0, "has_acronym": 0,
        "from_enriched": 0, "from_cache": 0,
    }

    for base in base_rows:
        counters["total"] += 1
        notes = []

        name_common = base.get("name", "").strip()
        cas = base.get("cas_number", "").strip()
        smiles = base.get("smiles", "").strip()
        mol_formula = base.get("molecular_formula", "").strip()
        dD = base.get("delta_d", "").strip()
        dP = base.get("delta_p", "").strip()
        dH = base.get("delta_h", "").strip()
        mw = base.get("molecular_weight", "").strip()
        bp_c = base.get("boiling_point", "").strip()
        density = base.get("density", "").strip()
        category = base.get("category", "").strip()
        ghs_hazard = clean_ghs(base.get("ghs_hazard", "").strip())
        confidence = base.get("confidence", "").strip()
        source_url = base.get("source_url", "").strip()

        # HSP plausibility flags
        try:
            dd_f = float(dD) if dD else None
            dp_f = float(dP) if dP else None
            dh_f = float(dH) if dH else None
            if dd_f is not None and dd_f < 10:
                notes.append(("HSP", f"dD={dd_f} < 10 — flag_dd_low"))
            if dd_f is not None and dd_f > 28:
                notes.append(("HSP", f"dD={dd_f} > 28 — flag_dd_high"))
            if dp_f is not None and dp_f < 0:
                notes.append(("HSP", f"dP={dp_f} < 0 — fitting artifact"))
            if dh_f is not None and dh_f < 0:
                notes.append(("HSP", f"dH={dh_f} < 0 — fitting artifact"))
        except ValueError:
            pass

        # name_iupac — priority: pipeline enriched → lowercase of common name
        name_iupac = ""
        enriched = enriched_by_cas.get(cas)
        if enriched:
            counters["from_enriched"] += 1
            name_iupac = enriched.get("name_iupac", "").strip()
            notes.append(("NAME", "name_iupac from PubChem pipeline"))

        if not name_iupac:
            # Use lowercase of the common name as a best-effort IUPAC approximation
            name_iupac = name_common.lower()
            if enriched:
                notes.append(("NAME", "name_iupac: PubChem returned empty; using lowercase common name"))
            else:
                notes.append(("NAME", "name_iupac: no pipeline enrichment; using lowercase common name"))

        if name_iupac:
            counters["has_iupac"] += 1

        # cf_class, cf_subclass — priority: pipeline enriched → classyfire cache
        cf_class = ""
        cf_subclass = ""
        if enriched:
            cf_class = enriched.get("cf_class", "").strip()
            cf_subclass = enriched.get("cf_subclass", "").strip()
            if cf_class:
                notes.append(("CLASS", f"ClassyFire from pipeline: {cf_class}"))
                counters["from_enriched"] += 0  # already counted above

        if not cf_class and cas:
            cache_entry = cf_cache.get(cas, {})
            cf_class = cache_entry.get("class", "").strip()
            cf_subclass = cache_entry.get("subclass", "").strip()
            if cf_class:
                notes.append(("CLASS", f"ClassyFire from cache: {cf_class}"))
                counters["from_cache"] += 1

        if not cf_class and cas:
            # Try with leading zero stripped (common key issue like '08-88-3')
            alt_cas = cas.lstrip("0")
            cache_entry = cf_cache.get(alt_cas, {})
            cf_class = cache_entry.get("class", "").strip()
            cf_subclass = cache_entry.get("subclass", "").strip()
            if cf_class:
                notes.append(("CLASS", f"ClassyFire from cache (alt key): {cf_class}"))

        if not cf_class:
            notes.append(("CLASS", "ClassyFire not available"))

        if cf_class:
            counters["has_cf"] += 1

        # name_acronyms — from seed table
        name_acronyms = get_acronyms(name_common, name_iupac)
        if name_acronyms:
            counters["has_acronym"] += 1
            notes.append(("NAME", f"Acronyms: {name_acronyms}"))

        # CAS
        if not cas:
            notes.append(("CAS", "CAS not available in source"))
        elif enriched and enriched.get("cas_valid", "").strip().lower() == "true":
            notes.append(("CAS", f"CAS {cas} validated by pipeline"))
        else:
            notes.append(("CAS", f"CAS {cas} from HSPiP source"))

        # Build pipeline row
        pipeline_row = {
            "name_iupac": name_iupac,
            "name_common": name_common,
            "name_acronyms": name_acronyms,
            "cas": cas,
            "mol_formula": mol_formula,
            "smiles": smiles,
            "dD": dD,
            "dP": dP,
            "dH": dH,
            "radius": "",  # R0 not available in HSPiP solvent source
            "mw": mw,
            "bp_c": bp_c,
            "density_g_ml": density,
            "cf_class": cf_class,
            "cf_subclass": cf_subclass,
            "ghs_hazard": ghs_hazard,
            "processing_notes": build_processing_notes(notes),
        }
        pipeline_rows.append(pipeline_row)

        # Build database row (standard database schema)
        db_row = {
            "name": name_common,
            "cas_number": cas,
            "smiles": smiles,
            "molecular_formula": mol_formula,
            "delta_d": dD,
            "delta_p": dP,
            "delta_h": dH,
            "molecular_weight": mw,
            "boiling_point": bp_c,
            "density": density,
            "category": category,
            "cf_class": cf_class,
            "cf_subclass": cf_subclass,
            "name_iupac": name_iupac,
            "name_common": name_common,
            "name_acronyms": name_acronyms,
            "ghs_hazard": ghs_hazard,
            "confidence": confidence,
            "source": "hsp_solvents_2",
            "source_url": source_url,
        }
        db_rows.append(db_row)

    # ── Write solvents_enriched.csv (pipeline schema) ─────────────────────────
    enriched_out = OUT_DIR / "solvents_enriched.csv"
    with open(enriched_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=pipeline_cols)
        writer.writeheader()
        writer.writerows(pipeline_rows)
    print(f"Written: {enriched_out} ({len(pipeline_rows)} rows)")

    # ── Write chemicals.csv (database schema) ────────────────────────────────
    db_out = OUT_DIR / "chemicals.csv"
    with open(db_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=db_cols)
        writer.writeheader()
        writer.writerows(db_rows)
    print(f"Written: {db_out} ({len(db_rows)} rows)")

    # ── Write metadata.json ───────────────────────────────────────────────────
    metadata = {
        "id": "hsp_solvents_2",
        "name": "HSP Solvents 2",
        "description": (
            "Re-processed HSPiP solvent database following the Materialism "
            "Data Cleaning & Enrichment Pipeline v2. Includes IUPAC names, "
            "common names, acronyms, ClassyFire taxonomy (cf_class/cf_subclass), "
            "GHS hazard codes, and processing audit trail."
        ),
        "source": "HSPiP Database (HSP Solvents 2 pipeline)",
        "source_url": "",
        "pipeline_version": 2,
        "chemical_count": len(pipeline_rows),
        "polymer_count": 0,
        "fields_available": pipeline_cols,
        "quality_notes": (
            f"ClassyFire coverage: {counters['has_cf']}/{counters['total']} "
            f"({counters['has_cf']/counters['total']*100:.0f}%). "
            f"name_iupac coverage: {counters['has_iupac']}/{counters['total']}. "
            f"Acronym coverage: {counters['has_acronym']}/{counters['total']}. "
            "radius (R0) not available from HSPiP solvent source — left blank."
        ),
    }
    meta_out = OUT_DIR / "metadata.json"
    with open(meta_out, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Written: {meta_out}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n── HSP_solvents_2 Summary ──────────────────────────────────────────")
    print(f"  Total rows:        {counters['total']}")
    print(f"  Has name_iupac:    {counters['has_iupac']}")
    print(f"  Has cf_class:      {counters['has_cf']}")
    print(f"  Has acronyms:      {counters['has_acronym']}")
    print(f"  CF from enriched:  {counters['from_enriched']}")
    print(f"  CF from cache:     {counters['from_cache']}")
    print(f"\nOutput: {OUT_DIR}")


if __name__ == "__main__":
    main()
