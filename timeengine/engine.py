# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""TimeEngine: one call, all systems, deterministic and cacheable."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# The Chinese calendar's civil day boundary is China Standard Time. A fixed UTC+8
# frame is used deliberately: historical Chinese DST (1986-1991) moved the clock,
# but the published lunar calendar is keyed to standard time.
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))

from . import ephem
from .bazi import four_pillars, Pillar
from .bazi_depth import bazi_depth, Gender, LuckDirection
from .cache import CacheBackend, InMemoryCache
from .cal import jd_from_datetime
from .lunar import ZhDateLunar
from .models import (AspectModel, BaziChart, BaziDepthModel, LunarDateModel, NumerologyProfile,
                     PillarModel, RulesetConfig, SolarTermInfo, TemporalSnapshot,
                     WesternChartModel, make_cache_key)
from .numerology import dual_name_profile, life_path
from .solar_terms import terms_for_year
from .western import chart_positions

def _pm(p: Pillar) -> PillarModel:
    return PillarModel(stem=p.stem, branch=p.branch, index=p.index, label=p.label)

class TimeEngine:
    def __init__(self, ruleset: RulesetConfig | None = None,
                 cache: CacheBackend | None = None,
                 lunar_provider=None) -> None:
        self.ruleset = ruleset or RulesetConfig()
        self.cache = cache or InMemoryCache()
        self.lunar = lunar_provider or ZhDateLunar()

    def resolve(self, dt: datetime, lat: float, lon: float, tz: str,
                birth_name: str | None = None,
                chosen_name: str | None = None,
                ruleset: RulesetConfig | None = None,
                gender: str | None = None,
                luck_direction: str | None = None) -> TemporalSnapshot:
        rs = ruleset or self.ruleset
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise ValueError("lat must be in [-90, 90] and lon in [-180, 180]")
        gender = Gender(gender).value if gender else None            # ValueError if invalid
        luck_direction = LuckDirection(luck_direction).value if luck_direction else None
        lat, lon = round(lat, 4), round(lon, 4)   # key and computation agree
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(tz))
        dt_utc = dt.astimezone(ZoneInfo("UTC"))
        mode = ephem.ephemeris_mode()
        key = make_cache_key(dt.isoformat(), lat, lon, tz, rs, mode,
                             birth_name, chosen_name, gender, luck_direction)
        hit = self.cache.get(key)
        if hit is not None:
            return hit

        jd_ut = jd_from_datetime(dt_utc)
        w = chart_positions(jd_ut, lat, lon)
        cusps = w.get("house_cusps")
        western = WesternChartModel(
            degraded=w["degraded"], positions=w["positions"],
            note=w.get("note"), ascendant=w.get("ascendant"), mc=w.get("mc"),
            house_system_used=w.get("house_system_used"),
            houses_degraded=bool(w.get("houses_degraded", False)),
            house_cusps=tuple(cusps) if cusps else None,
            speeds=w.get("speeds"), retrograde=w.get("retrograde"),
            north_node=w.get("north_node"), south_node=w.get("south_node"),
            node_kind=w.get("node_kind"),
            aspects=tuple(AspectModel(**a) for a in w.get("aspects", [])))
        bp = four_pillars(dt, lat, lon, tz, rs.zi_hour_rule,
                          rs.meridian_policy, rs.day_boundary)
        bazi = BaziChart(year=_pm(bp["year"]), month=_pm(bp["month"]),
                         day=_pm(bp["day"]), hour=_pm(bp["hour"]),
                         effective_time=bp["effective_time"],
                         correction_minutes=bp["correction_minutes"],
                         time_basis=bp["time_basis"],
                         day_boundary=bp["day_boundary"],
                         frame_conflict=bp["frame_conflict"])
        depth = BaziDepthModel(**bazi_depth(bp["year"], bp["month"], bp["day"], bp["hour"],
                                            jd_ut, dt.year, gender, luck_direction))
        terms = tuple(SolarTermInfo(slug=s, hanzi=h, angle=a, is_jie=j, jd_ut=round(jd, 5))
                      for a, s, h, j, jd in terms_for_year(dt.year))
        # Lunar date is read in fixed UTC+8, NOT the UTC date and NOT the birth's
        # local civil date: a New York birth late on Feb 4 is still Feb 4 in China.
        dt_cst = dt_utc.astimezone(CHINA_STANDARD_TIME)
        lunar = LunarDateModel(**self.lunar.lunar_date(dt_cst.year, dt_cst.month, dt_cst.day))
        numerology = None
        if birth_name:
            dual = dual_name_profile(birth_name, chosen_name)
            numerology = NumerologyProfile(
                life_path=life_path(dt.year, dt.month, dt.day), **dual)

        snap = TemporalSnapshot(
            dt=dt.isoformat(), lat=round(lat, 4), lon=round(lon, 4), tz=tz,
            ephemeris_mode=mode, ruleset=rs, western=western, bazi=bazi, bazi_depth=depth,
            solar_terms_year=terms, lunar=lunar, numerology=numerology, cache_key=key)
        self.cache.set(key, snap)
        return snap
