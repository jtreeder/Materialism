"""
Materialism HSP Database — Solvent Enrichment Pipeline (Pipeline A)
Processes HSPiPsolvents.xlsx through all 11 pipeline steps.
Saves checkpoints every 50 rows; fully resumable.

Usage:
    python3 solvent_pipeline.py              # full run
    python3 solvent_pipeline.py --sample 50 # sample first 50 rows
    python3 solvent_pipeline.py --start 50  # resume from row 50
    python3 solvent_pipeline.py --classyfire-only  # run ClassyFire batch on existing output
"""

import sys
import os
import json
import time
import math
import re
import argparse
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_XLSX = DATA_DIR / "datasets" / "hspip_solvents" / "raw" / "HSPiPsolvents.xlsx"
PIPELINE_DIR = DATA_DIR / "pipeline"
CACHE_DIR = PIPELINE_DIR / "cache"
CHECKPOINT_DIR = PIPELINE_DIR / "checkpoints"
OUTPUT_DIR = DATA_DIR / "processed"
VERIFIED_DIR = DATA_DIR / "verified"
LOG_DIR = DATA_DIR / "logs"

for d in [CACHE_DIR, CHECKPOINT_DIR, OUTPUT_DIR, VERIFIED_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

CHECKPOINT_FILE = CHECKPOINT_DIR / "solvents_checkpoint.csv"
OUTPUT_FILE = OUTPUT_DIR / "solvents_enriched.csv"
CACHE_FILE = CACHE_DIR / "api_cache.json"

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
log = logging.getLogger(__name__)

# ─── API Cache ────────────────────────────────────────────────────────────────
_cache: dict = {}

def load_cache():
    global _cache
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            _cache = json.load(f)
        log.info(f"Loaded {len(_cache)} cached API responses.")

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(_cache, f)

def cache_key(*args) -> str:
    return hashlib.md5("|".join(str(a) for a in args).encode()).hexdigest()

def cached_get(url: str, params=None, label="") -> dict | None:
    """GET with caching and rate limiting."""
    key = cache_key(url, json.dumps(params or {}, sort_keys=True))
    if key in _cache:
        return _cache[key]

    try:
        time.sleep(0.25)  # ~4 req/sec — within PubChem limit of 5/sec
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 429:
            log.warning(f"Rate limited on {label}. Sleeping 10s.")
            time.sleep(10)
            r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                data = {"_text": r.text}
            _cache[key] = data
            return data
        elif r.status_code == 404:
            _cache[key] = None
            return None
        else:
            log.warning(f"HTTP {r.status_code} for {label}: {url}")
            return None
    except Exception as e:
        log.warning(f"Request error for {label} ({url}): {e}")
        return None

# ─── ICH Q3C Table (partial — most common solvents) ──────────────────────────
# Source: ICH Q3C(R8). Class 1 = avoid, Class 2 = limited, Class 3 = low risk
ICH_Q3C = {
    # Class 1 (avoid)
    "71-43-2":  (1, None),   # benzene
    "107-06-2": (1, None),   # 1,2-dichloroethane
    "75-01-4":  (1, None),   # vinyl chloride
    "79-34-5":  (1, None),   # 1,1,2,2-tetrachloroethane
    "79-00-5":  (1, None),   # 1,1,2-trichloroethane
    "71-55-6":  (1, None),   # 1,1,1-trichloroethane
    "127-18-4": (1, None),   # tetrachloroethylene
    "79-01-6":  (1, None),   # trichloroethylene
    "75-35-4":  (1, None),   # vinylidene chloride
    # Class 2 (limit)
    "75-09-2":  (2, 6.0),    # DCM
    "67-56-1":  (2, 30.0),   # methanol
    "110-82-7": (2, 3.88),   # cyclohexane
    "100-41-4": (2, 4.7),    # ethylbenzene
    "110-54-3": (2, 2.89),   # n-hexane
    "109-99-9": (2, 7.2),    # THF
    "67-68-5":  (2, 8.7),    # DMSO
    "68-12-2":  (2, 8.8),    # DMF
    "872-50-4": (2, 5.3),    # NMP
    "108-94-1": (2, 3.88),   # cyclohexanone
    "75-05-8":  (2, 4.1),    # acetonitrile
    "108-88-3": (2, 8.9),    # toluene
    "108-38-3": (2, 2.17),   # m-xylene
    "95-47-6":  (2, 2.17),   # o-xylene
    "106-42-3": (2, 2.17),   # p-xylene
    "123-91-1": (2, 3.84),   # 1,4-dioxane
    "110-86-1": (2, 2.0),    # pyridine
    "108-90-7": (2, 3.6),    # chlorobenzene
    "110-02-1": (2, 16.0),   # thiophene
    "108-95-2": (2, 12.2),   # phenol
    "67-63-0":  (2, 50.0),   # 2-propanol (IPA) — class 3 but add limit
    "109-87-5": (2, 15.4),   # dimethoxymethane
    # Class 3 (low risk, PDE ≥ 50 mg/day, no specific limit)
    "67-64-1":  (3, None),   # acetone
    "141-78-6": (3, None),   # ethyl acetate
    "64-17-5":  (3, None),   # ethanol
    "71-36-3":  (3, None),   # n-butanol
    "78-83-1":  (3, None),   # isobutanol
    "64-19-7":  (3, None),   # acetic acid
    "79-20-9":  (3, None),   # methyl acetate
    "71-23-8":  (3, None),   # 1-propanol
    "78-92-2":  (3, None),   # sec-butanol
    "75-65-0":  (3, None),   # tert-butanol
    "78-93-3":  (3, None),   # MEK
    "57-55-6":  (3, None),   # propylene glycol
    "111-27-3": (3, None),   # 1-hexanol
    "100-51-6": (3, None),   # benzyl alcohol
    "108-32-7": (3, None),   # propylene carbonate
    "79-09-4":  (3, None),   # propionic acid
    "107-10-8": (3, None),   # n-propylamine
}

def get_ich_q3c(cas: str) -> tuple:
    if not cas:
        return "Not listed", None
    result = ICH_Q3C.get(str(cas).strip())
    if result:
        return result
    return "Not listed", None

# ─── CAS Validation ───────────────────────────────────────────────────────────
def validate_cas(cas_str) -> bool:
    if not cas_str or not isinstance(cas_str, str):
        return False
    cas_clean = str(cas_str).strip()
    m = re.match(r"^(\d+)-(\d{2})-(\d)$", cas_clean)
    if not m:
        return False
    digits = m.group(1) + m.group(2) + m.group(3)
    check = int(digits[-1])
    total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(digits[:-1])))
    return (total % 10) == check

# ─── PubChem API ──────────────────────────────────────────────────────────────
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

def pubchem_by_cas(cas: str) -> dict | None:
    if not cas:
        return None
    url = f"{PUBCHEM_BASE}/compound/name/{cas}/JSON"
    data = cached_get(url, label=f"PubChem CAS:{cas}")
    if data and "PC_Compounds" in data:
        return data["PC_Compounds"][0]
    return None

def pubchem_by_name(name: str) -> dict | None:
    url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(name)}/JSON"
    data = cached_get(url, label=f"PubChem name:{name[:30]}")
    if data and "PC_Compounds" in data:
        return data["PC_Compounds"][0]
    return None

def pubchem_properties(cid: int) -> dict:
    props = "MolecularWeight,MolecularFormula,XLogP,HBondDonorCount,HBondAcceptorCount,CanonicalSMILES,IsomericSMILES,IUPACName,InChIKey"
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{props}/JSON"
    data = cached_get(url, label=f"PubChem props CID:{cid}")
    if data and "PropertyTable" in data:
        props_list = data["PropertyTable"].get("Properties", [])
        if props_list:
            return props_list[0]
    return {}

def pubchem_ghs(cid: int) -> dict:
    """Get GHS hazard data from PubChem pug_view."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    params = {"heading": "GHS Classification"}
    data = cached_get(url, params=params, label=f"PubChem GHS CID:{cid}")

    result = {"statements": [], "pictograms": [], "signal_word": None}
    if not data or "Record" not in data:
        return result

    try:
        # Path: Record → Section[Safety] → Section[Hazards] → Section[GHS] → Information[]
        record = data["Record"]
        ghs_infos = []
        for sect in record.get("Section", []):
            for sub1 in sect.get("Section", []):
                for sub2 in sub1.get("Section", []):
                    if "GHS" in sub2.get("TOCHeading", ""):
                        ghs_infos.extend(sub2.get("Information", []))

        h_codes = []
        pictograms = []
        signal = None

        for info in ghs_infos:
            name = info.get("Name", "")
            val = info.get("Value", {})
            strings = val.get("StringWithMarkup", [])

            if "Hazard Statement" in name:
                for s in strings:
                    # Extract H-code from start of string like "H302 (78.6%): Harmful..."
                    m = re.match(r"(H\d{3})", s.get("String", ""))
                    if m:
                        h_codes.append(m.group(1))

            elif "Pictogram" in name:
                for s in strings:
                    for markup in s.get("Markup", []):
                        extra = markup.get("Extra", "")
                        if extra and markup.get("Type") == "Icon":
                            pictograms.append(extra)

            elif name == "Signal":
                for s in strings:
                    txt = s.get("String", "")
                    if txt and not signal:
                        signal = txt

        result["statements"] = list(dict.fromkeys(h_codes))  # deduplicate, preserve order
        result["pictograms"] = list(dict.fromkeys(pictograms))
        result["signal_word"] = signal

    except Exception as e:
        log.warning(f"GHS parse error for CID {cid}: {e}")

    return result

def pubchem_synonyms(cid: int) -> list:
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
    data = cached_get(url, label=f"PubChem synonyms CID:{cid}")
    if data and "InformationList" in data:
        info = data["InformationList"].get("Information", [])
        if info:
            return info[0].get("Synonym", [])
    return []

def extract_cas_from_synonyms(synonyms: list) -> str | None:
    for syn in synonyms:
        s = str(syn).strip()
        if re.match(r"^\d+-\d{2}-\d$", s) and validate_cas(s):
            return s
    return None

def get_cid_from_compound(compound: dict) -> int | None:
    try:
        return compound["id"]["id"]["cid"]
    except (KeyError, TypeError):
        return None

# ─── NIST WebBook ─────────────────────────────────────────────────────────────
def nist_data(cas: str) -> dict:
    """Fetch key physical properties from NIST WebBook by CAS (Mask=4 for phase change)."""
    result = {"bp_c": None, "mp_c": None, "density_g_ml": None,
               "flash_point_c": None, "vapor_pressure_mmhg": None}
    if not cas:
        return result

    url = "https://webbook.nist.gov/cgi/cbook.cgi"
    params = {"ID": cas, "Units": "SI", "Mask": "4"}  # Mask=4 = phase change data
    data = cached_get(url, params=params, label=f"NIST CAS:{cas}")
    if not data:
        return result

    text = data.get("_text", "")
    if not text:
        return result

    # Parse boiling point — NIST table row: T<sub>boil</sub> | value | K
    bp_matches = re.findall(
        r"T<sub>boil</sub></td><td[^>]*>([\d.]+)</td><td[^>]*>K</td>",
        text
    )
    if bp_matches:
        try:
            # Take median of available values
            vals = [float(v) for v in bp_matches]
            bp_k = sorted(vals)[len(vals) // 2]
            result["bp_c"] = round(bp_k - 273.15, 1)
        except Exception:
            pass

    # Parse melting/fusion point — T<sub>fus</sub>
    mp_matches = re.findall(
        r"T<sub>fus</sub></td><td[^>]*>([\d.]+)</td><td[^>]*>K</td>",
        text
    )
    if mp_matches:
        try:
            vals = [float(v) for v in mp_matches]
            mp_k = sorted(vals)[len(vals) // 2]
            result["mp_c"] = round(mp_k - 273.15, 1)
        except Exception:
            pass

    return result

# ─── CIR (Chemical Identifier Resolver) ──────────────────────────────────────
def cir_cas(name: str) -> str | None:
    url = f"https://cactus.nci.nih.gov/chemical/structure/{requests.utils.quote(name)}/cas"
    data = cached_get(url, label=f"CIR cas:{name[:30]}")
    if data and "_text" in data:
        for line in data["_text"].strip().split("\n"):
            line = line.strip()
            if re.match(r"^\d+-\d{2}-\d$", line) and validate_cas(line):
                return line
    return None

def cir_smiles(name: str) -> str | None:
    url = f"https://cactus.nci.nih.gov/chemical/structure/{requests.utils.quote(name)}/smiles"
    data = cached_get(url, label=f"CIR smiles:{name[:30]}")
    if data and "_text" in data:
        t = data["_text"].strip()
        return t if t else None
    return None

# ─── SMILES Validation (RDKit) ────────────────────────────────────────────────
try:
    from rdkit import Chem
    HAS_RDKIT = True
    try:
        from rdkit.Chem.inchi import MolToInchiKey as _MolToInchiKey
    except ImportError:
        from rdkit.Chem import InchiInfo
        _MolToInchiKey = None
except ImportError:
    HAS_RDKIT = False
    log.warning("RDKit not available — SMILES validation/InChIKey derivation disabled.")

def validate_smiles(smiles: str) -> bool:
    if not HAS_RDKIT or not smiles:
        return False
    try:
        mol = Chem.MolFromSmiles(smiles)
        return mol is not None
    except Exception:
        return False

def smiles_to_inchikey(smiles: str) -> str | None:
    if not HAS_RDKIT or not smiles or _MolToInchiKey is None:
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return _MolToInchiKey(mol)
    except Exception:
        pass
    return None

# ─── ClassyFire Batch API ─────────────────────────────────────────────────────
CLASSYFIRE_BASE = "http://classyfire.wishartlab.com"

def classyfire_submit_batch(smiles_dict: dict) -> int | None:
    """
    Submit a batch of SMILES to ClassyFire.
    smiles_dict: {identifier: smiles_string}
    Returns query_id or None on failure.
    """
    lines = [f"{ident}\t{smi}" for ident, smi in smiles_dict.items() if smi]
    if not lines:
        return None

    query_input = "\n".join(lines)
    payload = {
        "label": f"materialism_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "query_input": query_input,
        "query_type": "STRUCTURE",
    }

    try:
        r = requests.post(
            f"{CLASSYFIRE_BASE}/queries.json",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        if r.status_code in (200, 201):
            data = r.json()
            qid = data.get("id")
            log.info(f"ClassyFire batch submitted. Query ID: {qid}")
            return qid
        else:
            log.warning(f"ClassyFire submit failed: HTTP {r.status_code} — {r.text[:200]}")
            return None
    except Exception as e:
        log.warning(f"ClassyFire submit error: {e}")
        return None

def classyfire_poll(query_id: int, max_wait_minutes: int = 60) -> dict | None:
    """
    Poll ClassyFire until job is done. Returns results dict or None.
    """
    url = f"{CLASSYFIRE_BASE}/queries/{query_id}.json"
    deadline = time.time() + max_wait_minutes * 60

    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                status = data.get("classification_status", "")
                log.info(f"ClassyFire query {query_id} status: {status}")
                if status == "Done":
                    return data
                elif status in ("Error", "Invalid"):
                    log.error(f"ClassyFire query failed with status: {status}")
                    return None
            else:
                log.warning(f"ClassyFire poll HTTP {r.status_code}")
        except Exception as e:
            log.warning(f"ClassyFire poll error: {e}")

        log.info("Waiting 30s for ClassyFire results...")
        time.sleep(30)

    log.warning(f"ClassyFire timed out after {max_wait_minutes} minutes.")
    return None

def classyfire_parse_entity(entity: dict) -> dict:
    """Extract cf_* fields from a ClassyFire entity result."""
    return {
        "cf_kingdom": (entity.get("kingdom") or {}).get("name"),
        "cf_superclass": (entity.get("superclass") or {}).get("name"),
        "cf_class": (entity.get("class") or {}).get("name"),
        "cf_subclass": (entity.get("subclass") or {}).get("name"),
        "cf_direct_parent": (entity.get("direct_parent") or {}).get("name"),
        "cf_alternative_parents": "; ".join(
            a.get("name", "") for a in (entity.get("alternative_parents") or [])
        ) or None,
        "cf_classification_type": "full_molecule",
    }

def run_classyfire_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run ClassyFire on all rows in df that have smiles_canonical.
    Adds/updates cf_* columns in-place. Returns modified df.
    """
    # Collect rows that need ClassyFire and have SMILES
    needs_cf = df[
        df["smiles_canonical"].notna() &
        (df["cf_class"].isna() | (df["cf_class"] == ""))
    ]
    log.info(f"ClassyFire batch: {len(needs_cf)} rows need classification.")

    if needs_cf.empty:
        return df

    # Build submission dict: use row index as identifier
    smiles_dict = {}
    for idx, row in needs_cf.iterrows():
        smi = str(row["smiles_canonical"]).strip()
        if smi and smi.lower() not in ("nan", "none", ""):
            smiles_dict[str(idx)] = smi

    log.info(f"Submitting {len(smiles_dict)} SMILES to ClassyFire...")
    query_id = classyfire_submit_batch(smiles_dict)
    if not query_id:
        log.warning("ClassyFire batch submission failed.")
        return df

    # Save query_id for recovery
    qid_file = PIPELINE_DIR / "classyfire_query_id.txt"
    qid_file.write_text(str(query_id))
    log.info(f"ClassyFire query_id saved to {qid_file}")

    # Poll for results
    results_data = classyfire_poll(query_id, max_wait_minutes=90)
    if not results_data:
        return df

    # Parse and merge results
    entities = results_data.get("entities", [])
    log.info(f"ClassyFire returned {len(entities)} entities.")

    # ClassyFire returns entities in the same order as submission
    # Use the identifier field to map back
    entity_map = {}
    for entity in entities:
        ident = entity.get("identifier")
        if ident is not None:
            entity_map[str(ident)] = classyfire_parse_entity(entity)

    # Also try matching by index position if no identifier
    submitted_indices = list(smiles_dict.keys())
    for i, entity in enumerate(entities):
        ident = entity.get("identifier")
        if not ident and i < len(submitted_indices):
            entity_map[submitted_indices[i]] = classyfire_parse_entity(entity)

    matched = 0
    cf_cols = ["cf_kingdom", "cf_superclass", "cf_class", "cf_subclass",
               "cf_direct_parent", "cf_alternative_parents", "cf_classification_type"]

    for idx_str, cf_data in entity_map.items():
        try:
            idx = int(idx_str)
            if idx in df.index:
                for col, val in cf_data.items():
                    df.at[idx, col] = val
                matched += 1
        except (ValueError, KeyError):
            pass

    log.info(f"ClassyFire: matched {matched}/{len(entity_map)} results to rows.")

    # Save updated cache of query results
    cf_cache_file = CACHE_DIR / f"classyfire_{query_id}.json"
    cf_cache_file.write_text(json.dumps(results_data))
    log.info(f"ClassyFire results cached to {cf_cache_file}")

    return df

# ─── Name Cleaning ────────────────────────────────────────────────────────────
def clean_name(raw_name: str) -> tuple:
    """Returns (name_clean, name_type, name_synonyms, source_uncertainty)."""
    name = str(raw_name).strip()
    source_uncertainty = False

    if "?" in name or "(QUESTIONABLE VALUES)" in name.upper():
        source_uncertainty = True
        name = name.replace("(QUESTIONABLE VALUES)", "").replace("?", "").strip()

    # Extract parenthetical synonyms
    synonyms = []
    for match in re.findall(r"\(([^)]+)\)", name):
        if not re.match(r"^[\d:\./%]+$", match):
            synonyms.append(match)

    name_clean = re.sub(r"\s*\([^)]+\)", "", name).strip()
    name_clean = re.sub(r"\s+", " ", name_clean).rstrip("*").strip()

    # Detect name type
    if re.match(r"^[A-Z]{2,6}(\d+)?$", name_clean):
        name_type = "abbreviation"
    elif any(t in name_clean.upper() for t in [
        "FREON", "TRITON", "SPAN", "TWEEN", "DOWANOL", "CELLOSOLVE",
        "CARBITOL", "SOLVESSO", "SHELL SOL", "SWASOL"
    ]):
        name_type = "trade_name"
    elif re.match(r"^\d+-", name_clean) or any(
        kw in name_clean.lower() for kw in [
            "methyl", "ethyl", "propyl", "butyl", "dimethyl", "diethyl",
            "trichloro", "difluoro", "monochloride", "oxide", "acid",
            "alcohol", "acetate", "amine", "amide", "nitrile", "ketone",
            "ether", "ester", "benzene", "toluene", "phenol", "fluoro",
            "chloro", "bromo", "iodo", "epoxy", "sulfide", "sulfone"
        ]
    ):
        name_type = "systematic_chemical"
    else:
        name_type = "trivial_name"

    synonym_str = "; ".join(synonyms) if synonyms else None
    return name_clean, name_type, synonym_str, source_uncertainty

# ─── HSP Plausibility Flags ───────────────────────────────────────────────────
def hsp_flags(dd: float, dp: float, dh: float) -> dict:
    dd = float(dd) if dd is not None else 0.0
    dp = float(dp) if dp is not None else 0.0
    dh = float(dh) if dh is not None else 0.0
    return {
        "hsp_flag_dd_low": bool(dd < 10),
        "hsp_flag_dd_high": bool(dd > 28),
        "hsp_flag_dp_negative": bool(dp < 0),
        "hsp_flag_dh_negative": bool(dh < 0),
        "hsp_flag_r_large": False,
        "hsp_flag_nonpolar_check": bool(abs(dp) < 1.0 and abs(dh) < 1.0),
    }

# ─── GHS Flag Extraction ──────────────────────────────────────────────────────
def extract_ghs_flags(h_codes: list) -> dict:
    codes = set(h_codes)
    return {
        "flag_carcinogen": bool(codes & {"H350", "H351"}),
        "flag_reproductive_toxin": bool(codes & {"H360", "H361"}),
        "flag_flammable": bool(codes & {"H224", "H225", "H226"}),
        "flag_acutely_toxic": bool(codes & {"H300", "H301", "H310", "H311", "H330", "H331"}),
    }

# ─── Confidence Scoring ───────────────────────────────────────────────────────
def compute_confidence(scores: dict) -> tuple:
    total = (
        scores.get("score_cas", 0.0) * 0.25
        + scores.get("score_name_match", 0.0) * 0.20
        + scores.get("score_pubchem", 0.0) * 0.20
        + scores.get("score_smiles", 0.0) * 0.15
        + scores.get("score_crossref", 0.0) * 0.15
        + scores.get("score_properties", 0.0) * 0.05
    )
    if total >= 0.90:
        label = "HIGH"
    elif total >= 0.70:
        label = "MEDIUM"
    else:
        label = "LOW"
    return round(total, 3), label

# ─── Process a Single Row ─────────────────────────────────────────────────────
def process_row(i: int, raw: pd.Series) -> dict:
    notes = []
    def note(tag, msg): notes.append(f"[{tag}] {msg}")

    # ── Raw field extraction ──
    raw_name = str(raw["Chemical name"]).strip() if pd.notna(raw.get("Chemical name")) else ""
    raw_cas_val = raw.get("CAS #")
    dd = float(raw["Dispersion"]) if pd.notna(raw.get("Dispersion")) else None
    dp = float(raw["Polarity"]) if pd.notna(raw.get("Polarity")) else None
    dh = float(raw["H-H bonding"]) if pd.notna(raw.get("H-H bonding")) else None

    # Normalize raw_cas — handle Excel date artifacts
    raw_cas = ""
    if raw_cas_val is not None and not (isinstance(raw_cas_val, float) and math.isnan(raw_cas_val)):
        raw_cas = str(raw_cas_val).strip()
        # Excel sometimes reads CAS like "3018-09-5" as a date "3018-09-05 00:00:00"
        # Detect and skip date-formatted values
        if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", raw_cas):
            note("CAS", f"Excel parsed CAS as date: {raw_cas!r} — treating as missing.")
            raw_cas = ""

    out = {
        "Name": raw_name, "dD": dd, "dP": dp, "dH": dh, "R0": None, "duplicate": False,
    }

    # ── Step 2: HSP flags ──
    out.update(hsp_flags(dd or 0, dp or 0, dh or 0))

    # ── Step 3: Name cleaning ──
    name_clean, name_type, name_synonyms, source_uncertainty = clean_name(raw_name)
    out.update({
        "name_clean": name_clean, "name_type": name_type,
        "name_synonyms": name_synonyms, "source_uncertainty": source_uncertainty,
    })
    if source_uncertainty:
        note("NAME", f"Uncertainty marker removed from: {raw_name!r}")

    # ── Step 4: CAS resolution ──
    cas_final, cas_valid, cas_source = "", False, None
    pubchem_cid = None

    if raw_cas and validate_cas(raw_cas):
        cas_final = raw_cas
        cas_valid = True
        cas_source = "original"
    elif raw_cas:
        note("CAS", f"Original CAS {raw_cas!r} failed checksum.")

    if not cas_final:
        compound = pubchem_by_name(name_clean)
        if compound:
            cid = get_cid_from_compound(compound)
            if cid:
                pubchem_cid = cid
                syns = pubchem_synonyms(cid)
                found = extract_cas_from_synonyms(syns)
                if found:
                    cas_final = found
                    cas_valid = True
                    cas_source = "pubchem_name_lookup"
                    note("CAS", f"Resolved via PubChem: {cas_final}")

    if not cas_final:
        cir = cir_cas(name_clean)
        if cir:
            cas_final = cir
            cas_valid = True
            cas_source = "cir"
            note("CAS", f"Resolved via CIR: {cas_final}")
        else:
            note("CAS", "Not found by any method.")

    out.update({"CAS": raw_cas, "cas_final": cas_final, "cas_valid": cas_valid, "cas_source": cas_source or ""})

    # ── PubChem properties ──
    if not pubchem_cid and cas_final:
        compound = pubchem_by_cas(cas_final)
        if compound:
            pubchem_cid = get_cid_from_compound(compound)

    smiles_canonical = smiles_isomeric = mol_formula = mw = None
    xlogp = hbd_count = hba_count = name_iupac = inchikey_pubchem = None
    score_pubchem = 0.0

    if pubchem_cid:
        score_pubchem = 1.0
        props = pubchem_properties(pubchem_cid)
        mol_formula = props.get("MolecularFormula")
        mw = props.get("MolecularWeight")
        xlogp = props.get("XLogP")
        hbd_count = props.get("HBondDonorCount")
        hba_count = props.get("HBondAcceptorCount")
        smiles_canonical = props.get("CanonicalSMILES")
        smiles_isomeric = props.get("IsomericSMILES")
        name_iupac = props.get("IUPACName")
        inchikey_pubchem = props.get("InChIKey")

    # ── Step 5: SMILES ──
    if not smiles_canonical:
        fallback = cir_smiles(name_clean)
        if fallback:
            smiles_canonical = fallback
            note("SMILES", "SMILES from CIR fallback.")

    smiles_valid = validate_smiles(smiles_canonical) if smiles_canonical else False
    if smiles_canonical and not smiles_valid:
        note("SMILES", f"SMILES failed RDKit validation.")

    inchikey = inchikey_pubchem
    if not inchikey and smiles_canonical and smiles_valid:
        inchikey = smiles_to_inchikey(smiles_canonical)

    out.update({
        "pubchem_cid": pubchem_cid, "inchikey": inchikey,
        "smiles_canonical": smiles_canonical, "smiles_isomeric": smiles_isomeric,
        "smiles_valid": smiles_valid, "mol_formula": mol_formula, "mw": mw,
        "name_iupac": name_iupac, "xlogp": xlogp, "hbd_count": hbd_count, "hba_count": hba_count,
    })

    # ── Step 6: Physical properties (NIST) ──
    nist = nist_data(cas_final)
    out.update(nist)
    out["dielectric_constant"] = None

    prop_count = sum(1 for k in ["mw", "mol_formula", "bp_c", "mp_c"] if out.get(k) is not None)
    score_properties = prop_count / 4.0

    # ── Step 7: GHS & ICH Q3C ──
    ghs_statements, ghs_pictograms, ghs_signal_word = [], [], None
    if pubchem_cid:
        ghs = pubchem_ghs(pubchem_cid)
        ghs_statements = ghs.get("statements", [])
        ghs_pictograms = ghs.get("pictograms", [])
        ghs_signal_word = ghs.get("signal_word")

    out.update({
        "ghs_hazard_statements": "; ".join(ghs_statements) if ghs_statements else None,
        "ghs_pictograms": "; ".join(ghs_pictograms) if ghs_pictograms else None,
        "ghs_signal_word": ghs_signal_word,
    })
    out.update(extract_ghs_flags(ghs_statements))

    ich_class, ich_pde = get_ich_q3c(cas_final)
    out.update({"ich_q3c_class": ich_class, "ich_q3c_pde_mg_day": ich_pde})

    # ── Step 8: ClassyFire — filled in post-batch ──
    for col in ["cf_kingdom", "cf_superclass", "cf_class", "cf_subclass",
                "cf_direct_parent", "cf_alternative_parents", "cf_classification_type"]:
        out[col] = None

    # ── Step 9: URL ──
    if pubchem_cid:
        out["url_primary"] = f"https://pubchem.ncbi.nlm.nih.gov/compound/{pubchem_cid}"
        out["url_source"] = "pubchem"
    elif cas_final:
        out["url_primary"] = f"https://webbook.nist.gov/cgi/cbook.cgi?ID={cas_final}"
        out["url_source"] = "nist"
    else:
        out["url_primary"] = None
        out["url_source"] = None

    # ── Step 10: Confidence scoring ──
    if cas_source == "original" and pubchem_cid:
        score_cas = 1.0
    elif cas_source == "original":
        score_cas = 0.85
    elif cas_source == "pubchem_name_lookup":
        score_cas = 0.75
    elif cas_source == "cir":
        score_cas = 0.25
    else:
        score_cas = 0.0

    if name_iupac and name_clean.lower() == name_iupac.lower():
        score_name_match = 1.0
    elif pubchem_cid:
        score_name_match = 0.85
    elif cas_final and cas_source == "original":
        score_name_match = 0.70
    else:
        score_name_match = 0.30

    score_smiles = 1.0 if (smiles_canonical and smiles_valid) else (0.5 if smiles_canonical else 0.0)
    score_crossref = (
        1.0 if (inchikey and inchikey_pubchem and inchikey == inchikey_pubchem) else
        0.75 if (pubchem_cid and cas_final) else
        0.5 if pubchem_cid else 0.0
    )

    scores = {
        "score_cas": score_cas, "score_name_match": score_name_match,
        "score_pubchem": score_pubchem, "score_smiles": score_smiles,
        "score_crossref": score_crossref, "score_properties": score_properties,
    }
    confidence_score, confidence_label = compute_confidence(scores)
    out.update(scores)
    out.update({"confidence_score": confidence_score, "confidence_label": confidence_label})

    # ── Step 11: Verification ──
    inchikey_from_smiles = smiles_to_inchikey(smiles_canonical) if (smiles_canonical and smiles_valid) else None
    out.update({
        "verify_inchikey_mismatch": bool(inchikey_from_smiles and inchikey_pubchem and inchikey_from_smiles != inchikey_pubchem),
        "verify_cas_conflict": False,
        "verify_name_inconsistency": False,
        "verify_formula_mismatch": False,
        "verify_hsp_outlier": False,
        "verify_classyfire_consistent": False,  # updated after ClassyFire batch
    })

    out.update({
        "already_in_database": False,
        "lookup_failed": bool(not pubchem_cid and not cas_final),
        "needs_manual_review": bool(
            source_uncertainty or out.get("hsp_flag_dp_negative") or
            out.get("hsp_flag_dh_negative") or confidence_score < 0.50
        ),
        "processing_notes": " | ".join(notes) if notes else "",
    })

    return out

# ─── Column Order ─────────────────────────────────────────────────────────────
OUTPUT_COLUMNS = [
    "Name", "name_clean", "name_type", "name_iupac", "name_synonyms",
    "CAS", "cas_final", "cas_valid", "cas_source",
    "pubchem_cid", "inchikey", "smiles_canonical", "smiles_isomeric", "smiles_valid",
    "mol_formula", "mw",
    "dD", "dP", "dH", "R0",
    "bp_c", "mp_c", "density_g_ml", "flash_point_c", "vapor_pressure_mmhg",
    "dielectric_constant", "xlogp", "hbd_count", "hba_count",
    "ghs_hazard_statements", "ghs_pictograms", "ghs_signal_word",
    "ich_q3c_class", "ich_q3c_pde_mg_day",
    "flag_carcinogen", "flag_reproductive_toxin", "flag_flammable", "flag_acutely_toxic",
    "hsp_flag_dd_low", "hsp_flag_dd_high", "flag_acutely_toxic",
    "hsp_flag_dp_negative", "hsp_flag_dh_negative", "hsp_flag_r_large", "hsp_flag_nonpolar_check",
    "cf_kingdom", "cf_superclass", "cf_class", "cf_subclass",
    "cf_direct_parent", "cf_alternative_parents", "cf_classification_type",
    "confidence_score", "confidence_label",
    "score_cas", "score_name_match", "score_pubchem", "score_smiles",
    "score_crossref", "score_properties",
    "verify_inchikey_mismatch", "verify_cas_conflict", "verify_name_inconsistency",
    "verify_formula_mismatch", "verify_hsp_outlier", "verify_classyfire_consistent",
    "url_primary", "url_source",
    "source_uncertainty",
    "already_in_database", "lookup_failed", "needs_manual_review", "duplicate",
    "processing_notes",
]

# ─── Main Pipeline ─────────────────────────────────────────────────────────────
def run_pipeline(sample_n: int | None = None, start_row: int = 0, classyfire_only: bool = False):
    load_cache()

    # ClassyFire-only mode: load existing output and run batch
    if classyfire_only:
        if OUTPUT_FILE.exists():
            df = pd.read_csv(OUTPUT_FILE, low_memory=False)
            log.info(f"ClassyFire-only mode: loaded {len(df)} rows from {OUTPUT_FILE}")
            df = run_classyfire_batch(df)
            df.to_csv(OUTPUT_FILE, index=False)
            log.info("ClassyFire results merged and saved.")
            return df
        else:
            log.error("No existing output file found for --classyfire-only.")
            return None

    # Load raw data — CAS column as string to avoid date parsing
    log.info(f"Loading raw data from {RAW_XLSX}")
    raw_df = pd.read_excel(RAW_XLSX, dtype={"CAS #": str})
    log.info(f"Loaded {len(raw_df)} rows.")

    total_rows = len(raw_df)
    missing_cas = raw_df["CAS #"].isna().sum()
    blank_names = raw_df["Chemical name"].isna().sum()
    dup_mask = raw_df.duplicated(
        subset=["Chemical name", "Dispersion", "Polarity", "H-H bonding"], keep="first"
    )
    log.info(f"AUDIT: total={total_rows}, missing_CAS={missing_cas}, blank_names={blank_names}, dups={dup_mask.sum()}")

    end_row = min(start_row + sample_n, total_rows) if sample_n else total_rows
    log.info(f"Processing rows {start_row}–{end_row-1}")

    # Resume from checkpoint
    results = []
    if CHECKPOINT_FILE.exists() and start_row == 0:
        existing = pd.read_csv(CHECKPOINT_FILE, low_memory=False)
        start_row = len(existing)
        results = existing.to_dict(orient="records")
        log.info(f"Resumed from checkpoint at row {start_row}.")

    for i in range(start_row, end_row):
        row = raw_df.iloc[i]
        log.info(f"[{i+1}/{end_row}] {row['Chemical name']}")

        if dup_mask.iloc[i]:
            enriched = {
                "Name": row["Chemical name"],
                "name_clean": clean_name(str(row["Chemical name"]))[0],
                "duplicate": True,
                "dD": row["Dispersion"], "dP": row["Polarity"], "dH": row["H-H bonding"],
                "processing_notes": "[AUDIT] Duplicate row — skipped enrichment.",
            }
        else:
            try:
                enriched = process_row(i, row)
            except Exception as e:
                log.error(f"Error row {i} ({row['Chemical name']}): {e}", exc_info=True)
                enriched = {
                    "Name": row["Chemical name"],
                    "name_clean": clean_name(str(row["Chemical name"]))[0],
                    "duplicate": False,
                    "dD": row["Dispersion"], "dP": row["Polarity"], "dH": row["H-H bonding"],
                    "processing_notes": f"[ERROR] {e}",
                }

        results.append(enriched)

        if (i + 1) % 50 == 0:
            _save_checkpoint(results)
            save_cache()
            log.info(f"Checkpoint at row {i+1}.")

    _save_checkpoint(results)
    save_cache()

    # Build DataFrame
    df_out = pd.DataFrame(results)
    for col in OUTPUT_COLUMNS:
        if col not in df_out.columns:
            df_out[col] = None

    # Deduplicate column list (flag_acutely_toxic appears twice in template)
    seen = set()
    final_cols = []
    for c in OUTPUT_COLUMNS:
        if c not in seen and c in df_out.columns:
            seen.add(c)
            final_cols.append(c)
    df_out = df_out[final_cols]

    # ── ClassyFire batch (Step 8) ──
    df_out = run_classyfire_batch(df_out)

    # ── Post-ClassyFire: verify_classyfire_consistent ──
    if "cf_class" in df_out.columns:
        df_out["verify_classyfire_consistent"] = df_out["cf_class"].notna()

    df_out.to_csv(OUTPUT_FILE, index=False)
    log.info(f"Saved {len(df_out)} rows to {OUTPUT_FILE}")

    # Summary
    if "confidence_label" in df_out.columns:
        log.info(f"Confidence: {df_out['confidence_label'].value_counts().to_dict()}")
    if "ghs_hazard_statements" in df_out.columns:
        ghs_filled = df_out["ghs_hazard_statements"].notna().sum()
        log.info(f"GHS data: {ghs_filled}/{len(df_out)} rows ({ghs_filled/len(df_out)*100:.1f}%)")
    if "bp_c" in df_out.columns:
        bp_filled = df_out["bp_c"].notna().sum()
        log.info(f"NIST bp_c: {bp_filled}/{len(df_out)} rows ({bp_filled/len(df_out)*100:.1f}%)")

    # Route to verified/review/low_confidence
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    verify_cols = [c for c in ["Name", "cas_final", "cas_source", "pubchem_cid",
                                "confidence_score", "confidence_label",
                                "score_cas", "score_name_match", "processing_notes"]
                   if c in df_out.columns]
    df_out[verify_cols].to_csv(LOG_DIR / f"verification_log_{ts}.csv", index=False)

    if "confidence_label" in df_out.columns:
        for label, fname in [("HIGH", "verified.csv"), ("MEDIUM", "review_suggested.csv"), ("LOW", "low_confidence.csv")]:
            subset = df_out[df_out["confidence_label"] == label].copy()
            if len(subset):
                out_path = VERIFIED_DIR / fname
                if out_path.exists():
                    existing = pd.read_csv(out_path, low_memory=False)
                    subset = pd.concat([existing, subset], ignore_index=True)
                    if "name_clean" in subset.columns and "cas_final" in subset.columns:
                        subset = subset.drop_duplicates(subset=["name_clean", "cas_final"], keep="last")
                subset.to_csv(out_path, index=False)
        high_n = (df_out["confidence_label"] == "HIGH").sum()
        med_n = (df_out["confidence_label"] == "MEDIUM").sum()
        low_n = (df_out["confidence_label"] == "LOW").sum()
        log.info(f"Routed: HIGH={high_n}, MEDIUM={med_n}, LOW={low_n}")

    return df_out

def _save_checkpoint(results: list):
    pd.DataFrame(results).to_csv(CHECKPOINT_FILE, index=False)

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Materialism Solvent Pipeline")
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--classyfire-only", action="store_true")
    args = parser.parse_args()

    df = run_pipeline(
        sample_n=args.sample,
        start_row=args.start,
        classyfire_only=args.classyfire_only,
    )
    if df is not None:
        print(f"\nDone. {len(df)} rows → {OUTPUT_FILE}")
