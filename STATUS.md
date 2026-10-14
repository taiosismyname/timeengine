# TimeEngine — project status (Pip's working copy)

Home: `~/workspace/timeengine/` — extracted from `~/workspace/user/files/timeengine-0.3.0.zip`
on 2026-10-06. This is now the single continuity home for the project: no more
work scattered across stalling agent sessions. Venv at `.venv/` (python3).

## Where things stand (v0.3.0)

- `TimeEngine.resolve(dt, lat, lon, tz)` returns one frozen JSON snapshot:
  Western tropical chart, BaZi four pillars + depth, 24 solar terms, lunar date,
  Pythagorean numerology.
- v0.3.0 finished the BaZi depth slice: day master + element, hidden stems,
  ten gods, element counts, 8 luck pillars. Luck direction does NOT require a
  binary gender (explicit direction, classical rule if gender given, else both).
- Validation: Skyfield + JPL DE421 oracle, fully independent of the engine.
  Planets within 1 arcsec, solar terms within 5 s. Report in VALIDATION_REPORT.md.

## Roadmap (narrow-first)

1. **Western depth** (DONE 2026-10-06, v0.4.0): aspects (orbs, applying/separating),
   retrograde flags, lunar nodes (true node default). New `aspects.py` (pure
   arithmetic) + extended `western.py`; 16 new tests, 65 pass + 1 skipped.
2. **Interpretive / synthesis layer** (DRAFT v0.1 written 2026-10-06):
   `QUEER_RULEBOOK.md` — audit of every classical rule that assumes gender or
   heteronormative frames (BaZi spouse/children stars, Venus/Mars, Sun/Moon
   parental axis, 7th house, sign polarity, tarot courts/Lovers), reframe
   proposals, the synthesis order (say it once), and open questions for Tai.
   Still needs: Tai's calls on the open questions + a practitioner's eyes on
   the BaZi spouse-star reframe before it ships.
3. **Tarot layer**: separate daily/situational pull on top of the natal reading.
4. Deferred: place search (thin geocoding call for MVP), Postgres cache, Docker, auth.

## Open decisions

- **License (TIME-SENSITIVE, before any public launch):** pyswisseph is AGPL /
  commercial dual-license. AGPL path forces the whole app incl. the interpretive
  layer open. Commercial Professional Edition is CHF 700 one-time (re-verify at
  https://www.astro.com/swisseph/swephprice_e.htm before purchase). Recommendation:
  pay the CHF 700 unless the strategy is deliberately open-source. Clean-room
  ephemeris swap is the expensive alternative; NOT started.
- **Queer rulebook**: which classical rules to reframe and how — needs Tai's call,
  ideally with practitioner input. Starter list: gendered spouse stars (BaZi),
  luck direction (done), heteronormative spouse-palace framing.

## Product vision (Tai, 2026-10-06)

Unify the universal non-theistic systems — Western astrology, Chinese zodiac/BaZi,
numerology — "matched up" into the most accurate natal reading possible, then layer
a tarot reading on top for day-to-day circumstance. Start with the LGBT community:
the classical rules assume heteronormative frames and apply differently.
