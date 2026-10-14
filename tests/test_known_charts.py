# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Pinned tests against known charts. With pyswisseph absent these run on the
analytic ephemeris (sun ~0.01 deg); assertions are chosen to be robust to that.
Each of the six v0.2.0 fixes has a regression test at the bottom."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from timeengine import (TimeEngine, RulesetConfig, ZiHourRule, MeridianPolicy,
                        DayBoundary)
from timeengine import ephem
from timeengine.bazi import four_pillars, pillar_from_index, DAY_ANCHOR_JDN
from timeengine.cal import jdn_from_date
from timeengine.numerology import expression_number, life_path, reduce_master
from timeengine.solar_terms import find_term_jd
from timeengine.cal import datetime_from_jd

BJ = "Asia/Shanghai"

def test_day_pillar_anchors():
    # 1949-10-01 (PRC founding) is a documented 甲子 day; 2000-01-01 is a documented 戊午 day.
    assert pillar_from_index((jdn_from_date(1949, 10, 1) - DAY_ANCHOR_JDN) % 60).label == "甲子"
    assert pillar_from_index((jdn_from_date(2000, 1, 1) - DAY_ANCHOR_JDN) % 60).label == "戊午"

def test_lichun_1984_boundary():
    # 1984 is the 甲子 year; Lichun fell on Feb 4 (evening, Beijing time).
    before = four_pillars(datetime(1984, 2, 3, 12, 0), 39.9, 116.4, BJ)
    after = four_pillars(datetime(1984, 2, 5, 12, 0), 39.9, 116.4, BJ)
    assert before["year"].label == "癸亥"
    assert after["year"].label == "甲子"
    assert after["month"].label == "丙寅"  # 甲 year -> first month stem 丙 (五虎遁)

def test_lichun_1984_date_is_feb_4_beijing():
    lichun = find_term_jd(315.0, 1984)
    bj = datetime_from_jd(lichun).astimezone(ZoneInfo(BJ))
    # Moshier already lands this on Feb 4, so the date is pinned, not a 3-day window.
    assert bj.month == 2 and bj.day == 4

def test_zi_hour_rule_is_explicit():
    dt = datetime(2000, 1, 15, 23, 30)
    r00 = four_pillars(dt, 0.0, 0.0, "UTC", zi_rule=ZiHourRule.DAY_FLIPS_AT_00)
    r23 = four_pillars(dt, 0.0, 0.0, "UTC", zi_rule=ZiHourRule.DAY_FLIPS_AT_23)
    assert r00["hour"].branch == 0 and r23["hour"].branch == 0  # both 子 hour
    assert (r23["day"].index - r00["day"].index) % 60 == 1      # day flips only under the 23:00 rule

def test_urumqi_true_solar_time_flips_hour_pillar():
    # Urumqi: lon 87.6E but tz meridian 120E -> correction ~ -2h07m + EoT.
    # Clock 14:00 is 未 (branch 7); true solar time ~11:53 is 午 (branch 6).
    # NB: 1985, not 1988 — China ran a DST experiment 1986-1991 (UTC+9), which
    # shifts the meridian to 135E and the branch to 巳. Historical tz data matters.
    r = four_pillars(datetime(1985, 6, 1, 14, 0), 43.8, 87.6, BJ,
                     meridian=MeridianPolicy.TRUE_SOLAR)
    assert r["hour"].branch == 6
    assert -131.0 < r["correction_minutes"] < -123.0

def test_pre1970_dst_new_york():
    # 1955-07-15 10:00 EDT: clock says 巳 (9-11); TST ~8:58 says 辰 (branch 4).
    r = four_pillars(datetime(1955, 7, 15, 10, 0), 40.7, -74.0,
                     "America/New_York", meridian=MeridianPolicy.TRUE_SOLAR)
    assert r["hour"].branch == 4

def test_numerology_masters_and_life_path():
    assert expression_number("Pal") == 11          # 7+1+3 = 11, master preserved
    assert reduce_master(31) == 4
    assert life_path(1991, 9, 11) == 4

def test_engine_cache_key_determinism_and_ruleset_sensitivity():
    eng = TimeEngine()
    dt = datetime(1991, 9, 11, 8, 30)
    a = eng.resolve(dt, 35.2, -80.8, "America/New_York", birth_name="Tai")
    b = eng.resolve(dt, 35.2, -80.8, "America/New_York", birth_name="Tai")
    assert a.cache_key == b.cache_key and a is b  # cached object returned
    eng2 = TimeEngine(RulesetConfig(zi_hour_rule=ZiHourRule.DAY_FLIPS_AT_23))
    c = eng2.resolve(dt, 35.2, -80.8, "America/New_York", birth_name="Tai")
    assert c.cache_key != a.cache_key             # ruleset is part of the hash
    eng3 = TimeEngine(RulesetConfig(day_boundary=DayBoundary.CLOCK))
    d = eng3.resolve(dt, 35.2, -80.8, "America/New_York", birth_name="Tai")
    assert d.cache_key != a.cache_key             # day_boundary is part of the hash too

def test_engine_snapshot_shape():
    eng = TimeEngine()
    snap = eng.resolve(datetime(1991, 9, 11, 8, 30), 35.2, -80.8,
                       "America/New_York", birth_name="Tai", chosen_name="Tai")
    d = snap.model_dump(mode="json")              # must be JSON-serializable
    assert d["bazi"]["year"]["label"] and len(d["solar_terms_year"]) == 24
    assert snap.ephemeris_mode in ("swiseph", "moshier", "analytic")
    assert snap.bazi.time_basis == "true_solar"
    assert snap.bazi.day_boundary == "solar"
    assert snap.western.house_system_used in ("placidus", "whole_sign", "porphyry",
                                              "equal", None)

# ---------------------------------------------------------------------------
# Regression tests for the six v0.2.0 fixes.
# ---------------------------------------------------------------------------

def test_fix1_cache_key_includes_names():
    """Two different names at the same moment/place must not share a cached snapshot."""
    eng = TimeEngine()
    dt = datetime(1991, 9, 11, 8, 30)
    a = eng.resolve(dt, 35.2, -80.8, "America/New_York", birth_name="Tai")
    b = eng.resolve(dt, 35.2, -80.8, "America/New_York", birth_name="Zebediah Quincy")
    assert a.cache_key != b.cache_key
    assert a is not b
    assert a.numerology.birth_name_expression != b.numerology.birth_name_expression

def test_fix2_lunar_uses_china_standard_time():
    """The lunar date is read in fixed UTC+8, not the UTC calendar date."""
    pytest.importorskip("zhdate")
    eng = TimeEngine()
    # Shanghai 2000-02-05 00:30 CST == 2000-02-04 16:30 UTC. The UTC date would read
    # lunar 1999-12-29; China Standard Time correctly reads lunar new year day 1.
    snap = eng.resolve(datetime(2000, 2, 5, 0, 30), 31.2, 121.5, "Asia/Shanghai")
    assert snap.lunar.degraded is False
    assert (snap.lunar.lunar_year, snap.lunar.lunar_month,
            snap.lunar.lunar_day) == (2000, 1, 1)
    # A New York evening birth is already the next day in China, so it is also day 1.
    ny = eng.resolve(datetime(2000, 2, 4, 22, 0), 40.7, -74.0, "America/New_York")
    assert (ny.lunar.lunar_year, ny.lunar.lunar_month, ny.lunar.lunar_day) == (2000, 1, 1)

def test_fix3_standard_time_is_not_true_solar():
    """STANDARD_TIME reads the clock and applies no longitude correction."""
    dt = datetime(2000, 6, 1, 14, 0)
    ts = four_pillars(dt, 43.8, 87.6, BJ, meridian=MeridianPolicy.TRUE_SOLAR)
    st = four_pillars(dt, 43.8, 87.6, BJ, meridian=MeridianPolicy.CIVIL_CLOCK)
    assert ts["hour"].branch == 6                 # 午, true solar ~11:53
    assert st["hour"].branch == 7                 # 未, clock 14:00
    assert st["correction_minutes"] == 0.0              # CIVIL_CLOCK
    assert ts["correction_minutes"] != 0.0
    # The old BEIJING name is an alias of the corrected policy.
    assert MeridianPolicy.BEIJING is MeridianPolicy.STANDARD_TIME

def test_fix3b_standard_time_is_stable_through_china_dst():
    """No spurious one-hour drift in the 1986-1991 China DST years."""
    for year in (1985, 1988, 1991, 1992):
        r = four_pillars(datetime(year, 6, 1, 14, 0), 43.8, 87.6, BJ,
                         meridian=MeridianPolicy.CIVIL_CLOCK)
        assert r["hour"].branch == 7              # clock 14:00 -> 未, every year
        assert r["correction_minutes"] == 0.0

def test_fix4_placidus_polar_fallback_is_flagged():
    if not ephem.HAS_SWE:
        pytest.skip("house systems require pyswisseph")
    eng = TimeEngine()
    polar = eng.resolve(datetime(1990, 6, 15, 12, 0), 69.65, 18.95, "Europe/Oslo")
    assert polar.western.degraded is False
    assert polar.western.house_system_used == "porphyry"     # not placidus
    assert polar.western.houses_degraded is True
    assert polar.western.house_cusps is not None             # still a usable chart
    normal = eng.resolve(datetime(1990, 6, 15, 12, 0), 40.7, -74.0, "America/New_York")
    assert normal.western.house_system_used == "placidus"
    assert normal.western.houses_degraded is False

def test_fix5_late_zi_keeps_day_but_borrows_next_stem():
    dt = datetime(2000, 1, 15, 23, 30)
    r00 = four_pillars(dt, 0.0, 0.0, "UTC", zi_rule=ZiHourRule.DAY_FLIPS_AT_00)
    late = four_pillars(dt, 0.0, 0.0, "UTC", zi_rule=ZiHourRule.LATE_ZI)
    assert late["day"].label == r00["day"].label        # day pillar kept (壬申)
    assert late["hour"].label == "壬子"                  # stem borrowed from the next day
    assert late["hour"].label != r00["hour"].label      # ... not the same-day 庚子
    # It matches the 00:30 hour of the following day, which is the point of the school.
    nxt = four_pillars(datetime(2000, 1, 16, 0, 30), 0.0, 0.0, "UTC",
                       zi_rule=ZiHourRule.LATE_ZI)
    assert nxt["hour"].label == late["hour"].label

def test_fix6_day_boundary_option():
    # Urumqi clock 00:30 is ~22:20 true solar time on the previous calendar day, so
    # the two day-boundary policies must disagree on the day pillar.
    dt = datetime(2000, 6, 1, 0, 30)
    solar = four_pillars(dt, 43.8, 87.6, BJ, day_boundary=DayBoundary.SOLAR)
    clock = four_pillars(dt, 43.8, 87.6, BJ, day_boundary=DayBoundary.CLOCK)
    assert solar["day"].label != clock["day"].label
    assert solar["day_boundary"] == "solar" and clock["day_boundary"] == "clock"
    # Under CLOCK the day pillar equals the plain calendar-date pillar for June 1.
    assert clock["day"].label == pillar_from_index(
        (jdn_from_date(2000, 6, 1) - DAY_ANCHOR_JDN) % 60).label


# ---- 0.2.1 regression tests ---------------------------------------------------

NY = "America/New_York"

def test_v021_standard_time_removes_dst():
    # 11:30 EDT is 10:30 standard time (巳), not 午; CIVIL_CLOCK keeps the displayed 11:30.
    dt = datetime(1991, 7, 15, 11, 30)
    std = four_pillars(dt, 40.7, -74.0, NY, meridian=MeridianPolicy.STANDARD_TIME)
    civ = four_pillars(dt, 40.7, -74.0, NY, meridian=MeridianPolicy.CIVIL_CLOCK)
    assert std["hour"].branch == 5 and civ["hour"].branch == 6
    assert std["correction_minutes"] == -60.0 and civ["correction_minutes"] == 0.0
    # China's 1988 DST: standard time reads 13:00, still 未.
    cn = four_pillars(datetime(1988, 6, 1, 14, 0), 43.8, 87.6, BJ,
                      meridian=MeridianPolicy.STANDARD_TIME)
    assert cn["correction_minutes"] == -60.0 and cn["hour"].branch == 7

def test_v021_late_zi_judged_on_the_hour_clock():
    # Civil 23:10 in Charlotte is ~22:40 true solar (an 亥 hour): LATE_ZI must not
    # shift the stem, whichever clock sets the day boundary.
    dt = datetime(2001, 1, 10, 23, 10)
    solar = four_pillars(dt, 35.2, -80.8, NY, zi_rule=ZiHourRule.LATE_ZI,
                         day_boundary=DayBoundary.SOLAR)
    clock = four_pillars(dt, 35.2, -80.8, NY, zi_rule=ZiHourRule.LATE_ZI,
                         day_boundary=DayBoundary.CLOCK)
    assert solar["hour"].label == clock["hour"].label
    assert solar["frame_conflict"] is False
    assert clock["frame_conflict"] is True      # the two clocks disagree here, and it says so

def test_v021_lunar_out_of_range_degrades_instead_of_crashing():
    for yr in (1850, 2150):
        s = TimeEngine().resolve(datetime(yr, 6, 1, 12, 0), 40.0, -74.0, "UTC")
        assert s.lunar.degraded is True and s.lunar.lunar_year is None
        assert s.bazi.year.label                  # the rest of the chart still resolves

def test_v021_ruleset_per_call_changes_result_and_key():
    eng = TimeEngine()
    dt = datetime(2001, 1, 10, 23, 10)
    a = eng.resolve(dt, 35.2, -80.8, NY)
    b = eng.resolve(dt, 35.2, -80.8, NY,
                    ruleset=RulesetConfig(meridian_policy=MeridianPolicy.CIVIL_CLOCK))
    assert a.cache_key != b.cache_key and a.bazi.time_basis != b.bazi.time_basis
    assert b.ruleset.meridian_policy is MeridianPolicy.CIVIL_CLOCK

def test_v021_invalid_coordinates_rejected():
    with pytest.raises(ValueError):
        TimeEngine().resolve(datetime(2000, 1, 1), 200.0, 0.0, "UTC")

def test_v021_api_validation():
    from fastapi.testclient import TestClient
    from timeengine.api import app
    c = TestClient(app, raise_server_exceptions=False)
    base = {"dt": "1991-09-11T08:30:00", "lat": 35.2, "lon": -80.8, "tz": NY}
    assert c.post("/resolve", json=base).status_code == 200
    assert c.post("/resolve", json={**base, "tz": "Mars/Olympus"}).status_code == 422
    assert c.post("/resolve", json={**base, "lat": 200}).status_code == 422
    polar = {"dt": "2000-06-21T12:00:00", "lat": 69.65, "lon": 18.96, "tz": "Europe/Oslo"}
    assert c.post("/resolve", json=polar).status_code == 200
    r = c.post("/resolve", json={**base, "ruleset": {"zi_hour_rule": "late_zi"}})
    assert r.status_code == 200 and r.json()["ruleset"]["zi_hour_rule"] == "late_zi"
