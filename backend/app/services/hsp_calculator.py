"""Core Hansen Solubility Parameter calculations.

All HSP values are in MPa½. The key formulas:
- Ra² = 4(δD₁-δD₂)² + (δP₁-δP₂)² + (δH₁-δH₂)²
- RED = Ra / R₀  (Relative Energy Difference)
- RED < 1 → compatible, RED > 1 → incompatible
"""

import numpy as np
from scipy.optimize import minimize


def hsp_distance(hsp1, hsp2):
    """Calculate the Hansen distance Ra between two materials.

    Args:
        hsp1: (δD, δP, δH) tuple for material 1
        hsp2: (δD, δP, δH) tuple for material 2

    Returns:
        Ra distance in MPa½
    """
    d1, p1, h1 = hsp1
    d2, p2, h2 = hsp2
    ra_sq = 4 * (d1 - d2) ** 2 + (p1 - p2) ** 2 + (h1 - h2) ** 2
    return np.sqrt(ra_sq)


def red_number(hsp_solvent, hsp_material, radius):
    """Calculate the Relative Energy Difference (RED).

    RED < 1: solvent is inside the solubility sphere (compatible)
    RED = 1: on the boundary
    RED > 1: outside the sphere (incompatible)
    """
    ra = hsp_distance(hsp_solvent, hsp_material)
    return ra / radius if radius > 0 else float("inf")


def mixture_hsp(components):
    """Calculate HSP of a solvent mixture using volume-weighted average.

    Args:
        components: list of (hsp_tuple, volume_fraction) pairs
            where hsp_tuple = (δD, δP, δH)

    Returns:
        (δD_mix, δP_mix, δH_mix) tuple
    """
    total_fraction = sum(f for _, f in components)
    if abs(total_fraction - 1.0) > 0.01:
        # Normalize fractions
        components = [(hsp, f / total_fraction) for hsp, f in components]

    d_mix = sum(hsp[0] * f for hsp, f in components)
    p_mix = sum(hsp[1] * f for hsp, f in components)
    h_mix = sum(hsp[2] * f for hsp, f in components)
    return (d_mix, p_mix, h_mix)


def rank_solvents(solvents, target_hsp, target_radius=None, top_n=50):
    """Rank solvents by distance to a target point in Hansen space.

    Args:
        solvents: list of dicts with keys 'name', 'delta_d', 'delta_p', 'delta_h'
        target_hsp: (δD, δP, δH) of the target material
        target_radius: if provided, also compute RED
        top_n: number of results to return

    Returns:
        list of dicts with added 'ra_distance' and optionally 'red' keys, sorted by distance
    """
    results = []
    for s in solvents:
        solvent_hsp = (s["delta_d"], s["delta_p"], s["delta_h"])
        ra = hsp_distance(solvent_hsp, target_hsp)
        entry = {**s, "ra_distance": round(ra, 2)}
        if target_radius is not None:
            entry["red"] = round(red_number(solvent_hsp, target_hsp, target_radius), 3)
        results.append(entry)

    results.sort(key=lambda x: x["ra_distance"])
    return results[:top_n]


def fit_solubility_sphere(good_solvents, bad_solvents, initial_guess=None):
    """Fit a solubility sphere to experimental good/bad solvent data.

    Finds the center (δD, δP, δH) and radius R₀ that best separates
    good solvents (inside) from bad solvents (outside).

    Args:
        good_solvents: list of (δD, δP, δH) tuples — dissolved / compatible
        bad_solvents: list of (δD, δP, δH) tuples — did not dissolve
        initial_guess: optional (δD, δP, δH, R) starting point

    Returns:
        dict with 'center' (δD, δP, δH), 'radius', 'fit_quality',
        'misclassified_good', 'misclassified_bad'
    """
    good = np.array(good_solvents)
    bad = np.array(bad_solvents)

    if initial_guess is None:
        # Start at centroid of good solvents
        center_guess = good.mean(axis=0)
        # Initial radius: max distance from center to any good solvent
        dists = np.array([hsp_distance(center_guess, g) for g in good])
        r_guess = dists.max() * 1.1
        x0 = np.append(center_guess, r_guess)
    else:
        x0 = np.array(initial_guess)

    def objective(x):
        """Minimize misclassification with penalty."""
        center = x[:3]
        r = abs(x[3])

        penalty = 0.0

        # Good solvents should be inside (distance < r)
        for g in good:
            dist = hsp_distance(center, g)
            if dist > r:
                penalty += (dist - r) ** 2 * 10  # Heavy penalty

        # Bad solvents should be outside (distance > r)
        for b in bad:
            dist = hsp_distance(center, b)
            if dist < r:
                penalty += (r - dist) ** 2 * 5

        # Small penalty to prefer smaller spheres (Occam's razor)
        penalty += r * 0.01

        return penalty

    result = minimize(
        objective,
        x0,
        method="Nelder-Mead",
        options={"maxiter": 50000, "xatol": 1e-6, "fatol": 1e-8},
    )

    center = result.x[:3]
    radius = abs(result.x[3])

    # Count misclassifications
    misc_good = sum(1 for g in good if hsp_distance(center, g) > radius)
    misc_bad = sum(1 for b in bad if hsp_distance(center, b) < radius)
    total = len(good) + len(bad)
    accuracy = 1 - (misc_good + misc_bad) / total if total > 0 else 0

    return {
        "center": tuple(round(c, 2) for c in center),
        "radius": round(radius, 2),
        "fit_quality": round(accuracy, 3),
        "misclassified_good": misc_good,
        "misclassified_bad": misc_bad,
        "total_solvents": total,
    }


def optimize_blend(target_hsp, available_solvents, n_components=3,
                   target_radius=None, constraints=None):
    """Find the optimal solvent blend to match a target HSP.

    Args:
        target_hsp: (δD, δP, δH) to match
        available_solvents: list of dicts with HSP values
        n_components: max number of solvents in the blend
        target_radius: if provided, try to get RED < 1
        constraints: dict with optional keys:
            'max_cost', 'excluded_cas', 'min_bp', 'max_bp'

    Returns:
        list of dicts with 'solvent', 'volume_fraction', blend HSP, and distance
    """
    # Pre-filter by constraints
    candidates = available_solvents
    if constraints:
        if "excluded_cas" in constraints:
            excluded = set(constraints["excluded_cas"])
            candidates = [s for s in candidates if s.get("cas_number") not in excluded]
        if "min_bp" in constraints:
            candidates = [
                s for s in candidates
                if s.get("boiling_point") is None
                or s["boiling_point"] >= constraints["min_bp"]
            ]
        if "max_bp" in constraints:
            candidates = [
                s for s in candidates
                if s.get("boiling_point") is None
                or s["boiling_point"] <= constraints["max_bp"]
            ]

    if len(candidates) < n_components:
        n_components = len(candidates)

    if n_components == 0:
        return {"components": [], "blend_hsp": None, "distance": None}

    # Pre-rank by distance to target
    ranked = rank_solvents(candidates, target_hsp, top_n=min(20, len(candidates)))

    # Try combinations of top candidates
    from itertools import combinations

    best_result = None
    best_distance = float("inf")

    top_pool = ranked[:min(12, len(ranked))]

    for combo in combinations(range(len(top_pool)), min(n_components, len(top_pool))):
        combo_solvents = [top_pool[i] for i in combo]
        combo_hsps = [
            (s["delta_d"], s["delta_p"], s["delta_h"]) for s in combo_solvents
        ]

        # Optimize volume fractions
        n = len(combo)
        if n == 1:
            fractions = [1.0]
        else:
            def blend_dist(fracs):
                # Last fraction is 1 - sum(others)
                all_fracs = list(fracs) + [1.0 - sum(fracs)]
                if any(f < 0 for f in all_fracs):
                    return 1e6
                components = list(zip(combo_hsps, all_fracs))
                blend = mixture_hsp(components)
                return hsp_distance(blend, target_hsp)

            from scipy.optimize import minimize as sp_minimize

            x0 = np.ones(n - 1) / n
            bounds = [(0.01, 0.99)] * (n - 1)
            opt = sp_minimize(
                blend_dist, x0, method="L-BFGS-B", bounds=bounds
            )
            fracs_opt = list(opt.x) + [1.0 - sum(opt.x)]
            if any(f < 0 for f in fracs_opt):
                continue
            fractions = fracs_opt

        components = list(zip(combo_hsps, fractions))
        blend = mixture_hsp(components)
        dist = hsp_distance(blend, target_hsp)

        if dist < best_distance:
            best_distance = dist
            best_result = {
                "components": [
                    {
                        "name": combo_solvents[i]["name"],
                        "volume_fraction": round(fractions[i], 4),
                        "delta_d": combo_solvents[i]["delta_d"],
                        "delta_p": combo_solvents[i]["delta_p"],
                        "delta_h": combo_solvents[i]["delta_h"],
                    }
                    for i in range(n)
                ],
                "blend_hsp": tuple(round(v, 2) for v in blend),
                "distance": round(dist, 3),
            }
            if target_radius:
                best_result["red"] = round(dist / target_radius, 3)

    return best_result
