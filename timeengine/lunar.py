# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Lunar calendar via a pluggable provider. zhdate is the reference adapter;
kept behind a protocol so the dependency is optional and swappable."""
from __future__ import annotations
from typing import Protocol

class LunarProvider(Protocol):
    def lunar_date(self, year: int, month: int, day: int) -> dict: ...

class ZhDateLunar:
    def __init__(self) -> None:
        try:
            from zhdate import ZhDate  # noqa: F401
            self._ok = True
        except ImportError:
            self._ok = False
    def lunar_date(self, year: int, month: int, day: int) -> dict:
        if not self._ok:
            return {"degraded": True, "note": "install zhdate to enable lunar conversion"}
        from zhdate import ZhDate
        from datetime import datetime as _dt
        try:
            z = ZhDate.from_datetime(_dt(year, month, day))
        except Exception:   # zhdate only covers lunar years 1900-2100
            return {"degraded": True,
                    "note": "date outside the supported lunar table (1900-2100)"}
        return {"degraded": False, "lunar_year": z.lunar_year, "lunar_month": z.lunar_month,
                "lunar_day": z.lunar_day, "leap_month": z.leap_month}
