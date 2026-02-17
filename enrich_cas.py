"""CAS Number Enrichment Script for Materialism HSP Database.

Looks up missing CAS numbers from PubChem PUG REST API.
- Validates CAS format and checksum
- Caches all API responses to disk
- Produces a manual review CSV for ambiguous cases
- Resumes from where it left off (skips rows that already have CAS)

Usage:
    python enrich_cas.py              # enrich missing CAS numbers
    python enrich_cas.py --refresh    # re-check all rows, even with existing CAS
"""

import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# --- Configuration ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "pubchem")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
REVIEW_CSV = os.path.join(os.path.dirname(__file__), "data", "cas_manual_review.csv")
RATE_LIMIT = 0.22  # ~4.5 req/s (PubChem allows 5/s)
MAX_RETRIES = 4

CHEMICALS_CSV = os.path.join(DATA_DIR, "hsp_chemicals.csv")
POLYMERS_CSV = os.path.join(DATA_DIR, "hsp_polymers.csv")

os.makedirs(CACHE_DIR, exist_ok=True)

# --- CAS Validation ---
CAS_RE = re.compile(r"^(\d{2,7})-(\d{2})-(\d)$")


def validate_cas(cas_str):
    """Validate CAS format and checksum. Returns True if valid."""
    cas_str = cas_str.strip()
    m = CAS_RE.match(cas_str)
    if not m:
        return False
    digits = cas_str.replace("-", "")
    check_digit = int(digits[-1])
    total = 0
    body = digits[:-1]
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (i + 1)
    return (total % 10) == check_digit


# --- Name Normalization ---
STRIP_PATTERNS = [
    r"\b(?:ACS|reagent|grade|anhydrous|stabilized|inhibited|certified|extra\s*pure|"
    r"puriss|for\s+synthesis|p\.?a\.?|analytical|spectroscopic|technical|practical)\b",
    r"\b\d+(\.\d+)?%\s*(solution|in\b|v/v|w/w|wt)\b",
    r"\bsolution\s+in\s+\w+\b",
    r"\b(>|<|≥|≤)\s*\d+(\.\d+)?%\b",
]

MIXTURE_INDICATORS = re.compile(
    r"\b(mixture|proprietary|extract|fragrance|resin\s+blend|petroleum|"
    r"mineral\s+oil|fuel|gasoline|naphtha|kerosene|tar|pitch|wax\s+blend|"
    r"oil\s+blend|grease)\b",
    re.I,
)


def normalize_name(name):
    """Normalize chemical name for lookup. Returns (normalized, is_mixture)."""
    n = name.strip()
    if MIXTURE_INDICATORS.search(n):
        return n, True
    for pat in STRIP_PATTERNS:
        n = re.sub(pat, "", n, flags=re.I)
    n = re.sub(r"\s+", " ", n).strip().strip(",").strip()
    return n, False


# --- Caching ---
def cache_key(endpoint, query):
    h = hashlib.sha256(f"{endpoint}:{query}".encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{h}.json")


def cache_get(endpoint, query):
    path = cache_key(endpoint, query)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def cache_set(endpoint, query, data):
    path = cache_key(endpoint, query)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


# --- PubChem API ---
def pubchem_request(url, endpoint_key, query_key):
    """Make a PubChem API request with caching, rate limiting, and retries."""
    cached = cache_get(endpoint_key, query_key)
    if cached is not None:
        return cached

    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(RATE_LIMIT)
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                cache_set(endpoint_key, query_key, data)
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                cache_set(endpoint_key, query_key, {"error": "not_found"})
                return {"error": "not_found"}
            if e.code in (429, 500, 502, 503):
                wait = (2 ** attempt) * 2
                print(f"    HTTP {e.code}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            cache_set(endpoint_key, query_key, {"error": f"http_{e.code}"})
            return {"error": f"http_{e.code}"}
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = (2 ** attempt) * 2
                print(f"    Error: {e}, retrying in {wait}s...")
                time.sleep(wait)
                continue
            cache_set(endpoint_key, query_key, {"error": str(e)})
            return {"error": str(e)}

    cache_set(endpoint_key, query_key, {"error": "max_retries"})
    return {"error": "max_retries"}


def lookup_by_name(name):
    """Look up CAS from PubChem by chemical name. Returns (cas, source, confidence, evidence_url, notes) or None."""
    encoded = urllib.parse.quote(name, safe="")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/synonyms/JSON"
    data = pubchem_request(url, "name_synonyms", name.lower())
    return _extract_cas_from_synonyms(data, f"name:{name}")


def lookup_by_smiles(smiles):
    """Look up CAS from PubChem by SMILES. Returns (cas, source, confidence, evidence_url, notes) or None."""
    encoded = urllib.parse.quote(smiles, safe="")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/synonyms/JSON"
    data = pubchem_request(url, "smiles_synonyms", smiles)
    return _extract_cas_from_synonyms(data, f"smiles:{smiles}")


def _extract_cas_from_synonyms(data, evidence_key):
    """Extract and validate CAS numbers from PubChem synonyms response."""
    if not data or "error" in data:
        return None

    info_list = data.get("InformationList", {}).get("Information", [])
    if not info_list:
        return None

    # If multiple CIDs returned, ambiguous
    if len(info_list) > 1:
        all_candidates = []
        for info in info_list:
            cid = info.get("CID", "?")
            syns = info.get("Synonym", [])
            candidates = [s for s in syns if CAS_RE.match(s) and validate_cas(s)]
            all_candidates.extend([(c, cid) for c in candidates])
        return ("ambiguous", "pubchem", "manual", "", f"Multiple CIDs: {[i.get('CID') for i in info_list]}")

    info = info_list[0]
    cid = info.get("CID", "?")
    synonyms = info.get("Synonym", [])
    evidence_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"

    # Extract all valid CAS numbers
    candidates = []
    for syn in synonyms:
        syn = syn.strip()
        if CAS_RE.match(syn) and validate_cas(syn):
            candidates.append(syn)

    if not candidates:
        return None

    if len(candidates) == 1:
        return (candidates[0], "pubchem", "high", evidence_url, f"CID {cid}, sole CAS in synonyms")

    # Multiple CAS candidates for same CID — pick the first one (most prominent)
    # PubChem lists the primary CAS first in synonyms
    return (candidates[0], "pubchem", "medium", evidence_url,
            f"CID {cid}, {len(candidates)} CAS candidates, picked first: {candidates[:5]}")


# --- Main enrichment logic ---
def enrich_csv(csv_path, has_smiles=False, refresh=False):
    """Enrich a CSV with CAS numbers. Returns stats dict."""
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    stats = {"total": len(rows), "already_had": 0, "resolved_high": 0,
             "resolved_medium": 0, "manual": 0, "unresolved": 0, "skipped_mixture": 0}
    review_rows = []

    for i, row in enumerate(rows):
        name = row.get("name", "").strip()
        existing_cas = row.get("cas_number", "").strip()

        if existing_cas and validate_cas(existing_cas) and not refresh:
            stats["already_had"] += 1
            continue

        if not name:
            stats["unresolved"] += 1
            continue

        norm_name, is_mixture = normalize_name(name)
        if is_mixture:
            stats["skipped_mixture"] += 1
            review_rows.append({
                "row": i + 2, "original_name": name, "normalized_name": norm_name,
                "candidate_cas": "", "reason": "mixture/UVCB"
            })
            continue

        progress = f"[{i+1}/{len(rows)}]"
        print(f"  {progress} {name[:60]}...", end=" ", flush=True)

        result = None

        # Strategy 1: Look up by name
        result = lookup_by_name(norm_name)

        # Strategy 2: If name failed and we have SMILES, try SMILES
        smiles = row.get("smiles", "").strip() if has_smiles else ""
        if (result is None or (result and result[0] == "ambiguous")) and smiles:
            smiles_result = lookup_by_smiles(smiles)
            if smiles_result and smiles_result[0] != "ambiguous":
                result = smiles_result

        # Strategy 3: If normalized name differs, try original name
        if result is None and norm_name.lower() != name.lower():
            result = lookup_by_name(name)

        if result is None:
            stats["unresolved"] += 1
            print("NOT FOUND")
            review_rows.append({
                "row": i + 2, "original_name": name, "normalized_name": norm_name,
                "candidate_cas": "", "reason": "not found in PubChem"
            })
            continue

        cas, source, confidence, evidence_url, notes = result

        if cas == "ambiguous":
            stats["manual"] += 1
            print(f"AMBIGUOUS ({notes})")
            review_rows.append({
                "row": i + 2, "original_name": name, "normalized_name": norm_name,
                "candidate_cas": notes, "reason": "ambiguous"
            })
            continue

        if confidence == "high":
            stats["resolved_high"] += 1
        else:
            stats["resolved_medium"] += 1

        row["cas_number"] = cas
        print(f"-> {cas} ({confidence})")

    # Write back
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return stats, review_rows


def main():
    refresh = "--refresh" in sys.argv

    print("=" * 60)
    print("CAS Enrichment — Materialism HSP Database")
    print("=" * 60)

    all_review = []

    # Chemicals
    print(f"\n--- Enriching chemicals: {CHEMICALS_CSV}")
    chem_stats, chem_review = enrich_csv(CHEMICALS_CSV, has_smiles=True, refresh=refresh)
    all_review.extend(chem_review)
    print(f"\nChemicals: {chem_stats}")

    # Polymers
    print(f"\n--- Enriching polymers: {POLYMERS_CSV}")
    poly_stats, poly_review = enrich_csv(POLYMERS_CSV, has_smiles=False, refresh=refresh)
    all_review.extend(poly_review)
    print(f"\nPolymers: {poly_stats}")

    # Write review CSV
    if all_review:
        with open(REVIEW_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["row", "original_name", "normalized_name",
                                                     "candidate_cas", "reason"])
            writer.writeheader()
            writer.writerows(all_review)
        print(f"\nManual review file: {REVIEW_CSV} ({len(all_review)} entries)")

    print("\nDone!")


if __name__ == "__main__":
    main()
