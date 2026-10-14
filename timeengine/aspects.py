# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Western chart depth: aspects, retrograde, nodes.

Pure arithmetic on ecliptic longitudes. No ephemeris calls here: the caller
supplies longitudes (and, when available, daily speeds). That keeps the math
testable with hand-computed values and independent of which ephemeris produced
the positions.

Conventions (all documented, all overridable by the caller):
- Five major aspects only: conjunction, sextile, square, trine, opposition.
- Default orbs are one common modern assignment; schools differ, so the orb
  table is a parameter, not a constant baked into the logic.
- phase "exact" means within 3 arcminutes of exactness. Otherwise the phase is
  read from the bodies' relative motion: "applying" when the separation is
  closing toward exactness, "separating" when it is opening away from it,
  "unknown" when a speed is missing (house angles have no speed).
"""
from __future__ import annotations

MAJOR_ASPECTS: dict[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}

# One common modern assignment, in degrees. Override per school.
DEFAULT_ORBS: dict[str, float] = {
    "conjunction": 8.0,
    "sextile": 4.0,
    "square": 6.0,
    "trine": 8.0,
    "opposition": 8.0,
}

EXACT_WITHIN_DEG = 0.05          # 3 arcminutes counts as exact
_PHASE_DT_DAYS = 1.0 / 24.0      # one hour of linear motion resolves the phase


def angular_separation(a: float, b: float) -> float:
    """Shortest angular distance between two longitudes, in [0, 180]."""
    d = abs((a - b) % 360.0)
    return 360.0 - d if d > 180.0 else d


def deviation(a: float, b: float, angle: float) -> float:
    """Signed distance from exactness: separation minus the aspect angle."""
    return angular_separation(a, b) - angle


def match_aspect(a: float, b: float,
                 orbs: dict[str, float] = DEFAULT_ORBS
                 ) -> tuple[str, float, float] | None:
    """Closest major aspect within orb, or None.

    Returns (aspect name, exact angle, signed deviation). When orbs overlap,
    the aspect with the smallest absolute deviation wins.
    """
    best: tuple[str, float, float] | None = None
    for name, angle in MAJOR_ASPECTS.items():
        dev = deviation(a, b, angle)
        if abs(dev) <= orbs[name] and (best is None or abs(dev) < abs(best[2])):
            best = (name, angle, dev)
    return best


def phase(a: float, b: float, speed_a: float | None, speed_b: float | None,
          angle: float) -> str:
    """applying / separating / exact / unknown, from relative motion.

    The separation is recomputed one hour later using linear motion from the
    daily speeds. When the distance to exactness is shrinking the aspect is
    applying; when it is growing it is separating. Without both speeds the
    phase cannot be read ("unknown").
    """
    dev_now = abs(deviation(a, b, angle))
    if dev_now <= EXACT_WITHIN_DEG:
        return "exact"
    if speed_a is None or speed_b is None:
        return "unknown"
    later = angular_separation(a + speed_a * _PHASE_DT_DAYS,
                               b + speed_b * _PHASE_DT_DAYS)
    dev_later = abs(later - angle)
    if dev_later < dev_now - 1e-9:
        return "applying"
    if dev_later > dev_now + 1e-9:
        return "separating"
    return "exact"


def compute_aspects(points: dict[str, float],
                    speeds: dict[str, float] | None = None,
                    orbs: dict[str, float] = DEFAULT_ORBS) -> list[dict]:
    """All major aspects between the given points, tightest first.

    `points` maps body name -> ecliptic longitude in degrees. `speeds`, when
    given, maps body name -> longitude speed in degrees/day and feeds the
    applying/separating read; bodies without a speed get phase "unknown".
    """
    speeds = speeds or {}
    names = sorted(points)
    out: list[dict] = []
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            hit = match_aspect(points[n1], points[n2], orbs)
            if hit is None:
                continue
            name, angle, dev = hit
            out.append({
                "body1": n1, "body2": n2,
                "aspect": name, "angle": angle,
                "deviation": round(dev, 4),
                "phase": phase(points[n1], points[n2],
                               speeds.get(n1), speeds.get(n2), angle),
            })
    out.sort(key=lambda r: (abs(r["deviation"]), r["body1"], r["body2"]))
    return out


def is_retrograde(speed: float) -> bool:
    """A body is retrograde when its geocentric ecliptic longitude is decreasing."""
    return speed < 0.0
