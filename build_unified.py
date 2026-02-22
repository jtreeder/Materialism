#!/usr/bin/env python3
"""Build unified HSP database from all active datasets in the manifest.

Reads data/manifest.json, loads each active dataset's chemicals.csv and
polymers.csv, merges/deduplicates across datasets, and produces unified
output files for generate_html.py.

Usage:
    python build_unified.py
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "data", "datasets")
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "manifest.json")
OUT_DIR = os.path.join(BASE_DIR, "data", "processed")

sys.path.insert(0, BASE_DIR)
from lib.classify import classify_chemical, classify_polymer
from lib.confidence import compute_confidence
from lib.merge import merge_chemicals_with_tracking, merge_polymers
from lib.normalize import parse_float
from lib.schema import CHEMICAL_FIELDS, POLYMER_FIELDS


def load_manifest():
    """Load manifest, returning empty structure if missing."""
    if not os.path.exists(MANIFEST_PATH):
        return {"version": 1, "datasets": {}}
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def load_dataset_chemicals(ds_id, ds_dir, confidence_tier=None):
    """Load chemicals.csv from a dataset directory."""
    path = os.path.join(ds_dir, "chemicals.csv")
    if not os.path.exists(path):
        return []

    chemicals = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Parse numeric fields
            for field in ("delta_d", "delta_p", "delta_h",
                          "molecular_weight", "boiling_point", "density",
                          "molar_volume", "confidence"):
                val = row.get(field, "")
                row[field] = parse_float(val)

            row["source_count"] = int(row.get("source_count", 1) or 1)
            row["dataset_id"] = ds_id

            # Skip rows without HSP triplet
            if row["delta_d"] is None or row["delta_p"] is None or row["delta_h"] is None:
                continue

            chemicals.append(row)
    return chemicals


def load_dataset_polymers(ds_id, ds_dir, confidence_tier=None):
    """Load polymers.csv from a dataset directory."""
    path = os.path.join(ds_dir, "polymers.csv")
    if not os.path.exists(path):
        return []

    polymers = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for field in ("delta_d", "delta_p", "delta_h", "radius", "confidence"):
                val = row.get(field, "")
                row[field] = parse_float(val)

            row["source_count"] = int(row.get("source_count", 1) or 1)
            row["dataset_id"] = ds_id

            if row["delta_d"] is None or row["delta_p"] is None or row["delta_h"] is None:
                continue

            polymers.append(row)
    return polymers


def write_csv_file(data, filepath, fields):
    """Write a list of dicts to a CSV file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for entry in data:
            row = {}
            for field in fields:
                val = entry.get(field)
                row[field] = val if val is not None else ""
            writer.writerow(row)


def main():
    print("Building unified HSP database from manifest...\n")

    manifest = load_manifest()
    datasets = manifest.get("datasets", {})

    if not datasets:
        print("No datasets in manifest. Database will be empty.")
        print("Use import_dataset.py to add datasets.\n")

    # Load all active datasets
    all_chemicals = []
    all_polymers = []
    active_count = 0

    for ds_id, ds_meta in sorted(datasets.items()):
        active = ds_meta.get("active", True)
        ds_dir = os.path.join(DATASETS_DIR, ds_id)
        tier = ds_meta.get("confidence_tier")

        status = "active" if active else "INACTIVE (skipped)"
        print(f"  {ds_id}: {ds_meta.get('name', ds_id)} - {status}")

        if not active:
            continue

        if not os.path.isdir(ds_dir):
            print(f"    WARNING: Directory not found: {ds_dir}")
            continue

        active_count += 1
        chems = load_dataset_chemicals(ds_id, ds_dir, tier)
        polys = load_dataset_polymers(ds_id, ds_dir, tier)
        print(f"    Loaded: {len(chems)} chemicals, {len(polys)} polymers")

        all_chemicals.extend(chems)
        all_polymers.extend(polys)

    print(f"\n  Total raw: {len(all_chemicals)} chemicals, {len(all_polymers)} polymers")
    print(f"  Active datasets: {active_count}")

    # Merge/deduplicate across datasets
    print("\nMerging and deduplicating...")
    merged_chems, duplicates_map = merge_chemicals_with_tracking(all_chemicals)
    merged_polys = merge_polymers(all_polymers)
    print(f"  Result: {len(merged_chems)} unique chemicals, {len(merged_polys)} unique polymers")
    if duplicates_map:
        print(f"  Duplicate groups: {len(duplicates_map)}")

    # Enrich CAS from cache
    cas_cache_path = os.path.join(OUT_DIR, ".cas_cache.json")
    if os.path.exists(cas_cache_path) and merged_chems:
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

    # Classify unclassified entries
    for chem in merged_chems:
        if not chem.get("category"):
            chem["category"] = classify_chemical(chem.get("name", ""), chem.get("smiles"))
    for poly in merged_polys:
        if not poly.get("type"):
            poly["type"] = classify_polymer(poly.get("name", ""))

    # Recompute confidence (after CAS enrichment)
    for chem in merged_chems:
        chem["confidence"] = compute_confidence(chem, is_polymer=False)
    for poly in merged_polys:
        poly["confidence"] = compute_confidence(poly, is_polymer=True)

    # Sort
    merged_chems.sort(key=lambda x: (x.get("name") or "").lower())
    merged_polys.sort(key=lambda x: (x.get("name") or "").lower())

    # Write outputs
    os.makedirs(OUT_DIR, exist_ok=True)

    chem_path = os.path.join(OUT_DIR, "unified_chemicals.csv")
    write_csv_file(merged_chems, chem_path, CHEMICAL_FIELDS)
    print(f"\n  Written: {chem_path} ({len(merged_chems)} chemicals)")

    poly_path = os.path.join(OUT_DIR, "unified_polymers.csv")
    write_csv_file(merged_polys, poly_path, POLYMER_FIELDS)
    print(f"  Written: {poly_path} ({len(merged_polys)} polymers)")

    # Write duplicates map
    dup_path = os.path.join(OUT_DIR, "duplicates.json")
    with open(dup_path, "w") as f:
        json.dump(duplicates_map, f, indent=2)
    print(f"  Written: {dup_path} ({len(duplicates_map)} duplicate groups)")

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
            src = chem.get("dataset_id") or chem.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
        print("\nChemicals by dataset:")
        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            print(f"  {src:25s}: {count:>5}")

        # Metadata completeness
        has_cas = sum(1 for c in merged_chems if c.get("cas_number"))
        has_smiles = sum(1 for c in merged_chems if c.get("smiles"))
        n = len(merged_chems)
        print(f"\nMetadata completeness:")
        print(f"  CAS number:   {has_cas:>5}/{n} ({100*has_cas/n:.0f}%)")
        print(f"  SMILES:       {has_smiles:>5}/{n} ({100*has_smiles/n:.0f}%)")


if __name__ == "__main__":
    main()
