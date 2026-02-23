#!/usr/bin/env python3
"""Build unified HSP database from all active datasets in the manifest.

Reads data/manifest.json, loads each active dataset's chemicals.csv and
polymers.csv, merges/deduplicates across datasets, and writes unified
output CSVs to data/processed/.

Usage:
    python build_unified.py
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from lib.normalize import normalize_cas
from lib.classify import classify_chemical, classify_polymer
from lib.confidence import compute_confidence
from lib.merge import merge_chemicals_with_tracking, merge_polymers
from lib.schema import CHEMICAL_FIELDS, POLYMER_FIELDS

DATASETS_DIR = os.path.join(BASE_DIR, "data", "datasets")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "manifest.json")
OUT_DIR = os.path.join(BASE_DIR, "data", "processed")


def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return {"version": 1, "datasets": {}}
    with open(MANIFEST_PATH, "r") as f:
        return json.load(f)


def load_dataset_csv(filepath, fields):
    """Load a per-dataset CSV into a list of dicts."""
    if not os.path.exists(filepath):
        return []
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {}
            for field in fields:
                val = row.get(field, "")
                if val == "":
                    val = None if field not in ("name", "cas_number", "smiles",
                                                 "molecular_formula", "category",
                                                 "ghs_hazard", "source", "source_url",
                                                 "hidden", "type") else ""
                entry[field] = val
            # Parse numeric fields
            for nf in ("delta_d", "delta_p", "delta_h", "molecular_weight",
                       "boiling_point", "density", "molar_volume", "confidence",
                       "radius"):
                if nf in entry and entry[nf] is not None:
                    try:
                        entry[nf] = float(entry[nf])
                    except (ValueError, TypeError):
                        entry[nf] = None
            if "source_count" in entry and entry["source_count"] is not None:
                try:
                    entry["source_count"] = int(entry["source_count"])
                except (ValueError, TypeError):
                    entry["source_count"] = 1
            rows.append(entry)
    return rows


def main():
    print("Building unified HSP database from manifest...")
    print()

    manifest = load_manifest()
    datasets = manifest.get("datasets", {})

    active_datasets = {k: v for k, v in datasets.items() if v.get("active", True)}
    print(f"Manifest: {len(datasets)} total datasets, {len(active_datasets)} active")
    print()

    all_chemicals = []
    all_polymers = []

    for ds_id, ds_meta in sorted(active_datasets.items()):
        ds_dir = os.path.join(DATASETS_DIR, ds_id)
        chem_path = os.path.join(ds_dir, "chemicals.csv")
        poly_path = os.path.join(ds_dir, "polymers.csv")

        chems = load_dataset_csv(chem_path, CHEMICAL_FIELDS)
        polys = load_dataset_csv(poly_path, POLYMER_FIELDS)

        # Tag every entry with its source dataset_id
        for c in chems:
            c["dataset_id"] = ds_id
        for p in polys:
            p["dataset_id"] = ds_id

        chem_count = len(chems)
        poly_count = len(polys)
        print(f"  {ds_id:30s}: {chem_count:>5} chemicals, {poly_count:>4} polymers")

        all_chemicals.extend(chems)
        all_polymers.extend(polys)

    print(f"  {'':30s}  -----")
    print(f"  {'Total raw':30s}: {len(all_chemicals):>5} chemicals, {len(all_polymers):>4} polymers")
    print()

    # Merge / deduplicate
    print("Merging and deduplicating...")
    merged_chems, duplicates_map = merge_chemicals_with_tracking(all_chemicals)
    merged_polys = merge_polymers(all_polymers)
    print(f"  Result: {len(merged_chems)} unique chemicals, {len(merged_polys)} unique polymers")
    print(f"  Duplicate groups: {len(duplicates_map)}")

    # CAS enrichment from cache
    cas_cache_path = os.path.join(OUT_DIR, ".cas_cache.json")
    if os.path.exists(cas_cache_path):
        with open(cas_cache_path) as f:
            cas_cache = json.load(f)
        enriched = 0
        for chem in merged_chems:
            if not chem.get("cas_number"):
                cached = cas_cache.get(chem["name"].lower().strip(), "")
                if cached:
                    chem["cas_number"] = cached
                    enriched += 1
        if enriched:
            print(f"  CAS enrichment from cache: {enriched} additional CAS numbers")

    # Classify and score
    for chem in merged_chems:
        if not chem.get("category"):
            chem["category"] = classify_chemical(chem["name"], chem.get("smiles"))
        chem["confidence"] = compute_confidence(chem, is_polymer=False)

    for poly in merged_polys:
        if not poly.get("type"):
            poly["type"] = classify_polymer(poly["name"])
        poly["confidence"] = compute_confidence(poly, is_polymer=True)

    # Sort
    merged_chems.sort(key=lambda x: (x.get("name") or "").lower())
    merged_polys.sort(key=lambda x: (x.get("name") or "").lower())

    # Write unified CSVs
    os.makedirs(OUT_DIR, exist_ok=True)

    chem_path = os.path.join(OUT_DIR, "unified_chemicals.csv")
    with open(chem_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CHEMICAL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for chem in merged_chems:
            row = {}
            for field in CHEMICAL_FIELDS:
                val = chem.get(field)
                row[field] = val if val is not None else ""
            writer.writerow(row)
    print(f"  Written: {chem_path}")

    poly_path = os.path.join(OUT_DIR, "unified_polymers.csv")
    with open(poly_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=POLYMER_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for poly in merged_polys:
            row = {}
            for field in POLYMER_FIELDS:
                val = poly.get(field)
                row[field] = val if val is not None else ""
            writer.writerow(row)
    print(f"  Written: {poly_path}")

    # Write duplicates map
    dup_path = os.path.join(OUT_DIR, "duplicates.json")
    with open(dup_path, "w") as f:
        json.dump(duplicates_map, f, indent=2)
    print(f"  Written: {dup_path}")

    # Summary
    print()
    print("=" * 50)
    print(f"TOTAL CHEMICALS: {len(merged_chems)}")
    print(f"TOTAL POLYMERS:  {len(merged_polys)}")
    print("=" * 50)

    if merged_chems:
        # Source breakdown
        source_counts = {}
        for chem in merged_chems:
            src = chem.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
        print("\nChemicals by primary source:")
        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            print(f"  {src:30s}: {count:>5}")

        # Category breakdown
        cat_counts = {}
        for chem in merged_chems:
            cat = chem.get("category", "other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        print("\nChemicals by category:")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat:20s}: {count:>5}")


if __name__ == "__main__":
    main()
