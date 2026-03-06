"""Merge and deduplicate chemical/polymer datasets."""

from lib.normalize import normalize_name


def _merge_metadata(existing, new):
    """Fill in missing metadata from new source without overwriting HSP values."""
    for field in ["cas_number", "smiles", "molecular_formula", "molecular_weight",
                  "boiling_point", "density", "molar_volume", "ghs_hazard"]:
        if not existing.get(field) and new.get(field):
            existing[field] = new[field]
    if not existing.get("source_count"):
        existing["source_count"] = 1
    else:
        try:
            existing["source_count"] = int(existing["source_count"])
        except (TypeError, ValueError):
            existing["source_count"] = 1
    new_src = new.get("source", "")
    if new_src and new_src != existing.get("source", ""):
        existing["source_count"] = existing["source_count"] + 1
    # Accumulate dataset_ids so the entry stays visible when any
    # contributing dataset is active.
    new_ds = new.get("dataset_id", "")
    if new_ds:
        cur = existing.get("dataset_id", "")
        ids = set(cur.split(",")) if cur else set()
        ids.discard("")
        ids.add(new_ds)
        existing["dataset_id"] = ",".join(sorted(ids))


def merge_chemicals(all_sources):
    """Merge chemical datasets, deduplicating by CAS then by normalized name."""
    by_cas = {}
    by_name = {}
    result = []

    for chem in all_sources:
        cas = chem.get("cas_number", "")
        norm = normalize_name(chem["name"])

        if cas and cas in by_cas:
            _merge_metadata(by_cas[cas], chem)
            continue

        if norm and norm in by_name:
            _merge_metadata(by_name[norm], chem)
            if cas and cas not in by_cas:
                by_cas[cas] = by_name[norm]
            continue

        result.append(chem)
        if cas:
            by_cas[cas] = chem
        if norm:
            by_name[norm] = chem

    return result


def merge_chemicals_with_tracking(all_sources):
    """Like merge_chemicals but also returns a duplicate map.

    Returns:
        (merged_list, duplicates_map)
        duplicates_map: {cas_or_norm_key: [{"dataset": ..., "name": ..., ...}, ...]}
    """
    by_cas = {}
    by_name = {}
    result = []
    duplicates_map = {}

    def _track_duplicate(key, existing, new_entry):
        if key not in duplicates_map:
            duplicates_map[key] = [{
                "dataset": existing.get("source", ""),
                "name": existing.get("name", ""),
                "delta_d": existing.get("delta_d"),
                "delta_p": existing.get("delta_p"),
                "delta_h": existing.get("delta_h"),
            }]
        duplicates_map[key].append({
            "dataset": new_entry.get("source", ""),
            "name": new_entry.get("name", ""),
            "delta_d": new_entry.get("delta_d"),
            "delta_p": new_entry.get("delta_p"),
            "delta_h": new_entry.get("delta_h"),
        })

    for chem in all_sources:
        cas = chem.get("cas_number", "")
        norm = normalize_name(chem["name"])

        if cas and cas in by_cas:
            _merge_metadata(by_cas[cas], chem)
            _track_duplicate(cas, by_cas[cas], chem)
            continue

        if norm and norm in by_name:
            _merge_metadata(by_name[norm], chem)
            _track_duplicate(norm, by_name[norm], chem)
            if cas and cas not in by_cas:
                by_cas[cas] = by_name[norm]
            continue

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
        norm = normalize_name(poly["name"])

        if norm and norm in by_name:
            existing = by_name[norm]
            if not existing.get("cas_number") and poly.get("cas_number"):
                existing["cas_number"] = poly["cas_number"]
            if not existing.get("radius") and poly.get("radius"):
                existing["radius"] = poly["radius"]
            if not existing.get("type") and poly.get("type"):
                existing["type"] = poly["type"]
            # Accumulate dataset_ids
            new_ds = poly.get("dataset_id", "")
            if new_ds:
                cur = existing.get("dataset_id", "")
                ids = set(cur.split(",")) if cur else set()
                ids.discard("")
                ids.add(new_ds)
                existing["dataset_id"] = ",".join(sorted(ids))
            continue

        result.append(poly)
        if norm:
            by_name[norm] = poly

    return result
