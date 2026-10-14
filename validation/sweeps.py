# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Validation sweeps: run the engine against the independent oracle and return stats.

Every sweep is seeded, so a run is reproducible. Used by tests/test_validation.py (pass/fail
thresholds) and run_report.py (human-readable report).
"""
from __future__ import annotations
import datetime as dt
from functools import lru_cache
from zoneinfo import ZoneInfo
import numpy as np

from timeengine import ephem
from timeengine.bazi import four_pillars, MeridianPolicy, pillar_from_index
from timeengine.cal import jd_from_datetime
from timeengine.solar_terms import TERMS_24, find_term_jd
from timeengine.western import chart_positions, PLANETS
from . import oracle as o

SEED = 20261004
UTC = dt.timezone.utc

def _stats(err):
    err = np.abs(np.asarray(err, dtype=float))
    return {"n": int(err.size), "max": float(err.max()), "mean": float(err.mean()),
            "p99": float(np.percentile(err, 99))}

def _wrap_deg(d):
    return (np.asarray(d) + 180.0) % 360.0 - 180.0

def _jds(n, rng):
    return rng.uniform(o.JD_1901, o.JD_2049, n)

def planets(n=300):
    """Engine (Swiss/Moshier) vs JPL DE421: apparent geocentric longitude, arcseconds."""
    rng = np.random.default_rng(SEED)
    jds = _jds(n, rng)
    eng = {p: [] for p in PLANETS}
    for jd in jds:
        pos = chart_positions(float(jd), 0.0, 0.0)["positions"]
        for p in PLANETS:
            eng[p].append(pos[p])
    return {p: _stats(_wrap_deg(np.array(eng[p]) - o.apparent_longitude(p, jds)) * 3600.0)
            for p in PLANETS}

def solar_terms(step=4):
    """All 24 terms, every `step` years: engine root-find vs oracle bisection, seconds."""
    years = list(range(1901, 2049, step))
    angles = [a for a, *_ in TERMS_24]
    truth = o.solar_term_roots(angles, years)
    errs = []
    for i, y in enumerate(years):
        for j, a in enumerate(angles):
            errs.append((find_term_jd(float(a), y) - truth[i, j]) * 86400.0)
    return _stats(errs)

def equation_of_time(n=500):
    rng = np.random.default_rng(SEED + 1)
    jds = _jds(n, rng)
    mine = np.array([ephem.equation_of_time_minutes(float(j)) for j in jds])
    return _stats(mine - o.equation_of_time_minutes(jds))

def ascendant_mc(n=400, max_lat=60.0):
    """Ascendant/MC (Placidus-capable latitudes) vs independent RAMC/obliquity formulas, arcsec."""
    rng = np.random.default_rng(SEED + 2)
    jds = _jds(n, rng)
    lats = rng.uniform(-max_lat, max_lat, n); lons = rng.uniform(-180, 180, n)
    asc_e, mc_e = [], []
    for jd, la, lo in zip(jds, lats, lons):
        w = chart_positions(float(jd), float(la), float(lo))
        asc_e.append(w["ascendant"]); mc_e.append(w["mc"])
    asc_o, mc_o = o.asc_mc(jds, lats, lons)
    return {"ascendant": _stats(_wrap_deg(np.array(asc_e) - asc_o) * 3600.0),
            "mc": _stats(_wrap_deg(np.array(mc_e) - mc_o) * 3600.0)}

CITIES = [  # name, lat, lon(E), IANA tz
    ("Charlotte", 35.2271, -80.8431, "America/New_York"), ("London", 51.5074, -0.1278, "Europe/London"),
    ("Shanghai", 31.2304, 121.4737, "Asia/Shanghai"), ("Urumqi", 43.8256, 87.6168, "Asia/Urumqi"),
    ("Mumbai", 19.0760, 72.8777, "Asia/Kolkata"), ("Sydney", -33.8688, 151.2093, "Australia/Sydney"),
    ("Lagos", 6.5244, 3.3792, "Africa/Lagos"), ("Sao Paulo", -23.5505, -46.6333, "America/Sao_Paulo"),
    ("Honolulu", 21.3069, -157.8583, "Pacific/Honolulu"), ("Reykjavik", 64.1466, -21.9426, "Atlantic/Reykjavik"),
    ("Tokyo", 35.6762, 139.6503, "Asia/Tokyo"), ("Mexico City", 19.4326, -99.1332, "America/Mexico_City"),
    ("Cape Town", -33.9249, 18.4241, "Africa/Johannesburg"), ("Los Angeles", 34.0522, -118.2437, "America/Los_Angeles"),
]

def true_solar_time(per_city=60):
    """End to end: engine TRUE_SOLAR effective time vs oracle local apparent solar time, minutes.
    Shares only the tz-database offset (dt -> UTC) with the engine; tzdata itself is trusted."""
    rng = np.random.default_rng(SEED + 3)
    errs, worst = [], (0.0, None)
    for name, lat, lon, tz in CITIES:
        zi = ZoneInfo(tz)
        for _ in range(per_city):
            jd = float(rng.uniform(o.JD_1901 + 1, o.JD_2049 - 1))
            utc = dt.datetime(2000, 1, 1, 12, tzinfo=UTC) + dt.timedelta(days=jd - 2451545.0)
            local = utc.astimezone(zi).replace(microsecond=0)
            naive = local.replace(tzinfo=None)
            if naive.replace(tzinfo=zi).astimezone(UTC) != local.astimezone(UTC):
                continue   # ambiguous / non-existent wall time
            r = four_pillars(naive, lat, lon, tz, meridian=MeridianPolicy.TRUE_SOLAR)
            eff = dt.datetime.fromisoformat(r["effective_time"])
            eng_h = eff.hour + eff.minute / 60 + eff.second / 3600 + eff.microsecond / 3.6e9
            jd_exact = jd_from_datetime(naive.replace(tzinfo=zi).astimezone(UTC))
            ref_h = float(o.apparent_solar_time_hours(jd_exact, lon)[0])
            d = ((eng_h - ref_h + 12.0) % 24.0 - 12.0) * 60.0
            errs.append(d)
            if abs(d) > worst[0]:
                worst = (abs(d), f"{name} {naive}")
    s = _stats(errs); s["worst_case"] = worst[1]
    return s

def bazi_year_month(n=1500):
    """Year and month pillars vs the Sun's JPL longitude. Returns mismatch counts."""
    rng = np.random.default_rng(SEED + 4)
    jds = _jds(n, rng)
    lam = o.apparent_longitude("sun", jds)
    bad_month = bad_year = 0; examples = []
    for jd, l in zip(jds, lam):
        utc = dt.datetime(2000, 1, 1, 12, tzinfo=UTC) + dt.timedelta(days=float(jd) - 2451545.0)
        r = four_pillars(utc, 0.0, 0.0, "UTC")
        month_idx = int(((l - 315.0) % 360.0) // 30)
        if r["month"].branch != (2 + month_idx) % 12:
            bad_month += 1; examples.append(("month", str(utc)))
        before_lichun = utc.month <= 2 and 270.0 <= l < 315.0
        gy = utc.year - 1 if before_lichun else utc.year
        if r["year"].index != (gy - 4) % 60:
            bad_year += 1; examples.append(("year", str(utc)))
    return {"n": n, "bad_month": bad_month, "bad_year": bad_year, "examples": examples[:5]}

@lru_cache(maxsize=1)
def _lunar_tables():
    return o.lunisolar_months(1901, 2049)

def lunar_calendar(start_year=1901, end_year=2048):
    """Every day start_year..end_year: zhdate (what the engine uses) vs the oracle's
    astronomical Chinese calendar. Returns mismatch counts split before/after 1929."""
    from zhdate import ZhDate
    tabs = _lunar_tables()
    d0 = dt.date(start_year, 1, 1); d1 = dt.date(end_year, 12, 31)
    total = {"early": 0, "modern": 0}; bad = {"early": 0, "modern": 0}; examples = []
    d = d0
    while d <= d1:
        jdn = d.toordinal() + 1721425
        ref = o.lookup_lunar(tabs, jdn)
        if ref is not None:
            z = ZhDate.from_datetime(dt.datetime(d.year, d.month, d.day))
            mine = (z.lunar_year, z.lunar_month, z.lunar_day, bool(z.leap_month))
            era = "early" if d.year < 1929 else "modern"
            total[era] += 1
            if mine != ref:
                bad[era] += 1
                if len(examples) < 6:
                    examples.append((str(d), mine, ref))
        d += dt.timedelta(days=1)
    return {"days": total, "mismatches": bad, "examples": examples}

def luck_start(n=300):
    """Luck-pillar start distance (days to the adjacent jie term) vs oracle jie crossings."""
    from timeengine import TimeEngine
    from timeengine.solar_terms import JIE_ANGLES
    import numpy as np
    rng = np.random.default_rng(SEED + 5)
    eng = TimeEngine(); errs = []
    years = list(range(1900, 2051))
    roots = o.solar_term_roots(JIE_ANGLES, years)            # (years, 12) JD UT
    flat = np.sort(roots.ravel())
    for jd in _jds(n, rng):
        utc = dt.datetime(2000, 1, 1, 12, tzinfo=UTC) + dt.timedelta(days=float(jd) - 2451545.0)
        luck = eng.resolve(utc, 0.0, 0.0, "UTC").bazi_depth.luck
        nxt = flat[flat > jd].min() - jd; prv = jd - flat[flat <= jd].max()
        for l in luck:
            ref = nxt if l.direction == "forward" else prv
            errs.append((l.start_age_days - ref) * 86400.0)   # seconds
    return _stats(errs)

def run_all():
    return {"planets": planets(), "solar_terms": solar_terms(), "equation_of_time": equation_of_time(),
            "ascendant_mc": ascendant_mc(), "true_solar_time": true_solar_time(),
            "bazi_year_month": bazi_year_month(), "luck_start": luck_start(), "lunar_calendar": lunar_calendar()}
