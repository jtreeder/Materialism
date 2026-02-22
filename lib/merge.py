"""Merge and deduplication logic for HSP datasets."""

from .normalize import normalize_name


def _merge_metadata(existing, new_entry):
    """Merge metadata from new_entry into existing, filling blanks only."""
    for field in ("cas_number", "smiles", "molecular_formula",
                  "molecular_weight", "boiling_point", "density",
                  "molar_volume", "ghs_hazard"):
        if not existing.get(field) and new_entry.get(field):
            existing[field] = new_entry[field]

    # Track source count
    new_src = new_entry.get("source", "")
    existing_src = existing.get("source", "")
    if new_src and new_src != existing_src:
        existing["source_count"] = existing.get("source_count", 1) + 1


def merge_chemicals(all_sources):
    """Merge chemical datasets, deduplicating by CAS then by normalized name."""
    by_cas = {}
    by_name = {}
    result = []

    for chem in all_sources:
        cas = chem.get("cas_number", "")
        norm = normalize_name(chem.get("name", ""))

        # Check for duplicate by CAS
        if cas and cas in by_cas:
            _merge_metadata(by_cas[cas], chem)
            continue

        # Check for duplicate by normalized name
        if norm and norm in by_name:
            _merge_metadata(by_name[norm], chem)
            if cas and cas not in by_cas:
                by_cas[cas] = by_name[norm]
            continue

        # New compound
        result.append(chem)
        if cas:
            by_cas[cas] = chem
        if norm:
            by_name[norm] = chem

    return result


def merge_chemicals_with_tracking(all_sources):
    """Like merge_chemicals, but also returns a duplicate map.

    Returns:
        (merged_list, duplicates_map)
        duplicates_map: {key: {"primary": {...}, "duplicates": [...]}}
        where key is CAS number or normalized name.
    """
    by_cas = {}
    by_name = {}
    result = []
    duplicates_map = {}

    for chem in all_sources:
        cas = chem.get("cas_number", "")
        norm = normalize_name(chem.get("name", ""))

        # Check for duplicate by CAS
        if cas and cas in by_cas:
            existing = by_cas[cas]
            _merge_metadata(existing, chem)
            key = cas
            if key not in duplicates_map:
                duplicates_map[key] = {
                    "primary": {
                        "dataset": existing.get("dataset_id", ""),
                        "name": existing.get("name", ""),
                    },
                    "duplicates": [],
                }
            duplicates_map[key]["duplicates"].append({
                "dataset": chem.get("dataset_id", ""),
                "name": chem.get("name", ""),
                "delta_d": chem.get("delta_d"),
                "delta_p": chem.get("delta_p"),
                "delta_h": chem.get("delta_h"),
            })
            continue

        # Check for duplicate by normalized name
        if norm and norm in by_name:
            existing = by_name[norm]
            _merge_metadata(existing, chem)
            if cas and cas not in by_cas:
                by_cas[cas] = existing
            key = norm
            if key not in duplicates_map:
                duplicates_map[key] = {
                    "primary": {
                        "dataset": existing.get("dataset_id", ""),
                        "name": existing.get("name", ""),
                    },
                    "duplicates": [],
                }
            duplicates_map[key]["duplicates"].append({
                "dataset": chem.get("dataset_id", ""),
                "name": chem.get("name", ""),
                "delta_d": chem.get("delta_d"),
                "delta_p": chem.get("delta_p"),
                "delta_h": chem.get("delta_h"),
            })
            continue

        # New compound
        result.append(chem)
        if cas:
            by_cas[cas] = chem
        if norm:
            by_name[norm] = chem

    return result, duplicates_map


def merge_polymers(all_sources):
    """Merge polymer datasets, deduplicating by normalized name."""
    by_name = {}
    result = []

    for poly in all_sources:
        norm = normalize_name(poly.get("name", ""))

        if norm and norm in by_name:
            existing = by_name[norm]
            if not existing.get("cas_number") and poly.get("cas_number"):
                existing["cas_number"] = poly["cas_number"]
            if not existing.get("radius") and poly.get("radius"):
                existing["radius"] = poly["radius"]
            if not existing.get("type") and poly.get("type"):
                existing["type"] = poly["type"]
            new_src = poly.get("source", "")
            if new_src and new_src != existing.get("source", ""):
                existing["source_count"] = existing.get("source_count", 1) + 1
            continue

        result.append(poly)
        if norm:
            by_name[norm] = poly

    return result
