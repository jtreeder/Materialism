#!/usr/bin/env python3
"""
process_polymers_2.py — Full HSP polymer data processing pipeline
Generates data/HSP_polymers_2.csv from HSPiP_polymers.csv
"""

import os
import re
import time
import json
import requests
import pandas as pd
from pathlib import Path

# ─── Constants ────────────────────────────────────────────────────────────────

RAW_CSV_URL = (
    "https://raw.githubusercontent.com/jtreeder/Materialism/"
    "claude/hansen-solubility-planning-D5iok/data/datasets/"
    "hspip_polymers/raw/HSPiP_polymers.csv"
)
LOCAL_RAW = Path(__file__).parent / "datasets/hspip_polymers/raw/HSPiP_polymers.csv"
OUTPUT_PATH = Path(__file__).parent / "HSP_polymers_2.csv"
CHECKPOINT_DIR = Path(__file__).parent / "pipeline" / "checkpoints_polymers2"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# Out-of-scope terms
OUT_OF_SCOPE = [
    "BLOOD SERUM", "UREA", "SUCROSE", "PSORIASIS SCALES",
    "CHOLESTEROL", "LARD", "PALM OIL", "CARBON-60", "CHLOROPHYLL",
]

# Brand prefix → class
BRAND_CLASS_MAP = {
    "DESMOPHEN":  "Polyurethane",
    "DESMOLAC":   "Polyurethane",
    "DESMODUR":   "Polyurethane",
    "EPIKOTE":    "Epoxy Resin",
    "EPON":       "Epoxy Resin",
    "ARALDITE":   "Epoxy Resin",
    "VERSAMID":   "Polyamide",
    "CYMEL":      "Amino Resin",
    "PHENODUR":   "Amino Resin",
    "ALKYDAL":    "Polyester & Alkyd",
    "ALFTALAT":   "Polyester & Alkyd",
    "DYNAPOL":    "Polyester & Alkyd",
    "BUTVAR":     "Vinyl Polymer",
    "MOWITAL":    "Vinyl Polymer",
    "ELVAX":      "Vinyl Polymer",
    "PARALOID":   "Acrylic",
    "ACRYLOID":   "Acrylic",
    "MACRYNAL":   "Acrylic",
    "LUMIFLON":   "Fluoropolymer",
    "STYRON":     "Styrenic",
    "VITON":      "Elastomer",
    "HYCAR":      "Elastomer",
    "CELLIT":     "Cellulosic Polymer",
    "ETHOCEL":    "Cellulosic Polymer",
    "CELLIDORA":  "Cellulosic Polymer",
    "PICCOPALE":  "Natural & Petroleum Resin",
    "PICCORONE":  "Natural & Petroleum Resin",
    "PENTALYN":   "Natural & Petroleum Resin",
}

# Brand capitalization rules (prefix → display form)
BRAND_CAPS = {
    "DESMOPHEN": "Desmophen", "DESMODUR": "Desmodur", "DESMOLAC": "Desmolac",
    "EPIKOTE": "EPIKOTE", "EPON": "EPON",
    "ARALDITE": "Araldite",
    "VERSAMID": "Versamid",
    "CYMEL": "Cymel", "PHENODUR": "Phenodur",
    "ALKYDAL": "Alkydal", "ALFTALAT": "Alftalat",
    "DYNAPOL": "DYNAPOL",
    "BUTVAR": "Butvar", "MOWITAL": "Mowital",
    "ELVAX": "ELVAX",
    "PARALOID": "Paraloid", "ACRYLOID": "Acryloid", "MACRYNAL": "Macrynal",
    "LUMIFLON": "Lumiflon",
    "STYRON": "Styron",
    "VITON": "Viton", "HYCAR": "Hycar",
    "CELLIT": "Cellit", "ETHOCEL": "Ethocel", "CELLIDORA": "Cellidora",
    "PICCOPALE": "Piccopale", "PICCORONE": "Piccorone", "PENTALYN": "Pentalyn",
}

# Acronym seed table
ACRONYM_TABLE = {
    "PMMA": "Poly(methyl methacrylate)",
    "PVC": "Poly(vinyl chloride)",
    "PS": "Polystyrene",
    "EP": "Epoxy resin",
    "PU": "Polyurethane",
    "NBR": "Nitrile rubber",
    "SBR": "Styrene-butadiene rubber",
    "PET": "Poly(ethylene terephthalate)",
    "PBT": "Poly(butylene terephthalate)",
    "PVDF": "Poly(vinylidene fluoride)",
    "PTFE": "Polytetrafluoroethylene",
    "PE": "Polyethylene",
    "PP": "Polypropylene",
    "PIB": "Polyisobutylene",
    "HDPE": "High-density polyethylene",
    "LDPE": "Low-density polyethylene",
    "SAN": "Styrene-acrylonitrile",
    "ABS": "Acrylonitrile butadiene styrene",
    "HPMC": "Hydroxypropyl methylcellulose",
    "PVP": "Polyvinylpyrrolidone",
    "EVA": "Ethylene-vinyl acetate",
    "CR": "Chloroprene rubber",
    "IIR": "Butyl rubber",
    "BR": "Butadiene rubber",
    "EPDM": "Ethylene propylene diene monomer",
}

VALID_CLASSES = {
    "Vinyl Polymer", "Acrylic", "Elastomer", "Polyester & Alkyd",
    "Styrenic", "Epoxy Resin", "Natural & Petroleum Resin", "Polyurethane",
    "Biological & Other", "Cellulosic Polymer", "Polyolefin", "Fluoropolymer",
    "Polyamide", "Amino Resin", "Polysulfone / PES / PPS",
    "Polyacetal / PEI / PC", "Phenolic Resin",
}


# ─── STEP 0: PRE-CLASSIFICATION ───────────────────────────────────────────────

def pre_classify(name: str) -> dict:
    """Route row to category and detect brand class."""
    name_upper = name.upper().strip()
    result = {
        "route": "standard",
        "class_predicted": None,
        "brand_prefix": None,
    }

    # Out-of-scope
    for term in OUT_OF_SCOPE:
        if term in name_upper:
            result["route"] = "flag_out_of_scope"
            result["class_predicted"] = "Biological & Other"
            return result

    # Resistance data
    if name_upper.startswith("R "):
        result["route"] = "resistance_data"
        return result

    # Concentration series
    if re.search(r'\d+%\s*$', name_upper):
        result["route"] = "concentration_series"

    # Time series
    if re.search(r'\b(\d+)\s*(MIN|HR|HOUR)', name_upper):
        result["route"] = "time_series"
        return result

    # Copolymer
    if re.match(r'^[A-Z]{1,6}/[A-Z]{1,6}', name_upper):
        result["route"] = "copolymer"
        return result

    # Brand prefix → trade_name
    for prefix, cls in BRAND_CLASS_MAP.items():
        if name_upper.startswith(prefix):
            result["route"] = "trade_name"
            result["class_predicted"] = cls
            result["brand_prefix"] = prefix
            return result

    return result


def hsp_anomaly_flags(row) -> list:
    """Return list of anomaly flag strings."""
    flags = []
    try:
        dd = float(row["dD"]) if pd.notna(row.get("dD")) else None
        dp = float(row["dP"]) if pd.notna(row.get("dP")) else None
        dh = float(row["dH"]) if pd.notna(row.get("dH")) else None
        r  = float(row["radius"]) if pd.notna(row.get("radius")) else None
        if dp is not None and dp < 0:
            flags.append("hsp_flag_dp_negative")
        if dh is not None and dh < 0:
            flags.append("hsp_flag_dh_negative")
        if dd is not None and dd < 10:
            flags.append("hsp_flag_dd_low")
        if dd is not None and dd > 28:
            flags.append("hsp_flag_dd_high")
        if r is not None and r > 30:
            flags.append("hsp_flag_r_large")
    except Exception:
        pass
    return flags


# ─── STEP 1: LOAD AND AUDIT ───────────────────────────────────────────────────

def load_and_audit(csv_path: str) -> pd.DataFrame:
    """Load CSV, audit, and return cleaned DataFrame."""
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

    # Rename columns
    rename_map = {}
    col_map = {c.lower(): c for c in df.columns}
    for old, new in [
        ("material", "name"), ("d", "dD"), ("p", "dP"),
        ("h", "dH"), ("ro", "radius"),
    ]:
        if old in col_map:
            rename_map[col_map[old]] = new
    df = df.rename(columns=rename_map)

    # Drop index column if present
    if "No" in df.columns or "no" in df.columns:
        df = df.drop(columns=[c for c in df.columns if c.lower() == "no"], errors="ignore")

    # Add missing audit columns if they don't exist
    for col in ["cas", "hsp_fit_confidence", "type", "conf"]:
        if col not in df.columns:
            df[col] = None

    # Rename conf → hsp_fit_confidence if present
    if "conf" in df.columns and "hsp_fit_confidence" not in df.columns:
        df = df.rename(columns={"conf": "hsp_fit_confidence"})

    # Strip whitespace from name
    df["name"] = df["name"].astype(str).str.strip()

    # Report missing
    missing_cas = df["cas"].isna().sum() + (df["cas"] == "").sum()
    blank_names = (df["name"] == "").sum() + (df["name"] == "nan").sum()
    print(f"Missing CAS: {missing_cas} / {len(df)}")
    print(f"Blank names: {blank_names}")

    # Flag full duplicates
    dup_mask = df.duplicated(subset=["name", "dD", "dP", "dH"], keep="first")
    print(f"Full duplicates: {dup_mask.sum()}")
    df["is_duplicate"] = dup_mask
    df = df[~dup_mask].copy()
    print(f"After dedup: {len(df)} rows")

    # Flag near-duplicates (same name, different HSP)
    name_counts = df.groupby("name").size()
    near_dup_names = name_counts[name_counts > 1].index
    df["is_near_duplicate"] = df["name"].isin(near_dup_names)
    print(f"Near-duplicates (same name, diff HSP): {df['is_near_duplicate'].sum()}")

    # CAS: restore float format to dashed string
    def fix_cas(cas_val):
        if pd.isna(cas_val):
            return None
        cas_str = str(cas_val).strip()
        if cas_str.lower() in ("not found", "none", "nan", ""):
            return None
        # Already dashed?
        if re.match(r'^\d+-\d+-\d+$', cas_str):
            return cas_str
        # Float like 9002123.0 → strip .0
        cas_str = re.sub(r'\.0+$', '', cas_str)
        return cas_str or None

    df["cas"] = df["cas"].apply(fix_cas)

    return df


# ─── STEP 3: NAME CLEANING ────────────────────────────────────────────────────

def clean_name(name: str, pre_class_info: dict) -> dict:
    """Clean name, extract synonyms, acronyms."""
    original = name
    name_clean = name.strip()

    # Normalize spaces
    name_clean = re.sub(r'\s+', ' ', name_clean)

    # Detect source uncertainty
    source_uncertainty = False
    if '?' in name_clean or '(QUESTIONABLE VALUES)' in name_clean.upper():
        source_uncertainty = True
        name_clean = re.sub(r'\?', '', name_clean)
        name_clean = re.sub(r'\(QUESTIONABLE VALUES\)', '', name_clean, flags=re.IGNORECASE)
        name_clean = name_clean.strip()

    # Also strip +/- OK / NOT OK (resistance data suffixes)
    name_clean = re.sub(r'\s*\+/-\s*(OK|NOT OK)\s*$', '', name_clean, flags=re.IGNORECASE).strip()

    # Extract parenthetical synonyms
    name_synonyms = []
    paren_match = re.search(r'\(([^)]+)\)', name_clean)
    if paren_match:
        inner = paren_match.group(1)
        # Is it a synonym or just a grade indicator?
        if re.match(r'^[A-Z]', inner) and not re.match(r'^\d', inner):
            name_synonyms.append(inner)
            # Remove from main name
            name_clean = re.sub(r'\s*\([^)]+\)\s*', ' ', name_clean).strip()

    # Apply brand capitalization
    brand_prefix = pre_class_info.get("brand_prefix")
    if brand_prefix and brand_prefix in BRAND_CAPS:
        display_prefix = BRAND_CAPS[brand_prefix]
        # Replace the all-caps prefix with proper form
        suffix = name_clean[len(brand_prefix):].strip()
        name_clean = f"{display_prefix} {suffix}".strip()

    # Detect name type
    name_upper = original.upper().strip()
    name_type = "trivial_polymer"
    if pre_class_info.get("route") == "trade_name":
        name_type = "trade_name"
    elif re.match(r'^[A-Z]{2,8}$', name_upper):
        name_type = "abbreviation"
    elif re.match(r'^poly', name_upper.lower()):
        name_type = "systematic_chemical"
    elif re.match(r'^[A-Z]{1,6}/[A-Z]{1,6}', name_upper):
        name_type = "copolymer"

    # Acronym collection
    name_acronyms = []
    # Check if the whole name is an acronym
    upper_name = original.strip().upper()
    if upper_name in ACRONYM_TABLE:
        name_acronyms.append(upper_name)

    # Check for brand → acronym
    brand_acronym_map = {
        "DESMOPHEN": "PU", "DESMODUR": "PU", "DESMOLAC": "PU",
        "EPIKOTE": "EP", "EPON": "EP", "ARALDITE": "EP",
    }
    if brand_prefix and brand_prefix in brand_acronym_map:
        name_acronyms.append(brand_acronym_map[brand_prefix])

    # Determine common name and iupac name
    name_common = name_clean
    name_iupac = None
    if name_type == "systematic_chemical":
        name_iupac = name_clean
    elif upper_name in ACRONYM_TABLE:
        name_iupac = ACRONYM_TABLE[upper_name]
        name_common = name_clean

    return {
        "name_clean": name_clean,
        "name_synonyms": "; ".join(name_synonyms) if name_synonyms else None,
        "name_acronyms": "; ".join(name_acronyms) if name_acronyms else None,
        "name_type": name_type,
        "name_common": name_common,
        "name_iupac": name_iupac,
        "source_uncertainty": source_uncertainty,
    }


# ─── STEP 4: CAS RESOLUTION ───────────────────────────────────────────────────

_cas_cache = {}

def search_pubchem_cas(name: str) -> str | None:
    """Search PubChem for CAS by name."""
    if name in _cas_cache:
        return _cas_cache[name]

    # PubChem compound search
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name)}/JSON"
    try:
        resp = requests.get(url, timeout=10)
        time.sleep(0.5)
        if resp.status_code == 200:
            data = resp.json()
            cids = []
            for c in data.get("PC_Compounds", []):
                cids.append(c.get("id", {}).get("id", {}).get("cid"))
            if cids:
                # Get CAS from synonyms
                cid = cids[0]
                syn_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
                syn_resp = requests.get(syn_url, timeout=10)
                time.sleep(0.5)
                if syn_resp.status_code == 200:
                    syn_data = syn_resp.json()
                    for syn_info in syn_data.get("InformationList", {}).get("Information", []):
                        for syn in syn_info.get("Synonym", []):
                            if re.match(r'^\d{2,7}-\d{2}-\d$', syn):
                                _cas_cache[name] = syn
                                return syn
    except Exception as e:
        pass

    _cas_cache[name] = None
    return None


def search_cas_common_chemistry(name: str) -> str | None:
    """Search CAS Common Chemistry API."""
    url = f"https://commonchemistry.cas.org/api/search?q={requests.utils.quote(name)}"
    try:
        resp = requests.get(url, timeout=10)
        time.sleep(0.5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results[0].get("rn")  # CAS registry number
    except Exception:
        pass
    return None


def lookup_cas(name_clean: str, route: str) -> tuple[str | None, str]:
    """Try to find CAS for a polymer. Returns (cas, note)."""
    # Skip for out-of-scope
    if route == "flag_out_of_scope":
        return None, "CAS lookup skipped: out of scope"

    # Try PubChem
    cas = search_pubchem_cas(name_clean)
    if cas:
        return cas, f"CAS found via PubChem: {cas}"

    # Try CAS Common Chemistry
    cas = search_cas_common_chemistry(name_clean)
    if cas:
        return cas, f"CAS found via CAS Common Chemistry: {cas}"

    return None, "CAS not found after 2 lookups"


# ─── STEP 9: CLASSIFICATION VIA CLAUDE ───────────────────────────────────────

def classify_with_claude(rows: list[dict]) -> list[dict]:
    """Classify polymers using Claude claude-haiku-4-5. Returns list with class, subclass."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("WARNING: ANTHROPIC_API_KEY not set, skipping AI classification")
        return [{"class": r.get("class_predicted") or "Biological & Other",
                 "subclass": None, "confidence": 0.0,
                 "notes": "ANTHROPIC_API_KEY not set"} for r in rows]

    client = anthropic.Anthropic(api_key=api_key)
    results = []

    for row in rows:
        # If brand prefix gave unambiguous class, use it
        if row.get("class_predicted") and row.get("brand_prefix"):
            results.append({
                "class": row["class_predicted"],
                "subclass": None,
                "confidence": 0.95,
                "notes": f"Class from brand prefix: {row['brand_prefix']}",
            })
            time.sleep(0.05)  # small delay even for cached results
            continue

        # Out-of-scope
        if row.get("route") == "flag_out_of_scope":
            results.append({
                "class": "Biological & Other",
                "subclass": None,
                "confidence": 1.0,
                "notes": "Out-of-scope entry",
            })
            continue

        prompt = f"""Classify this polymer for the Materialism HSP database.
name_clean: {row.get('name_clean', '')}
chemical_name_resolved: {row.get('name_iupac') or 'Unknown'}
class_predicted (from Step 0): {row.get('class_predicted') or 'Unknown'}

Valid class values (use one exactly):
Vinyl Polymer | Acrylic | Elastomer | Polyester & Alkyd | Styrenic | Epoxy Resin | Natural & Petroleum Resin | Polyurethane | Biological & Other | Cellulosic Polymer | Polyolefin | Fluoropolymer | Polyamide | Amino Resin | Polysulfone / PES / PPS | Polyacetal / PEI / PC | Phenolic Resin

Respond only with JSON: {{"class": "...", "subclass": "...", "class_level1": "...", "confidence": 0.0-1.0, "notes": "..."}}"""

        try:
            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text.strip()
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                cls = data.get("class", "Biological & Other")
                # Validate
                if cls not in VALID_CLASSES:
                    cls = "Biological & Other"
                results.append({
                    "class": cls,
                    "subclass": data.get("subclass"),
                    "confidence": data.get("confidence", 0.0),
                    "notes": data.get("notes", ""),
                })
            else:
                results.append({
                    "class": row.get("class_predicted") or "Biological & Other",
                    "subclass": None,
                    "confidence": 0.0,
                    "notes": f"Could not parse API response: {text[:100]}",
                })
        except Exception as e:
            results.append({
                "class": row.get("class_predicted") or "Biological & Other",
                "subclass": None,
                "confidence": 0.0,
                "notes": f"API error: {str(e)[:100]}",
            })

        time.sleep(1.0)

    return results


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

def run_pipeline():
    print("=" * 60)
    print("HSP Polymer Processing Pipeline v2")
    print("=" * 60)

    # ── Download / use local CSV ──────────────────────────────────
    csv_path = LOCAL_RAW
    if csv_path.exists():
        print(f"Using local file: {csv_path}")
    else:
        print(f"Downloading from: {RAW_CSV_URL}")
        resp = requests.get(RAW_CSV_URL, timeout=30)
        resp.raise_for_status()
        csv_path = CHECKPOINT_DIR / "raw_download.csv"
        csv_path.write_bytes(resp.content)
        print(f"Saved to: {csv_path}")

    # ── STEP 1: Load and audit ────────────────────────────────────
    print("\n--- STEP 1: Load and Audit ---")
    df = load_and_audit(str(csv_path))
    total_input = len(df)

    # ── STEP 0: Pre-classify ──────────────────────────────────────
    print("\n--- STEP 0: Pre-Classification ---")
    pre_class_results = df["name"].apply(pre_classify)
    df["route"]           = pre_class_results.apply(lambda x: x["route"])
    df["class_predicted"] = pre_class_results.apply(lambda x: x["class_predicted"])
    df["brand_prefix"]    = pre_class_results.apply(lambda x: x["brand_prefix"])

    route_counts = df["route"].value_counts()
    print("Route distribution:")
    for route, count in route_counts.items():
        print(f"  {route}: {count}")

    # ── STEP 2: HSP Anomaly flags ─────────────────────────────────
    print("\n--- STEP 2: HSP Plausibility Flags ---")
    df["hsp_flags"] = df.apply(hsp_anomaly_flags, axis=1)
    total_flagged = df["hsp_flags"].apply(lambda x: len(x) > 0).sum()
    print(f"Rows with HSP anomalies: {total_flagged}")

    # ── STEP 3: Name Cleaning ─────────────────────────────────────
    print("\n--- STEP 3: Name Cleaning ---")
    name_info_list = []
    for _, row in df.iterrows():
        pre_info = {
            "route": row["route"],
            "class_predicted": row["class_predicted"],
            "brand_prefix": row["brand_prefix"],
        }
        name_info = clean_name(row["name"], pre_info)
        name_info_list.append(name_info)

    name_df = pd.DataFrame(name_info_list)
    df = pd.concat([df.reset_index(drop=True), name_df.reset_index(drop=True)], axis=1)

    # ── STEP 4: CAS Resolution ────────────────────────────────────
    print("\n--- STEP 4: CAS Resolution ---")
    cas_checkpoint = CHECKPOINT_DIR / "cas_results.json"

    # Load existing CAS cache if available
    if cas_checkpoint.exists():
        with open(cas_checkpoint) as f:
            cas_cache_data = json.load(f)
        print(f"Loaded {len(cas_cache_data)} CAS results from checkpoint")
    else:
        cas_cache_data = {}

    cas_results = []
    cas_notes = []

    for i, (_, row) in enumerate(df.iterrows()):
        name_clean = row.get("name_clean", row["name"])
        route = row["route"]

        # Check cache
        cache_key = f"{name_clean}_{route}"
        if cache_key in cas_cache_data:
            cas_val, note = cas_cache_data[cache_key]
        else:
            cas_val, note = lookup_cas(name_clean, route)
            cas_cache_data[cache_key] = [cas_val, note]

            # Save checkpoint every 20 lookups
            if i % 20 == 0:
                with open(cas_checkpoint, "w") as f:
                    json.dump(cas_cache_data, f)
                print(f"  CAS progress: {i+1}/{len(df)} | Found: {sum(1 for v in cas_results if v)}")

        cas_results.append(cas_val)
        cas_notes.append(note)

    # Save final CAS cache
    with open(cas_checkpoint, "w") as f:
        json.dump(cas_cache_data, f)

    df["cas_resolved"] = cas_results
    df["cas_lookup_note"] = cas_notes

    # Use original CAS if available, otherwise use resolved
    def final_cas(row):
        if row.get("cas") and str(row["cas"]) not in ("None", "nan", ""):
            return row["cas"]
        return row.get("cas_resolved")

    df["cas_final"] = df.apply(final_cas, axis=1)
    cas_found = df["cas_final"].notna().sum()
    print(f"CAS numbers found: {cas_found} / {len(df)}")

    # ── STEP 9: Classification ────────────────────────────────────
    print("\n--- STEP 9: Classification (Claude claude-haiku-4-5) ---")
    class_checkpoint = CHECKPOINT_DIR / "class_results.json"

    if class_checkpoint.exists():
        with open(class_checkpoint) as f:
            class_cache = json.load(f)
        print(f"Loaded {len(class_cache)} classification results from checkpoint")
    else:
        class_cache = {}

    class_results = [None] * len(df)
    uncached_indices = []
    uncached_rows = []

    for i, (_, row) in enumerate(df.iterrows()):
        cache_key = row.get("name_clean", row["name"])
        if cache_key in class_cache:
            class_results[i] = class_cache[cache_key]
        else:
            uncached_indices.append(i)
            uncached_rows.append({
                "name_clean": row.get("name_clean", row["name"]),
                "name_iupac": row.get("name_iupac"),
                "class_predicted": row.get("class_predicted"),
                "brand_prefix": row.get("brand_prefix"),
                "route": row.get("route"),
            })

    print(f"Rows needing classification: {len(uncached_rows)}")

    # Process in chunks of 50
    CHUNK_SIZE = 50
    for chunk_start in range(0, len(uncached_rows), CHUNK_SIZE):
        chunk = uncached_rows[chunk_start:chunk_start + CHUNK_SIZE]
        chunk_indices = uncached_indices[chunk_start:chunk_start + CHUNK_SIZE]
        print(f"  Classifying chunk {chunk_start//CHUNK_SIZE + 1}: rows {chunk_start+1}-{chunk_start+len(chunk)}")

        chunk_results = classify_with_claude(chunk)

        for i, result in zip(chunk_indices, chunk_results):
            class_results[i] = result
            name_key = uncached_rows[uncached_indices.index(i)]["name_clean"]
            class_cache[name_key] = result

        # Save checkpoint
        with open(class_checkpoint, "w") as f:
            json.dump(class_cache, f)

    # Fill remaining None with defaults
    for i, r in enumerate(class_results):
        if r is None:
            class_results[i] = {
                "class": df.iloc[i].get("class_predicted") or "Biological & Other",
                "subclass": None,
                "confidence": 0.0,
                "notes": "Classification not attempted",
            }

    class_df = pd.DataFrame(class_results)
    df["class"] = class_df["class"].values
    df["subclass"] = class_df["subclass"].values
    df["class_confidence"] = class_df["confidence"].values
    df["class_notes"] = class_df["notes"].values

    class_dist = df["class"].value_counts()
    print("\nClass distribution:")
    for cls, count in class_dist.items():
        print(f"  {cls}: {count}")

    # ── Assemble processing_notes ─────────────────────────────────
    def build_notes(row):
        notes = []
        if row.get("is_near_duplicate"):
            notes.append("near_duplicate")
        if row.get("source_uncertainty"):
            notes.append("source_uncertainty")
        if row.get("hsp_flags"):
            notes.extend(row["hsp_flags"])
        notes.append(row.get("cas_lookup_note", ""))
        notes.append(row.get("class_notes", ""))
        return "; ".join(n for n in notes if n)

    df["processing_notes"] = df.apply(build_notes, axis=1)

    # ── Build final output ────────────────────────────────────────
    print("\n--- Assembling final output ---")

    def get_name_common(row):
        nc = row.get("name_common") or row.get("name_clean") or row["name"]
        return nc

    def get_name_iupac(row):
        ni = row.get("name_iupac")
        if ni:
            return ni
        # For abbreviations, look up
        upper = row["name"].strip().upper()
        if upper in ACRONYM_TABLE:
            return ACRONYM_TABLE[upper]
        return row.get("name_clean") or row["name"]

    output_df = pd.DataFrame({
        "name_iupac":        df.apply(get_name_iupac, axis=1),
        "name_common":       df.apply(get_name_common, axis=1),
        "name_acronyms":     df.get("name_acronyms", pd.Series([None]*len(df))),
        "cas":               df["cas_final"],
        "dD":                df["dD"],
        "dP":                df["dP"],
        "dH":                df["dH"],
        "radius":            df["radius"],
        "class":             df["class"],
        "subclass":          df["subclass"],
        "processing_notes":  df["processing_notes"],
    })

    # Save
    output_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(output_df)} rows to: {OUTPUT_PATH}")

    # ── Summary Report ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Total rows processed: {len(output_df)}")
    print(f"CAS numbers found: {output_df['cas'].notna().sum()}")
    print(f"\nClass distribution:")
    for cls, count in output_df["class"].value_counts().items():
        print(f"  {cls}: {count}")

    return output_df


if __name__ == "__main__":
    run_pipeline()
