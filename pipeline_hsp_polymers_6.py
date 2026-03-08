#!/usr/bin/env python3
"""
Materialism HSP Database — Pipeline A: Solvent Enrichment (hsp_polymers_6)
===========================================================================
Processes Hansen Solubility Parameters Table A.1 solvents from the PDF source:
  data/raw/a1 and a2 only.pdf  (extracted into hansen_a1 dataset)

Following the Materialism Data Cleaning & Enrichment Pipeline specification.
This pipeline applies all Steps 0A–9 for solvents.

Output: data/datasets/hsp_polymers_6/chemicals.csv

Usage:
    python3 pipeline_hsp_polymers_6.py            # full run
    python3 pipeline_hsp_polymers_6.py --sample 50  # first 50 rows
    python3 pipeline_hsp_polymers_6.py --resume     # continue from checkpoint
"""

import sys
import os
import csv
import json
import re
import time
import math
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

import requests

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent
DATA_DIR = REPO_ROOT / "data"
DATASETS_DIR = DATA_DIR / "datasets"
PIPELINE_DIR = DATA_DIR / "pipeline"
CACHE_DIR = PIPELINE_DIR / "cache"
CHECKPOINT_DIR = PIPELINE_DIR / "checkpoints"
LOG_DIR = DATA_DIR / "logs"

SOURCE_CSV = DATASETS_DIR / "hansen_a1" / "chemicals.csv"
SOURCE_PDF = DATA_DIR / "raw" / "a1 and a2 only.pdf"
REF_SOLVENTS_CSV = DATASETS_DIR / "hsp_solvents_2" / "chemicals.csv"

DATASET_ID = "hsp_polymers_6"
OUTPUT_DIR = DATASETS_DIR / DATASET_ID
OUTPUT_CSV = OUTPUT_DIR / "chemicals.csv"
CHECKPOINT_FILE = CHECKPOINT_DIR / f"{DATASET_ID}_checkpoint.json"
CACHE_FILE = CACHE_DIR / "api_cache_polymers6.json"
CLASSYFIRE_CACHE = DATA_DIR / "classyfire_cache.json"

CHUNK_SIZE = 50

for d in [OUTPUT_DIR, CACHE_DIR, CHECKPOINT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"pipeline_{DATASET_ID}_{timestamp}.log"),
    ],
)
log = logging.getLogger(__name__)

# ─── API Cache ────────────────────────────────────────────────────────────────
_api_cache: dict = {}

def load_api_cache():
    global _api_cache
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            _api_cache = json.load(f)
        log.info(f"Loaded {len(_api_cache)} cached API responses.")

def save_api_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(_api_cache, f)

def _ckey(*args) -> str:
    return hashlib.md5("|".join(str(a) for a in args).encode()).hexdigest()

def cached_get(url: str, params=None, label="") -> dict | None:
    key = _ckey(url, json.dumps(params or {}, sort_keys=True))
    if key in _api_cache:
        return _api_cache[key]
    try:
        time.sleep(0.3)
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 429:
            log.warning(f"Rate limited on {label}. Sleeping 12s.")
            time.sleep(12)
            r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                data = {"_text": r.text}
            _api_cache[key] = data
            return data
        elif r.status_code == 404:
            _api_cache[key] = None
            return None
        else:
            log.warning(f"HTTP {r.status_code} for {label}: {url}")
            return None
    except Exception as e:
        log.warning(f"Request error for {label}: {e}")
        return None

# ─── ClassyFire Cache ──────────────────────────────────────────────────────────
_cf_cache: dict = {}

def load_cf_cache():
    global _cf_cache
    if CLASSYFIRE_CACHE.exists():
        with open(CLASSYFIRE_CACHE) as f:
            _cf_cache = json.load(f)
        log.info(f"Loaded {len(_cf_cache)} ClassyFire cache entries.")

def save_cf_cache():
    with open(CLASSYFIRE_CACHE, "w") as f:
        json.dump(_cf_cache, f, indent=2)

# ─── Step 0A: Load Source Data ─────────────────────────────────────────────────
def load_source_data() -> list[dict]:
    """Load Hansen A.1 solvents from the pre-extracted CSV.
    This data was extracted from data/raw/a1 and a2 only.pdf (Table A.1).
    """
    rows = []
    with open(SOURCE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    log.info(f"Loaded {len(rows)} solvents from {SOURCE_CSV}")
    return rows

# ─── Step 0B: Load Reference Enrichment Data ──────────────────────────────────
def load_reference_data() -> dict:
    """Load hsp_solvents_2 as enrichment reference. Keyed by lowercase name."""
    ref = {}
    if REF_SOLVENTS_CSV.exists():
        with open(REF_SOLVENTS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row.get("name", "").strip().lower()
                if key:
                    ref[key] = dict(row)
        log.info(f"Loaded {len(ref)} reference solvents from hsp_solvents_2.")
    return ref

# ─── Step 1: Name Cleaning ─────────────────────────────────────────────────────
def clean_name(raw_name: str) -> str:
    """Step 3: Clean the input name for display.
    - Title case
    - Collapse whitespace
    - Strip asterisk uncertainty markers
    - Strip trailing/leading whitespace
    """
    name = raw_name.strip()
    # Strip asterisk (uncertainty marker)
    asterisk_present = "*" in name
    name = name.replace("*", "").strip()
    # Collapse multiple spaces
    name = re.sub(r"\s{2,}", " ", name)
    # Convert all-caps abbreviations / words to title case where appropriate
    # But preserve known abbreviations (N-, N,N-, etc.)
    # If name is ALL CAPS, apply title case
    if name == name.upper() and len(name) > 4 and not re.match(r"^[A-Z]{1,6}$", name):
        name = name.title()
    elif name == name.lower() and len(name) > 1:
        name = name.capitalize()
    # Fix prefix capitalisation
    name = re.sub(r"\bN,n-", "N,N-", name)
    name = re.sub(r"\bN-([A-Z])", r"N-\1", name)
    return name

# ─── HSP Plausibility Flags ────────────────────────────────────────────────────
def hsp_flags(dd, dp, dh) -> list[str]:
    flags = []
    try:
        dd_f = float(dd)
        if dd_f < 10: flags.append("[HSP] dD_low (<10)")
        if dd_f > 28: flags.append("[HSP] dD_high (>28)")
    except (ValueError, TypeError):
        pass
    try:
        dp_f = float(dp)
        if dp_f < 0: flags.append("[HSP] dP_negative (fitting artifact)")
    except (ValueError, TypeError):
        pass
    try:
        dh_f = float(dh)
        if dh_f < 0: flags.append("[HSP] dH_negative (fitting artifact)")
    except (ValueError, TypeError):
        pass
    return flags

# ─── PubChem Lookups ───────────────────────────────────────────────────────────
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

def pubchem_cid_by_name(name: str) -> int | None:
    url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(name)}/cids/JSON"
    data = cached_get(url, label=f"PubChem CID by name: {name}")
    if data and "IdentifierList" in data:
        cids = data["IdentifierList"].get("CID", [])
        if cids:
            return cids[0]
    return None

def pubchem_cid_by_cas(cas: str) -> int | None:
    if not cas:
        return None
    url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(cas)}/cids/JSON"
    data = cached_get(url, label=f"PubChem CID by CAS: {cas}")
    if data and "IdentifierList" in data:
        cids = data["IdentifierList"].get("CID", [])
        if cids:
            return cids[0]
    return None

def pubchem_properties(cid: int) -> dict:
    props = ["CanonicalSMILES", "MolecularFormula", "MolecularWeight",
             "IUPACName", "XLogP"]
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{','.join(props)}/JSON"
    data = cached_get(url, label=f"PubChem props CID {cid}")
    if data and "PropertyTable" in data:
        table = data["PropertyTable"].get("Properties", [{}])
        if table:
            return table[0]
    return {}

def pubchem_synonyms(cid: int) -> list[str]:
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
    data = cached_get(url, label=f"PubChem synonyms CID {cid}")
    if data and "InformationList" in data:
        info = data["InformationList"].get("Information", [{}])
        if info:
            return info[0].get("Synonym", [])
    return []

def extract_cas_from_synonyms(synonyms: list[str]) -> str | None:
    cas_pat = re.compile(r"^\d{1,7}-\d{2}-\d$")
    for s in synonyms:
        s = s.strip()
        if cas_pat.match(s):
            return s
    return None

def filter_common_names(synonyms: list[str], iupac: str = "") -> list[str]:
    """Filter synonym list for common/trivial names only."""
    skip_patterns = [
        r"^\d+\.\d",         # starts with number (registry)
        r"^[A-Z]{14}",       # InChI key
        r"^InChI=",          # InChI string
        r"^[A-Z0-9@\[\]\\/:#+\-]{20,}",  # SMILES-like
        r"^\d{3}-\d{2}-\d$", # CAS
        r"^\d{3}-\d{3}-\d",  # EC number
        r"EINECS|ELINCS|EC \d",
        r"MFCD\d{8}",
        r"NSC-?\d",
        r"HSDB \d",
        r"AIDS-\d",
        r"UN\d{4}",
        r"WLN:",
        r"UNII-",
        r"ACMC-",
        r"D0\d{5}",
    ]
    common = []
    iupac_lower = iupac.lower().strip()
    for s in synonyms:
        s = s.strip()
        if not s:
            continue
        if s.lower() == iupac_lower:
            continue
        skip = False
        for pat in skip_patterns:
            if re.search(pat, s, re.IGNORECASE):
                skip = True
                break
        if skip:
            continue
        common.append(s)
    return common

def pubchem_ghs(cid: int) -> str:
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    data = cached_get(url, params={"heading": "GHS Classification"}, label=f"PubChem GHS CID {cid}")
    if not data:
        return ""
    # Navigate to GHS section
    try:
        record = data.get("Record", {})
        sections = record.get("Section", [])
        for sec in sections:
            if "Safety" in sec.get("TOCHeading", "") or "Hazard" in sec.get("TOCHeading", ""):
                for sub in sec.get("Section", []):
                    if "GHS" in sub.get("TOCHeading", ""):
                        h_codes = []
                        signal = ""
                        for subsub in sub.get("Section", []):
                            head = subsub.get("TOCHeading", "")
                            for info in subsub.get("Information", []):
                                for val in info.get("Value", {}).get("StringWithMarkup", []):
                                    text = val.get("String", "")
                                    if re.match(r"H\d{3}", text):
                                        if text not in h_codes:
                                            h_codes.append(text)
                                    if text in ("Warning", "Danger"):
                                        signal = text
                        if h_codes or signal:
                            parts = []
                            if signal:
                                parts.append(signal)
                            parts.extend(sorted(set(h_codes)))
                            return "; ".join(parts)
    except Exception as e:
        log.debug(f"GHS parse error for CID {cid}: {e}")
    return ""

def pubchem_boiling_point(cid: int) -> str:
    """Get boiling point from PubChem experimental properties."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    data = cached_get(url, params={"heading": "Boiling+Point"}, label=f"PubChem BP CID {cid}")
    if not data:
        return ""
    try:
        record = data.get("Record", {})
        for sec in record.get("Section", []):
            for sub in sec.get("Section", []):
                if "Boiling" in sub.get("TOCHeading", ""):
                    for subsub in sub.get("Section", []) + [sub]:
                        for info in subsub.get("Information", []):
                            for val in info.get("Value", {}).get("StringWithMarkup", []):
                                text = val.get("String", "")
                                # Extract temperature in °C
                                m = re.search(r"(-?\d+\.?\d*)\s*°?C", text)
                                if m:
                                    return m.group(1)
                                # Also try Kelvin
                                m = re.search(r"(-?\d+\.?\d*)\s*K\b", text)
                                if m:
                                    try:
                                        k = float(m.group(1))
                                        return str(round(k - 273.15, 1))
                                    except Exception:
                                        pass
    except Exception:
        pass
    return ""

def pubchem_density(cid: int) -> str:
    """Get density from PubChem experimental properties."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    data = cached_get(url, params={"heading": "Density"}, label=f"PubChem density CID {cid}")
    if not data:
        return ""
    try:
        record = data.get("Record", {})
        for sec in record.get("Section", []):
            for sub in sec.get("Section", []):
                if "Density" in sub.get("TOCHeading", ""):
                    for subsub in sub.get("Section", []) + [sub]:
                        for info in subsub.get("Information", []):
                            for val in info.get("Value", {}).get("StringWithMarkup", []):
                                text = val.get("String", "")
                                m = re.search(r"(\d+\.?\d*)\s*g/[cm][Ll3]", text)
                                if m:
                                    return m.group(1)
    except Exception:
        pass
    return ""

# ─── ClassyFire ────────────────────────────────────────────────────────────────
def classyfire_lookup(smiles: str, cas: str = "") -> tuple[str, str]:
    """Look up ClassyFire class and subclass for a given SMILES or CAS."""
    if not smiles and not cas:
        return "", ""

    # Check ClassyFire cache by CAS first
    if cas and cas in _cf_cache:
        entry = _cf_cache[cas]
        return entry.get("class", ""), entry.get("subclass", "") or ""

    # Check by SMILES key
    smiles_key = smiles.strip()
    if smiles_key and smiles_key in _cf_cache:
        entry = _cf_cache[smiles_key]
        return entry.get("class", ""), entry.get("subclass", "") or ""

    # Skip if no SMILES
    if not smiles_key:
        return "", ""

    # Submit to ClassyFire
    try:
        time.sleep(0.5)
        submit_url = "http://classyfire.wishartlab.com/queries.json"
        payload = {
            "label": cas or smiles_key[:20],
            "query_input": smiles_key,
            "query_type": "STRUCTURE"
        }
        r = requests.post(submit_url, json=payload, timeout=20)
        if r.status_code in (200, 201):
            qdata = r.json()
            query_id = qdata.get("id")
            if query_id:
                # Poll for result
                for attempt in range(5):
                    time.sleep(3 * (attempt + 1))
                    result_url = f"http://classyfire.wishartlab.com/queries/{query_id}.json"
                    rr = requests.get(result_url, timeout=20)
                    if rr.status_code == 200:
                        rdata = rr.json()
                        entities = rdata.get("entities", [])
                        if entities:
                            entity = entities[0]
                            cf_class = entity.get("class", {}).get("name", "") if entity.get("class") else ""
                            cf_subclass = entity.get("subclass", {}).get("name", "") if entity.get("subclass") else ""
                            # Cache result
                            cache_key_val = cas if cas else smiles_key
                            _cf_cache[cache_key_val] = {
                                "class": cf_class,
                                "subclass": cf_subclass,
                                "smiles": smiles_key
                            }
                            save_cf_cache()
                            return cf_class, cf_subclass
    except Exception as e:
        log.debug(f"ClassyFire error for {cas or smiles_key[:20]}: {e}")

    return "", ""

# ─── Chemical Category Classification ─────────────────────────────────────────
def classify_chemical_category(name: str, smiles: str = "", cf_class: str = "") -> str:
    """Assign a broad category string matching CATEGORY_COLORS in generate_html.py."""
    # Use ClassyFire class if available
    cf = cf_class.lower()
    if cf:
        if "alcohol" in cf or "ol" in cf: return "alcohol"
        if "ketone" in cf: return "ketone"
        if "ester" in cf or "lactone" in cf: return "ester"
        if "ether" in cf: return "ether"
        if "halogen" in cf or "chlor" in cf or "fluor" in cf or "brom" in cf or "iod" in cf:
            return "halogenated"
        if "aromatic" in cf or "benzene" in cf or "phenyl" in cf: return "aromatic"
        if "amine" in cf or "amino" in cf: return "amine"
        if "acid" in cf or "carboxylic" in cf: return "acid"
        if "nitrile" in cf or "cyanide" in cf: return "nitrile"
        if "amide" in cf: return "amide"
        if "sulfoxide" in cf or "sulfone" in cf: return "sulfoxide"
        if "nitro" in cf: return "nitro"
        if "terpene" in cf: return "terpene"

    # Fallback: name-based classification
    n = name.lower()
    if re.search(r"\bwater\b|\bH2O\b", n): return "inorganic"
    if re.search(r"alcohol|ethanol|methanol|propanol|butanol|ol\b", n): return "alcohol"
    if re.search(r"acetone|ketone|propanone|butanone|cyclohexanone", n): return "ketone"
    if re.search(r"acetate|formate|ester|acrylate|propionate|butyrate", n): return "ester"
    if re.search(r"ether|furan|dioxane|dioxolane|oxolane|tetrahydro", n): return "ether"
    if re.search(r"chloro|dichloro|trichloro|bromo|fluoro|iodo", n): return "halogenated"
    if re.search(r"benzene|toluene|xylene|phenyl|naphthal|styrene|cumene", n): return "aromatic"
    if re.search(r"amine|amino|diamine|triamine|morpholine|piperidine|pyrrolidine", n): return "amine"
    if re.search(r"acid|acetic|formic|propionic|butyric|lactic|citric", n): return "acid"
    if re.search(r"nitrile|acetonitrile|acrylonitrile", n): return "nitrile"
    if re.search(r"amide|dimethylformamide|dimethylacetamide|caprolactam", n): return "amide"
    if re.search(r"dimethyl sulfoxide|sulfolane|sulfone|sulfoxide", n): return "sulfoxide"
    if re.search(r"glycol ether|methoxy|ethoxy|propoxy|butoxy.*ether", n): return "glycol ether"
    if re.search(r"glycol|diol|triol", n): return "glycol"
    if re.search(r"nitro|nitrotoluene|nitrobenzene", n): return "nitro"
    if re.search(r"terpene|limonene|pinene|terpineol", n): return "terpene"
    if re.search(r"pyrrolidone|lactam|lactone|cyclic", n): return "heterocyclic"
    if re.search(r"formate|aldehyde|acetaldehyde", n): return "aldehyde"
    if re.search(r"disulfide|mercaptan|thiol|thio", n): return "sulfur compound"
    return "other"

# ─── Checkpoint System ─────────────────────────────────────────────────────────
def load_checkpoint() -> int:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            cp = json.load(f)
        last = cp.get("last_completed_row", 0)
        log.info(f"Resuming from checkpoint: last completed row = {last}")
        return last
    return 0

def save_checkpoint(last_completed_row: int, total_rows: int):
    cp = {
        "last_completed_row": last_completed_row,
        "total_rows": total_rows,
        "output_file": str(OUTPUT_CSV),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(cp, f, indent=2)

# ─── Output Schema ─────────────────────────────────────────────────────────────
OUTPUT_FIELDS = [
    "name",              # name_clean (main display — used by generate_html.py)
    "name_input",        # frozen original
    "cas_number",        # CAS
    "smiles",
    "molecular_formula",
    "delta_d",           # dD from source
    "delta_p",           # dP from source
    "delta_h",           # dH from source
    "molar_volume",      # from source (Table A.1 has molar_volume not radius)
    "molecular_weight",  # from PubChem
    "boiling_point",     # from PubChem / NIST (°C)
    "density",           # from PubChem / NIST (g/mL)
    "category",          # broad category for CATEGORY_COLORS
    "cf_class",          # ClassyFire class
    "cf_subclass",       # ClassyFire subclass
    "name_iupac",
    "name_common",
    "name_common_all",   # semicolon-separated
    "name_acronyms",     # semicolon-separated
    "ghs_hazard",
    "confidence",
    "source_count",
    "source",
    "source_url",
    "processing_notes",
]

# ─── Main Processing ───────────────────────────────────────────────────────────
def process_solvent(raw: dict, ref_data: dict, row_num: int) -> dict:
    """Process a single solvent row through all enrichment steps."""
    notes = []

    # ── name_input ─────────────────────────────────────────────────────────────
    name_input = raw.get("name", "").strip()
    if not name_input:
        notes.append("[NAME] empty name_input")

    # Check for asterisk uncertainty marker
    if "*" in name_input:
        notes.append("[NAME] asterisk present in source (uncertainty marker)")

    # ── name_clean ─────────────────────────────────────────────────────────────
    name_clean = clean_name(name_input)

    # ── HSP values from source ─────────────────────────────────────────────────
    dd = raw.get("delta_d", "").strip()
    dp = raw.get("delta_p", "").strip()
    dh = raw.get("delta_h", "").strip()
    mv = raw.get("molar_volume", "").strip()

    for flag in hsp_flags(dd, dp, dh):
        notes.append(flag)

    # ── Source CAS ─────────────────────────────────────────────────────────────
    # Table A.1 has no CAS column — must be looked up
    source_cas = raw.get("cas_number", "").strip()
    if source_cas and source_cas.lower() not in ("", "nan", "not found"):
        notes.append(f"[CAS] source CAS: {source_cas}")
    else:
        source_cas = ""

    # ── Reference lookup (hsp_solvents_2) ─────────────────────────────────────
    ref_key = name_input.lower().strip()
    ref = ref_data.get(ref_key) or ref_data.get(name_clean.lower()) or {}

    ref_match = bool(ref)
    if ref_match:
        notes.append("[REF] matched hsp_solvents_2")

    # ── Initialise output fields from reference ────────────────────────────────
    cas = source_cas or ref.get("cas_number", "").strip()
    smiles = ref.get("smiles", "").strip()
    mol_formula = ref.get("molecular_formula", "").strip()
    mw = ref.get("molecular_weight", "").strip()
    bp = ref.get("boiling_point", "").strip()
    density = ref.get("density", "").strip()
    cf_class = ref.get("cf_class", "").strip()
    cf_subclass = ref.get("cf_subclass", "").strip()
    name_iupac = ref.get("name_iupac", "").strip()
    name_common = ref.get("name_common", "").strip()
    name_common_all = ""
    name_acronyms = ref.get("name_acronyms", "").strip()
    ghs = ref.get("ghs_hazard", "").strip()
    confidence = 0.85

    # ── PubChem lookup (if not from reference or missing CAS) ──────────────────
    cid = None
    if not ref_match or not cas or not smiles:
        # Try CAS first, then name
        if cas:
            cid = pubchem_cid_by_cas(cas)
        if not cid:
            cid = pubchem_cid_by_name(name_clean)
        if not cid and name_clean != name_input.strip():
            cid = pubchem_cid_by_name(name_input.strip())

        if cid:
            notes.append(f"[CAS] PubChem CID: {cid}")
            props = pubchem_properties(cid)
            synonyms = pubchem_synonyms(cid)

            # CAS from PubChem
            if not cas:
                cas_found = extract_cas_from_synonyms(synonyms)
                if cas_found:
                    cas = cas_found
                    notes.append(f"[CAS] found via PubChem: {cas}")
                else:
                    notes.append("[CAS] Not found in PubChem synonyms")

            # SMILES
            if not smiles:
                smiles = props.get("CanonicalSMILES", "")

            # Molecular formula
            if not mol_formula:
                mol_formula = props.get("MolecularFormula", "")

            # MW
            if not mw:
                mw = str(props.get("MolecularWeight", ""))

            # IUPAC name
            if not name_iupac:
                name_iupac = props.get("IUPACName", "")

            # Common names
            commons = filter_common_names(synonyms, name_iupac)
            if commons and not name_common:
                name_common = commons[0]
            if commons:
                name_common_all = "; ".join(commons[:10])

            # BP and density (from PubChem)
            if not bp:
                bp = pubchem_boiling_point(cid)
                if bp:
                    notes.append(f"[PROP] boiling point from PubChem: {bp}°C")

            if not density:
                density = pubchem_density(cid)
                if density:
                    notes.append(f"[PROP] density from PubChem: {density} g/mL")

            # GHS
            if not ghs:
                ghs = pubchem_ghs(cid)
                if ghs:
                    notes.append("[GHS] from PubChem")

            confidence = 0.9
        else:
            notes.append(f"[CAS] PubChem CID not found for: {name_clean}")
            confidence = 0.7

    # ── name_common_all (build from reference if not already set) ──────────────
    if not name_common_all and ref_match:
        parts = [p.strip() for p in [name_common, name_acronyms] if p.strip()]
        name_common_all = "; ".join(parts) if parts else ""

    # ── ClassyFire ─────────────────────────────────────────────────────────────
    if smiles and not cf_class:
        cf_class, cf_subclass = classyfire_lookup(smiles, cas)
        if cf_class:
            notes.append(f"[CLASS] ClassyFire: {cf_class}")
        else:
            notes.append("[CLASS] ClassyFire: not found")

    # ── Category ───────────────────────────────────────────────────────────────
    # Use existing category if from reference, otherwise classify
    category = ref.get("category", "").strip() if ref_match else ""
    if not category or category == "other":
        category = classify_chemical_category(name_clean, smiles, cf_class)

    # ── Source URL (PubChem) ───────────────────────────────────────────────────
    source_url = ""
    if cid:
        source_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
    elif ref_match:
        source_url = ref.get("source_url", "").strip()

    return {
        "name": name_clean,
        "name_input": name_input,
        "cas_number": cas,
        "smiles": smiles,
        "molecular_formula": mol_formula,
        "delta_d": dd,
        "delta_p": dp,
        "delta_h": dh,
        "molar_volume": mv,
        "molecular_weight": mw,
        "boiling_point": bp,
        "density": density,
        "category": category,
        "cf_class": cf_class,
        "cf_subclass": cf_subclass,
        "name_iupac": name_iupac,
        "name_common": name_common,
        "name_common_all": name_common_all,
        "name_acronyms": name_acronyms,
        "ghs_hazard": ghs,
        "confidence": confidence,
        "source_count": "1",
        "source": DATASET_ID,
        "source_url": source_url,
        "processing_notes": " | ".join(notes),
    }

# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="HSP Polymers 6 — Solvent Enrichment Pipeline")
    parser.add_argument("--sample", type=int, default=0, help="Process only first N rows")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--start", type=int, default=0, help="Start from row N (0-indexed)")
    parser.add_argument("--no-classyfire", action="store_true", help="Skip ClassyFire lookups")
    args = parser.parse_args()

    load_api_cache()
    load_cf_cache()

    # Load data
    log.info("=== Step 0A: Loading source data ===")
    raw_rows = load_source_data()
    ref_data = load_reference_data()

    if args.sample:
        raw_rows = raw_rows[:args.sample]
        log.info(f"Sample mode: processing {args.sample} rows.")

    total = len(raw_rows)

    # Determine start row
    start_row = args.start
    if args.resume and not args.start:
        start_row = load_checkpoint()

    # Write header if starting fresh
    if start_row == 0:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
        log.info(f"Created fresh output: {OUTPUT_CSV}")
    else:
        log.info(f"Appending to existing output from row {start_row}.")

    # Process in chunks
    processed = 0
    errors = 0
    ref_hits = 0
    pubchem_hits = 0

    for i, raw in enumerate(raw_rows):
        if i < start_row:
            continue

        row_num = i + 1
        name = raw.get("name", "").strip()

        try:
            result = process_solvent(raw, ref_data, row_num)
            if "matched hsp_solvents_2" in result.get("processing_notes", ""):
                ref_hits += 1
            if "PubChem CID:" in result.get("processing_notes", ""):
                pubchem_hits += 1

            # Append to output CSV
            with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
                writer.writerow(result)

            processed += 1

            if processed % 10 == 0:
                log.info(f"Progress: {row_num}/{total} ({row_num/total*100:.0f}%) — "
                         f"ref_hits={ref_hits}, pubchem_hits={pubchem_hits}")

        except Exception as e:
            log.error(f"Row {row_num} ({name}): {e}", exc_info=True)
            errors += 1
            # Write error row
            error_row = {f: raw.get(f, "") for f in OUTPUT_FIELDS}
            error_row["name"] = clean_name(name)
            error_row["name_input"] = name
            error_row["delta_d"] = raw.get("delta_d", "")
            error_row["delta_p"] = raw.get("delta_p", "")
            error_row["delta_h"] = raw.get("delta_h", "")
            error_row["molar_volume"] = raw.get("molar_volume", "")
            error_row["processing_notes"] = f"[ERROR] {e}"
            error_row["source"] = DATASET_ID
            with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
                writer.writerow(error_row)

        # Save checkpoint every CHUNK_SIZE rows
        if processed > 0 and processed % CHUNK_SIZE == 0:
            save_checkpoint(row_num, total)
            save_api_cache()
            log.info(f"Checkpoint saved at row {row_num}/{total}.")

    # Final save
    save_api_cache()
    save_cf_cache()
    save_checkpoint(total, total)

    log.info("=== Pipeline Complete ===")
    log.info(f"Total processed: {processed}")
    log.info(f"Errors: {errors}")
    log.info(f"Reference (hsp_solvents_2) hits: {ref_hits}")
    log.info(f"PubChem lookups: {pubchem_hits}")
    log.info(f"Output: {OUTPUT_CSV}")

    return processed, errors


if __name__ == "__main__":
    main()
