# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Frozen, JSON-serializable snapshot models. Cache keys hash the full ruleset."""
from __future__ import annotations
import hashlib, json
from pydantic import BaseModel

from .bazi import DayBoundary, MeridianPolicy, ZiHourRule

RULESET_VERSION = "0.4.0"

class RulesetConfig(BaseModel, frozen=True):
    zi_hour_rule: ZiHourRule = ZiHourRule.DAY_FLIPS_AT_00
    meridian_policy: MeridianPolicy = MeridianPolicy.TRUE_SOLAR
    day_boundary: DayBoundary = DayBoundary.SOLAR
    ruleset_version: str = RULESET_VERSION

class PillarModel(BaseModel, frozen=True):
    stem: int
    branch: int
    index: int
    label: str

class BaziChart(BaseModel, frozen=True):
    year: PillarModel
    month: PillarModel
    day: PillarModel
    hour: PillarModel
    effective_time: str          # the time the pillars were read from
    correction_minutes: float    # offset from the civil clock (0.0 under STANDARD_TIME)
    time_basis: str              # MeridianPolicy value used
    day_boundary: str            # DayBoundary value used
    frame_conflict: bool = False  # True when day boundary and hour clock disagree here

class HiddenStemModel(BaseModel, frozen=True):
    stem: int
    label: str
    role: str                    # primary / middle / residual
    weight: float
    ten_god: str
    ten_god_slug: str

class PillarDepthModel(BaseModel, frozen=True):
    position: str                # year / month / day / hour
    pillar: PillarModel
    stem_ten_god: str            # 日主 for the day pillar
    stem_ten_god_slug: str
    hidden_stems: tuple[HiddenStemModel, ...]

class LuckPillarModel(BaseModel, frozen=True):
    pillar: PillarModel
    start_age: float
    start_year: int

class LuckModel(BaseModel, frozen=True):
    direction: str               # forward / backward
    basis: str                   # explicit_direction / classical_male / classical_female / both_shown
    start_age_years: float
    start_age_days: float        # raw distance to the adjacent jie term
    pillars: tuple[LuckPillarModel, ...]

class BaziDepthModel(BaseModel, frozen=True):
    day_master: str
    day_master_element: str
    day_master_element_hanzi: str
    pillars: tuple[PillarDepthModel, ...]
    stem_elements: dict[str, int]
    branch_elements: dict[str, int]
    luck: tuple[LuckModel, ...]

class SolarTermInfo(BaseModel, frozen=True):
    slug: str
    hanzi: str
    angle: float
    is_jie: bool
    jd_ut: float

class AspectModel(BaseModel, frozen=True):
    body1: str
    body2: str
    aspect: str              # conjunction / sextile / square / trine / opposition
    angle: float             # exact angle of the aspect
    deviation: float         # signed degrees from exact; negative = inside the angle
    phase: str               # applying / separating / exact / unknown

class WesternChartModel(BaseModel, frozen=True):
    degraded: bool
    positions: dict[str, float]
    note: str | None = None
    ascendant: float | None = None
    mc: float | None = None
    house_system_used: str | None = None      # e.g. "placidus" or the polar fallback
    houses_degraded: bool = False             # True when the requested system was replaced
    house_cusps: tuple[float, ...] | None = None
    speeds: dict[str, float] | None = None    # geocentric ecliptic-longitude rate, deg/day
    retrograde: dict[str, bool] | None = None # True when that planet's longitude is decreasing
    north_node: float | None = None           # true node by default; see node_kind
    south_node: float | None = None
    node_kind: str | None = None              # "true" or "mean"
    aspects: tuple[AspectModel, ...] = ()     # tightest first

class NumerologyProfile(BaseModel, frozen=True):
    life_path: int
    birth_name_expression: int | None = None
    chosen_name_expression: int | None = None

class LunarDateModel(BaseModel, frozen=True):
    degraded: bool
    note: str | None = None
    lunar_year: int | None = None
    lunar_month: int | None = None
    lunar_day: int | None = None
    leap_month: bool | None = None

class TemporalSnapshot(BaseModel, frozen=True):
    dt: str
    lat: float
    lon: float
    tz: str
    ephemeris_mode: str
    ruleset: RulesetConfig
    western: WesternChartModel
    bazi: BaziChart
    bazi_depth: BaziDepthModel
    solar_terms_year: tuple[SolarTermInfo, ...]
    lunar: LunarDateModel
    numerology: NumerologyProfile | None
    cache_key: str

def make_cache_key(dt: str, lat: float, lon: float, tz: str, ruleset: RulesetConfig,
                   ephemeris_mode: str, birth_name: str | None = None,
                   chosen_name: str | None = None, luck_gender: str | None = None,
                   luck_direction: str | None = None) -> str:
    # Names belong in the key: they change the numerology in the cached snapshot.
    # Canonicalised the same way numerology canonicalises them (case-insensitive).
    payload = json.dumps(
        {"dt": dt, "lat": round(lat, 4), "lon": round(lon, 4), "tz": tz,
         "ruleset": ruleset.model_dump(mode="json"), "eph": ephemeris_mode,
         "birth_name": (birth_name or "").strip().lower() or None,
         "chosen_name": (chosen_name or "").strip().lower() or None,
         "luck_gender": luck_gender, "luck_direction": luck_direction},
        sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]
