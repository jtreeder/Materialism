"""Tests for core HSP calculations against known published values."""

import pytest
from backend.app.services.hsp_calculator import (
    hsp_distance,
    red_number,
    mixture_hsp,
    rank_solvents,
    fit_solubility_sphere,
)


class TestHSPDistance:
    def test_identical_materials(self):
        hsp = (18.0, 10.0, 7.0)
        assert hsp_distance(hsp, hsp) == pytest.approx(0.0)

    def test_known_distance_toluene_to_ps(self):
        """Toluene (18.0, 1.4, 2.0) vs PS (18.5, 4.5, 2.9).
        Ra² = 4(18.0-18.5)² + (1.4-4.5)² + (2.0-2.9)²
            = 4(0.25) + 9.61 + 0.81 = 11.42
        Ra = 3.38
        """
        toluene = (18.0, 1.4, 2.0)
        ps = (18.5, 4.5, 2.9)
        assert hsp_distance(toluene, ps) == pytest.approx(3.38, abs=0.01)

    def test_large_distance_water_hexane(self):
        """Water and hexane should be far apart."""
        water = (15.5, 16.0, 42.3)
        hexane = (14.9, 0.0, 0.0)
        dist = hsp_distance(water, hexane)
        assert dist > 40  # Very incompatible

    def test_symmetry(self):
        a = (16.0, 8.0, 5.0)
        b = (18.0, 3.0, 12.0)
        assert hsp_distance(a, b) == pytest.approx(hsp_distance(b, a))

    def test_dispersion_weighted_double(self):
        """δD differences are weighted by factor of 4 (so 2x in distance)."""
        a = (15.0, 5.0, 5.0)
        b_d = (16.0, 5.0, 5.0)  # δD differs by 1
        b_p = (15.0, 6.0, 5.0)  # δP differs by 1
        # Ra(a, b_d) = sqrt(4*1) = 2.0
        # Ra(a, b_p) = sqrt(1) = 1.0
        assert hsp_distance(a, b_d) == pytest.approx(2.0)
        assert hsp_distance(a, b_p) == pytest.approx(1.0)


class TestREDNumber:
    def test_inside_sphere(self):
        solvent = (18.0, 1.4, 2.0)  # Toluene
        ps = (18.5, 4.5, 2.9)       # Polystyrene
        r0 = 5.3
        red = red_number(solvent, ps, r0)
        assert red < 1.0  # Toluene dissolves PS

    def test_outside_sphere(self):
        water = (15.5, 16.0, 42.3)
        ps = (18.5, 4.5, 2.9)
        r0 = 5.3
        red = red_number(water, ps, r0)
        assert red > 1.0  # Water doesn't dissolve PS

    def test_zero_radius(self):
        assert red_number((15, 5, 5), (15, 5, 5), 0) == float("inf")


class TestMixtureHSP:
    def test_single_component(self):
        hsp = (18.0, 5.0, 7.0)
        blend = mixture_hsp([(hsp, 1.0)])
        assert blend == pytest.approx(hsp)

    def test_equal_mix(self):
        """50/50 mix should be the midpoint."""
        a = (14.0, 0.0, 0.0)
        b = (18.0, 10.0, 6.0)
        blend = mixture_hsp([(a, 0.5), (b, 0.5)])
        assert blend == pytest.approx((16.0, 5.0, 3.0))

    def test_normalization(self):
        """Non-normalized fractions should still work."""
        a = (14.0, 0.0, 0.0)
        b = (18.0, 10.0, 6.0)
        blend = mixture_hsp([(a, 30), (b, 70)])
        expected_d = 14.0 * 0.3 + 18.0 * 0.7
        assert blend[0] == pytest.approx(expected_d)


class TestRankSolvents:
    def test_ranking_order(self):
        solvents = [
            {"name": "A", "delta_d": 18.5, "delta_p": 4.5, "delta_h": 2.9},
            {"name": "B", "delta_d": 15.0, "delta_p": 0.0, "delta_h": 0.0},
            {"name": "C", "delta_d": 18.0, "delta_p": 1.4, "delta_h": 2.0},
        ]
        target = (18.5, 4.5, 2.9)  # PS
        ranked = rank_solvents(solvents, target)
        assert ranked[0]["name"] == "A"  # Identical to target
        assert ranked[0]["ra_distance"] == 0.0

    def test_with_red(self):
        solvents = [
            {"name": "A", "delta_d": 18.0, "delta_p": 1.4, "delta_h": 2.0},
        ]
        target = (18.5, 4.5, 2.9)
        ranked = rank_solvents(solvents, target, target_radius=5.3)
        assert "red" in ranked[0]


class TestSphereFitting:
    def test_simple_separation(self):
        """Good solvents near center, bad solvents far away."""
        good = [
            (18.0, 5.0, 3.0),
            (17.5, 4.0, 2.5),
            (18.5, 5.5, 3.5),
            (18.2, 4.8, 2.8),
        ]
        bad = [
            (14.0, 0.0, 0.0),
            (15.5, 16.0, 42.0),
            (25.0, 18.0, 20.0),
            (13.0, 2.0, 1.0),
        ]
        result = fit_solubility_sphere(good, bad)
        assert result["fit_quality"] >= 0.75
        assert result["radius"] > 0
        # Center should be near the good solvents
        assert 16 < result["center"][0] < 20
