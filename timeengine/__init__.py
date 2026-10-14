# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""TimeEngine: unified Western astrology + BaZi + solar terms + numerology core."""
from .engine import TimeEngine
from .models import RulesetConfig, TemporalSnapshot
from .bazi import DayBoundary, MeridianPolicy, ZiHourRule

__all__ = ["TimeEngine", "RulesetConfig", "TemporalSnapshot",
           "ZiHourRule", "MeridianPolicy", "DayBoundary"]
__version__ = "0.4.0"
