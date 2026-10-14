# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Independent validation of TimeEngine against Skyfield + JPL DE421.

Test-only. Nothing here is imported by the engine, so Skyfield (MIT) and the JPL
ephemeris data (public domain) never become runtime dependencies.
"""
