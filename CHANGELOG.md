# Changelog

## 0.4.0

Western depth (`aspects.py`, extended `western.py`). Pure arithmetic on the
longitudes the engine already computes; no new ephemeris dependency.

- Daily speeds for all ten planets (Swiss Ephemeris only fills the speed slots
  when `FLG_SPEED` is set; positions are unaffected), retrograde flags, and the
  lunar nodes (true node by default, the modern Western standard; the south
  node is derived as exactly opposite).
- Every major aspect (conjunction, sextile, square, trine, opposition) between
  the ten planets, ascendant, MC and north node, tightest first, with signed
  deviation and phase: applying/separating read from relative motion, exact
  within 3 arcminutes, unknown when a speed is missing (chart angles carry
  none). The south node is deliberately excluded: it always opposes the north
  node, so aspecting it would duplicate every nodal aspect.
- Default orbs are one common modern assignment (8/4/6/8/8 degrees); schools
  differ, so the orb table is a parameter, not a baked-in constant.
- `RULESET_VERSION` is now 0.4.0, so cached snapshots from earlier versions are
  not reused.
- Tests: hand-computed aspect and phase cases (including the subtlety that a
  growing separation is only applying below the exact angle), Sun/Moon never
  retrograde across a year-long sweep, retrograde flag == speed sign, nodes
  opposite, every snapshot aspect within orb with unique pairs, degraded path
  reports the missing depth explicitly.

## 0.3.0

BaZi depth (`bazi_depth.py`), pure tables and arithmetic with no ephemeris dependency.
Builds on a draft from the previous session, which stopped before it was wired in or tested.

- Hidden stems (藏干) with primary/middle/residual roles and weights, ten gods (十神) for every
  stem and hidden stem, element counts, and eight luck pillars (大运) with start age and year.
- New `bazi_depth` block in every snapshot; new `gender` and `luck_direction` request fields.
- Changes to the draft: the day pillar's stem is labelled 日主 (day master), not 比肩; luck
  direction does not require a binary gender (explicit direction, or the classical rule if a
  classical gender is given, or both directions returned when neither is); start year is
  computed from the actual start moment.
- Tests: ten gods match the canonical 甲/乙 rows and appear exactly 10 times over all pairs;
  hidden-stem table matches the textbook for all 12 branches; direction rule for all four
  year-polarity x gender combinations; 1991 Charlotte chart hand-checked; luck start distance
  validated against independent JPL solar-term roots (max error 8 s).
- `RULESET_VERSION` is now 0.3.0, so cached snapshots from earlier versions are not reused.

### Open questions for a practitioner
- Hidden-stem weights (0.6/0.3/0.1 etc.) are one common choice; schools differ.
- Start age uses 3 days = 1 year with no rounding; some schools round, some use a
  nominal-age (虚岁) convention.
- Whether to read the luck-pillar direction from the year-stem polarity at all for people
  who do not map to the classical male/female rule is a product decision, not a computation.

## 0.2.2

Validation suite (no engine behaviour changes).

- `validation/`: an independent oracle on Skyfield + JPL DE421, sharing no ephemeris, root
  finder or formula code with the engine. Test-only: install with
  `pip install -r requirements-validation.txt`.
- `tests/test_validation.py`: planets, 24 solar terms, equation of time, ascendant/MC, end-to-end
  true solar time across 14 cities and historical time zones, year/month pillars vs the Sun's
  longitude, and the lunar calendar vs an astronomical Chinese calendar built from JPL new moons.
- `tests/test_bazi_structure.py`: textbook 五鼠遁 / 五虎遁 tables, day cycle arithmetic, known year
  pillars, exact flips at every jie term, Lichun and two-hour edges.
- `python -m validation.run_report` writes `VALIDATION_REPORT.md`. Slow sweeps are marked
  `slow`; run `pytest -m "not slow"` for the 10-second subset.
- Result on the first run: no engine defects found. The one open item is the 1901-1928 lunar
  calendar, where zhdate differs from astronomy on ~0.9% of days.

## 0.2.1

Review pass on 0.2.0. Each item has a regression test (`test_v021_*`).

1. **`STANDARD_TIME` now actually removes daylight saving.** In 0.2.0 it read the clock as
   displayed, so an 11:30 EDT birth stayed 午 although standard time is 10:30 (巳). The
   as-displayed reading is kept as the new `MeridianPolicy.CIVIL_CLOCK`.
2. **`LATE_ZI` judges the 23:00-24:00 window on the hour's own clock.** With
   `DayBoundary.CLOCK` + `TRUE_SOLAR` it used the civil clock, so an 亥 hour could get a
   next-day stem. `BaziChart.frame_conflict` now flags births where the day-boundary clock
   and the hour clock disagree on the date or the zi window.
3. **Lunar conversion no longer crashes outside 1900-2100.** It returns a degraded lunar
   block and the rest of the chart still resolves (was a 500 for e.g. 1850 or 2150).
4. **API validation.** Unknown timezone and out-of-range lat/lon return 422 (were 500 /
   silently accepted). `ValueError` from the engine returns 400.
5. **Rulesets are selectable per request** (`ruleset` in the POST body and an optional
   argument to `TimeEngine.resolve`); the conventions were previously only settable in code.
6. **Polar house fallback order is Porphyry -> whole sign -> equal** (Porphyry is the
   closest quadrant system to Placidus).
7. Latitude/longitude are rounded before computing, so the cache key and the result agree.
8. `NOTICE.md`: removed an unused `sxtwl` entry.

### Known limits (not fixed here)
- Numerology reads A-Z only: accented letters are dropped and non-Latin names return `None`.
- The ephemeris runs on Moshier unless `SWISSEPH_PATH` points at data files.
- No independent cross-check against reference software yet; tests are self-consistency
  plus hand-derived anchors.

## 0.2.0

Six correctness fixes, each with a regression test in `tests/test_known_charts.py`.

1. **Cache key now includes the names.** `make_cache_key` takes `birth_name` and
   `chosen_name` (canonicalised to strip/lowercase, matching how numerology reads them).
   Previously two different people at the same date and place shared one cached snapshot,
   so the second person received the first person's numerology.

2. **Lunar date is read in fixed UTC+8 (China Standard Time).** Previously the engine
   passed the UTC calendar date to the lunar provider, so a Shanghai birth just after
   midnight read the previous lunar day, and a New York evening birth read the next one.
   The Chinese calendar's civil day boundary is China Standard Time; historical Chinese
   DST (1986-1991) does not move the published lunar date.

3. **`MeridianPolicy` redefined.** `LOCAL`/`BEIJING` were physically identical outside
   China's DST years — `BEIJING` converted to Shanghai time but still subtracted 120 deg,
   and the two corrections cancelled. `BEIJING` is now an alias of `STANDARD_TIME`, a
   genuinely different school that reads the civil clock with no longitude correction.
   `LOCAL` is renamed `TRUE_SOLAR` (unchanged behaviour).

4. **Placidus polar fallback.** `swe.houses_ex` raises above the polar circle, which
   surfaced as an unhandled 500. `western.chart_positions` now walks a fallback chain
   (whole sign -> Porphyry -> equal) and reports the substitution through the new
   structured fields `WesternChartModel.house_system_used` and
   `WesternChartModel.houses_degraded`, plus `house_cusps`.

5. **Third zi-hour rule added.** `ZiHourRule.LATE_ZI`: the day pillar advances at 00:00
   (as in `DAY_FLIPS_AT_00`) but the 23:00-24:00 hour stem is drawn from the next day.
   The two previous rules could not express this documented school.

6. **`DayBoundary` option added.** The day pillar previously always read its calendar
   date from the true-solar-time frame. `DayBoundary.SOLAR` (default) keeps that;
   `DayBoundary.CLOCK` reads the birth civil clock date. It is part of `RulesetConfig`
   and therefore hashed into the cache key.

### Breaking changes

- `MeridianPolicy.LOCAL` -> `MeridianPolicy.TRUE_SOLAR`.
- `MeridianPolicy.BEIJING` now means the standard-time school (still accepted as an alias).
- `BaziChart.true_solar_time` -> `BaziChart.effective_time`.
- `BaziChart.tst_correction_minutes` -> `BaziChart.correction_minutes`.
- New `BaziChart` fields: `time_basis`, `day_boundary`.
- New `WesternChartModel` fields: `house_system_used`, `houses_degraded`, `house_cusps`.
- `RulesetConfig` gains `day_boundary`; `RULESET_VERSION` is `0.2.0`, so every cached
  snapshot is invalidated by the ruleset hash.

### Documentation

- `LICENSE` now contains the full AGPL-3.0 text (it was a stub).
- `NOTICE.md` records the Swiss Ephemeris terms, including that the AGPL obligation
  covers the whole software project and that the Professional License is CHF 700.
