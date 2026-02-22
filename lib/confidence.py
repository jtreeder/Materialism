"""Confidence scoring for database entries."""

# Source reliability tiers (higher = more reliable)
SOURCE_CONFIDENCE = {
    "handbook": 0.50,
    "hspip": 0.50,
    "mendeley": 0.40,
    "solvpred": 0.35,
    "accudyne": 0.40,
    "wolfram": 0.35,
    "pang2024": 0.30,
    "hansen_a2": 0.30,
}


def compute_confidence(entry, is_polymer=False, confidence_tier=None):
    """Compute a confidence score (0.0-1.0) for a database entry.

    Args:
        entry: dict with chemical/polymer data
        is_polymer: if True, skip SMILES bonus
        confidence_tier: override base score (from dataset manifest)
    """
    if confidence_tier is not None:
        score = confidence_tier
    else:
        source = entry.get("source", "")
        score = SOURCE_CONFIDENCE.get(source, 0.25)

    if entry.get("cas_number"):
        score += 0.15

    if not is_polymer and entry.get("smiles"):
        score += 0.10

    source_count = entry.get("source_count", 1)
    if source_count > 1:
        score += min((source_count - 1) * 0.15, 0.30)

    return round(min(score, 1.0), 2)
