# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Engine vs an independent oracle (Skyfield + JPL DE421). See validation/.

Thresholds are set roughly 2-3x above the errors measured on the first run, so they catch
regressions without being flaky. Measured values are in VALIDATION_REPORT.md.
"""
import pytest
pytest.importorskip("skyfield")
pytest.importorskip("skyfield_data")

from timeengine import ephem
from validation import sweeps

needs_swe = pytest.mark.skipif(not ephem.HAS_SWE, reason="precision checks need pyswisseph")
slow = pytest.mark.slow

@needs_swe
def test_planet_longitudes_match_jpl():
    r = sweeps.planets(200)
    assert r["sun"]["max"] < 0.5
    assert r["moon"]["max"] < 5.0
    for p, s in r.items():
        if p not in ("sun", "moon"):
            assert s["max"] < 2.0, (p, s)

@needs_swe
def test_solar_terms_match_independent_root_find():
    assert sweeps.solar_terms(step=8)["max"] < 10.0          # seconds

@needs_swe
def test_equation_of_time_matches_sidereal_derivation():
    assert sweeps.equation_of_time(300)["max"] < 0.15        # minutes

@needs_swe
def test_ascendant_and_midheaven_match_closed_form():
    r = sweeps.ascendant_mc(200)
    assert r["ascendant"]["max"] < 0.5 and r["mc"]["max"] < 0.5   # arcsec

@needs_swe
@slow
def test_true_solar_time_end_to_end_across_cities_and_history():
    r = sweeps.true_solar_time(per_city=25)
    assert r["n"] > 250 and r["max"] < 0.15                  # minutes

@needs_swe
@slow
def test_year_and_month_pillars_follow_the_suns_longitude():
    r = sweeps.bazi_year_month(400)
    assert r["bad_month"] == 0 and r["bad_year"] == 0, r["examples"]

@slow
def test_lunar_calendar_matches_astronomy_in_the_modern_era():
    r = sweeps.lunar_calendar(1929, 2048)
    assert r["days"]["modern"] > 40000
    assert r["mismatches"]["modern"] == 0, r["examples"]

@slow
def test_lunar_calendar_early_era_differences_are_bounded_and_known():
    # Characterisation, not a pass of correctness: 1901-1928 differs on ~1% of days
    # (likely a different time standard in that era). If this number moves, look.
    r = sweeps.lunar_calendar(1901, 1928)
    assert r["mismatches"]["early"] <= 120

@needs_swe
@slow
def test_luck_pillar_start_distance_matches_independent_jie_crossings():
    assert sweeps.luck_start(150)["max"] < 20.0              # seconds (measured max ~8)
