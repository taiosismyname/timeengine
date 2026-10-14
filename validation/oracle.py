# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Independent oracle built on Skyfield + JPL DE421 (1900-2050).

Deliberately shares no code with the engine: different ephemeris (JPL DE421 vs Swiss
Moshier), different time scale handling, own root finder, and its own derivations of
equation of time, ascendant/MC and the Chinese lunisolar calendar.
"""
from __future__ import annotations
import os
import numpy as np
import skyfield_data
from skyfield.api import Loader
from skyfield.nutationlib import iau2000b_radians
from skyfield import almanac

_DATA = os.path.join(os.path.dirname(skyfield_data.__file__), "data")
_L = Loader(_DATA, verbose=False)
EPH = _L("de421.bsp")
TS = _L.timescale()
EARTH = EPH["earth"]

BODIES = {
    "sun": "sun", "moon": "moon", "mercury": "mercury barycenter",
    "venus": "venus barycenter", "mars": "mars barycenter",
    "jupiter": "jupiter barycenter", "saturn": "saturn barycenter",
    "uranus": "uranus barycenter", "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}
JD_1901 = 2415385.5   # 1901-01-01
JD_2049 = 2469807.5   # 2049-01-01

def _t(jd_ut):
    return TS.ut1_jd(np.atleast_1d(np.asarray(jd_ut, dtype=float)))

def apparent_longitude(body: str, jd_ut) -> np.ndarray:
    """Apparent geocentric ecliptic longitude of date, degrees."""
    t = _t(jd_ut)
    app = EARTH.at(t).observe(EPH[BODIES[body]]).apparent()
    return app.ecliptic_latlon(epoch="date")[1].degrees % 360.0

def apparent_solar_time_hours(jd_ut, lon_east_deg) -> np.ndarray:
    """Local apparent solar time (hours, 0-24) from Greenwich apparent sidereal time
    and the Sun's apparent right ascension -- no equation-of-time series involved."""
    t = _t(jd_ut)
    ra, _, _ = EARTH.at(t).observe(EPH["sun"]).apparent().radec(epoch="date")
    return (t.gast - ra.hours + 12.0 + np.asarray(lon_east_deg) / 15.0) % 24.0

def equation_of_time_minutes(jd_ut) -> np.ndarray:
    """Apparent minus mean solar time (minutes), from sidereal time and apparent RA."""
    jd_ut = np.atleast_1d(np.asarray(jd_ut, dtype=float))
    ut_hours = ((jd_ut + 0.5) % 1.0) * 24.0
    app = apparent_solar_time_hours(jd_ut, 0.0)
    d = (app - ut_hours + 12.0) % 24.0 - 12.0
    return d * 60.0

def true_obliquity_rad(jd_ut) -> np.ndarray:
    t = _t(jd_ut)
    T = (t.tt - 2451545.0) / 36525.0
    eps0 = (84381.406 - 46.836769 * T - 0.0001831 * T**2 + 0.00200340 * T**3
            - 0.000000576 * T**4 - 0.0000000434 * T**5) / 3600.0
    _, deps = iau2000b_radians(t)
    return np.radians(eps0) + deps

def asc_mc(jd_ut, lat_deg, lon_east_deg):
    """Ascendant and Midheaven (degrees) from RAMC and the true obliquity."""
    t = _t(jd_ut)
    ramc = np.radians((t.gast * 15.0 + np.asarray(lon_east_deg)) % 360.0)
    eps = true_obliquity_rad(jd_ut)
    phi = np.radians(np.asarray(lat_deg))
    asc = np.degrees(np.arctan2(np.cos(ramc),
                                -(np.sin(ramc) * np.cos(eps) + np.tan(phi) * np.sin(eps)))) % 360.0
    mc = np.degrees(np.arctan2(np.sin(ramc), np.cos(ramc) * np.cos(eps))) % 360.0
    return asc, mc

def solar_term_roots(angles, years) -> np.ndarray:
    """JD(UT) at which the apparent Sun first reaches each angle after 1 Jan of each year.
    Vectorised bisection; returns shape (len(years), len(angles))."""
    years = np.asarray(years, dtype=int)
    angles = np.asarray(angles, dtype=float)
    jan1 = np.array([TS.utc(int(y), 1, 1).ut1 for y in years])
    lam0 = apparent_longitude("sun", jan1)
    deg = (angles[None, :] - lam0[:, None]) % 360.0
    lo = jan1[:, None] + deg / 1.03 - 1.0
    hi = jan1[:, None] + deg / 0.94 + 1.0
    target = np.broadcast_to(angles[None, :], lo.shape)
    for _ in range(50):
        mid = (lo + hi) / 2.0
        lam = apparent_longitude("sun", mid.ravel()).reshape(mid.shape)
        below = ((lam - target + 180.0) % 360.0 - 180.0) < 0
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
    return (lo + hi) / 2.0

# ---- Chinese lunisolar calendar from astronomy ---------------------------------

def _cst_jdn(jd_ut) -> np.ndarray:
    """Integer day number of the China Standard Time (UTC+8) calendar date."""
    return np.floor(np.asarray(jd_ut) + 0.5 + 8.0 / 24.0).astype(int)

def lunisolar_months(first_year: int, last_year: int):
    """Return (start_jdn, lunar_year, lunar_month, is_leap) arrays for every complete
    lunar month between month 11 of lunar year first_year-1 and month 10 of last_year.

    Rules: months start on the CST date of the new moon; the month containing the
    winter solstice is month 11; a year of 13 months gets a leap month = the first
    month after month 11 containing no zhongqi (Sun at a multiple of 30 deg)."""
    t0 = TS.utc(first_year - 1, 10, 1); t1 = TS.utc(last_year + 1, 6, 1)
    t, ph = almanac.find_discrete(t0, t1, almanac.moon_phases(EPH))
    nm = _cst_jdn(t[ph == 0].ut1)                           # new-moon CST dates
    yrs = list(range(first_year - 1, last_year + 2))
    zq = solar_term_roots(np.arange(0, 360, 30), yrs)       # zhongqi, JD UT
    zq_jdn = _cst_jdn(zq)                                   # (years, 12)
    sol_jdn = _cst_jdn(solar_term_roots([270.0], yrs)[:, 0])  # winter solstices
    allzq = np.sort(zq_jdn.ravel())
    n = len(nm) - 1
    has_zq = np.array([np.any((allzq >= nm[i]) & (allzq < nm[i + 1])) for i in range(n)])
    has_sol = np.array([np.any((sol_jdn >= nm[i]) & (sol_jdn < nm[i + 1])) for i in range(n)])
    m11 = np.flatnonzero(has_sol)
    starts, lyears, lmonths, leaps = [], [], [], []
    for a, b in zip(m11[:-1], m11[1:]):
        seg = list(range(a, b))
        leap_idx = None
        if len(seg) == 13:
            leap_idx = next(j for j in seg[1:] if not has_zq[j])
        num, rows = 11, []
        for j in seg:
            if j == a:
                rows.append((j, 11, False))
            elif j == leap_idx:
                rows.append((j, num, True))
            else:
                num = num % 12 + 1
                rows.append((j, num, False))
        # lunar year number = Gregorian year of this segment's month 1
        m1 = next(j for j, mm, lp in rows if mm == 1 and not lp)
        gy = int(_jdn_to_year(nm[m1]))
        for j, mm, lp in rows:
            starts.append(nm[j]); lmonths.append(mm); leaps.append(lp)
            lyears.append(gy - 1 if mm in (11, 12) else gy)
    return (np.array(starts), np.array(lyears), np.array(lmonths), np.array(leaps))

def _jdn_to_year(jdn: int) -> int:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    month = m + 3 - 12 * (m // 10)
    return 100 * b + d - 4800 + m // 10

def lookup_lunar(tables, jdn: int):
    starts, lyears, lmonths, leaps = tables
    i = int(np.searchsorted(starts, jdn, side="right")) - 1
    if i < 0 or i >= len(starts) - 1:
        return None
    return (int(lyears[i]), int(lmonths[i]), int(jdn - starts[i] + 1), bool(leaps[i]))
