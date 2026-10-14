# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Solar longitude + equation of time with a deterministic fallback chain.

Chain: swiseph data files -> Moshier (pyswisseph builtin) -> analytic Meeus low-precision.
The analytic fallback exists so the core logic is testable with zero binary deps;
in production pyswisseph is installed and the flag is chosen EXPLICITLY, never silently.
"""
from __future__ import annotations
import math, os
from pathlib import Path

try:
    import swisseph as swe
    HAS_SWE = True
except ImportError:
    swe = None
    HAS_SWE = False

EPHE_PATH = os.environ.get("SWISSEPH_PATH", "")

def ephemeris_mode() -> str:
    if HAS_SWE:
        if EPHE_PATH and Path(EPHE_PATH).exists():
            return "swiseph"
        return "moshier"
    return "analytic"

def _flag() -> int:
    if ephemeris_mode() == "swiseph":
        swe.set_ephe_path(EPHE_PATH)
        return swe.FLG_SWIEPH
    return swe.FLG_MOSEPH

def solar_apparent_longitude(jd_ut: float) -> float:
    """Apparent geocentric ecliptic longitude of the Sun, degrees [0, 360)."""
    if HAS_SWE:
        return swe.calc_ut(jd_ut, swe.SUN, _flag())[0][0] % 360.0
    # Meeus low-precision (~0.01 deg): fine for tests, NOT for production charts.
    T = (jd_ut - 2451545.0) / 36525.0
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360.0
    M = math.radians((357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360.0)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M)
         + 0.000289 * math.sin(3 * M))
    omega = math.radians(125.04 - 1934.136 * T)
    return (L0 + C - 0.00569 - 0.00478 * math.sin(omega)) % 360.0

def equation_of_time_minutes(jd_ut: float) -> float:
    """Apparent solar time minus mean solar time, in minutes (NOAA series)."""
    T = (jd_ut - 2451545.0) / 36525.0
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    M = math.radians((357.52911 + T * (35999.05029 - 0.0001537 * T)) % 360.0)
    L0 = math.radians((280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360.0)
    eps = math.radians(23 + (26 + (21.448 - T * (46.815 + T * (0.00059 - T * 0.001813))) / 60) / 60)
    y = math.tan(eps / 2) ** 2
    E = (y * math.sin(2 * L0) - 2 * e * math.sin(M)
         + 4 * e * y * math.sin(M) * math.cos(2 * L0)
         - 0.5 * y * y * math.sin(4 * L0) - 1.25 * e * e * math.sin(2 * M))
    return math.degrees(E) * 4.0
