"""Participant privacy — public APIs must not expose internal simulation metadata."""

from __future__ import annotations

from decimal import Decimal

from tests.conftest import join_participant

from app.services import news_service

FORBIDDEN_NEWS_KEYS = frozenset(
    {
        "sector_impacts",
        "stock_impacts",
        "effective_impact",
        "decay_rate",
        "confidence",
        "impact",
        "direction",
        "market_wide_impact_pct",
        "fundamental_impact_pct",
        "affected_tickers",
        "affected_sectors",
        "market_wide",
        "status",
        "is_released",
        "scheduled_at",
        "sector_impacts_json",
        "stock_impacts_json",
        "duration_minutes",
    }
)

FORBIDDEN_STATUS_KEYS = frozenset({"current_phase", "sim_speed_multiplier"})

ALLOWED_NEWS_KEYS = frozenset({"id", "title", "description", "released_at", "brief_points"})


def _release_sample_news(client) -> int:
    created = client.post(
        "/api/v1/admin/news",
        json={
            "title": "Major investment bank reports record quarterly profits.",
            "description": "Earnings beat expectations across the sector.",
            "direction": 1,
            "impact": "1.0",
            "confidence": "1.0",
            "duration_minutes": 60,
            "decay_rate": "0.05",
            "sector_impacts": {"financials": 4},
            "status": "draft",
        },
    )
    assert created.status_code == 200, created.text
    news_id = created.json()["id"]
    released = client.post(f"/api/v1/admin/news/{news_id}/release")
    assert released.status_code == 200, released.text
    return news_id


def test_public_news_list_has_no_internal_metadata(client):
    _release_sample_news(client)
    rows = client.get("/api/v1/news").json()
    assert rows, "expected at least one released news item"
    for item in rows:
        assert set(item.keys()) <= ALLOWED_NEWS_KEYS
        assert not FORBIDDEN_NEWS_KEYS.intersection(item.keys())
        for forbidden in ("EUPHORIA", "CRASH", "RECOVERY", "PHASE 1"):
            assert forbidden not in (item.get("title") or "").upper()
            assert forbidden not in (item.get("description") or "").upper()


def test_public_news_detail_has_no_internal_metadata(client):
    news_id = _release_sample_news(client)
    item = client.get(f"/api/v1/news/{news_id}").json()
    assert set(item.keys()) <= ALLOWED_NEWS_KEYS
    assert not FORBIDDEN_NEWS_KEYS.intersection(item.keys())


def test_market_status_has_no_phase_or_sector_impacts(client):
    _release_sample_news(client)
    body = client.get("/api/v1/market/status").json()
    assert "current_phase" not in body
    assert "sim_speed_multiplier" not in body
    assert "duration" in body
    assert "market_change_pct" in body
    latest = body.get("latest_news")
    if latest:
        assert "sector_impacts" not in latest
        assert set(latest.keys()) <= ALLOWED_NEWS_KEYS


def test_session_bootstrap_simulation_has_no_phase(client):
    _release_sample_news(client)
    _, auth = join_participant(client, "PrivacyUser")
    body = client.get("/api/v1/session/bootstrap", headers=auth).json()
    sim = body["simulation"]
    assert not FORBIDDEN_STATUS_KEYS.intersection(sim.keys())
    for row in body["released_news"]:
        assert set(row.keys()) <= ALLOWED_NEWS_KEYS
        assert not FORBIDDEN_NEWS_KEYS.intersection(row.keys())


def test_admin_simulation_status_still_includes_internal_fields(client):
    body = client.get("/api/v1/admin/simulation/status").json()
    assert "current_phase" in body


def test_participant_news_dict_shape(db_session):
    event = news_service.create_news(
        db_session,
        title="Headline only",
        description="Body text",
        direction=1,
        impact=Decimal("1"),
        confidence=Decimal("1"),
        sector_impacts={"financials": 4},
        status="draft",
    )
    released = news_service.release_news(db_session, event.id)
    public = news_service.participant_news_dict(released)
    assert set(public.keys()) == ALLOWED_NEWS_KEYS
    assert public["title"] == "Headline only"
    assert "sector_impacts" not in public
