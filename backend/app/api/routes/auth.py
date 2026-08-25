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
from app.services.pin_service import verify_event_pin

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
        requested_name = payload.display_name.strip()
        existing = db.scalar(select(Trader).where(Trader.session_id == session_id))
        if existing is not None:
            if settings.participant_event_mode and existing.identity_locked and existing.name != requested_name:
                raise HTTPException(
                    status_code=403,
                    detail="participant identity is locked — name cannot be changed",
                )
            trader = existing
            display_name = existing.name
        elif settings.participant_event_mode:
            locked_human = db.scalar(
                select(Trader).where(
                    Trader.trader_type == TraderType.HUMAN,
                    Trader.identity_locked.is_(True),
                )
            )
            if locked_human is not None:
                if locked_human.session_id and locked_human.session_id != session_id:
                    raise HTTPException(
                        status_code=403,
                        detail="a participant identity already exists on this machine",
                    )
                trader = locked_human
                if trader.name != requested_name:
                    raise HTTPException(
                        status_code=403,
                        detail="participant identity is locked — name cannot be changed",
                    )
                trader.session_id = session_id
                db.commit()
                db.refresh(trader)
                display_name = trader.name
            else:
                humans = list(
                    db.scalars(
                        select(Trader).where(Trader.trader_type == TraderType.HUMAN)
                    ).all()
                )
                if humans and humans[0].identity_locked:
                    trader = humans[0]
                    if trader.name != requested_name:
                        raise HTTPException(
                            status_code=403,
                            detail="participant identity is locked — name cannot be changed",
                        )
                    trader.session_id = session_id
                    db.commit()
                    db.refresh(trader)
                    display_name = trader.name
                elif humans and not humans[0].identity_locked and humans[0].session_id is None:
                    trader = humans[0]
                    trader.session_id = session_id
                    trader.name = requested_name
                    trader.identity_locked = True
                    db.commit()
                    db.refresh(trader)
                    display_name = trader.name
                else:
                    trader = trader_service.create_trader(
                        db,
                        TraderCreate(
                            name=requested_name,
                            trader_type=TraderType.HUMAN,
                            session_id=session_id,
                        ),
                    )
                    trader.identity_locked = True
                    db.commit()
                    db.refresh(trader)
                    display_name = trader.name
        else:
            humans = list(
                db.scalars(
                    select(Trader).where(Trader.trader_type == TraderType.HUMAN)
                ).all()
            )
            if humans:
                trader = humans[0]
                trader.session_id = session_id
                trader.name = requested_name
                db.commit()
                db.refresh(trader)
            else:
                trader = trader_service.create_trader(
                    db,
                    TraderCreate(
                        name=requested_name,
                        trader_type=TraderType.HUMAN,
                        session_id=session_id,
                    ),
                )
            display_name = requested_name
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
    if not (settings.event_pin_hash or settings.event_pin):
        raise HTTPException(status_code=503, detail="event pin not configured")
    if not verify_event_pin(payload.pin):
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
