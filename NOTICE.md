# NOTICE

## Project

TimeEngine — unified Western astrology + BaZi + solar terms + lunar + numerology core.

Copyright (C) 2026 TimeEngine contributors.

This program is free software: you can redistribute it and/or modify it under the
terms of the GNU Affero General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

The full license text is in the `LICENSE` file in this repository.

## Third-party components

### Swiss Ephemeris / pyswisseph

This project depends on the Swiss Ephemeris (`pyswisseph`), dual-licensed by
Astrodienst AG under AGPL-3.0 or the Swiss Ephemeris Professional License.

**If you use the AGPL path, the obligation is on the whole software project, not
just this library.** Astrodienst's published terms state that a developer choosing
AGPL "must fulfill the conditions of that license, which includes the obligation to
place his or her whole software project under the AGPL or a compatible license,"
and that the choice "must be made before the software developer distributes software
containing parts of Swiss Ephemeris to others, and before any public service using
the developed software is activated."

Consequences to be aware of before shipping:

- Any application that links to this library is part of the same software project
  and must itself be released under AGPL-3.0 or a compatible license. You cannot
  keep a downstream application (e.g. an interpretive layer) closed-source while
  using this library on the AGPL path.
- The commercial alternative is the Swiss Ephemeris Professional Edition, an
  unlimited license currently priced at **CHF 700** one-time, valid 99 years,
  purchased from Astrodienst against a signed contract. It permits proprietary use
  and the "Swiss Ephemeris Inside" label.
- Verify current terms and pricing at https://www.astro.com/swisseph/swephinfo_e.htm
  and https://www.astro.com/swisseph/swephprice_e.htm before relying on them.

### zhdate

Optional lunar-calendar adapter (`zhdate`), used under its own license.
