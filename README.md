# TimeEngine v0.3.0

One deterministic call — `TimeEngine.resolve(dt, lat, lon, tz)` — returns a frozen,
JSON-serializable `TemporalSnapshot` covering: Western tropical chart, BaZi four pillars,
24 solar terms, lunar date, and Pythagorean numerology. The Chinese layer shares the
Western ephemeris (solar terms are root-found on apparent solar longitude, not lookup
tables), which is what makes cross-system synthesis honest later.

## License & ephemeris
- Code: AGPL-3.0. The full license text is in `LICENSE`; attribution and third-party
  terms are in `NOTICE.md`.
- pyswisseph is AGPL/commercial dual-licensed. **On the AGPL path the obligation is on
  the whole software project** — any application that links this library must also be
  AGPL-3.0 (or compatible). You cannot keep a downstream interpretive layer closed while
  using the free path. The commercial alternative is the Astrodienst Professional
  Edition at **CHF 700** one-time (99 years), which permits proprietary use. The choice
  must be made *before* you distribute or activate a public service. See `NOTICE.md`.
- Ephemeris fallback chain, explicit never silent: `SWISSEPH_PATH` data files -> Moshier
  (pyswisseph builtin, ~1 arcsec) -> analytic Meeus low-precision (tests only).

## Documented conventions (all configurable, all hashed into the cache key)
- BaZi year flips at Lichun (Sun at 315 deg), NOT Chinese New Year.
- **`MeridianPolicy.TRUE_SOLAR`** (default) reads the hour pillar from physical true
  solar time: equation of time + longitude correction vs the birth timezone's own
  meridian. **`MeridianPolicy.STANDARD_TIME`** reads the clock with daylight saving
  removed and no longitude correction. **`MeridianPolicy.CIVIL_CLOCK`** reads the clock
  exactly as displayed. These differ physically; the old `BEIJING` name is an alias of
  `STANDARD_TIME` (attribute only, not the string `"beijing"`).
- **`ZiHourRule`** has three values, covering all documented schools:
  - `DAY_FLIPS_AT_00` (default) — day pillar advances at 00:00; the 23:00-24:00 hour
    uses the same day's stem.
  - `DAY_FLIPS_AT_23` — day pillar advances at 23:00; the hour stem comes from the new day.
  - `LATE_ZI` — day pillar advances at 00:00, but the 23:00-24:00 hour stem is borrowed
    from the next day.
- Rulesets can be chosen per request: `POST /resolve` accepts a `ruleset` object.
- **`DayBoundary`** selects the date the day pillar's 60-day cycle is read from:
  `SOLAR` (default, the adjusted pillar time) or `CLOCK` (the birth civil clock date).
- The **lunar date** is read in a fixed UTC+8 (China Standard Time) frame — not the UTC
  calendar date and not the birth's local civil date.
- **Houses**: Placidus is undefined above the polar circle. When it fails the chart
  falls back to Porphyry (then whole sign, then equal) and reports it via
  `western.house_system_used` and `western.houses_degraded` — a fallback is never silent.

## BaZi depth
Every snapshot carries `bazi_depth`: day master and element, per-pillar hidden stems and ten
gods, element counts, and luck pillars. Luck direction is chosen by, in order: `luck_direction`
(`forward`/`backward`), the classical rule if `gender` (`male`/`female`) is given, otherwise both
directions are returned with `basis: both_shown`. Hidden-stem weights are one common
assignment (`HIDDEN_WEIGHTS`); override them if your school differs.

## Western depth
Every snapshot carries `speeds` (geocentric ecliptic-longitude rate, deg/day),
`retrograde` flags, the lunar nodes (`north_node` / `south_node`, true node by
default — the modern Western standard), and `aspects`: every major aspect
(conjunction, sextile, square, trine, opposition) between the ten planets,
ascendant, MC and north node, tightest first. Each aspect reports the signed
`deviation` from exactness and a `phase`: applying/separating from the bodies'
relative motion, exact within 3 arcminutes, unknown when a speed is missing
(chart angles carry none). Default orbs are one common modern assignment
(8/4/6/8/8 degrees); override them per school. The south node is excluded on
purpose — it always opposes the north node, so aspecting it would duplicate
every nodal aspect.

## Validation
Measured agreement with Skyfield + JPL DE421 is in `VALIDATION_REPORT.md`
(regenerate with `python -m validation.run_report`). Summary: planets within 1 arcsec
(Moon 2.5), solar terms within 5 s, true solar time within 0.06 min, 0 year/month pillar
mismatches in 1,500 instants. It does not validate school conventions or dates outside 1901-2049.

## Run
```bash
pip install -r requirements.txt
pytest
uvicorn timeengine.api:app --reload   # POST /resolve, GET /health
```

## Deliberately not built yet
Postgres cache (InMemoryCache behind CacheBackend protocol — swap when a second process
needs it), Docker, auth, the interpretive layer (the actual product moat — this repo is
plumbing, not product).

See `CHANGELOG.md` for the 0.2.x fixes and the API renames they introduced.
