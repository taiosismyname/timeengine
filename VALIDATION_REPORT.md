# TimeEngine validation report

Generated 2026-10-06 | ephemeris mode: **moshier** | Python 3.12.3 | seed 20261004

Oracle: Skyfield + JPL DE421 (1900-2050). It shares no ephemeris, root finder or formula code with the engine. Range: 1901-2049.

## Numeric agreement

| Check | n | mean | p99 | max | unit |
|---|---|---|---|---|---|
| sun apparent longitude | 300 | 0.0304 | 0.1544 | 0.1829 | arcsec |
| moon apparent longitude | 300 | 0.6859 | 2.2433 | 2.5245 | arcsec |
| mercury apparent longitude | 300 | 0.0396 | 0.2084 | 0.2700 | arcsec |
| venus apparent longitude | 300 | 0.0635 | 0.3313 | 0.3811 | arcsec |
| mars apparent longitude | 300 | 0.0740 | 0.5056 | 0.5695 | arcsec |
| jupiter apparent longitude | 300 | 0.1424 | 0.4718 | 0.5183 | arcsec |
| saturn apparent longitude | 300 | 0.1223 | 0.4112 | 0.5582 | arcsec |
| uranus apparent longitude | 300 | 0.1176 | 0.3367 | 0.4015 | arcsec |
| neptune apparent longitude | 300 | 0.2277 | 0.9090 | 0.9659 | arcsec |
| pluto apparent longitude | 300 | 0.2525 | 0.7150 | 0.7701 | arcsec |
| 24 solar terms (time of crossing) | 888 | 0.6291 | 3.4194 | 4.1216 | seconds |
| equation of time | 500 | 0.0165 | 0.0489 | 0.0612 | minutes |
| ascendant | 400 | 0.0005 | 0.0018 | 0.0024 | arcsec |
| midheaven | 400 | 0.0004 | 0.0014 | 0.0016 | arcsec |
| luck-pillar start distance (to adjacent jie term) | 600 | 2.3858 | 6.0381 | 8.0065 | seconds |
| true solar time (14 cities, historical tz) | 840 | 0.0164 | 0.0481 | 0.0582 | minutes |

Largest true-solar-time gap: Urumqi 2025-10-30 08:09:28.

## Discrete agreement

- BaZi year and month pillars vs the Sun's JPL longitude: 1500 random instants, **0 month mismatches, 0 year mismatches**.
- Chinese lunar calendar, engine's zhdate vs an astronomical calendar built from JPL new moons and solar terms: **0 mismatches in 43830 days (1929-2048)**; 90 mismatches in 10227 days (1901-1928).
  First early-era differences (date, zhdate, astronomical): 1914-11-17 (1914, 10, 1, False) vs (1914, 9, 30, False); 1914-11-18 (1914, 10, 2, False) vs (1914, 10, 1, False); 1914-11-19 (1914, 10, 3, False) vs (1914, 10, 2, False)

## What this does and does not prove

- Proves: the astronomy (positions, solar terms, equation of time, angles, true solar time) and the year/month pillar boundaries agree with an independent source to the precision shown.
- Does not prove: school conventions (zi hour, day boundary, which clock to read) are the ones a given practitioner expects; those need practitioner review.
- Does not prove: tz-database offsets (trusted, shared with the oracle) or dates outside 1901-2049 (DE421 range).
- The 1901-1928 lunar differences are consistent with that era's calendar using a different time standard than UTC+8; this is the likely cause, not a verified one.
