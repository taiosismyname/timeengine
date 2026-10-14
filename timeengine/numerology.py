# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Pythagorean numerology with master-number preservation (11/22/33)."""
from __future__ import annotations

MAP = {c: (i % 9) + 1 for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}
MASTERS = {11, 22, 33}

def reduce_master(n: int) -> int:
    while n > 9 and n not in MASTERS:
        n = sum(int(d) for d in str(n))
    return n

def expression_number(name: str) -> int | None:
    vals = [MAP[c] for c in name.lower() if c in MAP]
    if not vals:
        return None
    return reduce_master(sum(vals))

def life_path(year: int, month: int, day: int) -> int:
    return reduce_master(sum(int(d) for d in f"{year:04d}{month:02d}{day:02d}"))

def dual_name_profile(birth_name: str, chosen_name: str | None) -> dict:
    out = {"birth_name_expression": expression_number(birth_name)}
    if chosen_name and chosen_name.strip().lower() != birth_name.strip().lower():
        out["chosen_name_expression"] = expression_number(chosen_name)
    return out
