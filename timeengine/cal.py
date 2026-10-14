# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Julian day / calendar conversions. Pure stdlib."""
from __future__ import annotations
from datetime import datetime, timezone

def jdn_from_date(year: int, month: int, day: int) -> int:
    """Integer Julian Day Number for a Gregorian calendar date (JDN begins at noon UT)."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

def jd_from_datetime(dt_utc: datetime) -> float:
    """JD (UT) from an aware UTC datetime."""
    dt_utc = dt_utc.astimezone(timezone.utc)
    jdn = jdn_from_date(dt_utc.year, dt_utc.month, dt_utc.day)
    secs = dt_utc.hour * 3600 + dt_utc.minute * 60 + dt_utc.second + dt_utc.microsecond / 1e6
    return jdn - 0.5 + secs / 86400.0

def datetime_from_jd(jd: float) -> datetime:
    """Aware UTC datetime from JD (UT)."""
    j = jd + 0.5
    z, f = int(j), j - int(j)
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)
    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    secs = f * 86400.0
    h = int(secs // 3600); rem = secs - h * 3600
    mi = int(rem // 60); s = rem - mi * 60
    return datetime(year, month, day, h, mi, int(s), int((s - int(s)) * 1e6), tzinfo=timezone.utc)
