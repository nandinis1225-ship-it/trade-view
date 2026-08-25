"""Public news + leaderboard + sector market views."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.orders import NewsPublicRead
from app.services import leaderboard_service, news_service, sector_service
from app.services.simulation_clock import participant_status_dict

router = APIRouter(tags=["market"])


@router.get("/market/status")
def market_status(db: Session = Depends(get_db)) -> dict:
    """Public market dashboard data — no checkpoint spoilers or internal metadata."""
    clock = participant_status_dict(db)
    change = sector_service.market_change_pct(db)
    events = news_service.list_news(db, released_only=True)
    latest = None
    if events:
        latest = news_service.participant_news_dict(events[0])
    return {
        "elapsed": clock["elapsed"],
        "status": clock["status"],
        "market_change_pct": str(change),
        "latest_news": latest,
    }


@router.get("/news", response_model=list[NewsPublicRead])
def public_news(db: Session = Depends(get_db)) -> list[NewsPublicRead]:
    return [
        NewsPublicRead.model_validate(news_service.participant_news_dict(event))
        for event in news_service.list_news(db, released_only=True)
    ]


@router.get("/news/{news_id}", response_model=NewsPublicRead)
def news_detail(news_id: int, db: Session = Depends(get_db)) -> NewsPublicRead:
    event = news_service.get_news(db, news_id)
    if event is None or not event.is_released:
        raise HTTPException(404, "news not found")
    return NewsPublicRead.model_validate(news_service.participant_news_dict(event))


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)) -> list[dict]:
    # Public: rank, name, return%, portfolio value — no private order details
    rows = leaderboard_service.compute_leaderboard(db)
    return [
        {
            "rank": r["rank"],
            "trader_id": r["trader_id"],
            "name": r["name"],
            "portfolio_value": str(r["portfolio_value"]),
            "return_pct": str(r["return_pct"]),
            "trade_count": r["trade_count"],
        }
        for r in rows
    ]


@router.get("/market/sectors")
def market_sectors(db: Session = Depends(get_db)) -> list[dict]:
    """Stocks grouped by sector with performance summary."""
    return sector_service.sector_summary(db)
