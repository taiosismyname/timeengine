# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""BaZi depth: hidden stems, ten gods, element counts, luck pillars.

Expected values are hand-derived from the textbook rules, not read back from the code.
"""
import datetime as dt
from collections import Counter
import pytest
from fastapi.testclient import TestClient

from timeengine import TimeEngine
from timeengine.api import app
from timeengine.bazi import pillar_from_index
from timeengine.bazi_depth import (ten_god, hidden_stems, HIDDEN_STEMS, HIDDEN_WEIGHTS,
                                   BRANCH_ELEMENT, element_of_stem, luck_pillars, STEMS)
from timeengine.cal import jd_from_datetime
from timeengine.solar_terms import jie_terms_spanning

NY = "America/New_York"
UTC = dt.timezone.utc

# Canonical rows: day master 甲 and 乙 read against stems 甲乙丙丁戊己庚辛壬癸.
TEN_GODS_JIA = "比肩 劫财 食神 伤官 偏财 正财 七杀 正官 偏印 正印".split()
TEN_GODS_YI = "劫财 比肩 伤官 食神 正财 偏财 正官 七杀 正印 偏印".split()

def test_ten_gods_match_the_canonical_rows_for_jia_and_yi():
    assert [ten_god(0, s)[0] for s in range(10)] == TEN_GODS_JIA
    assert [ten_god(1, s)[0] for s in range(10)] == TEN_GODS_YI

def test_ten_gods_each_appear_exactly_ten_times_over_all_pairs():
    counts = Counter(ten_god(dm, s)[1] for dm in range(10) for s in range(10))
    assert len(counts) == 10 and set(counts.values()) == {10}

def test_ten_gods_are_polarity_mirrored_for_every_day_master():
    # Same-element target: same polarity vs opposite polarity must give the paired god.
    pairs = {"bijian": "jiecai", "shishen": "shangguan", "piancai": "zhengcai",
             "qisha": "zhengguan", "pianyin": "zhengyin"}
    pairs.update({v: k for k, v in pairs.items()})
    for dm in range(10):
        for e in range(5):
            a, b = 2 * e, 2 * e + 1                      # yang and yin stem of one element
            assert pairs[ten_god(dm, a)[1]] == ten_god(dm, b)[1]

CANON_HIDDEN = ["癸", "己癸辛", "甲丙戊", "乙", "戊乙癸", "丙庚戊",
                "丁己", "己丁乙", "庚壬戊", "辛", "戊辛丁", "壬甲"]

def test_hidden_stem_table_matches_the_textbook_for_all_twelve_branches():
    for b, canon in enumerate(CANON_HIDDEN):
        assert "".join(STEMS[s] for s in HIDDEN_STEMS[b]) == canon

def test_hidden_stems_primary_element_equals_the_branch_element():
    for b in range(12):
        assert element_of_stem(HIDDEN_STEMS[b][0]) == BRANCH_ELEMENT[b], b

def test_hidden_stem_weights_sum_to_one():
    for w in HIDDEN_WEIGHTS.values():
        assert abs(sum(w) - 1.0) < 1e-9

def test_known_chart_ten_gods_1991_charlotte():
    # 辛未 / 丁酉 / 甲申 / 戊辰, day master 甲 (hand-derived from the rules above).
    d = TimeEngine().resolve(dt.datetime(1991, 9, 11, 8, 30), 35.2271, -80.8431, NY).bazi_depth
    assert d.day_master == "甲" and d.day_master_element == "wood"
    stems = {p.position: p.stem_ten_god for p in d.pillars}
    assert stems == {"year": "正官", "month": "伤官", "day": "日主", "hour": "偏财"}
    year = next(p for p in d.pillars if p.position == "year")        # 未 hides 己 丁 乙
    assert [(h.label, h.ten_god) for h in year.hidden_stems] == [("己", "正财"), ("丁", "伤官"), ("乙", "劫财")]
    assert d.stem_elements == {"wood": 1, "fire": 1, "earth": 1, "metal": 1, "water": 0}
    assert sum(d.branch_elements.values()) == 4

def _luck(year, month, day, **kw):
    s = TimeEngine().resolve(dt.datetime(year, month, day, 12, 0), 35.2271, -80.8431, NY, **kw)
    return s, s.bazi_depth.luck

def test_classical_direction_rule_all_four_combinations():
    # 2000 is 庚辰 (yang); 1991 is 辛未 (yin).
    assert _luck(2000, 6, 15, gender="male")[1][0].direction == "forward"
    assert _luck(2000, 6, 15, gender="female")[1][0].direction == "backward"
    assert _luck(1991, 6, 15, gender="male")[1][0].direction == "backward"
    assert _luck(1991, 6, 15, gender="female")[1][0].direction == "forward"

def test_without_gender_or_direction_both_directions_are_returned():
    _, luck = _luck(2000, 6, 15)
    assert [l.direction for l in luck] == ["forward", "backward"]
    assert {l.basis for l in luck} == {"both_shown"}

def test_explicit_direction_overrides_gender():
    _, luck = _luck(2000, 6, 15, gender="male", luck_direction="backward")
    assert len(luck) == 1 and luck[0].direction == "backward" and luck[0].basis == "explicit_direction"

def test_luck_sequence_steps_one_pillar_per_decade_from_the_month_pillar():
    s, luck = _luck(2000, 6, 15)
    month = s.bazi.month.index
    for l in luck:
        step = 1 if l.direction == "forward" else -1
        assert [p.pillar.index for p in l.pillars] == [(month + step * (k + 1)) % 60 for k in range(8)]
        ages = [p.start_age for p in l.pillars]
        assert all(abs((b - a) - 10) < 1e-3 for a, b in zip(ages, ages[1:]))

def test_start_age_is_distance_to_adjacent_jie_over_three():
    dt_ = dt.datetime(2000, 6, 15, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
    jd = jd_from_datetime(dt_.astimezone(UTC))
    terms = [t[1] for t in jie_terms_spanning(2000)]
    nxt = min(t for t in terms if t > jd) - jd
    prv = jd - max(t for t in terms if t <= jd)
    _, luck = _luck(2000, 6, 15)
    by_dir = {l.direction: l for l in luck}
    assert abs(by_dir["forward"].start_age_days - nxt) < 1e-3
    assert abs(by_dir["backward"].start_age_days - prv) < 1e-3
    assert abs(by_dir["forward"].start_age_years - nxt / 3.0) < 1e-3

def test_luck_works_across_the_new_year_boundaries():
    for (y, m, d) in [(1999, 12, 30), (2000, 1, 2), (2000, 12, 31), (2001, 1, 1)]:
        _, luck = _luck(y, m, d)
        assert all(0 < l.start_age_years < 10.1 for l in luck), (y, m, d)

def test_start_year_matches_the_birth_year_plus_the_start_age():
    _, luck = _luck(1991, 9, 11)
    for l in luck:
        assert l.pillars[0].start_year in (1991 + int(l.start_age_years), 1991 + int(l.start_age_years) + 1)

def test_gender_and_direction_are_part_of_the_cache_key():
    e = TimeEngine()
    args = (dt.datetime(2000, 6, 15, 12, 0), 35.2, -80.8, NY)
    k = {e.resolve(*args).cache_key, e.resolve(*args, gender="male").cache_key,
         e.resolve(*args, gender="female").cache_key, e.resolve(*args, luck_direction="forward").cache_key}
    assert len(k) == 4

def test_invalid_gender_or_direction_is_rejected():
    with pytest.raises(ValueError):
        TimeEngine().resolve(dt.datetime(2000, 6, 15), 35.2, -80.8, NY, gender="x")
    c = TestClient(app, raise_server_exceptions=False)
    base = {"dt": "2000-06-15T12:00:00", "lat": 35.2, "lon": -80.8, "tz": NY}
    assert c.post("/resolve", json={**base, "luck_direction": "sideways"}).status_code == 422
    r = c.post("/resolve", json={**base, "luck_direction": "backward"})
    assert r.status_code == 200 and r.json()["bazi_depth"]["luck"][0]["direction"] == "backward"
