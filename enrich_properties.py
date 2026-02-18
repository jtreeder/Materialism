"""Enrich missing MW and BP values from PubChem PUG REST API.

Looks up molecular weight and boiling point for chemicals that are
missing these values, using CAS number, name, or SMILES for lookup.
Caches all API responses to disk (shares cache with enrich_cas.py).

Usage:
    python enrich_properties.py
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

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache", "pubchem")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
CHEMICALS_CSV = os.path.join(DATA_DIR, "hsp_chemicals.csv")
RATE_LIMIT = 0.22  # ~4.5 req/s
MAX_RETRIES = 4

os.makedirs(CACHE_DIR, exist_ok=True)


# --- Caching (same scheme as enrich_cas.py) ---
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


def pubchem_request(url, endpoint_key, query_key):
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


def get_cid(name=None, cas=None, smiles=None):
    """Resolve a CID from PubChem using CAS, name, or SMILES."""
    # Try CAS first (most reliable)
    if cas:
        encoded = urllib.parse.quote(cas, safe="")
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/cids/JSON"
        data = pubchem_request(url, "cid_by_cas", cas)
        if data and "error" not in data:
            cids = data.get("IdentifierList", {}).get("CID", [])
            if len(cids) == 1:
                return cids[0]

    # Try name
    if name:
        encoded = urllib.parse.quote(name, safe="")
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded}/cids/JSON"
        data = pubchem_request(url, "cid_by_name", name.lower())
        if data and "error" not in data:
            cids = data.get("IdentifierList", {}).get("CID", [])
            if len(cids) == 1:
                return cids[0]

    # Try SMILES
    if smiles:
        encoded = urllib.parse.quote(smiles, safe="")
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/cids/JSON"
        data = pubchem_request(url, "cid_by_smiles", smiles)
        if data and "error" not in data:
            cids = data.get("IdentifierList", {}).get("CID", [])
            if len(cids) == 1:
                return cids[0]

    return None


def get_properties(cid):
    """Get MW and BP from PubChem for a given CID."""
    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/"
        f"property/MolecularWeight,MolecularFormula/JSON"
    )
    data = pubchem_request(url, "props", str(cid))

    mw = None
    formula = None
    if data and "error" not in data:
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            mw = props[0].get("MolecularWeight")
            formula = props[0].get("MolecularFormula")

    return mw, formula


def get_boiling_point(cid):
    """Get boiling point from PubChem experimental properties."""
    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/"
        f"JSON?heading=Boiling+Point"
    )
    data = pubchem_request(url, "bp_view", str(cid))

    if not data or "error" in data:
        return None

    # Navigate the nested PUG View structure
    try:
        record = data.get("Record", {})
        sections = record.get("Section", [])
        for section in sections:
            for sub in section.get("Section", []):
                for subsub in sub.get("Section", []):
                    if "Boiling Point" in subsub.get("TOCHeading", ""):
                        for info in subsub.get("Information", []):
                            val = info.get("Value", {})
                            # Try StringWithMarkup first
                            swm = val.get("StringWithMarkup", [])
                            if swm:
                                text = swm[0].get("String", "")
                                bp = parse_bp(text)
                                if bp is not None:
                                    return bp
                            # Try Number
                            num = val.get("Number", [])
                            unit = val.get("Unit", "")
                            if num:
                                if "°C" in unit or "C" in unit or not unit:
                                    return num[0]
                                elif "°F" in unit or "F" in unit:
                                    return round((num[0] - 32) * 5 / 9, 1)
                                elif "K" in unit:
                                    return round(num[0] - 273.15, 1)
    except Exception:
        pass

    return None


def parse_bp(text):
    """Parse a boiling point string like '100 °C', '212 °F', '80-82 °C' etc."""
    if not text:
        return None

    # Remove decomposition markers
    if re.search(r"decomp|sublim", text, re.I):
        return None

    # Handle ranges: take midpoint
    m = re.search(r"(-?\d+\.?\d*)\s*[-–]\s*(-?\d+\.?\d*)\s*°?\s*([CFK])", text)
    if m:
        lo, hi, unit = float(m.group(1)), float(m.group(2)), m.group(3)
        val = (lo + hi) / 2
        if unit == "F":
            val = (val - 32) * 5 / 9
        elif unit == "K":
            val = val - 273.15
        return round(val, 1)

    # Single value
    m = re.search(r"(-?\d+\.?\d*)\s*°?\s*([CFK])", text)
    if m:
        val, unit = float(m.group(1)), m.group(2)
        if unit == "F":
            val = (val - 32) * 5 / 9
        elif unit == "K":
            val = val - 273.15
        return round(val, 1)

    # Bare number (assume °C)
    m = re.search(r"(-?\d+\.?\d*)", text)
    if m:
        return round(float(m.group(1)), 1)

    return None


def main():
    print("=" * 60)
    print("Property Enrichment — MW & BP from PubChem")
    print("=" * 60)

    with open(CHEMICALS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Add source tracking columns if not present
    for col in ["mw_source", "bp_source"]:
        if col not in fieldnames:
            fieldnames.append(col)

    need_mw = [(i, r) for i, r in enumerate(rows) if not r.get("molecular_weight", "").strip()]
    need_bp = [(i, r) for i, r in enumerate(rows) if not r.get("boiling_point", "").strip()]

    print(f"Total chemicals: {len(rows)}")
    print(f"Missing MW: {len(need_mw)}")
    print(f"Missing BP: {len(need_bp)}")

    # Collect all entries that need any property
    need_any = {}
    for i, r in need_mw:
        need_any[i] = r
    for i, r in need_bp:
        need_any[i] = r

    print(f"Entries needing lookup: {len(need_any)}")

    stats = {"mw_found": 0, "bp_found": 0, "no_cid": 0, "total": len(need_any)}

    for count, (idx, row) in enumerate(sorted(need_any.items())):
        name = row.get("name", "").strip()
        cas = row.get("cas_number", "").strip()
        smiles = row.get("smiles", "").strip()
        has_mw = bool(row.get("molecular_weight", "").strip())
        has_bp = bool(row.get("boiling_point", "").strip())

        progress = f"[{count+1}/{len(need_any)}]"
        print(f"  {progress} {name[:50]}...", end=" ", flush=True)

        cid = get_cid(name=name, cas=cas, smiles=smiles)
        if not cid:
            stats["no_cid"] += 1
            print("NO CID")
            continue

        pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"

        if not has_mw:
            mw, formula = get_properties(cid)
            if mw:
                row["molecular_weight"] = str(round(float(mw), 1))
                row["mw_source"] = pubchem_url
                stats["mw_found"] += 1
                if formula and not row.get("molecular_formula", "").strip():
                    row["molecular_formula"] = formula

        if not has_bp:
            bp = get_boiling_point(cid)
            if bp is not None:
                row["boiling_point"] = str(bp)
                row["bp_source"] = pubchem_url
                stats["bp_found"] += 1

        got = []
        if row.get("mw_source", ""): got.append(f"MW={row['molecular_weight']}")
        if row.get("bp_source", ""): got.append(f"BP={row['boiling_point']}")
        print(", ".join(got) if got else "no new data")

    # Also record source for existing data
    for row in rows:
        src_url = row.get("source_url", "").strip()
        if row.get("molecular_weight", "").strip() and not row.get("mw_source", "").strip():
            row["mw_source"] = src_url
        if row.get("boiling_point", "").strip() and not row.get("bp_source", "").strip():
            row["bp_source"] = src_url

    # Write back
    with open(CHEMICALS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  MW found: {stats['mw_found']}/{len(need_mw)} missing")
    print(f"  BP found: {stats['bp_found']}/{len(need_bp)} missing")
    print(f"  No CID:   {stats['no_cid']}")
    print(f"  CSV written: {CHEMICALS_CSV}")


if __name__ == "__main__":
    main()
