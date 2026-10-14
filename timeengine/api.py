# Copyright (C) 2026 Tai Osborne
# SPDX-License-Identifier: AGPL-3.0-only
# This file is part of TimeEngine. See LICENSE for the full license text.

"""FastAPI wrapper. Run: uvicorn timeengine.api:app --reload"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from typing import Literal
from pydantic import BaseModel, Field, field_validator

from .engine import TimeEngine
from .models import RulesetConfig
from . import ephem

app = FastAPI(title="TimeEngine", version="0.4.0")
engine = TimeEngine()

class ResolveRequest(BaseModel):
    dt: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str
    birth_name: str | None = None
    chosen_name: str | None = None
    ruleset: RulesetConfig | None = None   # per-request school selection
    # Luck-pillar direction. Give luck_direction explicitly, or the classical gender used by
    # the traditional rule, or neither (both directions are returned).
    gender: Literal["male", "female"] | None = None
    luck_direction: Literal["forward", "backward"] | None = None

    @field_validator("tz")
    @classmethod
    def _tz_exists(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            raise ValueError(f"unknown IANA timezone: {v}")
        return v

@app.get("/health")
def health():
    return {"status": "ok", "ephemeris_mode": ephem.ephemeris_mode()}

@app.post("/resolve")
def resolve(req: ResolveRequest):
    try:
        snap = engine.resolve(req.dt, req.lat, req.lon, req.tz,
                              req.birth_name, req.chosen_name, req.ruleset,
                              req.gender, req.luck_direction)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    return snap.model_dump(mode="json")
