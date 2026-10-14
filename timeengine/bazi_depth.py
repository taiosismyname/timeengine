# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""BaZi depth: hidden stems (藏干), ten gods (十神), element counts and luck pillars (大运).

Pure tables and arithmetic over the four pillars: no ephemeris dependency, so it behaves
identically on Swiss Ephemeris, Moshier or the analytic fallback.

Based on the draft written in the previous session (hidden-stem and ten-god tables kept as
written; both were re-derived and checked). Changes made here:
- the day pillar's own stem is labelled 日主 (day master), not 比肩;
- luck pillars no longer require a binary gender. Direction can be given explicitly, derived
  from the classical rule if a classical gender is supplied, or, if neither is given, both
  directions are returned so the person can choose;
- start year is computed from the actual start moment instead of rounding the age.

School variance is kept visible, not hidden:
- Hidden-stem weights (HIDDEN_WEIGHTS) are one common assignment; schools differ.
- Start age uses the mainstream 3 days = 1 year. The raw distance in days is returned too.
"""
from __future__ import annotations
from enum import Enum

from .bazi import Pillar, pillar_from_index
from .cal import datetime_from_jd
from .solar_terms import jie_terms_spanning

STEMS = "甲乙丙丁戊己庚辛壬癸"

ELEMENT_NAMES = ("wood", "fire", "earth", "metal", "water")
ELEMENT_HANZI = ("木", "火", "土", "金", "水")

STEM_ELEMENT = tuple(s // 2 for s in range(10))      # 甲乙 wood, 丙丁 fire, 戊己 earth, 庚辛 metal, 壬癸 water
BRANCH_ELEMENT = (4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4)   # 子丑寅卯辰巳午未申酉戌亥

# 藏干: hidden stems per branch, in 本气 / 中气 / 余气 order.
HIDDEN_STEMS = (
    (9,), (5, 9, 7), (0, 2, 4), (1,), (4, 1, 9), (2, 6, 4),
    (3, 5), (5, 3, 1), (6, 8, 4), (7,), (4, 7, 3), (8, 0),
)
HIDDEN_WEIGHTS = {1: (1.0,), 2: (0.7, 0.3), 3: (0.6, 0.3, 0.1)}
ROLE_NAMES = ("primary", "middle", "residual")

GEN = tuple((a + 1) % 5 for a in range(5))    # 木->火->土->金->水->木
CTRL = tuple((a + 2) % 5 for a in range(5))   # 木->土->水->火->金->木

TEN_GODS = {
    ("same", True): ("比肩", "bijian"), ("same", False): ("劫财", "jiecai"),
    ("output", True): ("食神", "shishen"), ("output", False): ("伤官", "shangguan"),
    ("wealth", True): ("偏财", "piancai"), ("wealth", False): ("正财", "zhengcai"),
    ("officer", True): ("七杀", "qisha"), ("officer", False): ("正官", "zhengguan"),
    ("resource", True): ("偏印", "pianyin"), ("resource", False): ("正印", "zhengyin"),
}

class Gender(str, Enum):
    """Classical term used only by the traditional luck-direction rule."""
    MALE = "male"
    FEMALE = "female"

class LuckDirection(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"

def element_of_stem(stem: int) -> int:
    return STEM_ELEMENT[stem % 10]

def is_yang_stem(stem: int) -> bool:
    return stem % 2 == 0

def ten_god(day_master_stem: int, target_stem: int) -> tuple[str, str]:
    """(hanzi, slug) for `target_stem` read against the day master."""
    e_dm, e_t = element_of_stem(day_master_stem), element_of_stem(target_stem)
    same_polarity = is_yang_stem(day_master_stem) == is_yang_stem(target_stem)
    if e_t == e_dm:
        rel = "same"
    elif e_t == GEN[e_dm]:
        rel = "output"
    elif e_t == CTRL[e_dm]:
        rel = "wealth"
    elif e_dm == CTRL[e_t]:
        rel = "officer"
    else:
        rel = "resource"
    return TEN_GODS[(rel, same_polarity)]

def hidden_stems(day_master_stem: int, branch: int) -> list[dict]:
    stems = HIDDEN_STEMS[branch % 12]
    weights = HIDDEN_WEIGHTS[len(stems)]
    out = []
    for i, s in enumerate(stems):
        hanzi, slug = ten_god(day_master_stem, s)
        out.append({"stem": s, "label": STEMS[s], "role": ROLE_NAMES[i], "weight": weights[i],
                    "ten_god": hanzi, "ten_god_slug": slug})
    return out

def _pdict(p: Pillar) -> dict:
    return {"stem": p.stem, "branch": p.branch, "index": p.index, "label": p.label}

def _pillar_detail(position: str, pillar: Pillar, day_master_stem: int) -> dict:
    if position == "day":
        hanzi, slug = "日主", "day_master"
    else:
        hanzi, slug = ten_god(day_master_stem, pillar.stem)
    return {"position": position, "pillar": _pdict(pillar),
            "stem_ten_god": hanzi, "stem_ten_god_slug": slug,
            "hidden_stems": hidden_stems(day_master_stem, pillar.branch)}

def _element_counts(stems, branches) -> tuple[dict, dict]:
    se = {n: 0 for n in ELEMENT_NAMES}
    be = {n: 0 for n in ELEMENT_NAMES}
    for s in stems:
        se[ELEMENT_NAMES[element_of_stem(s)]] += 1
    for b in branches:
        be[ELEMENT_NAMES[BRANCH_ELEMENT[b % 12]]] += 1
    return se, be

def _one_luck(jd_ut, month_pillar, civil_year, direction: LuckDirection, basis: str, count: int):
    forward = direction is LuckDirection.FORWARD
    terms = jie_terms_spanning(civil_year)
    if forward:
        days = min(jd for _, jd, _ in terms if jd > jd_ut) - jd_ut
    else:
        days = jd_ut - max(jd for _, jd, _ in terms if jd <= jd_ut)
    start_age = days / 3.0                                    # 3 days = 1 year
    pillars = []
    for k in range(count):
        p = pillar_from_index(month_pillar.index + (k + 1) * (1 if forward else -1))
        age = start_age + 10 * k
        start = datetime_from_jd(jd_ut + age * 365.2422)
        pillars.append({"pillar": _pdict(p), "start_age": round(age, 4), "start_year": start.year})
    return {"direction": direction.value, "basis": basis,
            "start_age_years": round(start_age, 4), "start_age_days": round(days, 4),
            "pillars": pillars}

def luck_pillars(jd_ut: float, year_stem: int, month_pillar: Pillar, civil_year: int,
                 gender: Gender | str | None = None,
                 direction: LuckDirection | str | None = None, count: int = 8) -> list[dict]:
    """Decade pillars (大运). Precedence: explicit direction > classical gender rule >
    both directions returned. Start age = distance to the adjacent jie term / 3."""
    if direction is not None:
        return [_one_luck(jd_ut, month_pillar, civil_year, LuckDirection(direction),
                          "explicit_direction", count)]
    if gender is not None:
        g = Gender(gender)
        fwd = is_yang_stem(year_stem) == (g is Gender.MALE)   # yang male / yin female run forward
        return [_one_luck(jd_ut, month_pillar, civil_year,
                          LuckDirection.FORWARD if fwd else LuckDirection.BACKWARD,
                          f"classical_{g.value}", count)]
    return [_one_luck(jd_ut, month_pillar, civil_year, d, "both_shown", count)
            for d in (LuckDirection.FORWARD, LuckDirection.BACKWARD)]

def bazi_depth(year_p: Pillar, month_p: Pillar, day_p: Pillar, hour_p: Pillar,
               jd_ut: float, civil_year: int, gender: Gender | str | None = None,
               luck_direction: LuckDirection | str | None = None, luck_count: int = 8) -> dict:
    dm = day_p.stem
    se, be = _element_counts([year_p.stem, month_p.stem, day_p.stem, hour_p.stem],
                             [year_p.branch, month_p.branch, day_p.branch, hour_p.branch])
    return {
        "day_master": STEMS[dm],
        "day_master_element": ELEMENT_NAMES[element_of_stem(dm)],
        "day_master_element_hanzi": ELEMENT_HANZI[element_of_stem(dm)],
        "pillars": [_pillar_detail(n, p, dm) for n, p in
                    (("year", year_p), ("month", month_p), ("day", day_p), ("hour", hour_p))],
        "stem_elements": se, "branch_elements": be,
        "luck": luck_pillars(jd_ut, year_p.stem, month_p, civil_year, gender,
                             luck_direction, luck_count),
    }
