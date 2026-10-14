# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Run every validation sweep and write VALIDATION_REPORT.md.

    pip install -r requirements-validation.txt
    python -m validation.run_report
"""
from __future__ import annotations
import datetime as dt, pathlib, platform
from timeengine import ephem
from . import sweeps

def _row(label, s, unit):
    return f"| {label} | {s['n']} | {s['mean']:.4f} | {s['p99']:.4f} | {s['max']:.4f} | {unit} |"

def main(path="VALIDATION_REPORT.md"):
    r = sweeps.run_all()
    L = [f"# TimeEngine validation report", "",
         f"Generated {dt.date.today()} | ephemeris mode: **{ephem.ephemeris_mode()}** | "
         f"Python {platform.python_version()} | seed {sweeps.SEED}", "",
         "Oracle: Skyfield + JPL DE421 (1900-2050). It shares no ephemeris, root finder or "
         "formula code with the engine. Range: 1901-2049.", "",
         "## Numeric agreement", "", "| Check | n | mean | p99 | max | unit |", "|---|---|---|---|---|---|"]
    for p, s in r["planets"].items():
        L.append(_row(f"{p} apparent longitude", s, "arcsec"))
    L.append(_row("24 solar terms (time of crossing)", r["solar_terms"], "seconds"))
    L.append(_row("equation of time", r["equation_of_time"], "minutes"))
    L.append(_row("ascendant", r["ascendant_mc"]["ascendant"], "arcsec"))
    L.append(_row("midheaven", r["ascendant_mc"]["mc"], "arcsec"))
    L.append(_row("luck-pillar start distance (to adjacent jie term)", r["luck_start"], "seconds"))
    tst = r["true_solar_time"]
    L.append(_row("true solar time (14 cities, historical tz)", tst, "minutes"))
    L += ["", f"Largest true-solar-time gap: {tst['worst_case']}.", "",
          "## Discrete agreement", ""]
    b = r["bazi_year_month"]
    L.append(f"- BaZi year and month pillars vs the Sun's JPL longitude: {b['n']} random instants, "
             f"**{b['bad_month']} month mismatches, {b['bad_year']} year mismatches**.")
    lc = r["lunar_calendar"]
    L.append(f"- Chinese lunar calendar, engine's zhdate vs an astronomical calendar built from "
             f"JPL new moons and solar terms: **{lc['mismatches']['modern']} mismatches in "
             f"{lc['days']['modern']} days (1929-2048)**; {lc['mismatches']['early']} mismatches in "
             f"{lc['days']['early']} days (1901-1928).")
    if lc["examples"]:
        L.append("  First early-era differences (date, zhdate, astronomical): "
                 + "; ".join(f"{d} {m} vs {a}" for d, m, a in lc["examples"][:3]))
    L += ["", "## What this does and does not prove", "",
          "- Proves: the astronomy (positions, solar terms, equation of time, angles, true solar "
          "time) and the year/month pillar boundaries agree with an independent source to the "
          "precision shown.",
          "- Does not prove: school conventions (zi hour, day boundary, which clock to read) are "
          "the ones a given practitioner expects; those need practitioner review.",
          "- Does not prove: tz-database offsets (trusted, shared with the oracle) or dates outside "
          "1901-2049 (DE421 range).",
          "- The 1901-1928 lunar differences are consistent with that era's calendar using a "
          "different time standard than UTC+8; this is the likely cause, not a verified one."]
    pathlib.Path(path).write_text("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
