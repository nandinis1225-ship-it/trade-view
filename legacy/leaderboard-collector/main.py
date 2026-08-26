"""Central leaderboard collector — SQLite DB only, no simulation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

API_PREFIX = "/api/v1"
DATA_DIR = Path(os.environ.get("TRADEVERSE_COLLECTOR_DATA", ".")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "leaderboard.db"
DATABASE_URL = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"


class Base(DeclarativeBase):
    pass


class ParticipantSnapshot(Base):
    __tablename__ = "participant_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(index=True)
    session_id: Mapped[str] = mapped_column(unique=True, index=True)
    cash: Mapped[str] = mapped_column(default="0")
    holdings_json: Mapped[str] = mapped_column(default="[]")
    realized_pnl: Mapped[str] = mapped_column(default="0")
    unrealized_pnl: Mapped[str] = mapped_column(default="0")
    portfolio_value: Mapped[str] = mapped_column(default="0")
    return_pct: Mapped[str] = mapped_column(default="0")
    trade_count: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[str] = mapped_column(default="")


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


class SnapshotPayload(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=64)
    cash: str = "0"
    holdings: list[dict] = Field(default_factory=list)
    realized_pnl: str = "0"
    unrealized_pnl: str = "0"
    portfolio_value: str = "0"
    return_pct: str = "0"
    trade_count: int = 0
    timestamp: str | None = None


def compute_score(return_pct: str, trade_count: int) -> Decimal:
    return Decimal(return_pct) + (Decimal(str(trade_count)) * Decimal("0.01"))


app = FastAPI(title="TRADEVERSE Leaderboard Collector", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get(f"{API_PREFIX}/health")
def health() -> dict:
    ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            ok = True
    except Exception:
        pass
    return {"status": "ok" if ok else "degraded", "db": str(DB_PATH)}


@app.post(f"{API_PREFIX}/snapshot")
def upsert_snapshot(payload: SnapshotPayload) -> dict:
    now = payload.timestamp or datetime.now(timezone.utc).isoformat()
    with SessionLocal() as db:
        row = db.scalar(
            select(ParticipantSnapshot).where(ParticipantSnapshot.session_id == payload.session_id)
        )
        if row is None:
            row = ParticipantSnapshot(
                display_name=payload.display_name,
                session_id=payload.session_id,
            )
            db.add(row)
        row.display_name = payload.display_name
        row.cash = payload.cash
        row.holdings_json = json.dumps(payload.holdings)
        row.realized_pnl = payload.realized_pnl
        row.unrealized_pnl = payload.unrealized_pnl
        row.portfolio_value = payload.portfolio_value
        row.return_pct = payload.return_pct
        row.trade_count = payload.trade_count
        row.updated_at = now
        db.commit()
    return {"ok": True, "session_id": payload.session_id}


@app.get(f"{API_PREFIX}/leaderboard")
def leaderboard() -> list[dict]:
    with SessionLocal() as db:
        rows = list(db.scalars(select(ParticipantSnapshot)).all())
    scored = []
    for row in rows:
        score = compute_score(row.return_pct, row.trade_count)
        scored.append(
            {
                "display_name": row.display_name,
                "session_id": row.session_id,
                "portfolio_value": row.portfolio_value,
                "return_pct": row.return_pct,
                "realized_pnl": row.realized_pnl,
                "unrealized_pnl": row.unrealized_pnl,
                "trade_count": row.trade_count,
                "score": str(score),
                "updated_at": row.updated_at,
            }
        )
    scored.sort(key=lambda r: Decimal(r["score"]), reverse=True)
    for i, row in enumerate(scored, start=1):
        row["rank"] = i
        row["name"] = row["display_name"]
    return scored


@app.get("/")
def root() -> dict:
    return {"service": "leaderboard-collector", "health": f"{API_PREFIX}/health"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("COLLECTOR_PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
