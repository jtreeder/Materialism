"""Apply CAS corrections from cas_corrections.csv into the build pipeline.

This script reads corrections exported from the CAS Review Tool (cas_review.html)
and updates the CAS cache so that build_hsp_database.py picks them up on rebuild.

Usage:
  1. Review chemicals in cas_review.html
  2. Click "Download Approved" to get cas_corrections.csv
  3. Place cas_corrections.csv in the project root (or data/processed/)
  4. Run: python scripts/apply_cas_corrections.py
  5. Rebuild: python build_hsp_database.py && python generate_html.py
"""

import csv
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CACHE_PATH = os.path.join(PROJECT_DIR, "data", "processed", ".cas_cache.json")

# Look for corrections file in multiple locations
CORRECTIONS_PATHS = [
    os.path.join(PROJECT_DIR, "cas_corrections.csv"),
    os.path.join(PROJECT_DIR, "data", "processed", "cas_corrections.csv"),
]


def main():
    # Find corrections file
    corrections_path = None
    for p in CORRECTIONS_PATHS:
        if os.path.exists(p):
            corrections_path = p
            break

    if not corrections_path:
        print("Error: cas_corrections.csv not found.")
        print("Looked in:")
        for p in CORRECTIONS_PATHS:
            print(f"  {p}")
        print("\nDownload it from the CAS Review Tool (cas_review.html).")
        sys.exit(1)

    # Load existing cache
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)

    # Read corrections
    with open(corrections_path) as f:
        reader = csv.DictReader(f)
        corrections = list(reader)

    print(f"Loaded {len(corrections)} corrections from {corrections_path}")

    updated = 0
    for row in corrections:
        original = row.get("original_name", "").strip()
        corrected = row.get("corrected_name", "").strip()
        cas = row.get("cas_number", "").strip()

        if not original:
            continue

        key = original.lower().strip()

        if cas:
            cache[key] = cas
            updated += 1
            print(f"  {original} -> CAS {cas}" + (f" (name: {corrected})" if corrected != original else ""))
        elif corrected and corrected != original:
            # Name correction without CAS — store corrected name lookup
            cache[key] = ""
            # Also store by corrected name in case it helps
            cache[corrected.lower().strip()] = cache.get(corrected.lower().strip(), "")
            print(f"  {original} -> renamed to {corrected} (no CAS)")

    # Save updated cache
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)

    print(f"\nUpdated {updated} CAS entries in cache.")
    print(f"Cache now has {sum(1 for v in cache.values() if v)} CAS numbers.")
    print(f"\nRun 'python build_hsp_database.py && python generate_html.py' to rebuild.")


if __name__ == "__main__":
    main()
