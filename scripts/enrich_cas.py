"""Enrich hsp_chemicals.csv with CAS numbers from PubChem.

Strategy:
1. For each chemical missing a CAS number, query PubChem by name.
2. If name lookup fails and SMILES is available, try SMILES lookup.
3. Write results back into the CSV preserving all other columns.

Uses PubChem PUG REST (no API key needed, rate limit ~5 req/s).
"""

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "hsp_chemicals.csv")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", ".cas_cache.json")
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Valid CAS pattern
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


def pubchem_get(url, retries=3):
    """Fetch URL with retries and rate limiting."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 503 or e.code == 429:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            return None
        except Exception:
            time.sleep(1)
            continue
    return None


def get_cas_by_name(name):
    """Look up CAS number for a chemical name via PubChem."""
    encoded = urllib.parse.quote(name, safe="")
    url = f"{BASE}/compound/name/{encoded}/property/IUPACName/JSON"
    data = pubchem_get(url)
    if not data:
        return None
    try:
        cid = data["PropertyTable"]["Properties"][0]["CID"]
    except (KeyError, IndexError):
        return None
    return get_cas_by_cid(cid)


def get_cas_by_smiles(smiles):
    """Look up CAS number for a SMILES string via PubChem."""
    encoded = urllib.parse.quote(smiles, safe="")
    url = f"{BASE}/compound/smiles/{encoded}/property/IUPACName/JSON"
    data = pubchem_get(url)
    if not data:
        return None
    try:
        cid = data["PropertyTable"]["Properties"][0]["CID"]
    except (KeyError, IndexError):
        return None
    return get_cas_by_cid(cid)


def get_cas_by_cid(cid):
    """Given a PubChem CID, extract the CAS registry number from synonyms."""
    url = f"{BASE}/compound/cid/{cid}/synonyms/JSON"
    data = pubchem_get(url)
    if not data:
        return None
    try:
        synonyms = data["InformationList"]["Information"][0]["Synonym"]
    except (KeyError, IndexError):
        return None
    for s in synonyms:
        if CAS_RE.match(s):
            return s
    return None


def main():
    # Load CSV
    with open(CSV_PATH) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    missing = [(i, r) for i, r in enumerate(rows) if not r.get("cas_number", "").strip()]
    print(f"Total chemicals: {len(rows)}")
    print(f"Missing CAS: {len(missing)}")

    if not missing:
        print("Nothing to do.")
        return

    cache = load_cache()
    found = 0
    not_found = 0

    for idx, (row_idx, row) in enumerate(missing):
        name = row["name"]
        smiles = row.get("smiles", "").strip()

        # Check cache first
        cache_key = name.lower().strip()
        if cache_key in cache:
            cas = cache[cache_key]
            if cas:
                rows[row_idx]["cas_number"] = cas
                found += 1
            else:
                not_found += 1
            continue

        # Try name lookup
        cas = get_cas_by_name(name)

        # Fallback: try SMILES
        if not cas and smiles:
            cas = get_cas_by_smiles(smiles)

        # Rate limit: ~4 requests/sec
        time.sleep(0.25)

        if cas:
            rows[row_idx]["cas_number"] = cas
            cache[cache_key] = cas
            found += 1
            status = cas
        else:
            cache[cache_key] = ""
            not_found += 1
            status = "NOT FOUND"

        if (idx + 1) % 25 == 0 or idx == len(missing) - 1:
            print(f"  [{idx + 1}/{len(missing)}] found={found} missing={not_found}")
            save_cache(cache)

    # Final save
    save_cache(cache)

    # Write CSV back
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total_cas = sum(1 for r in rows if r.get("cas_number", "").strip())
    print(f"\nDone! Found {found} new CAS numbers.")
    print(f"Total with CAS: {total_cas}/{len(rows)} ({100*total_cas/len(rows):.0f}%)")


if __name__ == "__main__":
    main()
