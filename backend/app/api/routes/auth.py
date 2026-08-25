"""Participant and admin authentication."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, enforce_rate_limit
from app.models import Trader
from app.models.enums import TraderType
from app.schemas import TraderCreate
from app.services import trader_service

router = APIRouter(prefix="/auth", tags=["auth"])


class JoinRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)


class JoinResponse(BaseModel):
    trader_id: int
    display_name: str
    access_token: str
    token_type: str = "bearer"
    session_id: str | None = None


class PinValidateRequest(BaseModel):
    pin: str = Field(min_length=1, max_length=32)


class PinValidateResponse(BaseModel):
    ok: bool = True


class AdminLoginRequest(BaseModel):
    secret: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/join", response_model=JoinResponse)
def join_session(
    request: Request,
    payload: JoinRequest,
    db: Session = Depends(get_db),
) -> JoinResponse:
    enforce_rate_limit(request)
    settings = get_settings()

    if settings.local_instance_mode:
        session_id = (payload.session_id or "").strip() or str(uuid.uuid4())
        existing = db.scalar(select(Trader).where(Trader.session_id == session_id))
        if existing is not None:
            trader = existing
        else:
            humans = list(
                db.scalars(
                    select(Trader).where(Trader.trader_type == TraderType.HUMAN)
                ).all()
            )
            if humans:
                trader = humans[0]
                trader.session_id = session_id
                trader.name = payload.display_name.strip()
                db.commit()
                db.refresh(trader)
            else:
                trader = trader_service.create_trader(
                    db,
                    TraderCreate(
                        name=payload.display_name.strip(),
                        trader_type=TraderType.HUMAN,
                        session_id=session_id,
                    ),
                )
        display_name = payload.display_name.strip()
    else:
        suffix = secrets.token_hex(3)
        trader = trader_service.create_trader(
            db,
            TraderCreate(name=f"{payload.display_name}-{suffix}", trader_type=TraderType.HUMAN),
        )
        display_name = payload.display_name
        session_id = None

    token = create_access_token(
        subject=str(trader.id),
        role="participant",
        trader_id=trader.id,
    )
    return JoinResponse(
        trader_id=trader.id,
        display_name=display_name,
        access_token=token,
        session_id=trader.session_id or session_id,
    )


@router.post("/validate-pin", response_model=PinValidateResponse)
def validate_event_pin(
    request: Request,
    payload: PinValidateRequest,
) -> PinValidateResponse:
    """Validate event PIN locally — no network sync."""
    enforce_rate_limit(request)
    settings = get_settings()
    if not settings.participant_event_mode:
        return PinValidateResponse(ok=True)
    expected = (settings.event_pin or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="event pin not configured")
    if payload.pin.strip() != expected:
        raise HTTPException(status_code=403, detail="invalid event pin")
    return PinValidateResponse(ok=True)


@router.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(
    request: Request,
    payload: AdminLoginRequest,
) -> AdminLoginResponse:
    """Exchange ADMIN_SECRET for an admin bearer token."""
    from app.core.config import get_settings

    enforce_rate_limit(request)
    settings = get_settings()
    if payload.secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail="invalid admin secret")
    token = create_access_token(subject="admin", role="admin")
    return AdminLoginResponse(access_token=token)


@router.post("/admin/token", response_model=AdminLoginResponse)
def admin_token_from_secret(
    request: Request,
    payload: AdminLoginRequest,
) -> AdminLoginResponse:
    """Alias for admin login."""
    return admin_login(request, payload)
