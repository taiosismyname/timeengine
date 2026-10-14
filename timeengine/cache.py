# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""Cache seam: in-memory now, Postgres later without touching the engine."""
from __future__ import annotations
from typing import Protocol

class CacheBackend(Protocol):
    def get(self, key: str): ...
    def set(self, key: str, value) -> None: ...

class InMemoryCache:
    def __init__(self) -> None:
        self._d: dict = {}
    def get(self, key: str):
        return self._d.get(key)
    def set(self, key: str, value) -> None:
        self._d[key] = value
