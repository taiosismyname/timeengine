# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""24 solar terms via root-finding on apparent solar longitude.

Each term is the Sun crossing a multiple of 15 deg. Lichun (315 deg) starts the
BaZi year; the 12 'jie' terms start the BaZi months. No lookup tables: the Chinese
layer and the Western layer share one ephemeris by construction.
"""
from __future__ import annotations
from functools import lru_cache
from . import ephem

TERMS_24 = [
    (315, "lichun", "立春", True), (330, "yushui", "雨水", False),
    (345, "jingzhe", "惊蛰", True), (0, "chunfen", "春分", False),
    (15, "qingming", "清明", True), (30, "guyu", "谷雨", False),
    (45, "lixia", "立夏", True), (60, "xiaoman", "小满", False),
    (75, "mangzhong", "芒种", True), (90, "xiazhi", "夏至", False),
    (105, "xiaoshu", "小暑", True), (120, "dashu", "大暑", False),
    (135, "liqiu", "立秋", True), (150, "chushu", "处暑", False),
    (165, "bailu", "白露", True), (180, "qiufen", "秋分", False),
    (195, "hanlu", "寒露", True), (210, "shuangjiang", "霜降", False),
    (225, "lidong", "立冬", True), (240, "xiaoxue", "小雪", False),
    (255, "daxue", "大雪", True), (270, "dongzhi", "冬至", False),
    (285, "xiaohan", "小寒", True), (300, "dahan", "大寒", False),
]
JIE_ANGLES = [a for a, _, _, is_jie in TERMS_24 if is_jie]  # month boundaries, in order

def _angdiff(jd: float, target: float) -> float:
    return (ephem.solar_apparent_longitude(jd) - target + 180.0) % 360.0 - 180.0

def find_term_jd(angle: float, gregorian_year: int) -> float:
    """JD (UT) when the Sun crosses `angle` near Gregorian `gregorian_year`. Bisection to ~0.1s."""
    jd0 = (2451545.0 + (gregorian_year - 2000) * 365.2422
           + ((angle - 280.0) % 360.0) / 360.0 * 365.2422)
    prev_jd, prev_d = None, None
    for i in range(-14, 15):
        jd = jd0 + i
        d = _angdiff(jd, angle)
        if prev_d is not None and prev_d < 0 <= d and abs(d - prev_d) < 30:
            lo, hi = prev_jd, jd
            for _ in range(60):
                mid = (lo + hi) / 2
                if _angdiff(mid, angle) < 0:
                    lo = mid
                else:
                    hi = mid
            return (lo + hi) / 2
        prev_jd, prev_d = jd, d
    raise RuntimeError(f"solar term {angle} deg not bracketed near {gregorian_year}")

@lru_cache(maxsize=64)
def terms_for_year(year: int) -> tuple:
    """All 24 terms for a Gregorian year, as (angle, slug, hanzi, is_jie, jd_ut)."""
    out = []
    for angle, slug, hanzi, is_jie in TERMS_24:
        out.append((angle, slug, hanzi, is_jie, find_term_jd(angle, year)))
    return tuple(out)

@lru_cache(maxsize=64)
def jie_terms_spanning(year: int) -> tuple:
    """The 12 jie (month-start) terms for year-1..year+1, sorted by jd, as (angle, jd_ut, month_index)."""
    order = JIE_ANGLES  # lichun=0 ... xiaohan=11
    out = []
    for y in (year - 1, year, year + 1):
        for m_idx, angle in enumerate(order):
            out.append((angle, find_term_jd(angle, y), m_idx))
    return tuple(sorted(out, key=lambda t: t[1]))
