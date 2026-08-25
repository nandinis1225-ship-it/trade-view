"""Participant-safe API response models — no internal simulation metadata."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ParticipantNewsRead(BaseModel):
    id: int
    title: str
    description: str = ""
    released_at: str | None = None
    brief_points: list[str] | None = None


class ParticipantStockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    company_name: str
    last_traded_price: Decimal
    percent_change: str | None = None
    sector_id: int | None = None
    sector_slug: str | None = None
    sector_name: str | None = None
    is_open: bool = True
    is_halted: bool = False


class ParticipantIPORead(BaseModel):
    id: int
    company_name: str
    ticker: str
    issue_price: str
    lot_size: int
    maximum_lots_per_user: int
    status: str


class ParticipantIPOApplicationRead(BaseModel):
    id: int
    ipo_id: int
    requested_lots: int
    allocated_lots: int
    status: str


class ParticipantSimulationStatus(BaseModel):
    status: str
    elapsed_sec: float
    elapsed: str
    duration_sec: float
    duration: str
    trading_enabled: bool = False
