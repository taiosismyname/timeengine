# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""BaZi structure checks that need no oracle: explicit textbook tables, cycle arithmetic and
exact boundary behaviour."""
import datetime as dt
import pytest
from timeengine.bazi import four_pillars, MeridianPolicy, STEMS, BRANCHES, DAY_ANCHOR_JDN
from timeengine.cal import jdn_from_date, datetime_from_jd
from timeengine.solar_terms import find_term_jd, JIE_ANGLES

UTC = dt.timezone.utc
CIVIL = MeridianPolicy.CIVIL_CLOCK

# 五鼠遁: stem of the 子 hour for each day stem (index into 甲乙丙丁戊己庚辛壬癸)
ZI_STEM_BY_DAY_STEM = {0: 0, 5: 0, 1: 2, 6: 2, 2: 4, 7: 4, 3: 6, 8: 6, 4: 8, 9: 8}
# 五虎遁: stem of the 寅 month for each year stem
YIN_STEM_BY_YEAR_STEM = {0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0}

def test_hour_stem_table_wushu_dun():
    for day in range(10, 20):                     # ten consecutive days cover all ten day stems
        for k in range(12):
            h, m = (0, 30) if k == 0 else (2 * k, 0)
            r = four_pillars(dt.datetime(2001, 3, day, h, m), 0.0, 0.0, "UTC", meridian=CIVIL)
            assert r["hour"].branch == k
            assert r["hour"].stem == (ZI_STEM_BY_DAY_STEM[r["day"].stem] + k) % 10, (day, k)

def test_month_stem_table_wuhu_dun():
    for year in range(1984, 1994):                # ten consecutive year stems
        r = four_pillars(dt.datetime(year, 2, 25, 12, 0), 0.0, 0.0, "UTC", meridian=CIVIL)
        assert r["month"].branch == 2             # 寅 month
        assert r["month"].stem == YIN_STEM_BY_YEAR_STEM[r["year"].stem], year

def test_day_pillar_follows_jdn_plus_49_mod_60():
    prev = None
    for n in range(6000):
        d = dt.date(1990, 1, 1) + dt.timedelta(days=n)
        r = four_pillars(dt.datetime(d.year, d.month, d.day, 12, 0), 0.0, 0.0, "UTC", meridian=CIVIL)
        assert r["day"].index == (jdn_from_date(d.year, d.month, d.day) + 49) % 60
        if prev is not None:
            assert r["day"].index == (prev + 1) % 60
        prev = r["day"].index

@pytest.mark.parametrize("year,label", [(1900, "庚子"), (1984, "甲子"), (2000, "庚辰"),
                                        (2024, "甲辰"), (2044, "甲子")])
def test_known_year_pillars(year, label):
    assert four_pillars(dt.datetime(year, 7, 1, 12, 0), 0.0, 0.0, "UTC")["year"].label == label

def test_month_pillars_advance_one_step_each_month_across_years():
    # Mar..Dec of each year: ten consecutive months, each one step on the 60-cycle
    for year in range(1990, 2031):
        seq = [four_pillars(dt.datetime(year, m, 20, 12, 0), 0.0, 0.0, "UTC")["month"].index
               for m in range(3, 13)]
        assert all((b - a) % 60 == 1 for a, b in zip(seq, seq[1:])), year

def test_every_jie_boundary_flips_the_month_pillar_within_two_minutes():
    for year in range(1950, 2051, 7):
        for angle in JIE_ANGLES:
            jd = find_term_jd(float(angle), year)
            before = datetime_from_jd(jd - 120 / 86400); after = datetime_from_jd(jd + 120 / 86400)
            b = four_pillars(before, 0.0, 0.0, "UTC")["month"].label
            a = four_pillars(after, 0.0, 0.0, "UTC")["month"].label
            assert a != b, (year, angle)

def test_lichun_flips_the_year_pillar_within_two_minutes():
    for year in range(1950, 2051, 5):
        jd = find_term_jd(315.0, year)
        b = four_pillars(datetime_from_jd(jd - 120 / 86400), 0.0, 0.0, "UTC")["year"].label
        a = four_pillars(datetime_from_jd(jd + 120 / 86400), 0.0, 0.0, "UTC")["year"].label
        assert a != b, year

def test_hour_pillar_flips_exactly_on_two_hour_edges():
    for edge in range(1, 24, 2):                  # 01:00, 03:00, ... 23:00
        b = four_pillars(dt.datetime(2001, 3, 14, edge - 1, 59), 0.0, 0.0, "UTC", meridian=CIVIL)["hour"]
        a = four_pillars(dt.datetime(2001, 3, 14, edge, 0), 0.0, 0.0, "UTC", meridian=CIVIL)["hour"]
        assert a.branch == (b.branch + 1) % 12, edge
