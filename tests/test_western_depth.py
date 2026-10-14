# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Western depth: aspects, retrograde, nodes.

Pure-math expectations are hand-computed, not read back from the code.
Sky-dependent checks assert structural facts (the Sun and Moon are never
retrograde; the nodes sit opposite each other) rather than specific dates.
"""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

from timeengine import TimeEngine, ephem
from timeengine.api import app
from timeengine.aspects import (DEFAULT_ORBS, MAJOR_ASPECTS, angular_separation,
                                compute_aspects, deviation, is_retrograde,
                                match_aspect, phase)
from timeengine.cal import jd_from_datetime
from timeengine.western import PLANETS, chart_positions

needs_swe = pytest.mark.skipif(not ephem.HAS_SWE, reason="needs pyswisseph")

UTC = dt.timezone.utc


def test_angular_separation_wraps_correctly():
    assert angular_separation(10.0, 350.0) == pytest.approx(20.0)
    assert angular_separation(0.0, 180.0) == pytest.approx(180.0)
    assert angular_separation(45.0, 45.0) == pytest.approx(0.0)


def test_deviation_is_signed_distance_from_exact():
    assert deviation(10.0, 100.0, 90.0) == pytest.approx(0.0)
    assert deviation(10.0, 95.0, 90.0) == pytest.approx(-5.0)
    assert deviation(10.0, 103.0, 90.0) == pytest.approx(3.0)


def test_match_aspect_finds_square_and_rejects_out_of_orb():
    name, angle, dev = match_aspect(0.0, 93.0)
    assert (name, angle) == ("square", 90.0)
    assert dev == pytest.approx(3.0)
    assert match_aspect(0.0, 80.0) is None          # 10 deg off square, orb is 6


def test_match_aspect_picks_closest_when_orbs_overlap():
    wide = dict(DEFAULT_ORBS, sextile=15.0, square=15.0)
    name, _, dev = match_aspect(0.0, 72.0, wide)    # 12 off sextile, 18 off square
    assert name == "sextile" and dev == pytest.approx(12.0)


def test_phase_applying_vs_separating_from_relative_motion():
    # b outruns a: separation 88 -> 88.04, closing on the 90 deg square.
    assert phase(0.0, 88.0, 0.13, 1.0, 90.0) == "applying"
    # b outruns a: separation 92 -> 92.04, opening away from the square.
    assert phase(0.0, 92.0, 0.13, 1.0, 90.0) == "separating"
    # Partile: within 3 arcminutes counts as exact regardless of motion.
    assert phase(10.0, 100.0, 1.0, 1.0, 90.0) == "exact"
    assert phase(10.0, 100.02, 1.0, 1.0, 90.0) == "exact"
    # No speeds, no phase read.
    assert phase(0.0, 88.0, None, 0.13, 90.0) == "unknown"


def test_is_retrograde_is_speed_sign():
    assert is_retrograde(-0.5) is True
    assert is_retrograde(0.0) is False
    assert is_retrograde(1.2) is False


def test_compute_aspects_returns_tightest_first_with_unique_pairs():
    found = compute_aspects({"a": 0.0, "b": 90.0, "c": 180.0},
                            {"a": 1.0, "b": 1.0, "c": 1.0})
    pairs = [(r["body1"], r["body2"]) for r in found]
    assert len(pairs) == len(set(pairs)) == 3
    assert pairs == [("a", "b"), ("a", "c"), ("b", "c")]   # dev 0 ties: alpha order
    assert [r["aspect"] for r in found] == ["square", "opposition", "square"]


@needs_swe
def test_sun_and_moon_are_never_retrograde():
    base = dt.datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for day in range(0, 360, 4):
        w = chart_positions(jd_from_datetime(base + dt.timedelta(days=day)), 40.7, -74.0)
        assert w["speeds"]["sun"] > 0 and w["speeds"]["moon"] > 0
        assert w["retrograde"]["sun"] is False and w["retrograde"]["moon"] is False


@needs_swe
def test_retrograde_flag_matches_speed_sign_across_a_year():
    base = dt.datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for day in range(0, 360, 7):
        w = chart_positions(jd_from_datetime(base + dt.timedelta(days=day)), 40.7, -74.0)
        for p in PLANETS:
            assert w["retrograde"][p] == (w["speeds"][p] < 0.0), (p, day)


@needs_swe
def test_planet_speeds_are_plausible_means():
    w = chart_positions(jd_from_datetime(dt.datetime(2026, 6, 1, 12, 0, tzinfo=UTC)),
                        40.7, -74.0)
    assert 0.9 < w["speeds"]["sun"] < 1.1        # mean motion ~0.986 deg/day
    assert 11.5 < w["speeds"]["moon"] < 15.5    # varies ~11.8-15.3 over the anomalistic cycle


@needs_swe
def test_nodes_are_opposite_and_true_by_default():
    eng = TimeEngine()
    snap = eng.resolve(dt.datetime(1991, 5, 14, 8, 30), 35.2, -80.8, "America/New_York")
    west = snap.western
    assert west.node_kind == "true"
    assert west.north_node is not None and west.south_node is not None
    assert (west.north_node + 180.0) % 360.0 == pytest.approx(west.south_node)


@needs_swe
def test_aspects_in_snapshot_are_within_orb_and_well_formed():
    eng = TimeEngine()
    snap = eng.resolve(dt.datetime(1991, 5, 14, 8, 30), 35.2, -80.8, "America/New_York")
    west = snap.western
    known = set(PLANETS) | {"ascendant", "mc", "north_node"}
    pairs = set()
    for a in west.aspects:
        assert a.body1 in known and a.body2 in known
        assert a.body1 != a.body2
        assert a.aspect in MAJOR_ASPECTS
        assert abs(a.deviation) <= DEFAULT_ORBS[a.aspect] + 1e-9
        assert a.phase in ("applying", "separating", "exact", "unknown")
        key = (a.body1, a.body2)
        assert key not in pairs, f"duplicate aspect pair {key}"
        pairs.add(key)
    assert len(west.aspects) > 0                     # a real chart always has some
    devs = [abs(a.deviation) for a in west.aspects]
    assert devs == sorted(devs)                       # tightest first


@needs_swe
def test_angle_aspects_report_unknown_phase():
    eng = TimeEngine()
    snap = eng.resolve(dt.datetime(1991, 5, 14, 8, 30), 35.2, -80.8, "America/New_York")
    angled = [a for a in snap.western.aspects if a.body1 in ("ascendant", "mc")]
    assert angled, "expected at least one aspect involving a chart angle"
    assert all(a.phase == "unknown" for a in angled)  # angles carry no speed


def test_degraded_path_reports_no_depth_explicitly(monkeypatch):
    monkeypatch.setattr(ephem, "HAS_SWE", False)
    w = chart_positions(jd_from_datetime(dt.datetime(2026, 6, 1, 12, 0, tzinfo=UTC)),
                        40.7, -74.0)
    assert w["degraded"] is True
    assert w["speeds"] is None and w["retrograde"] is None
    assert w["north_node"] is None and w["node_kind"] is None
    assert w["aspects"] == []
    assert "no speeds" in w["note"]


def test_api_resolve_includes_western_depth():
    if not ephem.HAS_SWE:
        pytest.skip("depth fields require pyswisseph")
    client = TestClient(app)
    r = client.post("/resolve", json={"dt": "1991-05-14T08:30:00",
                                      "lat": 35.2, "lon": -80.8,
                                      "tz": "America/New_York"})
    assert r.status_code == 200
    west = r.json()["western"]
    assert set(west["speeds"]) == set(PLANETS)
    assert set(west["retrograde"]) == set(PLANETS)
    assert west["node_kind"] == "true"
    assert isinstance(west["aspects"], list) and west["aspects"]
