#!/usr/bin/env python3
"""Database cleanup script for Materialism HSP Database.

Fixes:
1. Names that are just "CAS xxx-xx-x" (from pang2024) → resolves real name via PubChem
2. Trailing periods and double spaces in names
3. Enriches missing CAS numbers via PubChem (by name and SMILES)

Uses PubChem PUG REST API with caching and rate limiting.

Usage:
    python clean_database.py
"""

import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache", "pubchem")
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
CHEMICALS_CSV = os.path.join(DATA_DIR, "hsp_chemicals.csv")
POLYMERS_CSV = os.path.join(DATA_DIR, "hsp_polymers.csv")

RATE_LIMIT = 0.22  # ~4.5 req/s (PubChem allows 5/s)
MAX_RETRIES = 4

os.makedirs(CACHE_DIR, exist_ok=True)

# --- CAS Validation ---
CAS_RE = re.compile(r"^(\d{2,7})-(\d{2})-(\d)$")


def validate_cas(cas_str):
    """Validate CAS format and checksum."""
    cas_str = cas_str.strip()
    m = CAS_RE.match(cas_str)
    if not m:
        return False
    digits = cas_str.replace("-", "")
    check_digit = int(digits[-1])
    total = sum(int(ch) * (i + 1) for i, ch in enumerate(reversed(digits[:-1])))
    return (total % 10) == check_digit


# --- Caching ---
def _cache_path(endpoint, query):
    h = hashlib.sha256(f"{endpoint}:{query}".encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{h}.json")


def cache_get(endpoint, query):
    path = _cache_path(endpoint, query)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def cache_set(endpoint, query, data):
    path = _cache_path(endpoint, query)
    with open(path, "w") as f:
        json.dump(data, f, indent=1)


# --- PubChem API ---
def pubchem_get(url, endpoint_key, query_key):
    """PubChem API request with caching, rate limiting, and retries."""
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


def _extract_cas_from_synonyms(data):
    """Extract and validate the best CAS number from PubChem synonyms response."""
    if not data or "error" in data:
        return None, None

    info_list = data.get("InformationList", {}).get("Information", [])
    if not info_list:
        return None, None

    # If multiple CIDs, ambiguous — skip
    if len(info_list) > 1:
        return None, None

    info = info_list[0]
    cid = info.get("CID", "?")
    synonyms = info.get("Synonym", [])

    # Extract all valid CAS numbers
    candidates = [s.strip() for s in synonyms if CAS_RE.match(s.strip()) and validate_cas(s.strip())]

    # Extract the best common name (first non-CAS synonym, typically the IUPAC name)
    best_name = None
    for syn in synonyms:
        syn = syn.strip()
        if not CAS_RE.match(syn) and len(syn) > 2 and not syn.startswith("DTXSID"):
            best_name = syn
            break

    cas = candidates[0] if candidates else None
    return cas, best_name


def lookup_cas_by_name(name):
    """Look up CAS number from PubChem by chemical name."""
    encoded = urllib.parse.quote(name, safe="")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/synonyms/JSON"
    data = pubchem_get(url, "name_synonyms", name.lower())
    return _extract_cas_from_synonyms(data)


def lookup_cas_by_smiles(smiles):
    """Look up CAS number from PubChem by SMILES."""
    encoded = urllib.parse.quote(smiles, safe="")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/synonyms/JSON"
    data = pubchem_get(url, "smiles_synonyms", smiles)
    return _extract_cas_from_synonyms(data)


def lookup_name_by_cas(cas):
    """Look up chemical name from PubChem by CAS number."""
    encoded = urllib.parse.quote(cas, safe="")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/synonyms/JSON"
    data = pubchem_get(url, "cas_synonyms", cas)
    _, name = _extract_cas_from_synonyms(data)
    return name


# --- Name cleaning ---
def clean_name(name):
    """Fix minor formatting issues in chemical names."""
    n = name.strip()
    # Remove trailing periods (e.g., "Perillyl Alcohol." → "Perillyl Alcohol")
    n = n.rstrip(".")
    # Collapse multiple spaces
    n = re.sub(r"\s{2,}", " ", n)
    return n.strip()


# --- Main cleanup ---
def cleanup_chemicals(csv_path):
    """Clean up chemical names and enrich CAS numbers."""
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    stats = {
        "total": len(rows),
        "name_fixed_punctuation": 0,
        "name_resolved_from_cas": 0,
        "cas_enriched_by_name": 0,
        "cas_enriched_by_smiles": 0,
        "cas_already_had": 0,
        "cas_unresolved": 0,
    }

    for i, row in enumerate(rows):
        name = row.get("name", "").strip()
        cas = row.get("cas_number", "").strip()
        smiles = row.get("smiles", "").strip()

        # --- Phase 1: Fix names ---

        # Fix punctuation issues
        cleaned = clean_name(name)
        if cleaned != name:
            stats["name_fixed_punctuation"] += 1
            print(f"  [punct] '{name}' -> '{cleaned}'")
            row["name"] = cleaned
            name = cleaned

        # Resolve "CAS xxx-xx-x" placeholder names from pang2024
        cas_name_match = re.match(r"^CAS\s+(\d{2,7}-\d{2}-\d)$", name)
        if cas_name_match:
            cas_in_name = cas_name_match.group(1)
            if validate_cas(cas_in_name):
                resolved_name = lookup_name_by_cas(cas_in_name)
                if resolved_name:
                    stats["name_resolved_from_cas"] += 1
                    print(f"  [cas-name] '{name}' -> '{resolved_name}' (CAS {cas_in_name})")
                    row["name"] = resolved_name
                    name = resolved_name
                    # Also set the CAS number if it was missing
                    if not cas or not validate_cas(cas):
                        row["cas_number"] = cas_in_name
                        cas = cas_in_name

        # --- Phase 2: Enrich CAS numbers ---

        if cas and validate_cas(cas):
            stats["cas_already_had"] += 1
            continue

        progress = f"[{i + 1}/{len(rows)}]"

        # Try by name first
        found_cas, _ = lookup_cas_by_name(name)
        if found_cas and validate_cas(found_cas):
            stats["cas_enriched_by_name"] += 1
            row["cas_number"] = found_cas
            print(f"  {progress} {name[:50]} -> CAS {found_cas} (by name)")
            continue

        # Try by SMILES if available
        if smiles:
            found_cas, _ = lookup_cas_by_smiles(smiles)
            if found_cas and validate_cas(found_cas):
                stats["cas_enriched_by_smiles"] += 1
                row["cas_number"] = found_cas
                print(f"  {progress} {name[:50]} -> CAS {found_cas} (by SMILES)")
                continue

        stats["cas_unresolved"] += 1

    # Write back
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return stats


def cleanup_polymers(csv_path):
    """Clean up polymer names."""
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    fixed = 0
    for row in rows:
        name = row.get("name", "").strip()
        cleaned = clean_name(name)
        if cleaned != name:
            fixed += 1
            print(f"  [punct] '{name}' -> '{cleaned}'")
            row["name"] = cleaned

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {"total": len(rows), "name_fixed": fixed}


def main():
    print("=" * 60)
    print("Database Cleanup — Materialism HSP Database")
    print("=" * 60)

    print(f"\n--- Cleaning chemicals: {CHEMICALS_CSV}")
    chem_stats = cleanup_chemicals(CHEMICALS_CSV)
    print(f"\nChemicals summary:")
    for k, v in chem_stats.items():
        print(f"  {k}: {v}")

    print(f"\n--- Cleaning polymers: {POLYMERS_CSV}")
    poly_stats = cleanup_polymers(POLYMERS_CSV)
    print(f"\nPolymers summary:")
    for k, v in poly_stats.items():
        print(f"  {k}: {v}")

    print("\nDone!")


if __name__ == "__main__":
    main()
