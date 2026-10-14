# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""BaZi (Four Pillars) with an explicit, configurable time frame.

Three documented enums make every silent convention explicit and reproducible:
- ZiHourRule: when the DAY pillar flips (23:00 vs 00:00), and which day's stem the
  23:00-24:00 hour uses. Three schools, all valid:
    DAY_FLIPS_AT_23 - day pillar advances at 23:00; hour stem from the NEW day.
    DAY_FLIPS_AT_00 - day pillar advances at 00:00; 23:00 hour uses the SAME day stem.
    LATE_ZI         - day pillar advances at 00:00 (like _AT_00), but the 23:00-24:00
                      hour stem is drawn from the NEXT day. The documented "late zi"
                      school.
- MeridianPolicy: what time the hour pillar is read from.
    TRUE_SOLAR     - civil clock + equation of time + longitude correction vs the
                     birth timezone's own meridian. This is physical true solar time.
    STANDARD_TIME  - the civil clock with daylight saving removed, no longitude
                     correction. The "standard time" school. (0.2.0 left DST in;
                     fixed in 0.2.1. Was mislabelled BEIJING before that.)
    CIVIL_CLOCK    - the clock exactly as displayed, DST included, no correction.
- DayBoundary: which calendar date the DAY pillar's 60-day cycle is read from.
    SOLAR          - the adjusted time used for the pillars (default).
    CLOCK          - the birth civil clock date.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

from .cal import jdn_from_date, jd_from_datetime
from .ephem import equation_of_time_minutes
from .solar_terms import find_term_jd, jie_terms_spanning

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
DAY_ANCHOR_JDN = jdn_from_date(1949, 10, 1)  # 1949-10-01 (PRC founding) was a 甲子 day.


class ZiHourRule(str, Enum):
    DAY_FLIPS_AT_23 = "day_flips_at_23"
    DAY_FLIPS_AT_00 = "day_flips_at_00"
    LATE_ZI = "late_zi"


class MeridianPolicy(str, Enum):
    TRUE_SOLAR = "true_solar"          # physical true solar time
    STANDARD_TIME = "standard_time"    # civil clock minus DST; no longitude correction
    CIVIL_CLOCK = "civil_clock"        # civil clock exactly as displayed, DST included
    # Deprecated alias kept so callers using the old name get the corrected policy.
    BEIJING = "standard_time"


class DayBoundary(str, Enum):
    SOLAR = "solar"    # day pillar date read from the adjusted (pillar) time
    CLOCK = "clock"    # day pillar date read from the birth civil clock date


@dataclass(frozen=True)
class Pillar:
    stem: int
    branch: int
    index: int
    label: str


def make_pillar(stem: int, branch: int) -> Pillar:
    for k in range(60):
        if k % 10 == stem % 10 and k % 12 == branch % 12:
            return Pillar(stem % 10, branch % 12, k, STEMS[stem % 10] + BRANCHES[branch % 12])
    raise ValueError("stem/branch parity mismatch")


def pillar_from_index(k: int) -> Pillar:
    return make_pillar(k % 10, k % 12)


def _aware(dt: datetime, tz: str | None) -> datetime:
    if dt.tzinfo is not None:
        return dt
    if tz is None:
        raise ValueError("naive datetime requires tz=")
    return dt.replace(tzinfo=ZoneInfo(tz))


def _tst_frame(dt: datetime, tz: str | None, policy: MeridianPolicy) -> tuple[datetime, float | None]:
    """Return (civil datetime used, reference meridian degrees East or None).

    None means "apply no longitude correction" (the STANDARD_TIME school).
    """
    dt = _aware(dt, tz)
    if policy in (MeridianPolicy.STANDARD_TIME, MeridianPolicy.CIVIL_CLOCK):
        return dt, None
    off = dt.utcoffset()
    if off is None:
        raise ValueError("tz produced no utcoffset")
    return dt, off.total_seconds() / 240.0  # 240 s per degree


def adjusted_time(dt: datetime, lon: float, tz: str | None,
                  policy: MeridianPolicy) -> tuple[datetime, float]:
    """(time used for the pillars, correction in minutes relative to the civil clock).

    Under TRUE_SOLAR this is physical true solar time. Under STANDARD_TIME the clock
    has any daylight saving removed. Under CIVIL_CLOCK it is used unchanged.
    """
    civil, meridian = _tst_frame(dt, tz, policy)
    if meridian is None:
        if policy is MeridianPolicy.STANDARD_TIME:
            dst = civil.dst() or timedelta(0)
            return civil - dst, -dst.total_seconds() / 60.0
        return civil, 0.0
    jd_ut = jd_from_datetime(civil.astimezone(timezone.utc))
    corr = 4.0 * (lon - meridian) + equation_of_time_minutes(jd_ut)
    return civil + timedelta(minutes=corr), corr


def four_pillars(dt: datetime, lat: float, lon: float, tz: str | None = None,
                 zi_rule: ZiHourRule = ZiHourRule.DAY_FLIPS_AT_00,
                 meridian: MeridianPolicy = MeridianPolicy.TRUE_SOLAR,
                 day_boundary: DayBoundary = DayBoundary.SOLAR) -> dict:
    civil, _ = _tst_frame(dt, tz, meridian)
    jd_ut = jd_from_datetime(civil.astimezone(timezone.utc))
    eff, corr_min = adjusted_time(dt, lon, tz, meridian)

    # Year pillar: flips at Lichun (315 deg), NOT at Chinese New Year.
    lichun = find_term_jd(315.0, civil.year)
    ganzhi_year = civil.year if jd_ut >= lichun else civil.year - 1
    year_p = pillar_from_index((ganzhi_year - 4) % 60)

    # Month pillar: starts at the 12 jie terms; stem from year stem (五虎遁).
    month_idx = None
    for angle, term_jd, m_idx in jie_terms_spanning(civil.year):
        if term_jd <= jd_ut:
            month_idx = m_idx
    if month_idx is None:
        raise RuntimeError("no jie term precedes birth moment; span window too small")
    month_stem = ((year_p.stem % 5) * 2 + 2 + month_idx) % 10
    month_p = make_pillar(month_stem, 2 + month_idx)  # 寅 is branch 2

    # Day pillar: continuous 60-day cycle from the anchor. The calendar date comes
    # from either the adjusted (pillar) time or the civil clock, and the zi-hour rule
    # decides whether the cycle advances inside the 23:00-24:00 window.
    basis = eff if day_boundary is DayBoundary.SOLAR else civil
    day_jdn = jdn_from_date(basis.year, basis.month, basis.day)
    zi_window = (basis.hour + basis.minute / 60.0) >= 23.0
    eff_zi_window = (eff.hour + eff.minute / 60.0) >= 23.0
    # The day boundary and the hour pillar may be read from different clocks
    # (DayBoundary.CLOCK + TRUE_SOLAR). Report when they disagree near midnight.
    frame_conflict = (basis.date() != eff.date()) or (zi_window != eff_zi_window)
    if zi_rule is ZiHourRule.DAY_FLIPS_AT_23 and zi_window:
        day_jdn += 1
    day_p = pillar_from_index((day_jdn - DAY_ANCHOR_JDN) % 60)

    # Hour pillar: branch from the adjusted time; stem from the day stem (五鼠遁),
    # except the late-zi school, which draws the 23:00-24:00 stem from the NEXT day.
    h = (eff.hour + eff.minute / 60.0 + 1.0) % 24.0
    hour_branch = int(h // 2)
    hour_day_stem = day_p.stem
    if zi_rule is ZiHourRule.LATE_ZI and eff_zi_window:   # judged on the HOUR's own clock
        hour_day_stem = (day_p.stem + 1) % 10
    hour_stem = ((hour_day_stem % 5) * 2 + hour_branch) % 10
    hour_p = make_pillar(hour_stem, hour_branch)

    return {
        "year": year_p, "month": month_p, "day": day_p, "hour": hour_p,
        "effective_time": eff.isoformat(),
        "correction_minutes": round(corr_min, 2),
        "time_basis": meridian.value,
        "day_boundary": day_boundary.value,
        "frame_conflict": frame_conflict,
        "lichun_jd_ut": round(lichun, 5),
        "zi_hour_rule": zi_rule.value, "meridian_policy": meridian.value,
    }
