# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Western tropical chart. Full planet set via pyswisseph when present;
degrades to Sun-only with an explicit flag otherwise (never silent).

House systems are requested by name and resolved through a fallback chain: Placidus
is undefined above the polar circle, so a birth there is served by a system that is
defined at every latitude and the substitution is reported in `house_system_used` /
`houses_degraded`. A fallback is never silent.
"""
from __future__ import annotations
from . import ephem
from .aspects import compute_aspects, is_retrograde

PLANETS = ["sun", "moon", "mercury", "venus", "mars",
           "jupiter", "saturn", "uranus", "neptune", "pluto"]

# Swiss Ephemeris house-system codes.
HOUSE_SYSTEMS = {
    "placidus": b"P",
    "whole_sign": b"W",
    "porphyry": b"O",
    "equal": b"A",
}

DEFAULT_FALLBACKS = ("porphyry", "whole_sign", "equal")

# Bodies that participate in aspects: the ten planets plus the chart angles and
# the north node. The south node is excluded on purpose: it always sits exactly
# opposite the north node, so aspecting it would duplicate every nodal aspect.
ASPECT_BODIES = ("ascendant", "mc", "north_node")


def _resolve_houses(swe, jd_ut, lat, lon, flag, requested, fallbacks):
    """Try the requested system, then each fallback. Returns (cusps, ascmc, used, degraded)."""
    for name in (requested, *fallbacks):
        code = HOUSE_SYSTEMS.get(name)
        if code is None:
            continue
        try:
            cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, code, flag)
            return list(cusps), ascmc, name, name != requested
        except Exception:
            continue  # e.g. Placidus above the polar circle
    return None, None, None, True


def chart_positions(jd_ut: float, lat: float, lon: float,
                    house_system: str = "placidus",
                    house_fallbacks=DEFAULT_FALLBACKS,
                    node: str = "true") -> dict:
    """Full Western chart with depth: speeds, retrograde, nodes, aspects.

    `node` selects the lunar node: "true" (default, standard in modern Western
    practice) or "mean" (always retrograde, steadier). Speeds are geocentric
    ecliptic-longitude rates in degrees/day, read from the same ephemeris call
    as the positions, so they can never disagree with them.
    """
    if ephem.HAS_SWE:
        swe = ephem.swe
        # FLG_SPEED is required for calc_ut to return speeds; without it the
        # speed slots come back as 0. Positions are unaffected by the flag.
        flag = ephem._flag() | swe.FLG_SPEED
        ids = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
               swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]
        calc = [swe.calc_ut(jd_ut, pid, flag)[0] for pid in ids]
        pos = {name: c[0] % 360.0 for name, c in zip(PLANETS, calc)}
        speeds = {name: c[3] for name, c in zip(PLANETS, calc)}
        node_id = swe.TRUE_NODE if node == "true" else swe.MEAN_NODE
        ncalc = swe.calc_ut(jd_ut, node_id, flag)[0]
        north_node, node_speed = ncalc[0] % 360.0, ncalc[3]
        cusps, ascmc, used, degraded = _resolve_houses(
            swe, jd_ut, lat, lon, flag, house_system, house_fallbacks)
        out: dict = {"degraded": False, "positions": pos, "speeds": speeds,
                     "retrograde": {n: is_retrograde(s) for n, s in speeds.items()},
                     "north_node": north_node,
                     "south_node": (north_node + 180.0) % 360.0,
                     "node_kind": node,
                     "house_system_used": used, "houses_degraded": degraded}
        points = dict(pos)
        point_speeds = dict(speeds)
        if cusps is not None:
            out["ascendant"] = ascmc[0] % 360.0
            out["mc"] = ascmc[1] % 360.0
            out["house_cusps"] = cusps
            points["ascendant"] = out["ascendant"]
            points["mc"] = out["mc"]
            # Angles have no ephemeris speed; their aspects report phase "unknown".
        else:
            out["note"] = ("no supported house system is defined at this latitude; "
                           "houses and angles omitted")
        points["north_node"] = north_node
        point_speeds["north_node"] = node_speed
        out["aspects"] = compute_aspects(points, point_speeds)
        return out
    return {"degraded": True,
            "note": ("pyswisseph not installed; Sun-only analytic fallback, "
                     "no speeds, retrograde, nodes or aspects"),
            "positions": {"sun": ephem.solar_apparent_longitude(jd_ut)},
            "speeds": None, "retrograde": None,
            "north_node": None, "south_node": None, "node_kind": None,
            "aspects": []}
